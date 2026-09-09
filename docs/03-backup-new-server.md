# 03 — Phase 2: Backup the New Server

> **Depends on**: Phase 1 (maintenance mode ON)
> **Blocks**: Phases 3–6 (do not mutate the new server's DB before this backup exists)
> **Goal**: Create a verified, restorable snapshot of the new server so any failed migration can be rolled back.

The new server is the target. We are about to write foreign data into its database and copy files into its data directory. A backup taken now is the single rollback point for the entire migration.

## Subtasks

### 2.1 Dump the new server's MySQL/MariaDB database
Using the credentials from Phase 0.3:
```
mysqldump --single-transaction --default-character-set=utf8mb4 \
  -u <dbuser> -p<dbpassword> -h <dbhost> <dbname> \
  > /root/backups/nextcloud-new-pre-migration-$(date +%F).sql
```
- Use `--single-transaction` for a consistent dump without locking (InnoDB).
- Use `--default-character-set=utf8mb4` to preserve emoji/unicode in filenames and shares.
- Do NOT use `--routines`/`--triggers` unless the new server actually has them (check first); the goal is a data+schema snapshot.

### 2.2 Snapshot the new server's config and data directory metadata
```
# Config + small metadata (cheap, full tarball):
tar czf /root/backups/nextcloud-new-config-$(date +%F).tar.gz \
  -C <nextcloud-webroot> config

# Data directory metadata only (do NOT tarball all files unless small):
# Record the file list + sizes for later verification:
find <datadirectory> -printf '%p\t%s\n' > /root/backups/nextcloud-new-data-manifest-$(date +%F).txt
```
If the new server's data directory already contains real user data (Phase 0.6 will tell us), take a full tarball of it instead of just a manifest.

### 2.3 Store backups in a known, restorable location and record the paths
- Keep backups on the new server under `/root/backups/` (or a mounted backup volume).
- Also copy the DB dump to the local PC for off-server safety:
  ```
  scp root@164.68.104.123:/root/backups/nextcloud-new-pre-migration-*.sql ./
  ```
- Record the exact filenames and SHA256 sums:
  ```
  sha256sum /root/backups/nextcloud-new-pre-migration-*.sql
  ```

### 2.4 Verify the backup is restorable
Load the dump into a temporary database to confirm it is not corrupt:
```
mysql -u root -p -e "CREATE DATABASE nc_restore_test;"
mysql -u root -p nc_restore_test < /root/backups/nextcloud-new-pre-migration-*.sql
mysql -u root -p -e "SELECT COUNT(*) FROM nc_restore_test.oc_users;"
mysql -u root -p -e "DROP DATABASE nc_restore_test;"
```
If the count returns and no errors appear, the backup is restorable.

## Exit Criteria
- [ ] Full DB dump exists on the new server AND on the local PC
- [ ] Config tarball exists
- [ ] Data manifest (or full data tarball) exists
- [ ] SHA256 sums recorded
- [ ] Dump verified restorable into a temp DB

## Notes
- This backup is referenced by the rollback procedure in `docs/00-overview.md` §7.
- Do not delete this backup until Phase 8 (verification) is complete and signed off.
