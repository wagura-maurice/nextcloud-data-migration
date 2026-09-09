# Manual Phases — Step-by-Step Commands

> This document covers the phases that are NOT handled by `migrate.py`.
> All commands are tailored to the specific servers in this migration.
>
> **Old server** (38.242.141.240): this local machine, Apache, webroot `/var/www/nextcloud`, web user `www-data`
> **New server** (164.68.104.123): remote, Nginx, webroot `/www/wwwroot/cloud.amarisstock.com`, web user `www`

---

## Phase 1 — Enable Maintenance Mode

Freeze both servers so no writes occur during migration.

### 1.1 Enable on the OLD server (local)

```bash
cd /var/www/nextcloud && sudo -u www-data php occ maintenance:mode --on
```

### 1.2 Enable on the NEW server (remote)

```bash
ssh root@164.68.104.123 'cd /www/wwwroot/cloud.amarisstock.com && sudo -u www php occ maintenance:mode --on'
```

### 1.3 Verify both report maintenance mode active

```bash
# Old server
cd /var/www/nextcloud && sudo -u www-data php occ maintenance:mode
# Expected: "Maintenance mode is currently enabled"

# New server
ssh root@164.68.104.123 'cd /www/wwwroot/cloud.amarisstock.com && sudo -u www php occ maintenance:mode'
# Expected: "Maintenance mode is currently enabled"
```

### 1.4 (Optional) Quiesce cron and background workers

```bash
# Old server — check for cron jobs
crontab -u www-data -l 2>/dev/null | grep nextcloud
# If a cron line exists, comment it out:
# crontab -u www-data -e  (add # before the nextcloud cron.php line)

# New server — check for cron jobs
ssh root@164.68.104.123 'crontab -u www -l 2>/dev/null | grep nextcloud'
# If a cron line exists, comment it out on the new server too
```

### Exit Criteria
- [ ] Old server maintenance mode: ON (verified)
- [ ] New server maintenance mode: ON (verified)
- [ ] Cron/background workers quiesced on both servers (optional)

---

## Phase 2 — Snapshot New Server Config (minimal)

The new server is fresh — only a throwaway `support` user and 75M of data.
A full DB dump is unnecessary. We only need to snapshot the **two irreplaceable things**
in case something goes wrong and we need to roll back:

1. **`config/config.php`** — contains `instanceid`, `passwordsalt`, `secret`, DB credentials, trusted_domains
2. **`oc_appconfig` table** — contains OnlyOffice and Talk signaling configs that took effort to set up

Everything else is either throwaway (the `support` user) or will be replaced by old server data.

### 2.1 Create backup directory and snapshot config + appconfig

```bash
mkdir -p /root/backups
ssh root@164.68.104.123 'mkdir -p /root/backups'

# Snapshot config.php
ssh root@164.68.104.123 'cp /www/wwwroot/cloud.amarisstock.com/config/config.php /root/backups/config.php.bak'

# Snapshot oc_appconfig (the only table with irreplaceable new-server-specific data)
ssh root@164.68.104.123 'mysqldump --no-create-info --default-character-set=utf8mb4 \
  -u sql_cloud_amarisstock_com -p"$NEW_SERVER_DB_PASS" -h 127.0.0.1 \
  sql_cloud_amarisstock_com oc_appconfig \
  > /root/backups/oc_appconfig-snapshot.sql'
```

### 2.2 Copy snapshots to local machine for off-server safety

```bash
scp root@164.68.104.123:/root/backups/config.php.bak /root/backups/
scp root@164.68.104.123:/root/backups/oc_appconfig-snapshot.sql /root/backups/
```

### Exit Criteria
- [ ] `config.php.bak` exists on new server AND locally
- [ ] `oc_appconfig-snapshot.sql` exists on new server AND locally
- [ ] Keep these until Phase 8 (verification) is fully signed off

---

## Phase 5 — File Data Migration

Copy the actual user file data from the old server's data directory to the new server's, preserving ACLs, extended attributes, and ownership.

### Your specific paths

| Item | Old server | New server |
|------|-----------|-----------|
| Data directory | `/var/www/nextcloud/data` | `/www/wwwroot/cloud.amarisstock.com-data` |
| Web user | `www-data` | `www` |
| Data size | 48G | 75M (essentially empty) |
| Free disk | 27G | 951G |

### 5.1 Confirm paths and free space

```bash
# Old server — confirm data dir exists and check size
du -sh /var/www/nextcloud/data

# New server — confirm data dir exists and check free space
ssh root@164.68.104.123 'ls -la /www/wwwroot/cloud.amarisstock.com-data && df -h /www/wwwroot/cloud.amarisstock.com-data'
```

### 5.2 Run rsync (Option A — direct, preferred)

This is the fastest method. Run from the old server (this local machine):

```bash
rsync -Aax --info=progress2 --partial \
  /var/www/nextcloud/data/ \
  root@164.68.104.123:/www/wwwroot/cloud.amarisstock.com-data/
```

- `-A` preserves ACLs
- `-a` (archive) preserves ownership, group, permissions, times, symlinks
- `-x` stays on one filesystem (does not cross mount points)
- `--info=progress2` shows overall progress
- `--partial` allows resuming if interrupted

If interrupted, just re-run the same command — rsync only transfers differences.

### 5.2 Alternative — Run rsync (Option B — per-user, safer/resumable)

If you prefer to migrate user-by-user (so a failure on one user doesn't block the rest):

```bash
for u in $(ls /var/www/nextcloud/data/); do
  echo "=========================================="
  echo "Syncing: $u"
  echo "=========================================="
  rsync -Aax --partial --info=progress2 \
    /var/www/nextcloud/data/"$u"/ \
    root@164.68.104.123:/www/wwwroot/cloud.amarisstock.com-data/"$u"/
done
```

### 5.3 Directories to skip or handle specially

| Directory | Size | Action |
|-----------|------|--------|
| `appdata_oczvho61glg2/` | 11G | **Rsync** to preserve previews/avatars, OR skip and regenerate via `occ maintenance:repair` (slower first run but cleaner) |
| `updater-oczvho61glg2/` | 21G | **SKIP** — old update backup data, not needed on the new server |
| `uploads/` | small | **SKIP** — abandoned upload chunks from before maintenance mode |
| `__groupfolders/` | 8K | **Rsync** — group folders data (groupfolders app is in use) |

To skip the updater and uploads directories:

```bash
rsync -Aax --info=progress2 --partial \
  --exclude='updater-oczvho61glg2/' \
  --exclude='uploads/' \
  /var/www/nextcloud/data/ \
  root@164.68.104.123:/www/wwwroot/cloud.amarisstock.com-data/
```

> **Do NOT rsync the old server's `config/` directory** — that would overwrite the new server's system config.

### 5.4 Fix ownership on the new server

The old server uses `www-data`; the new server uses `www`. After rsync, fix ownership:

```bash
ssh root@164.68.104.123 'chown -R www:www /www/wwwroot/cloud.amarisstock.com-data'
```

### 5.5 Fix permissions on the new server

Nextcloud expects directories to be 770 and files to be 660:

```bash
ssh root@164.68.104.123 'find /www/wwwroot/cloud.amarisstock.com-data -type d -exec chmod 770 {} \;'
ssh root@164.68.104.123 'find /www/wwwroot/cloud.amarisstock.com-data -type f -exec chmod 660 {} \;'
```

### 5.6 Verify file counts and total sizes match

```bash
# File counts
echo "OLD:"
find /var/www/nextcloud/data -type f | wc -l
echo "NEW:"
ssh root@164.68.104.123 'find /www/wwwroot/cloud.amarisstock.com-data -type f | wc -l'

# Total sizes
echo "OLD:"
du -sb /var/www/nextcloud/data
echo "NEW:"
ssh root@164.68.104.123 'du -sb /www/wwwroot/cloud.amarisstock.com-data'
```

Old and new counts/sizes should match (modulo any files excluded intentionally like `updater-*` and `uploads/`).

### 5.7 (Optional) Sample checksum verification

Pick a few files and compare checksums between old and new:

```bash
# Example: check a specific file
sha256sum /var/www/nextcloud/data/admin/files/example.txt
ssh root@164.68.104.123 'sha256sum /www/wwwroot/cloud.amarisstock.com-data/admin/files/example.txt'
```

### Exit Criteria
- [ ] All user folders copied to the new data dir
- [ ] `updater-*` and `uploads/` excluded
- [ ] Ownership = `www:www` on the new server
- [ ] Permissions: dirs 770, files 660
- [ ] File counts and total size match old vs. new
- [ ] Sample checksums match (optional)

---

## Phase 7 — Rescan & Activate

Register the newly transferred files in Nextcloud's file cache and bring the new server back online.

### 7.1 Run files:scan --all on the new server

```bash
ssh root@164.68.104.123 'cd /www/wwwroot/cloud.amarisstock.com && sudo -u www php occ files:scan --all'
```

- This walks the data directory and reconciles `oc_filecache` with what is actually on disk.
- If `oc_filecache` was migrated in Phase 4 (by the script), the scan is fast (only updates drift).
- If it was dropped, the scan rebuilds it fully (slower).

> Note: some Nextcloud versions use `occ files:rescan --all`. Use `occ files:scan --help` to confirm. Nextcloud 34 uses `files:scan --all`.

### 7.2 Confirm the scan completes cleanly

```bash
# Check the exit code and summary line (files scanned, errors)
# The command above will print a summary. Look for:
#   "Scan for <n> users complete"
#   No errors listed

# Verify oc_filecache row count is reasonable
ssh root@164.68.104.123 'mysql -u sql_cloud_amarisstock_com -p"$NEW_SERVER_DB_PASS" -h 127.0.0.1 \
  sql_cloud_amarisstock_com -e "SELECT COUNT(*) FROM oc_filecache;"'
```

The old server had 32,623 rows in `oc_filecache`. The new server should have a similar count after scanning.

### 7.3 Turn OFF maintenance mode on the new server

```bash
ssh root@164.68.104.123 'cd /www/wwwroot/cloud.amarisstock.com && sudo -u www php occ maintenance:mode --off'
```

### 7.4 Verify maintenance mode is off

```bash
ssh root@164.68.104.123 'cd /www/wwwroot/cloud.amarisstock.com && sudo -u www php occ maintenance:mode'
# Expected: "Maintenance mode is currently disabled"
```

### 7.5 Verify the web UI loads

Open `https://cloud.amarisstock.com` in a browser. It should show the Nextcloud login page, NOT the maintenance screen.

### 7.6 Re-enable cron and background jobs on the new server

If you stopped cron in Phase 1.4, re-enable it now:

```bash
# Check cron status
ssh root@164.68.104.123 'crontab -u www -l 2>/dev/null | grep nextcloud'

# Trigger one manual run to confirm it works
ssh root@164.68.104.123 'cd /www/wwwroot/cloud.amarisstock.com && sudo -u www php occ cron:run'

# Confirm background jobs are running
ssh root@164.68.104.123 'cd /www/wwwroot/cloud.amarisstock.com && sudo -u www php occ background:status'
```

### Exit Criteria
- [ ] `occ files:scan --all` completes with no errors
- [ ] `oc_filecache` row count is sane (~32,000)
- [ ] New server maintenance mode: OFF (verified)
- [ ] New server web UI loads at `https://cloud.amarisstock.com`
- [ ] Cron / background jobs re-enabled and running

> **Important:** The OLD server remains in maintenance mode at this point. It is turned off only in Phase 8.7 if/when the old server is being decommissioned. Keeping it in maintenance mode prevents users from accidentally using the old instance during verification.

---

## Phase 8 — Verification

Prove the migration succeeded — users, files, shares, and apps all work at the new URL — and document the final confirmation.

### 8.1 Confirm old users can log in with original passwords

Pick a sample of users (at least one admin + several regular users):

| Test user | UID |
|-----------|-----|
| Admin | `admin` |
| Amaris Admin | `Amaris Admin` |
| Employee 1 | `Colin` |
| Employee 2 | `Deidre Mmbone` |
| Company account | `Amaris Chemical Solutions` |

For each:
1. Go to `https://cloud.amarisstock.com`
2. Log in with their original (old server) password
3. Confirm login succeeds — no password reset needed (argon2id hashes ported directly)

### 8.2 Confirm each test user sees their files

For each test user, after logging in:
- Verify their file tree is present
- Verify file counts match what they had on the old server
- Open a few sample files — confirm they open/preview/download correctly
- Verify file modification times are preserved

Cross-check file counts:
```bash
# Old server
for u in admin Colin "Deidre Mmbone" "Amaris Chemical Solutions"; do
  echo "$u: $(find "/var/www/nextcloud/data/$u" -type f 2>/dev/null | wc -l) files"
done

# New server
for u in admin Colin "Deidre Mmbone" "Amaris Chemical Solutions"; do
  echo "$u: $(ssh root@164.68.104.123 "find \"/www/wwwroot/cloud.amarisstock.com-data/$u\" -type f 2>/dev/null | wc -l") files"
done
```

### 8.3 Confirm group memberships and group shares are intact

Expected groups (from Phase 0 investigation):

| Group | Members |
|-------|---------|
| `COMPANIES` | Amaris, Amaris Agribusiness Solutions, Amaris Beauty Solutions, Amaris Chemical Solutions, Amaris Digital Solutions, Amaris FMCG Solutions, Amaris Hardware Solutions, Amaris Medical Solutions, Amaris Prime |
| `EMPLOYEES` | Colin, Deidre Mmbone, Diana Ngarari, Faith Mutethya Mwendwa, Hilda Nyambura Rubiro, Ignatius Kuria, Justus Weru Irungu, Lilian wacuka Nguru, Mike Mbithi Mbithuka, Onesmus kyalo Kithuku, Robert G Irungu, Victor Mwangi Mbuthia |
| `admin` | Amaris Admin, admin |

For each test user, verify:
- Their group memberships appear in the Nextcloud UI (Settings → Personal info → Groups)
- Group-shared folders are visible to the right members

Cross-check against the database:
```bash
ssh root@164.68.104.123 'mysql -u sql_cloud_amarisstock_com -p"$NEW_SERVER_DB_PASS" -h 127.0.0.1 \
  sql_cloud_amarisstock_com -e "SELECT gid, uid FROM oc_group_user ORDER BY gid, uid;"'
```

### 8.4 Confirm shared links still resolve

There were 38 shares on the old server. To check them:

```bash
# List all shares on the new server
ssh root@164.68.104.123 'mysql -u sql_cloud_amarisstock_com -p"$NEW_SERVER_DB_PASS" -h 127.0.0.1 \
  sql_cloud_amarisstock_com -e "SELECT id, share_type, share_with, file_target, token FROM oc_share ORDER BY id;"'
```

For public link shares (share_type = 3), open the link at the new URL:
```
https://cloud.amarisstock.com/s/<token>
```

Confirm each resolves to the correct file/folder with the correct permissions/password.

### 8.5 Confirm installed apps behave correctly

For each key app installed in Phase 3, do a smoke test:

| App | Test |
|-----|------|
| Calendar | Log in as a user, go to Calendar, verify calendars and events appear |
| Contacts | Go to Contacts, verify address books and contacts appear |
| Mail | Go to Mail, verify mail accounts are present |
| Notes | Go to Notes, verify notes appear |
| Polls | Go to Polls, verify polls appear |
| Forms | Go to Forms, verify forms appear |
| Tables | Go to Tables, verify tables and data appear |
| Group folders | Verify group folders are visible to the right groups |
| Collectives | Go to Collectives, verify collectives appear |
| OnlyOffice | Open a document — verify it loads (tests Docker container + Nginx proxy + JWT) |
| Talk (spreed) | Start a call — verify signaling works (tests HPB + NATS) |
| Maps | Go to Maps, verify devices/favorites appear |
| TeamHub | Go to TeamHub, verify data appears |

### 8.6 Document the final table-sync list and user/file mapping confirmation

Fill in the verification tables in `docs/09-verification.md`:

**Login & Files:**

| UID | Login OK | File count (old) | File count (new) | Files match | Notes |
|-----|----------|------------------|------------------|-------------|-------|
| admin | | | | | |
| Colin | | | | | |
| Deidre Mmbone | | | | | |
| Amaris Chemical Solutions | | | | | |

**Groups & Shares:**

| UID | Groups (old) | Groups (new) | Group shares OK | Link shares OK | Notes |
|-----|--------------|--------------|-----------------|----------------|-------|
| admin | | | | | |
| Colin | | | | | |
| Deidre Mmbone | | | | | |
| Amaris Chemical Solutions | | | | | |

**Apps:**

| App | Smoke test result | Notes |
|-----|-------------------|-------|
| Calendar | | |
| Contacts | | |
| OnlyOffice | | |
| Talk (spreed) | | |
| Group folders | | |
| Mail | | |
| Notes | | |
| Polls | | |
| Tables | | |
| Collectives | | |
| Maps | | |
| TeamHub | | |

**User/File Mapping Confirmation:**

- Total users migrated: 23
- Total files migrated: _(fill in from Phase 5.6)_
- All test users login with original passwords: _yes/no_
- All test users see their files: _yes/no_
- All group memberships intact: _yes/no_
- All tested share links resolve: _yes/no_
- All apps smoke-tested pass: _yes/no_

**Signed off by**: _<name>_  **Date**: _<date>_

### 8.7 Turn OFF maintenance mode on the OLD server (only if decommissioning)

If the old server is being kept as a fallback:
```bash
# Leave it in maintenance mode to prevent split-brain usage
# Do nothing — it stays frozen
```

If the old server is being decommissioned:
```bash
# Turn off maintenance mode for a final check
cd /var/www/nextcloud && sudo -u www-data php occ maintenance:mode --off

# Then shut it down or remove its DNS
```

Record the decision:
- Old server disposition: _(keep as fallback / decommission)_

### Exit Criteria
- [ ] All test users log in with original passwords
- [ ] All test users see their files (counts match)
- [ ] Group memberships and group shares intact
- [ ] Share links resolve
- [ ] Apps smoke-tested
- [ ] Tables-synced list in `docs/05-database-migration-report.md` complete
- [ ] User/file mapping confirmation above complete
- [ ] Old server disposition decided (decommission / keep as fallback)

> **If any check fails:** Do NOT turn off the old server's maintenance mode. Diagnose using the relevant phase's doc, fix, and re-verify. If unfixable, follow the rollback in `docs/00-overview.md` section 7.

---

## Quick Reference — Full Execution Order

```
Phase 1  [manual]   Enable maintenance mode on both servers         → this doc §1
Phase 2  [manual]   Snapshot new server config + appconfig           → this doc §2
Phase 3  [script]   python3 migrate.py --phase apps                → migrate.py
Phase 4  [script]   python3 migrate.py --phase db                 → migrate.py
Phase 5  [manual]   rsync ~27G of file data old → new              → this doc §5
Phase 6  [script]   python3 migrate.py --phase storage             → migrate.py
Phase 7  [manual]   occ files:scan --all + turn off maintenance    → this doc §7
Phase 8  [manual]   Login tests, file checks, share checks, apps    → this doc §8
```

## Rollback Procedure

If any phase fails catastrophically, restore the new server's irreplaceable config
from the Phase 2 snapshot. The new server is fresh, so we don't restore a full DB —
we just put back the two things that took effort to configure:

```bash
# 1. Restore config.php (instanceid, passwordsalt, secret, DB creds, trusted_domains)
ssh root@164.68.104.123 'cp /root/backups/config.php.bak /www/wwwroot/cloud.amarisstock.com/config/config.php'

# 2. Restore oc_appconfig (OnlyOffice + Talk signaling configs)
ssh root@164.68.104.123 'mysql -u sql_cloud_amarisstock_com -p"$NEW_SERVER_DB_PASS" -h 127.0.0.1 \
  sql_cloud_amarisstock_com -e "TRUNCATE TABLE oc_appconfig;" && \
  mysql -u sql_cloud_amarisstock_com -p"$NEW_SERVER_DB_PASS" -h 127.0.0.1 \
  sql_cloud_amarisstock_com < /root/backups/oc_appconfig-snapshot.sql'

# 3. Delete migrated user folders from the new data dir (if Phase 5 ran)
ssh root@164.68.104.123 'rm -rf /www/wwwroot/cloud.amarisstock.com-data/*/'

# 4. Turn off maintenance mode on the new server
ssh root@164.68.104.123 'cd /www/wwwroot/cloud.amarisstock.com && sudo -u www php occ maintenance:mode --off'

# 5. Turn off maintenance mode on the old server (resume normal operation)
cd /var/www/nextcloud && sudo -u www-data php occ maintenance:mode --off
```

Always verify the rollback restored the new server to its pre-migration working state before declaring the migration aborted.
