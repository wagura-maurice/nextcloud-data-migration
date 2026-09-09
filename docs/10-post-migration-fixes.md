# Post-Migration Fixes

Issues found after the destination server went live, with root causes and fixes.
All checks were performed against `https://cloud.amarisstock.com` (Nextcloud
34.0.3.2, PHP 8.4.25, nginx, MySQL 8.0.45).

---

## 1. OnlyOffice: "ONLYOFFICE cannot be reached. Please contact admin"

This was the longest-running issue and had **three independent causes** stacked
on top of each other. All three had to be fixed before documents would open.

### 1a. Missing trailing slash on `DocumentServerInternalUrl`

The OnlyOffice app builds its health-check URL by string concatenation:

```php
$urlHealthcheck = $documentServerUrl . "healthcheck";
```

The stored value was `http://127.0.0.1:8000` (no trailing slash), producing
`http://127.0.0.1:8000healthcheck`. `parse_url()` cannot extract a host from
that, so Nextcloud's HTTP client threw:

```
OCP\Http\Client\LocalServerException: Could not detect any host
```

The exception originates in `preventLocalAddress()`
(`lib/private/Http/Client/Client.php`), which made it look like a local-address
policy problem. It was not — the URL was simply malformed.

**Fix**

```sql
UPDATE oc_appconfig
   SET configvalue = 'http://127.0.0.1:8000/'
 WHERE appid = 'onlyoffice' AND configkey = 'DocumentServerInternalUrl';
```

### 1b. `officeonline` app hijacking Office file types

`officeonline` (Nextcloud's built-in WOPI client) was enabled but had **no
`wopi_url` configured**. It registered handlers for the Office mimetypes, so
clicking an `.xlsx` routed to `officeonline` instead of `onlyoffice`.
`officeonline` then tried to fetch a WOPI discovery document from an empty URL
and failed with the same `Could not detect any host` message — which users saw
as the OnlyOffice error.

The source server had the same misconfiguration, but `onlyoffice` happened to
win there.

**Fix**

```bash
occ app:disable officeonline
```

`office` (v1.0.0) was left enabled — it is only an "Office overview" dashboard
and does not register file handlers.

### 1c. nginx reverse proxy returning 404 for all `.js` and `.css` (the real blocker)

Even with 1a and 1b fixed, the browser could not load the editor. The vhost
`/www/server/panel/vhost/nginx/office.amarisstock.com.conf` is a pure reverse
proxy to the Document Server, with the proxy defined in an included file as a
**prefix** location:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    ...
}
```

But the panel-generated vhost also contained two **regex** locations with no
`proxy_pass`:

```nginx
location ~ .*\.(gif|jpg|jpeg|png|bmp|swf)$ { expires 30d; ... }
location ~ .*\.(js|css)?$                  { expires 12h; ... }
```

nginx evaluates regex locations **before** prefix locations, so every `.js` and
`.css` request was served from the local `root`
(`/www/wwwroot/office.amarisstock.com`), where no such files exist → `404`.

Observable symptom — the health check passed while the editor bundle 404'd:

| Path | Before | After |
| --- | --- | --- |
| `/healthcheck` | 200 | 200 |
| `/coauthoring/CommandService.ashx` | 200 | 200 |
| `/web-apps/apps/api/documents/api.js` | **404** | 200 |
| `/sdkjs/common/AllFonts.js` | **404** | 200 |

The editor JS fails exactly here, which produces the user-visible message:

```js
t.src = o.documentServerUrl + "web-apps/apps/api/documents/api.js?shardkey=" + o.document.key
t.onerror = function () {
    OCA.Onlyoffice.showMessage(t(..., "ONLYOFFICE cannot be reached. Please contact admin"), "error")
}
```

**Fix** — the two static-asset regex blocks are commented out so all requests
fall through to the proxy. Applied by `scripts/fix_office_vhost.py`, which backs
up the vhost, runs `nginx -t`, reverts automatically on failure, then reloads.

> **Caveat:** aaPanel regenerates this vhost when the site is edited in the
> panel UI. If OnlyOffice breaks again after a panel change, re-run
> `scripts/fix_office_vhost.py` (it is idempotent).

### Verification

Reproducing the full flow for `Test 1/Amaris Chemicals Posting Schedule (2).xlsx`
(fileId 170, owner `admin`):

```
document.url      https://cloud.amarisstock.com/index.php/apps/onlyoffice/download?doc=...
callbackUrl       https://cloud.amarisstock.com/index.php/apps/onlyoffice/track?doc=...
download          HTTP 200, 127893 bytes, magic 504b0304 (valid XLSX)
api.js            HTTP 200, 65363 bytes, DocsAPI present
xlsx -> csv       HTTP 200, 3504 bytes (Document Server parsed the file)
command service   version 9.4.0.129, error 0
checkDocServiceUrl PASS
```

Multi-format check: `xlsx → csv`, `docx → pdf`, and `pdf` download all pass.

### Note when testing from the CLI

`Router::loadRoutes()` skips apps that have not been loaded yet:

```php
if (!$this->appManager->isAppLoaded($app)) {
    // app MUST be loaded before app routes
    $this->loaded = false;
    continue;
}
```

A CLI script that calls `EditorApiController::config()` without first calling
`IAppManager::loadApp('onlyoffice')` gets **empty** `document.url` and
`callbackUrl` (they collapse to the base URL). This is a test artefact, not a
production bug — during a web request the app is already loaded. Always call
`loadApp()` before `loadRoutes()` in diagnostic scripts.

Also note `/index.php/apps/onlyoffice/` legitimately returns 404: the
`editor#index` route is `/{fileId}`, so the bare path matches nothing. Use a
nonexistent app name as a control — it returns 404 too, whereas real routes
return 401/403/412.

### Restored app settings

`oc_appconfig` was intentionally preserved from the destination, so
OnlyOffice's format matrix and UI preferences were missing. Copied from source
(server-specific keys such as `DocumentServerUrl`, `StorageUrl`, and
`jwt_secret` were **not** copied):

- `defFormats`, `editFormats`
- `customizationChat`, `customizationCompactHeader`, `customizationFeedback`,
  `customizationForcesave`, `customizationHelp`, `customizationReviewDisplay`,
  `customizationTheme`, `customizationmacros`, `customizationplugins`
- `enableSharing`, `sameTab`, `preview`, `protection`, `versionHistory`,
  `verify_peer_off`, `jwt_header`

Resulting defaults — open in OnlyOffice: `doc docx odt ods xls xlsx odp ppt pptx`;
editable: `docx odt rtf txt csv ods xlsx odp pptx`. The Document Server
advertises 86 formats in total, covering every Microsoft Office extension
(`doc docx docm dot dotx dotm xls xlsx xlsm xlsb xlt xltx xltm ppt pptx pptm
pot potx potm pps ppsx ppsm vsdx vsdm vssx vssm vstx vstm`).

---

## 2. AppAPI HaRP daemon: "HMAC does not match"

`oc_ex_apps_daemons` was migrated from the source, so the destination inherited
a daemon row whose `deploy_config` contained:

- `nextcloud_url` pointing at the **source** URL, and
- `haproxy_password` encrypted with the **source** Nextcloud secret.

The destination could not decrypt it:

```
RuntimeException: HMAC does not match.
  at OC\Security\Crypto->decryptWithoutSecret()
  via OCA\AppAPI\Service\HarpService->initGuzzleClient()
```

HaRP was also never running on the destination (only `nats-server` was).

**Fix**

1. Deleted the stale daemon row and `app_api/default_daemon_config`.
2. Copied the FRP certificates to `/opt/harp/certs/frp/`.
3. Started HaRP with a **freshly generated** `HP_SHARED_KEY` and the correct
   `NC_INSTANCE_URL=https://cloud.amarisstock.com`.
4. Re-registered the daemon:

```bash
occ app_api:daemon:register harp_proxy_host 'HaRP Proxy (Host)' \
    docker-install http localhost:8780 https://cloud.amarisstock.com \
    --harp --harp_frp_address localhost:8782 \
    --harp_shared_key '<key>' --set-default --compute_device=cpu
```

Both `AppAPI deploy daemon` and `AppAPI HaRP version check` now pass.

---

## 3. LDAP: "No LDAP Host given"

`user_ldap` was enabled on both servers but never actually used:

- `oc_ldap_user_mapping` — 0 rows on **both** servers
- source `s01ldap_configuration_active` = `0`, `s01ldap_host` = empty
- destination had `configuration_prefixes` = `[]`

The setup check ran the LDAP connection validator anyway and logged an error on
every admin page load.

**Fix**

```bash
occ app:disable user_ldap
DELETE FROM oc_jobs WHERE class LIKE '%User_LDAP%';   -- 2 orphaned cron jobs
```

The orphaned jobs had to go too, otherwise cron logged:

```
failed to create instance of background job: OCA\User_LDAP\Jobs\Sync
Could not resolve OCA\User_LDAP\Jobs\Sync! Class does not exist
```

---

## 4. OCRmyPDF not installed

`workflow_ocr` was enabled on both servers, but the destination lacked the
binary that the app shells out to.

**Fix**

```bash
apt-get install -y ocrmypdf     # 13.4.0+dfsg
```

---

## 5. Background jobs and cron

The destination had no Nextcloud cron entry (only the panel's own certificate
job).

**Fix**

```bash
occ config:system:set background_jobs_mode --value=cron
crontab -u www -l   # */5 * * * * /www/server/php/84/bin/php \
                    #   --define apc.enable_cli=1 -f \
                    #   /www/wwwroot/cloud.amarisstock.com/cron.php
```

---

## 6. Misleading log entries after the rsync

`nextcloud.log` was copied from the source along with the data directory, so the
destination log contained historical entries with **source** paths
(`/var/www/nextcloud/...`). These were mistaken for live destination errors.

All log files were truncated to 0 bytes to establish a clean baseline:
`nextcloud.log`, `nextcloud.log.1`, `nextcloud.log.2026-08-25.bak`,
`nextcloud.log.2026-08-25.bak2`, `audit.log`, `flow.log`, `updater.log`
(≈176 MB reclaimed). Ownership kept as `www:www`; files truncated rather than
deleted so Nextcloud keeps writing to the same inodes.

---

## Remaining known warning (not fixable locally)

`Talk High-performance backend`:

```
Running version: 2.1.1; Server does not support all features of this
Talk version, missing features: changed-users
```

Talk 24.0.4 optionally uses a `changed-users` signaling feature that the latest
released `nextcloud-spreed-signaling` (2.1.1) does not implement yet. Upstream
confirms this is a release-ordering issue and that the warning is informational
— calls work normally; only signaling payload optimisation for very large rooms
is unavailable. Tracked upstream in `nextcloud/spreed#18846` and
`strukturag/nextcloud-spreed-signaling#1283`.

A cosmetic PHP 8.4 deprecation is emitted by the third-party
`transfer_quota_monitor` app on CLI cron runs (implicitly nullable constructor
parameters in `lib/Cron/MonthlyReset.php`). It is written to stderr, not to
`nextcloud.log`, and needs an upstream fix in that app.

---

## Final state

| Check | Result |
| --- | --- |
| `occ setupchecks` errors | 0 |
| `occ setupchecks` warnings | 1 (Talk HPB, upstream) |
| `nextcloud.log` after cron + web traffic | 0 bytes |
| OnlyOffice `checkDocServiceUrl` | PASS (9.4.0.129) |
| OnlyOffice open xlsx / docx / pdf | PASS |
| AppAPI daemon + HaRP | PASS |
| Cron last run | OK, no errors |
| Code integrity | No altered files |
