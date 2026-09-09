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

### Old Server (38.242.141.240)
- Installation type: _<to be confirmed>_
- Webroot: _<to be confirmed>_
- Data directory: _<to be confirmed>_
- Web server user: _<to be confirmed>_
- Nextcloud version: _<to be confirmed>_
- DB host / name / user: _<to be confirmed>_
- User count: _<to be confirmed>_
- Group count: _<to be confirmed>_
- Share count: _<to be confirmed>_
- Data dir size: _<to be confirmed>_
- Apps enabled: _<to be confirmed>_

### New Server (164.68.104.123)
- Installation type: _<to be confirmed>_
- Webroot: _<to be confirmed>_
- Data directory: _<to be confirmed>_
- Web server user: _<to be confirmed>_
- Nextcloud version: _<to be confirmed>_
- DB host / name / user: _<to be confirmed>_
- Existing user count: _<to be confirmed>_
- Existing users (list): _<to be confirmed>_
- Free disk space: _<to be confirmed>_
- Apps enabled: _<to be confirmed>_

### Go / No-Go
- Decision: _<GO / NO-GO>_
- Conditions/risks: _<to be confirmed>_
