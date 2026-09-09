# 05 — Phase 4: Database Migration (Users, Groups, Shares, Passwords, Preferences)

> **Depends on**: Phase 2 (new server backed up), Phase 3 (apps installed → app tables exist)
> **Blocks**: Phase 5 (file metadata in `oc_filecache`/`oc_storages` must exist before files are scanned)
> **Goal**: Move the user/group/share/credential/preference data from the old DB into the new DB using paramiko as the transport, while preserving the new server's system settings.

This is the most delicate phase. We use **paramiko** to connect to the old server, dump the relevant tables, then connect to the new server and import them. We must avoid overwriting system rows on the new server and resolve any ID conflicts.

## Subtasks

### 4.1 Connect to the OLD server via paramiko and dump the relevant tables
Using paramiko, SSH to `38.242.141.240` and run a per-table `mysqldump` for the table set defined in subtasks 4.3–4.7:
```
mysqldump --no-create-info --skip-add-locks --skip-disable-keys \
  --default-character-set=utf8mb4 \
  -u <old_dbuser> -p<old_dbpassword> -h <old_dbhost> <old_dbname> \
  <table1> <table2> ... > /tmp/old-export.sql
```
- `--no-create-info`: we only want data; the schema already exists on the new server (created by Phase 3 app installs and the new server's own install).
- Pull the dump back to the local PC over the paramiko SFTP channel (or stage it for the new server).

### 4.2 Connect to the NEW server via paramiko and stage the dump for import
Using paramiko, SSH to `164.68.104.123`, push the dump file via SFTP to `/tmp/new-import.sql`, then import:
```
mysql --default-character-set=utf8mb4 \
  -u <new_dbuser> -p<new_dbpassword> -h <new_dbhost> <new_dbname> \
  < /tmp/new-import.sql
```
- Disable foreign-key checks during import to allow tables to load out of dependency order:
  ```
  SET FOREIGN_KEY_CHECKS=0;
  -- (import)
  SET FOREIGN_KEY_CHECKS=1;
  ```
- Import table-by-table rather than one giant file, so a failure in one table does not block the rest.

### 4.3 Migrate core identity tables
- `oc_users` — local user accounts (UID, display name, password hash)
- `oc_accounts` — the newer accounts table (UID, name, email, etc.)
- `oc_preferences` — per-user app preferences/settings

> **Conflict check:** if the new server already has users with the same UID (Phase 0.6), either (a) the new server is not truly fresh and you must merge carefully, or (b) drop the new server's conflicting users first (only safe if they are throwaway). Default assumption: new server is fresh.

### 4.4 Migrate credential / password tables
- `oc_authtoken` — browser/app login tokens (so existing sessions may survive if feasible)
- Password-related app tables, e.g. for the `passwords` app if installed: `oc_passwords_*`
- `oc_user_ldap` — only if LDAP was in use on the old server (skip if not)

The password hashes in `oc_users.password` are bcrypt/argon2 and are portable as-is — users keep their original passwords.

### 4.5 Migrate group tables
- `oc_groups` — group definitions
- `oc_group_user` — group memberships
- `oc_group_admin` — group administrators

### 4.6 Migrate share tables
- `oc_share` — primary shares table (user, group, link, federated)
- `oc_shares` — legacy/secondary shares table if present
- `oc_share_external` — incoming federated shares
- `oc_filecache` — file metadata cache (size, mtime, etag, permissions) — needed so Phase 5's files are recognized
- `oc_storages` — storage definitions (local, home, shared)
- `oc_mounts` — user mount points (external storages, group folders)

> `oc_filecache` can be large. If it is impractical to migrate, it can be dropped and fully rebuilt by `occ files:scan --all` in Phase 7 — but migrating it speeds up the scan and preserves etags.

### 4.7 Migrate app-specific user/share tables
For each app enabled in Phase 3 that stores user/share data, migrate its tables. Examples:
- Calendar: `oc_calendar_*`
- Contacts: `oc_cards`, `oc_addressbooks`, `oc_cards_properties`
- Notes: `oc_notes_*`
- Bookmarks: `oc_bookmarks_*`
- Tasks: `oc_calendartasks_*`, `oc_calendartasks_*`
- Group folders: `oc_group_folders*`

Use the app list from Phase 3 to enumerate these.

### 4.8 Preserve the new server's system settings
Do NOT overwrite these tables/rows on the new server:
- `oc_appconfig` — system app configuration (only migrate user-facing app rows if needed, and never overwrite system rows)
- `oc_jobs` — background job queue
- `oc_systemtag*` (optional — migrate only if tags are user-created and desired)
- `config.php` system entries (`instanceid`, `passwordsalt`, `secret`, `datadirectory`, `db*`)
- The new server's `oc_accounts` rows for any admin user created during install

When importing, use `INSERT IGNORE` or `REPLACE` strategically, or import into a staging table and merge, to avoid clobbering system rows.

### 4.9 Resolve ID conflicts
- Auto-increment offsets: after import, reset auto-increment on each migrated table to max(id)+1:
  ```
  ALTER TABLE oc_share AUTO_INCREMENT = <max+1>;
  ```
- Primary key collisions: if the new server already has rows with IDs that the old data also uses, remap the old IDs to new values and update foreign references. This is only needed if the new server was not fresh (Phase 0.6).
- Foreign key ordering: import parent tables before child tables (e.g. `oc_groups` before `oc_group_user`; `oc_storages` before `oc_filecache`).

### 4.10 Document the exact list of tables synced
Append the final table list (with row counts before/after) to the "Tables Synced" section below. This satisfies the plan's requirement to "document which database tables you sync".

## Tables Synced

> Fill in during execution.

| Table | Old row count | New row count (after) | Notes |
|-------|---------------|----------------------|-------|
| `oc_users` | _<n>_ | _<n>_ | |
| `oc_accounts` | _<n>_ | _<n>_ | |
| `oc_preferences` | _<n>_ | _<n>_ | |
| `oc_authtoken` | _<n>_ | _<n>_ | |
| `oc_groups` | _<n>_ | _<n>_ | |
| `oc_group_user` | _<n>_ | _<n>_ | |
| `oc_group_admin` | _<n>_ | _<n>_ | |
| `oc_share` | _<n>_ | _<n>_ | |
| `oc_share_external` | _<n>_ | _<n>_ | |
| `oc_storages` | _<n>_ | _<n>_ | |
| `oc_filecache` | _<n>_ | _<n>_ | |
| `oc_mounts` | _<n>_ | _<n>_ | |
| _<app tables...>_ | _<n>_ | _<n>_ | |

## Exit Criteria
- [ ] All tables in 4.3–4.7 imported into the new DB
- [ ] New server system settings (4.8) untouched
- [ ] ID conflicts resolved (4.9)
- [ ] Row counts old vs. new match for each table (4.10)
- [ ] Tables-synced table above completed

## Notes
- paramiko is used for both SSH connections (old to pull, new to push). Keep the dump on the local PC as an intermediate so the two servers never need direct network access to each other.
- If `oc_filecache` is too large to migrate, drop it on the new server and let Phase 7 rebuild it — but still migrate `oc_storages` and `oc_mounts`.
- After import, run `SELECT COUNT(*) FROM oc_users;` on the new server and confirm it matches the old count from Phase 0.5.
