# Final Pre-Migration Sweep Report v3

> Date: 2026-09-09 (third sweep — after CI/CD and .env refactor)
> Status: **GO — READY TO MIGRATE**

---

## Summary

| Check | Old Server | New Server | Status |
|-------|-----------|-----------|--------|
| Nextcloud version | 34.0.3.2 | 34.0.3.2 | OK |
| PHP version | 8.4.22 | 8.4.25 | OK |
| DB engine | MariaDB 10.6.23 | MySQL 8.0.45 | OK |
| DB connection | Works | Works | OK |
| Disk space | 27G free | 951G free | OK |
| Data dir | 48G | 75M | OK |
| Maintenance mode | OFF | OFF | OK |
| Docker access | YES | YES (FIXED) | OK |
| Nginx upload limit | N/A | 16g (FIXED) | OK |
| Mail re-encryption | N/A | VERIFIED | OK |
| Config protection | N/A | oc_appconfig protected | OK |
| OnlyOffice + Talk | N/A | Running + configured | OK |
| Credential scan | N/A | No leaks | OK |
| .env loaded | N/A | 26 vars, all SET | OK |
| Git repo | N/A | Clean, pushed | OK |
| CI/CD | N/A | 4 jobs, passing | OK |
| Dry-run all phases | N/A | PASS | OK |

---

## Old Server (38.242.141.240)

### System
- OS: Ubuntu 22.04.5 LTS, uptime 15 days
- Disk: 97G total, 71G used, 27G free (73%)
- RAM: 11G total, 7.8G free
- Load: 0.95, 0.69, 0.58

### Nextcloud
- Version: 34.0.3.2, maintenance: false, needsDbUpgrade: false
- Webroot: /var/www/nextcloud, datadir: /var/www/nextcloud/data (48G)
- Web user: www-data:www-data
- PHP: 8.4.22
- Enabled apps: 98

### Database
- Engine: MariaDB 10.6.23
- Tables: 412, size: 245.1 MB
- Password: verified working

### Data
- Users: 23 (admins: Amaris Admin, admin)
- Groups: 3
- Shares: 38
- Storages: 25, filecache: 32,623, mounts: 62, authtokens: 70
- Mail accounts: 20 (all encrypted with server secret, all use mail.amarissolutions.com)
- Max IDs: filecache=166948, share=42, storages=27, mounts=77, authtoken=1453

### Integrity
- Encryption: disabled, 0 encrypted files
- Federated shares: 0
- File locks: 16 (will clear via repair)
- Pending uploads: 1
- .part/.tmp files: 0
- Queued jobs: 240 (server-specific, will NOT be migrated)

### Encrypted data tables
- oc_mail_accounts: 20 rows (RE-ENCRYPTION REQUIRED — handled in Phase 6)
- oc_talk_bots_server: 9 rows (plain base64, no re-encryption needed)
- All other encrypted tables: 0 rows

### Data dir breakdown
| Directory | Size | Action |
|-----------|------|--------|
| updater-oczvho61glg2/ | 21G | SKIP |
| appdata_oczvho61glg2/ | 11G | Copy or regenerate |
| User dirs (26) | ~16G | Copy |
| __groupfolders/ | 8K | Copy |
| **Total to transfer** | **~27G** | |

### Services
- Apache: active
- Cron: every 5 min (cron.php)
- Docker: active (appapi-harp container)
- notify_push: active
- signaling: active

---

## New Server (164.68.104.123)

### System
- OS: Ubuntu 22.04.5 LTS, uptime 1h 22min
- Disk: 969G total, 19G used, 951G free (2%)
- RAM: 17G total, 14G free
- Load: 0.40, 0.46, 0.47

### Nextcloud
- Version: 34.0.3.2, maintenance: false, needsDbUpgrade: false
- Webroot: /www/wwwroot/cloud.amarisstock.com, datadir: /www/wwwroot/cloud.amarisstock.com-data (75M)
- Web user: www:www
- PHP: 8.4.25
- Enabled apps: 52

### Database
- Engine: MySQL 8.0.45
- Tables: 181, size: 8.8 MB
- Password: verified working

### Data (throwaway — will be replaced)
- Users: 1 (support — will be deleted in Phase 4)
- Groups: 1, shares: 0
- Storages: 2, filecache: 132, mounts: 1, authtokens: 2
- Auto-increment: filecache=134, share=1, storages=3, mounts=2, authtoken=4

### Previous fixes verified
| Fix | Status |
|-----|--------|
| www in docker group | OK — groups=1001(www),998(docker) |
| www can read/write docker.sock | OK — YES/YES |
| Nginx client_max_body_size | OK — 16g |
| PHP-FPM running | OK — active |

### Services
- Docker containers: nats-server, onlyoffice-ds (both running)
- Signaling: active
- app_api daemon: not configured (post-migration task)
- Cron: every 5 min (cron.php)
- Background jobs: cron mode, 71 queued

### Config protection
- oc_appconfig: 207 rows (protected — in SKIP_TABLES)
- OnlyOffice: DocumentServerUrl=https://office.amarisstock.com, jwt_enabled=true
- Talk signaling: configured for cloud.amarisstock.com

---

## Migration Script Verification

### Dry-run all phases: PASS

| Phase | What | Status |
|-------|------|--------|
| Phase 3 | Install 46 missing apps | DRY RUN OK |
| Phase 4 | Migrate 403 tables (147 shared + 256 old-only) | DRY RUN OK |
| Phase 4 | Delete support, truncate 13 core tables, plain INSERT | DRY RUN OK |
| Phase 6 | Rewrite storage paths + appdata instance ID | DRY RUN OK |
| Phase 6 | Re-encrypt 20 mail account passwords | DRY RUN OK |

### prereqs.py --check: ALL PREREQUISITES MET

| # | Check | Status |
|---|-------|--------|
| 1 | www in docker group | OK |
| 2 | www can access docker.sock | OK |
| 3 | PHP-FPM running | OK |
| 4 | Nginx upload limit 16g | OK |
| 5 | Docker containers running | OK |
| 6 | Signaling service active | OK |
| 7 | app_api daemon | Needs setup (post-migration) |
| 8 | Maintenance mode off | OK |

### .env file
- 26 environment variables loaded
- OLD_SERVER_DB_PASS: SET
- NEW_SERVER_DB_PASS: SET
- NEW_SERVER_SSH_PASS: SET

### Credential scan
- No hardcoded credentials in any tracked file
- .env is gitignored and not tracked

### Git repo
- Branch: main, clean working tree
- Remote: git@github.com:wagura-maurice/nextcloud-data-migration.git
- Latest commit: ab40cd5 (Fix flake8 errors)
- CI/CD: 4 jobs configured (python-quality, security-scan, docs-check, dry-run-validation)

---

## Collision Analysis

| Table | Old max ID | New auto_increment | After truncate+import | After AI reset |
|-------|-----------|-------------------|----------------------|----------------|
| oc_filecache | 166,948 | 134 | 166,949 | OK |
| oc_share | 42 | 1 | 43 | OK |
| oc_storages | 27 | 3 | 28 | OK |
| oc_mounts | 77 | 2 | 78 | OK |
| oc_authtoken | 1,453 | 4 | 1,454 | OK |

All handled by truncate + plain INSERT + auto-increment reset.

---

## Open Items (Non-Blocking)

1. **app_api daemon** — not configured on new server. Set up after migration (Phase 8):
   - Pull harp Docker image
   - Run container
   - Register daemon via `occ app_api:daemon:register`

2. **File locks (16)** — will be cleared by `occ maintenance:repair` in Phase 6

3. **Pending upload (1)** — minor, will be cleared by `occ files:cleanup`

4. **Queued jobs (240 old)** — server-specific, in SKIP_TABLES, will NOT be migrated. New server keeps its own 71 jobs.

5. **Backup directories** — `/root/backups` needs to be created on both servers in Phase 2

---

## Go/No-Go: **GO**

All systems verified. All fixes in place. All scripts pass dry-run. No credentials leaked. Ready to execute Phase 1.
