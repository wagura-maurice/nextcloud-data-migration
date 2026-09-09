# 00 — Migration Overview & Master Runbook

This document is the master index for the Nextcloud data migration from the **old server** (`38.242.141.240`) to the **new server** (`164.68.104.123`). It defines scope, principles, the dependency-ordered phase list, the rollback strategy, and links to each phase's detailed document.

## 1. Scope

**Migrate (from old → new):**
- Users and their credentials/passwords
- Groups and group memberships
- Shares (user, group, link, federated) and share metadata
- User file data (the contents of the data directory)
- App/plugin parity (install the same apps on the new server)

**Do NOT migrate / do NOT overwrite on the new server:**
- System configuration (OS, web server, PHP config)
- Nextcloud system settings (`config.php` system-level entries, `oc_appconfig` system rows, `oc_jobs`, etc.)
- The new server's instance fingerprint unless explicitly required
- The new server's existing URL / hostname

## 2. Servers

| Role | IP | SSH |
|------|----|-----|
| Old (source) | `38.242.141.240` | `ssh root@38.242.141.240` |
| New (target) | `164.68.104.123` | `ssh root@164.68.104.123` |

Root SSH access is already available from the local PC for both servers.

## 3. Tooling

- **paramiko** — SSH library used to connect to the old server, pull DB data, then connect to the new server and push DB data.
- **rsync** (`rsync -Aax`) — copy file data preserving ACLs, xattrs, ownership.
- **occ** — Nextcloud CLI for maintenance mode, repair, scan, app management.
- **mysqldump / mysql** — DB dump/restore on the new server for backups.

## 4. Guiding Principles

1. **Investigate before executing.** Phase 0 is mandatory and produces a go/no-go decision.
2. **Dependency-ordered execution.** Phases run in the order below; do not skip ahead.
3. **Never clobber the new server's system config.** Only user/share/file/app data is migrated.
4. **Back up before mutating.** Phase 2 backs up the new server before any DB writes.
5. **Document everything.** Record the exact tables synced and confirm user/file mapping at the end.

## 5. Phase List (Dependency Order)

| # | Phase | Doc | Depends on | Blocks |
|---|-------|-----|------------|--------|
| 0 | Pre-Migration Investigation | [01-pre-migration-investigation.md](01-pre-migration-investigation.md) | — | 1–8 |
| 1 | Maintenance Mode | [02-maintenance-mode.md](02-maintenance-mode.md) | 0 | 2–8 |
| 2 | Backup New Server | [03-backup-new-server.md](03-backup-new-server.md) | 1 | 3–6 |
| 3 | App Discovery & Installation | [04-app-discovery-and-installation.md](04-app-discovery-and-installation.md) | 0, 1 | 4 |
| 4 | Database Migration | [05-database-migration.md](05-database-migration.md) | 2, 3 | 5 |
| 5 | File Data Migration | [06-file-data-migration.md](06-file-data-migration.md) | 4 | 6 |
| 6 | Fingerprint & Repair | [07-fingerprint-and-repair.md](07-fingerprint-and-repair.md) | 4, 5 | 7 |
| 7 | Rescan & Activate | [08-rescan-and-activate.md](08-rescan-and-activate.md) | 6 | 8 |
| 8 | Verification | [09-verification.md](09-verification.md) | 7 | — |

## 6. Dependency Graph

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

## 7. Rollback Strategy

If any phase fails catastrophically:

1. **Before DB migration (Phase 4):** simply turn maintenance mode back off on both servers; nothing has been mutated on the new server yet.
2. **After DB migration (Phase 4) but before files (Phase 5):** restore the new server's DB from the Phase 2 backup:
   ```
   mysql -u <dbuser> -p <nextcloud_db> < /path/to/phase2-dump.sql
   occ maintenance:mode --off
   ```
3. **After file migration (Phase 5):** restore the DB from Phase 2 backup; delete the migrated user folders from the new data directory (or restore from the Phase 2 data tarball); then `occ maintenance:mode --off`.
4. **After activation (Phase 7):** restore DB from Phase 2 backup, restore data tarball, `occ files:scan --all`, `occ maintenance:mode --off`.

Always verify the rollback restored the new server to its pre-migration working state before declaring the migration aborted.

## 8. Acceptance Criteria

The migration is complete when ALL of the following hold:

- [ ] Old users can log in to the new URL with their original passwords
- [ ] Each migrated user sees their files at the new URL
- [ ] Group memberships and group shares are intact
- [ ] Public/federated share links still resolve
- [ ] All old-server apps are installed and enabled on the new server
- [ ] The list of synced DB tables is documented in `docs/05-database-migration.md`
- [ ] User/file mapping confirmation is documented in `docs/09-verification.md`
- [ ] New server system config is unchanged

## 9. Open Items / Assumptions

- Installation types (Docker/Snap/Manual) and data directory paths are confirmed in Phase 0.
- The new server is otherwise empty of user data (Phase 0 verifies this); if it is not, ID-conflict handling in Phase 4 must be expanded.
- Database engine is MySQL/MariaDB on both servers (confirmed in Phase 0).
- paramiko is the transport for DB data; rsync is the transport for file data (rsync may run over SSH directly from the local PC or server-to-server — decided in Phase 5).
