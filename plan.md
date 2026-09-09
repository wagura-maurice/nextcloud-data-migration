# Nextcloud Data Migration Plan

I have a fresh, working installation of Nextcloud on a new server with a new URL. I need to migrate ONLY the users, group shares, passwords, and file data from my old Nextcloud server into this existing new server. Do not overwrite the underlying system configuration of the new server.

### Server Access Details

- **Old Server SSH**: `ssh root@38.242.141.240`
- **New Server SSH**: `ssh root@164.68.104.123`

### Environment Specifications

- **Installation Type (Old)**: [e.g., Docker, Snap, Manual Apache] — to be confirmed during Phase 0 investigation
- **Installation Type (New)**: [e.g., Docker, Snap, Manual Apache] — to be confirmed during Phase 0 investigation
- **Database Type**: MySQL / MariaDB (both servers)
- **Old Data Directory Path**: [e.g., /var/www/nextcloud/data] — to be confirmed during Phase 0 investigation
- **New Data Directory Path**: [e.g., /var/www/nextcloud/data] — to be confirmed during Phase 0 investigation

### Tooling

- **paramiko** — used to connect to the old server, pull data from its database, then connect to the new server and push the data into its database.
- **rsync** (`rsync -Aax`) — used to copy user file data from the old data directory to the new data directory, preserving ACLs and extended attributes.
- **occ** — Nextcloud's command-line tool, used for maintenance mode, repair, rescan, and app management.

### Execution Philosophy

1. Run an end-to-end investigation on BOTH servers BEFORE executing the migration to ensure data is transferred correctly and to determine the order of tasks based on their dependencies.
2. Look up the existing plugins and applications running on the old Nextcloud server and install them on the new Nextcloud server.
3. Document which database tables are synced and confirm when the users and files are successfully mapped.

---

## Task Breakdown and Dependency Order

The migration is divided into 10 phases. Phases must be executed in dependency order; subtasks within a phase may be parallelized where noted. Each phase has a dedicated document in the `/docs` folder.

### Phase 0 — Pre-Migration Investigation  →  `docs/01-pre-migration-investigation.md`
> **Depends on**: nothing  |  **Blocks**: all subsequent phases

- 0.1 Discover installation type (Docker / Snap / Manual) on both servers
- 0.2 Locate Nextcloud webroot, data directory, and config.php on both servers
- 0.3 Identify the database name, user, password, and host for both servers
- 0.4 Record Nextcloud version and app list (`occ app:list`) on both servers
- 0.5 Record user count, group count, share count, and total file data size on the old server
- 0.6 Record current user count and any existing data on the new server (to avoid clobbering)
- 0.7 Validate SSH/paramiko connectivity and sudo/occ privileges on both servers
- 0.8 Produce a written investigation report (saved to `docs/01-...`) and a go/no-go decision

### Phase 1 — Maintenance Mode  →  `docs/02-maintenance-mode.md`
> **Depends on**: Phase 0  |  **Blocks**: Phases 2–8

- 1.1 Enable maintenance mode on the OLD server (`occ maintenance:mode --on`)
- 1.2 Enable maintenance mode on the NEW server (`occ maintenance:mode --on`)
- 1.3 Verify both servers report maintenance mode active
- 1.4 (Optional) Quiesce any cron jobs / background workers on both servers

### Phase 2 — Backup the New Server  →  `docs/03-backup-new-server.md`
> **Depends on**: Phase 1  |  **Blocks**: Phases 3–6

- 2.1 Dump the new server's MySQL/MariaDB database (`mysqldump` of the full Nextcloud DB)
- 2.2 Snapshot/tarball the new server's Nextcloud config and data directory metadata
- 2.3 Store backups in a known, restorable location and record the paths
- 2.4 Verify the backup is restorable (test-load the dump into a temp DB)

### Phase 3 — App / Plugin Discovery & Installation  →  `docs/04-app-discovery-and-installation.md`
> **Depends on**: Phase 0 (app list), Phase 1  |  **Blocks**: Phase 5 (some tables are app-specific)

- 3.1 Diff the old server's `occ app:list` against the new server's `occ app:list`
- 3.2 For each missing app: `occ app:install <app>` and `occ app:enable <app>` on the new server
- 3.3 Match app versions where possible; note version mismatches that may affect schema
- 3.4 Re-run `occ app:list` on the new server and confirm parity with the old server

### Phase 4 — Database Migration (Users, Groups, Shares, Passwords, Preferences)  →  `docs/05-database-migration.md`
> **Depends on**: Phases 2, 3  |  **Blocks**: Phase 6 (file metadata lives in DB)

- 4.1 Connect to the OLD server via paramiko and dump the relevant tables
- 4.2 Connect to the NEW server via paramiko and stage the dump for import
- 4.3 Migrate core identity tables: `oc_users`, `oc_accounts`, `oc_preferences`
- 4.4 Migrate credential/password tables: `oc_user_ldap`, `oc_authtoken` (login tokens), password-related app tables
- 4.5 Migrate group tables: `oc_groups`, `oc_group_user`, `oc_group_admin`
- 4.6 Migrate share tables: `oc_share`, `oc_shares`, `oc_share_external`, `oc_filecache` (metadata), `oc_storages`, `oc_mounts`
- 4.7 Migrate app-config tables that are user/share related (per Phase 3 app list)
- 4.8 Preserve the new server's system settings (do NOT overwrite `oc_appconfig` system rows, `oc_jobs`, etc.)
- 4.9 Resolve ID conflicts (auto-increment offsets, primary key collisions) and remap where needed
- 4.10 Document the exact list of tables synced (append to `docs/05-...`)

### Phase 5 — File Data Migration  →  `docs/06-file-data-migration.md`
> **Depends on**: Phase 4 (DB must know the users/storages first)  |  **Blocks**: Phase 6

- 5.1 Confirm old and new data directory paths (from Phase 0)
- 5.2 Run `rsync -Aax` from old data dir to new data dir for each user folder
- 5.3 Preserve ACLs / xattrs / ownership (verify web server user, e.g. `www-data`)
- 5.4 Fix ownership/permissions on the new server (`chown -R www-data:www-data`)
- 5.5 Verify file counts and total sizes match between old and new (checksum sample)
- 5.6 Handle the `appdata_*` and `uploads` directories appropriately

### Phase 6 — Fingerprint & Repair  →  `docs/07-fingerprint-and-repair.md`
> **Depends on**: Phases 4, 5  |  **Blocks**: Phase 7

- 6.1 Update the instance fingerprint on the new server if it changed (config.php)
- 6.2 Run `occ maintenance:repair` on the new server
- 6.3 Run `occ db:add-missing-indices` and `occ db:convert-filecache-bigint` if needed
- 6.4 Review repair output for errors and resolve any reported inconsistencies

### Phase 7 — Rescan & Activate  →  `docs/08-rescan-and-activate.md`
> **Depends on**: Phase 6  |  **Blocks**: Phase 8

- 7.1 Run `occ files:rescan --all` (or `occ files:scan --all`) on the new server
- 7.2 Confirm scan completes without errors and filecache row count matches expectations
- 7.3 Turn OFF maintenance mode on the new server (`occ maintenance:mode --off`)
- 7.4 Re-enable cron / background jobs on the new server

### Phase 8 — Verification  →  `docs/09-verification.md`
> **Depends on**: Phase 7  |  **Blocks**: nothing (terminal phase)

- 8.1 Confirm old users can log in with their original passwords at the new URL
- 8.2 Confirm each test user can see their files and shares
- 8.3 Confirm group memberships and group shares are intact
- 8.4 Confirm shared links still resolve
- 8.5 Confirm installed apps behave correctly
- 8.6 Document the final table-sync list and user/file mapping confirmation
- 8.7 Turn OFF maintenance mode on the OLD server only if it is being decommissioned later

### Phase 9 — Overview & Dependency Map  →  `docs/00-overview.md`
> Master index, dependency graph, rollback strategy, and runbook.

---

## Dependency Graph

```
Phase 0 (Investigation)
   │
   ▼
Phase 1 (Maintenance Mode)
   │
   ▼
Phase 2 (Backup New Server) ──┐
   │                          │
   ▼                          ▼
Phase 3 (App Parity) ───► Phase 4 (DB Migration)
                               │
                               ▼
                        Phase 5 (File Migration)
                               │
                               ▼
                        Phase 6 (Fingerprint & Repair)
                               │
                               ▼
                        Phase 7 (Rescan & Activate)
                               │
                               ▼
                        Phase 8 (Verification)
```

## Documentation Index

| Doc | Phase | Description |
|-----|-------|-------------|
| `docs/00-overview.md` | 9 | Master overview, dependency graph, rollback, runbook |
| `docs/01-pre-migration-investigation.md` | 0 | End-to-end investigation of both servers |
| `docs/02-maintenance-mode.md` | 1 | Enable maintenance mode on both servers |
| `docs/03-backup-new-server.md` | 2 | Backup the new server's DB and config |
| `docs/04-app-discovery-and-installation.md` | 3 | Discover and install old server's apps on the new server |
| `docs/05-database-migration.md` | 4 | Migrate users, groups, shares, passwords, preferences via paramiko |
| `docs/06-file-data-migration.md` | 5 | rsync user file data with permissions |
| `docs/07-fingerprint-and-repair.md` | 6 | Update fingerprint and run maintenance:repair |
| `docs/08-rescan-and-activate.md` | 7 | Rescan files and bring the new server back online |
| `docs/09-verification.md` | 8 | Verify logins, files, shares, and document results |

---

Please document which database tables you sync and confirm when the users and files are successfully mapped.

the old nextcloud server is running on the ip : 38.242.141.240 which we already have root ssh access to from this local pc of mine. by running the `ssh root@38.242.141.240` command we can access the old nextcloud server.

the new nextcloud server is running on the ip : 164.68.104.123, which we already have root ssh access to from this local pc of mine. by running the `ssh root@164.68.104.123` command we can access the new nextcloud server.

Specs: use paramiko to connect to the old nextcloud server and pull the data from the database and then use paramiko to connect to the new nextcloud server and push the data to the database - also look up the existing plugins and application running in the old nextcloud server and install them in the new nextcloud server.

before executing the script lets run an end to end investigation on the old nextcloud server and the new nextcloud server in order to make sure that the data is being transferred correctly.

to determine the order of the tasks we need to look at the dependencies between the tasks.

---

for now just generate for us the step by step plan in .md format i.e in the `/docs` folder and you do multiple documents for segment of the tasks.
