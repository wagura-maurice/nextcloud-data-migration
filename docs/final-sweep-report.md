# Final Pre-Migration Sweep Report

> Date: 2026-09-09
> Performed: Deep sweep of both servers before live migration
> Status: **READY TO MIGRATE** with 2 issues to fix first

---

## Summary

| Check | Old Server | New Server | Status |
|-------|-----------|-----------|--------|
| Nextcloud version | 34.0.3.2 | 34.0.3.2 | OK |
| PHP version | 8.4.22 | 8.4.25 | OK (minor diff, compatible) |
| DB engine | MariaDB 10.6.23 | MySQL 8.0.45 | OK (tested compatible) |
| DB connection | Works | Works | OK |
| DB passwords in script | Match | Match | OK |
| Disk space | 27G free | 951G free | OK |
| Data dir size | 48G | 75M | OK |
| Web user | www-data (uid 33) | www (uid 1001) | OK |
| Web server | Apache | Nginx | OK |
| Maintenance mode | OFF | OFF | OK (will enable in Phase 1) |
| Cron | Every 5 min | Every 5 min | OK (will quiesce in Phase 1) |
| Docker | appapi-harp running | nats-server + onlyoffice-ds | OK |
| Signaling service | active | active | OK |
| app_api Docker access | YES (www-data in docker group) | **NO (www NOT in docker group)** | **ISSUE #1** |
| app_api daemon config | harp_proxy_host configured | Not configured | **ISSUE #2** |
| Encryption | Disabled | Disabled | OK |
| Federated shares | 0 | 0 | OK |
| External storage | 1 (collectives-user, internal) | 0 | OK (internal, migrates with DB) |

---

## Issue #1 — FIXED: New server `www` user now has Docker access

### Problem (FIXED 2026-09-09)
The old server's `www-data` user was in the `docker` group, allowing app_api to access `/var/run/docker.sock`.
The new server's `www` user was **NOT** in the `docker` group.

### Fix Applied
```bash
ssh root@164.68.104.123 'usermod -aG docker www && systemctl restart php-fpm-84'
```

### Verification
- `id www` now shows: `uid=1001(www) gid=1001(www) groups=1001(www),998(docker)`
- `www` can read AND write to `/var/run/docker.sock`
- `sudo -u www docker ps` works (lists nats-server, onlyoffice-ds)
- `occ app_api:daemon:list` runs without permission errors (returns "No registered daemon configs" — that's Issue #2, separate)

---

## Issue #2 — MEDIUM: New server has no app_api daemon configured

### Problem
The old server has an app_api daemon called `harp_proxy_host` (backed by the `appapi-harp` Docker container).
The new server has no daemon configured:

```
Old: app_api:daemon:list → harp_proxy_host
New: app_api:daemon:list → "No registered daemon configs."
```

### Impact
AppAPI-based apps won't have a backend daemon to run on. This doesn't block the migration itself,
but AppAPI apps won't work until the daemon is set up.

### Fix (after migration, during Phase 8 verification)
This requires setting up the `appapi-harp` Docker container on the new server and registering it:
```bash
# Pull and run the harp container on the new server
ssh root@164.68.104.123 'docker pull ghcr.io/nextcloud/nextcloud-appapi-harp:release'
ssh root@164.68.104.123 'docker run -d --name appapi-harp --restart always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -p 127.0.0.1:9000:9000 \
  ghcr.io/nextcloud/nextcloud-appapi-harp:release'

# Register the daemon with Nextcloud
ssh root@164.68.104.123 'cd /www/wwwroot/cloud.amarisstock.com && sudo -u www php occ app_api:daemon:register \
  --name harp_proxy_host \
  --label "Harp Proxy" \
  --host "localhost" \
  --nextcloud_url "https://cloud.amarisstock.com" \
  --haproxy_password "$(openssl rand -hex 16)"'
```

Note: The exact registration command depends on the app_api version. Check `occ app_api:daemon:register --help` for the correct syntax.

---

## Detailed Findings

### 1. System Resources

| Property | Old Server | New Server |
|----------|-----------|-----------|
| IP | 38.242.141.240 | 164.68.104.123 |
| Hostname | vmi2802244 | vmi3556218 |
| OS | Ubuntu 22.04.5 LTS | Ubuntu 22.04.5 LTS |
| CPU cores | 6 | 6 |
| RAM | 11G total, 7.8G free | 17G total, 14G free |
| Disk | 97G total, 27G free (73% used) | 969G total, 951G free (2% used) |
| Swap | 0B | 0B |
| Uptime | 15 days | 36 min |

### 2. Nextcloud

| Property | Old Server | New Server |
|----------|-----------|-----------|
| Version | 34.0.3.2 | 34.0.3.2 |
| Webroot | /var/www/nextcloud | /www/wwwroot/cloud.amarisstock.com |
| Data dir | /var/www/nextcloud/data | /www/wwwroot/cloud.amarisstock.com-data |
| Data dir size | 48G | 75M |
| Instance ID | oczvho61glg2 | ocmu0qdk9tdd |
| URL | https://cloud.amarissolutions.com | https://cloud.amarisstock.com |
| Trusted domains | localhost, vmi2802244.contaboserver.net, cloud.amarissolutions.com, mail.amarissolutions.com | localhost, cloud.amarisstock.com, 127.0.0.1 |
| mysql.utf8mb4 | true | (not set, but tables use utf8mb4) |
| Maintenance mode | false | false |
| needsDbUpgrade | false | false |

### 3. Database

| Property | Old Server | New Server |
|----------|-----------|-----------|
| Engine | MariaDB 10.6.23 | MySQL 8.0.45 |
| DB name | nextcloud | sql_cloud_amarisstock_com |
| DB user | nextcloud | sql_cloud_amarisstock_com |
| DB host | 127.0.0.1 | 127.0.0.1 |
| DB charset | utf8mb4 / utf8mb4_general_ci | utf8mb3 / utf8mb3_general_ci |
| Table count | 412 | 181 |
| Total rows | 789,169 | 6,534 |
| DB size | 245.1 MB | 8.8 MB |
| InnoDB buffer pool | 128 MB | 2048 MB |
| Max allowed packet | 16 MB | 1024 MB |
| SQL mode | STRICT_TRANS_TABLES,ERROR_FOR_DIVISION_BY_ZERO,NO_AUTO_CREATE_USER,NO_ENGINE_SUBSTITUTION | STRICT_TRANS_TABLES,NO_ENGINE_SUBSTITUTION |

### 4. Users, Groups, Shares

| Property | Old Server | New Server |
|----------|-----------|-----------|
| Users | 23 | 1 (support — will be deleted) |
| Admin users | admin, Amaris Admin | support |
| Groups | 3 (COMPANIES, EMPLOYEES, admin) | 1 (admin) |
| Group memberships | 23 | 1 |
| Shares | 38 | 0 |
| Share types | 0:user(23), 3:link(1), 10:talk(6), 11:talk-reshare(8) | — |

### 5. Storage & Filecache

| Property | Old Server | New Server |
|----------|-----------|-----------|
| Storages | 25 | 2 |
| Filecache entries | 32,623 | 132 |
| Filecache max ID | 166,948 | 133 |
| Mounts | 62 | 1 |
| Authtokens | 70 | 2 |
| Share max ID | 42 | 0 |
| Storage max ID | 27 | 2 |

### 6. Data Directory Breakdown (Old Server)

| Directory | Size | Action |
|-----------|------|--------|
| updater-oczvho61glg2/ | 21G | **SKIP** (old update backup) |
| appdata_oczvho61glg2/ | 11G | Copy (or regenerate via repair) |
| Amaris Chemical Solutions/ | 9.5G | Copy |
| Amaris Hardware Solutions/ | 3.8G | Copy |
| Amaris Medical Solutions/ | 1.2G | Copy |
| Justus Weru Irungu/ | 751M | Copy |
| Amaris FMCG Solutions/ | 447M | Copy |
| Amaris/ | 341M | Copy |
| Other user dirs (15) | ~600M total | Copy |
| __groupfolders/ | 8K | Copy |
| **Total to transfer** | **~27G** (excluding updater) | |
| **Total if appdata skipped** | **~16G** | |

### 7. Data Integrity

| Check | Old Server | Status |
|-------|-----------|--------|
| Files on disk (excl appdata/updater/logs) | 14,099 | OK |
| Filecache entries (user files, non-local storage) | 19,160 | OK (includes dirs, versions, trash) |
| Trashbin entries in filecache | 1,270 | OK (will migrate) |
| Versions entries in filecache | 151 | OK (will migrate) |
| File locks | 16 | OK (will clear via repair) |
| Pending uploads in filecache | 1 | OK (minor) |
| .part files | 0 | OK |
| .tmp files | 0 | OK |
| Encrypted files | 0 | OK (no encryption) |
| Federated shares | 0 | OK |
| External storages (real) | 0 | OK (collectives-user is internal) |
| Zero dates in oc_share | 0 | OK |
| Empty strings in NOT NULL columns | 0 | OK |

### 8. Web Server & PHP

| Property | Old Server | New Server |
|----------|-----------|-----------|
| Web server | Apache | Nginx |
| PHP version | 8.4.22 | 8.4.25 |
| PHP memory_limit | -1 (unlimited) | 512M |
| PHP upload_max_filesize | 2M | 16G |
| PHP max_execution_time | 0 (unlimited) | 3600 |
| PHP post_max_size | (default) | 16G |
| Nginx client_max_body_size | N/A | 50M |

**Note:** New server Nginx `client_max_body_size` is 50M, but PHP allows 16G uploads.
This means file uploads >50M will fail at Nginx even though PHP allows them.
This is a pre-existing config issue on the new server, not a migration issue.
To fix: `ssh root@164.68.104.123 'sed -i "s/client_max_body_size 50m/client_max_body_size 16g/" /www/server/panel/vhost/nginx/cloud.amarisstock.com.conf && nginx -s reload'`

### 9. Cron & Background Jobs

| Property | Old Server | New Server |
|----------|-----------|-----------|
| Cron (www-data/www) | Every 5 min: `cron.php` | Every 5 min: `cron.php` |
| Cron (root) | Weekly updater at 3 AM Sunday | Daily BT panel task at 6:31 AM |
| oc_jobs | 240 pending | 71 pending |
| Background jobs mode | cron | cron |

**Note:** oc_jobs is in SKIP_TABLES — old server's 240 pending jobs will NOT be migrated.
The new server keeps its own 71 jobs. This is correct — jobs are server-specific.

### 10. Docker & Services

| Property | Old Server | New Server |
|----------|-----------|-----------|
| Docker | Installed | Installed |
| Containers | appapi-harp (healthy, 2 weeks) | nats-server, onlyoffice-ds (both running) |
| Signaling service | active (systemd) | active (systemd) |
| notify_push | active (systemd) | (not found as systemd service) |
| www/web user in docker group | YES | **NO** (Issue #1) |
| app_api daemon | harp_proxy_host | None (Issue #2) |

### 11. Config Protection (oc_appconfig)

The new server's `oc_appconfig` contains server-specific configs that MUST NOT be overwritten:

| App | Key | Value (new server) |
|-----|-----|-------------------|
| onlyoffice | DocumentServerUrl | https://office.amarisstock.com |
| onlyoffice | DocumentServerInternalUrl | http://127.0.0.1:8000 |
| onlyoffice | jwt_secret | (redacted) |
| onlyoffice | jwt_enabled | true |
| spreed | signaling_servers | https://cloud.amarisstock.com/signaling |
| spreed | signaling_token_privkey_es256 | (redacted) |
| spreed | signaling_token_pubkey_es256 | (redacted) |
| spreed | stun_servers | cloud.amarisstock.com:3478 |
| spreed | turn_servers | cloud.amarisstock.com:3478 |
| core | backgroundjobs_mode | cron |

**Status:** `oc_appconfig` is in `SKIP_TABLES` in migrate.py — **PROTECTED**.

### 12. Appdata Directories

| Old server appdata subdirs | New server appdata subdirs |
|---------------------------|--------------------------|
| appstore | appstore |
| avatar | avatar |
| collectives | (missing) |
| core | (missing) |
| dav | dav |
| dav-photocache | (missing) |
| identityproof | identityproof |
| js | (missing) |
| mail | (missing) |
| officeonline | (missing) |
| onlyoffice | onlyoffice |
| photos | (missing) |
| preview | preview |
| richdocuments | (missing) |
| sketch_picker | (missing) |
| spreed | spreed |
| suspicious_login | (missing) |
| teamhub | (missing) |
| text | text |
| theming | theming |

**Note:** The old server has 20 appdata subdirs; the new server has 10.
If appdata is copied, the old `appdata_oczvho61glg2/` directory must be renamed to
`appdata_ocmu0qdk9tdd/` on the new server (different instance ID).
Phase 6 (storage rewrite) handles this in the DB, but the directory rename must be done manually:

```bash
ssh root@164.68.104.123 'mv /www/wwwroot/cloud.amarisstock.com-data/appdata_oczvho61glg2 \
  /www/wwwroot/cloud.amarisstock.com-data/appdata_ocmu0qdk9tdd'
```

Or, skip appdata entirely and let `occ maintenance:repair` regenerate it (previews, avatars, etc. will be rebuilt).

### 13. migrate.py Script Verification

| Check | Status |
|-------|--------|
| OLD_SERVER host | 38.242.141.240 — matches |
| OLD_SERVER webroot | /var/www/nextcloud — matches |
| OLD_SERVER datadir | /var/www/nextcloud/data — matches |
| OLD_SERVER web_user | www-data — matches |
| OLD_SERVER db_name | nextcloud — matches |
| OLD_SERVER db_pass | $OLD_SERVER_DB_PASS — verified working |
| NEW_SERVER host | 164.68.104.123 — matches |
| NEW_SERVER webroot | /www/wwwroot/cloud.amarisstock.com — matches |
| NEW_SERVER datadir | /www/wwwroot/cloud.amarisstock.com-data — matches |
| NEW_SERVER web_user | www — matches |
| NEW_SERVER db_name | sql_cloud_amarisstock_com — matches |
| NEW_SERVER db_pass | $NEW_SERVER_DB_PASS — verified working |
| SKIP_TABLES | oc_appconfig included — correct |
| CORE_TABLES | all 13 core tables listed — correct |
| TRUNCATE_TABLES | all 13 core tables listed — correct |
| Pre-import cleanup | deletes support user + truncates — correct |
| Auto-increment reset | 5 tables covered — correct |

---

## Pre-Migration Checklist

Before starting Phase 1:

- [x] **Issue #1 FIXED**: `www` added to docker group on new server (verified)
- [x] **Nginx upload limit FIXED**: `client_max_body_size` changed from 50m to 16g
- [ ] Confirm both servers are accessible
- [ ] Confirm migrate.py dry-run passes for all phases
- [ ] Create `/root/backups` on new server (for Phase 2 snapshot)

All prerequisite fixes are now codified in `prereqs.py`:
- `python3 prereqs.py --check` — verify current state
- `python3 prereqs.py --dry-run` — preview fixes
- `python3 prereqs.py` — apply all fixes

After migration (Phase 8):

- [ ] **Fix Issue #2**: Set up app_api harp daemon on new server
- [ ] Verify app_api works: `occ app_api:daemon:list`
- [ ] Verify OnlyOffice works (open a document)
- [ ] Verify Talk works (start a call)
