# 07 — Phase 6: Fingerprint & Repair

> **Depends on**: Phases 4 (DB migrated) and 5 (files on disk)
> **Blocks**: Phase 7 (rescan needs a consistent DB+filesystem state)
> **Goal**: Reconcile the new server's instance identity and run Nextcloud's built-in repair routines so the DB and filesystem are consistent before scanning.

After importing foreign DB rows and foreign files, the new server's internal state is likely inconsistent (stale storages, missing indices, mismatched instance references). This phase fixes that.

## Subtasks

### 6.1 Update the instance fingerprint if necessary
- The `instanceid` in `config.php` should stay the new server's own value (do NOT copy the old server's `instanceid` — it is used in storage paths like `appdata_<instanceid>`).
- If `oc_storages` rows from the old server reference the old `instanceid` in their `id` column (e.g. `local::/var/www/nextcloud/data/`), update them to point at the new server's data path:
  ```
  UPDATE oc_storages
  SET id = REPLACE(id, '<old_datadirectory>', '<new_datadirectory>')
  WHERE id LIKE 'local::<old_datadirectory>%';
  ```
- Also fix any `oc_filecache.path` / storage references that embed the old path if the data directory path differs between servers.
- Do NOT change `passwordsalt`, `secret`, or `instanceid` in `config.php`.

### 6.2 Run maintenance:repair on the new server
```
occ maintenance:repair
```
This runs a set of repair steps that:
- Rebuilds missing cache entries
- Fixes storages
- Repairs share tables
- Cleans up stale entries
- Recreates `.ocdata` marker and other metadata

Review the output line by line. Warnings are usually fine; errors must be resolved before Phase 7.

### 6.3 Add missing indices and convert filecache bigints
```
occ db:add-missing-indices
occ db:add-missing-columns
occ db:add-missing-primary-keys
occ db:convert-filecache-bigint --no-interaction
```
- These align the schema with the installed Nextcloud version (important if old/new versions differ).
- `convert-filecache-bigint` can take a while on large `oc_filecache` tables.

### 6.4 Review repair output for errors and resolve inconsistencies
For each error reported by 6.2/6.3:
- Note the error and the table/step it came from.
- Resolve (e.g. drop and let rescan rebuild `oc_filecache`, fix a duplicate key, re-run the specific repair step).
- Re-run `occ maintenance:repair` until it completes cleanly.

## Exit Criteria
- [ ] `oc_storages` paths point at the new data directory
- [ ] `occ maintenance:repair` completes without errors
- [ ] Missing indices/columns/primary keys added
- [ ] `oc_filecache` bigint conversion done (or skipped with reason)
- [ ] Re-run of `maintenance:repair` is clean

## Notes
- If `oc_filecache` was NOT migrated in Phase 4 (dropped intentionally), `maintenance:repair` + Phase 7's `files:scan --all` will rebuild it from scratch — this is expected and fine.
- Keep the new server's `config.php` system keys (`instanceid`, `passwordsalt`, `secret`) intact. Only data-path references inside tables are rewritten in 6.1.
