# Admin User & ID Collision Analysis

> Investigated: 2026-09-09
> Finding: Admin user UIDs do NOT collide, but **storage IDs, filecache IDs, and mount IDs DO collide**.
> The `INSERT IGNORE` approach in the original script would silently drop critical data.

---

## 1. Admin User UIDs — NO COLLISION

| Server | Admin users (in `admin` group) | UID |
|--------|-------------------------------|-----|
| Old | `admin` | `admin` |
| Old | `Amaris Admin` | `Amaris Admin` |
| New | `support` | `support` |

The UIDs are completely different (`admin` / `Amaris Admin` vs `support`). There is **no UID collision**.

After migration, the new server will have THREE admin users:
- `admin` (from old server, with old server's password)
- `Amaris Admin` (from old server, with old server's password)
- `support` (new server's original admin, keeps its own password)

This is safe — no crash, no conflict. All three can log in with their respective passwords.

---

## 2. The REAL Problem: Storage/Filecache/Mount ID Collisions

### oc_storages — CRITICAL COLLISION

| numeric_id | Old server | New server | INSERT IGNORE result |
|-----------|-----------|-----------|---------------------|
| 1 | `home::admin` | `local::/www/wwwroot/cloud.amarisstock.com-data/` | OLD SKIPPED — admin's storage lost! |
| 2 | `local::/var/www/nextcloud/data/` | `home::support` | OLD SKIPPED — local data storage lost! |
| 3-27 | `home::Amaris Admin`, `home::Amaris Chemical Solutions`, etc. | (none) | IMPORTED OK |

**Impact:** If old storage IDs 1 and 2 are skipped:
- `home::admin` storage is never created → admin's files have no storage mapping
- `local::/var/www/nextcloud/data/` storage is never created → the main data directory storage is missing
- All `oc_filecache` rows referencing `storage=1` or `storage=2` would point to the WRONG storages (the new server's storages instead of the old server's)

### oc_filecache — CRITICAL COLLISION

| fileid range | Old server | New server | INSERT IGNORE result |
|-------------|-----------|-----------|---------------------|
| 1-133 | admin's files, appdata, templates | support's files, new appdata | OLD SKIPPED — 133 entries lost! |
| 134-166948 | all other users' files | (none) | IMPORTED OK |

**Impact:** 133 filecache entries from the old server are silently dropped. These include admin's files, system templates, and appdata references.

### oc_mounts — MINOR COLLISION

| id | Old server | New server | INSERT IGNORE result |
|----|-----------|-----------|---------------------|
| 1 | mount for `Amaris` (storage_id=20) | mount for `support` (storage_id=2) | OLD SKIPPED — 1 mount lost |
| 2-77 | other mounts | (none) | IMPORTED OK |

### oc_authtoken — NO COLLISION

| id range | Old server | New server | Result |
|----------|-----------|-----------|--------|
| 1-3 | (none — old starts at 154) | support's tokens | No conflict |
| 154-1452 | old server tokens | (none) | IMPORTED OK |

---

## 3. The Fix: Truncate New Server Data Tables Before Import

Since the `support` user is a throwaway user created during the new server setup, the cleanest solution is:

### Step 1: Delete the `support` user from the new server
```bash
ssh root@164.68.104.123 'cd /www/wwwroot/cloud.amarisstock.com && sudo -u www php occ user:delete support'
```
This removes the user and cleans up related data (preferences, group memberships, etc.)

### Step 2: TRUNCATE data tables on the new server (removes leftover entries)
```sql
TRUNCATE TABLE oc_storages;
TRUNCATE TABLE oc_filecache;
TRUNCATE TABLE oc_mounts;
TRUNCATE TABLE oc_authtoken;
TRUNCATE TABLE oc_users;
TRUNCATE TABLE oc_accounts;
TRUNCATE TABLE oc_accounts_data;
TRUNCATE TABLE oc_preferences;
TRUNCATE TABLE oc_groups;
TRUNCATE TABLE oc_group_user;
TRUNCATE TABLE oc_group_admin;
TRUNCATE TABLE oc_share;
TRUNCATE TABLE oc_share_external;
```

### Step 3: Import all old data with plain INSERT (no INSERT IGNORE needed)
Since the tables are now empty, there are no collisions. All old data imports cleanly:
- Old storage numeric_id 1 (`home::admin`) → imports as-is
- Old storage numeric_id 2 (`local::/var/www/nextcloud/data/`) → imports, then Phase 6 rewrites to new path
- All filecache entries import with correct storage references
- All mounts import with correct storage references

### Step 4: Reset auto-increment values
After import, reset auto-increment to max(id)+1 for each table:
```sql
ALTER TABLE oc_filecache AUTO_INCREMENT = (SELECT MAX(fileid) FROM oc_filecache) + 1;
ALTER TABLE oc_share AUTO_INCREMENT = (SELECT MAX(id) FROM oc_share) + 1;
ALTER TABLE oc_storages AUTO_INCREMENT = (SELECT MAX(numeric_id) FROM oc_storages) + 1;
ALTER TABLE oc_mounts AUTO_INCREMENT = (SELECT MAX(id) FROM oc_mounts) + 1;
ALTER TABLE oc_authtoken AUTO_INCREMENT = (SELECT MAX(id) FROM oc_authtoken) + 1;
```

### Result After Fix

| Table | Before | After |
|-------|--------|-------|
| `oc_users` | 1 row (`support`) | 23 rows (all old server users) |
| `oc_storages` | 2 rows (new server's) | 25 rows (all old server storages, paths rewritten in Phase 6) |
| `oc_filecache` | 132 rows (support's files) | 32,623 rows (all old server files) |
| `oc_mounts` | 1 row (support's mount) | 62 rows (all old server mounts) |
| `oc_share` | 0 rows | 38 rows (all old server shares) |
| `oc_authtoken` | 2 rows (support's tokens) | 70 rows (all old server tokens) |

The `support` user is gone — replaced entirely by the old server's users. This is the intended outcome of the migration.

---

## 4. What About the `support` User's Files on Disk?

The `support` user's files are in `/www/wwwroot/cloud.amarisstock.com-data/support/`. After deleting the user and truncating the tables, these files become orphaned. They should be cleaned up:

```bash
ssh root@164.68.104.123 'rm -rf /www/wwwroot/cloud.amarisstock.com-data/support'
```

This is safe because `support` is a throwaway user with no real data.

---

## 5. Updated Migration Flow

```
Phase 1  [manual]   Enable maintenance mode on both servers
Phase 2  [manual]   Backup the new server's DB + config
Phase 3  [script]   Install missing apps on new server
PHASE 4a [script]   DELETE support user + TRUNCATE new server data tables  ← NEW STEP
Phase 4b [script]   Import all old server data (plain INSERT, no IGNORE)   ← CHANGED
Phase 5  [manual]   rsync file data old → new
Phase 6  [script]   Rewrite storage paths + repair
Phase 7  [manual]   Rescan files + activate
Phase 8  [manual]   Verification
```
