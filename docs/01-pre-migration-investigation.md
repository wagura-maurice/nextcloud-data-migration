# 01 — Phase 0: Pre-Migration Investigation

> **Depends on**: nothing
> **Blocks**: all subsequent phases
> **Goal**: Produce a complete, written picture of both servers and a go/no-go decision BEFORE any migration commands run.

This is the most important phase. Nothing on either server is changed here — it is read-only reconnaissance. The findings feed every later phase (paths, DB credentials, app list, data sizes, conflict detection).

## Subtasks

### 0.1 Discover installation type on both servers
Determine whether Nextcloud on each server is installed as:
- **Docker** (check `docker ps` for a nextcloud container)
- **Snap** (check `snap list nextcloud`)
- **Manual Apache/Nginx** (check `/var/www/nextcloud` or similar webroot)

Record the result for each server. The installation type determines how `occ` is invoked (e.g. `docker exec ... occ`, `sudo -u www-data occ`, or `sudo nextcloud.occ`).

### 0.2 Locate Nextcloud webroot, data directory, and config.php
For each server:
- Find the Nextcloud webroot (where `occ` lives)
- Read `config/config.php` and extract:
  - `datadirectory` (the data dir path)
  - `dbtype`, `dbname`, `dbuser`, `dbpassword`, `dbhost`
  - `apps_paths`
  - `instanceid` and `passwordsalt` (note: do NOT migrate these to the new server)
- Record the web server user (e.g. `www-data`) and PHP version

### 0.3 Identify database credentials for both servers
From `config.php` (subtask 0.2), record for each server:
- DB host, port, name, user, password
- Confirm engine is MySQL/MariaDB (`mysql --version` / `mariadb --version`)

### 0.4 Record Nextcloud version and app list on both servers
On each server run:
```
occ status
occ app:list
occ app:list --enabled
occ app:list --disabled
```
Save the full output. The app list diff drives Phase 3 (app parity). The version drives whether a direct table copy is safe (versions should match or be very close).

### 0.5 Inventory the old server's data
On the OLD server, record:
- User count: `occ user:list | wc -l` (or `SELECT COUNT(*) FROM oc_users;`)
- Group count: `SELECT COUNT(*) FROM oc_groups;`
- Share count: `SELECT COUNT(*) FROM oc_share;`
- Total data directory size: `du -sh <datadirectory>`
- Per-user folder sizes: `du -sh <datadirectory>/* | sort -h`
- List of tables present: `SHOW TABLES;` (filter for the ones we will migrate)

### 0.6 Inventory the new server's existing state
On the NEW server, record:
- Current user count and list (to detect collisions with old users)
- Current group list
- Whether any user files exist in the data directory
- Current `oc_accounts` / `oc_users` contents

This tells us whether the new server is truly "fresh" or whether Phase 4 needs ID-conflict handling.

### 0.7 Validate connectivity and privileges
- Confirm SSH from the local PC to both servers works
- Confirm paramiko can authenticate to both servers (test a trivial command)
- Confirm `occ` can be run as the correct user on both servers (e.g. `occ status` returns cleanly)
- Confirm `mysqldump` / `mysql` CLI access on the new server for backups

### 0.8 Produce investigation report and go/no-go decision
Compile subtasks 0.1–0.7 into a report appended to this document (see "Investigation Report" section below). The migration proceeds only if:
- Both servers are reachable and `occ` works
- DB credentials are known for both
- Nextcloud versions are compatible (ideally equal; if not, document the risk)
- The new server's existing users do not collide with old users (or a collision plan exists)
- Sufficient disk space exists on the new server for the old data (subtask 0.5 size vs. new server free space)

## Investigation Report

> Fill this in after running the subtasks. Replace the placeholders below.

### Old Server (38.242.141.240) — also the LOCAL machine running this migration
- Installation type: **Manual Apache** (webroot `/var/www/nextcloud`); plus a Docker container `appapi-harp` (AppAPI helper daemon)
- Webroot: `/var/www/nextcloud`
- Data directory: `/var/www/nextcloud/data`
- Web server user: `www-data`
- PHP: system PHP via Apache
- Nextcloud version: **34.0.3.2** (versionstring 34.0.3)
- DB host / name / user: `127.0.0.1` / `nextcloud` / `nextcloud` (password: `$OLD_SERVER_DB_PASS`, MySQL/MariaDB, utf8mb4)
- instanceid: `oczvho61glg2`
- data-fingerprint: `4dc37cb1c32bee25c1420b3a6f5910b0`
- User count: **23**
- Group count: **3** (`COMPANIES`, `EMPLOYEES`, `admin`)
- Share count: **38**
- oc_filecache rows: **32,623**
- oc_storages rows: **25**
- Data dir size: **48G** (largest: `appdata_oczvho61glg2` 11G, `updater-oczvho61glg2` 21G, `Amaris Chemical Solutions` 9.5G)
- Free disk on old server: 27G avail (73% used) — not relevant for migration target
- Apps enabled: **95 apps** (see full list in `docs/04-app-discovery-and-installation.md`)
- Notable apps: calendar, contacts, mail, groupfolders, onlyoffice, officeonline, spreed, notes, polls, tables, recognize, maps, collectives, forms, user_ldap, electronicsignatures, workflow_ocr, workflow_script
- LDAP: `user_ldap` enabled (ldapProviderFactory set in config.php)

### New Server (164.68.104.123)
- Installation type: **Manual Nginx** (webroot `/www/wwwroot/cloud.amarisstock.com`); plus Docker containers `nats-server` (NATS) and `onlyoffice-ds` (OnlyOffice Document Server)
- Webroot: `/www/wwwroot/cloud.amarisstock.com`
- Data directory: `/www/wwwroot/cloud.amarisstock.com-data`
- Web server user: **`www`** (NOT `www-data` — important for ownership fixes in Phase 5)
- Nextcloud version: **34.0.3.2** (versionstring 34.0.3) — **IDENTICAL to old server**
- DB host / name / user: `127.0.0.1` / `sql_cloud_amarisstock_com` / `sql_cloud_amarisstock_com` (password: `$NEW_SERVER_DB_PASS`, MySQL/MariaDB, utf8mb4)
- instanceid: `ocmu0qdk9tdd` (must NOT be overwritten)
- Existing user count: **1** (`support`)
- Existing users (list): `support`
- Existing group count: **1** (`admin` containing `support`)
- Existing share count: **0**
- oc_filecache rows: **132**
- oc_storages rows: **2**
- Data dir size: **75M** (essentially empty)
- Free disk space: **951G avail** (2% used) — ample for 48G of old data
- Apps enabled: **50 apps** (baseline Nextcloud set + onlyoffice)
- Apps missing vs old server: **46 apps** (see `docs/04-app-discovery-and-installation.md`)

### Key Differences & Migration Considerations
| Item | Old Server | New Server | Action |
|------|-----------|-----------|--------|
| Web server | Apache | Nginx | No action (system config not migrated) |
| Web user | `www-data` | `www` | Phase 5: `chown -R www:www` (not www-data) |
| Webroot | `/var/www/nextcloud` | `/www/wwwroot/cloud.amarisstock.com` | No action (do not migrate webroot) |
| Data dir | `/var/www/nextcloud/data` | `/www/wwwroot/cloud.amarisstock.com-data` | Phase 6: rewrite `oc_storages` paths |
| instanceid | `oczvho61glg2` | `ocmu0qdk9tdd` | Do NOT copy; rewrite storage id references |
| DB name | `nextcloud` | `sql_cloud_amarisstock_com` | Different DBs; table-prefix same (`oc_`) |
| URL | `cloud.amarissolutions.com` | `cloud.amarisstock.com` | Do NOT migrate; new server keeps its URL |
| Nextcloud version | 34.0.3.2 | 34.0.3.2 | Match — direct table copy is safe |
| App count | 95 enabled | 50 enabled | Phase 3: install 46 missing apps |

### SSH Connectivity
- Local → Old (38.242.141.240): **local machine** — no SSH needed, direct shell access
- Local → New (164.68.104.123): **SSH works** (`sshpass -p "$NEW_SERVER_SSH_PASS" ssh root@164.68.104.123`), port 22, root password auth confirmed
- paramiko target: both servers reachable (old via localhost, new via SSH password auth)

### Go / No-Go
- Decision: **GO**
- Conditions/risks:
  - Versions match exactly (34.0.3.2) — low schema-mismatch risk
  - New server is essentially fresh (1 throwaway `support` user, 0 shares) — no ID collision risk for users/shares; the `support` user UID does not collide with any old user UID
  - 951G free on new server vs 48G to transfer — ample space
  - 46 apps must be installed on the new server BEFORE DB import (Phase 3) so app tables exist
  - Data directory path differs — `oc_storages` paths must be rewritten in Phase 6
  - Web user is `www` not `www-data` — ownership fix in Phase 5 must use `www`
  - LDAP (`user_ldap`) is enabled on old server but **NOT active** (`ldapConfigurationActive = 0`, no `ldapHost` set, `oc_user_ldap` table does not exist). All 23 users are **local database users** with argon2id password hashes in `oc_users` and JSON profile data in `oc_accounts`. LDAP config migration is NOT required; `user_ldap` app still needs to be installed on the new server for app parity but does not need configuration.
  - `appdata_oczvho61glg2` (11G) and `updater-oczvho61glg2` (21G) are large — decide whether to rsync or regenerate (Phase 5.6)
