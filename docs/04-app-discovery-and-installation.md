# 04 — Phase 3: App / Plugin Discovery & Installation

> **Depends on**: Phase 0 (app lists captured), Phase 1 (maintenance mode)
> **Blocks**: Phase 4 (some migrated tables belong to apps; the app's schema must exist before its data is imported)
> **Goal**: Make the new server's app set match the old server's so app-specific database tables and file metadata resolve correctly.

If an app exists on the old server but not the new one, its tables (e.g. `oc_notes_*`, `oc_calendar_*`, `oc_bookmarks_*`) will have no schema on the new server to receive the migrated data. Installing the apps first creates those tables.

## Subtasks

### 3.1 Diff the app lists
From Phase 0.4 we have `occ app:list` output for both servers. Produce two sets:
- `old_enabled` — apps enabled on the old server
- `new_enabled` — apps enabled on the new server

Compute:
- `to_install` = `old_enabled − new_enabled` (missing on new)
- `to_enable` = apps present but disabled on new that are enabled on old
- `extra_on_new` = `new_enabled − old_enabled` (informational; do NOT disable unless it conflicts)

### 3.2 Install and enable each missing app on the new server
For each app in `to_install`:
```
occ app:install <app>
occ app:enable  <app>
```
For each app in `to_enable`:
```
occ app:enable <app>
```
- Run as the correct user per the installation type (Phase 0.1).
- Some apps may not be installable via `occ app:install` if they are not in the App Store (e.g. custom/3rd-party apps). For those, copy the app folder from the old server's `apps/` directory into the new server's `apps/` directory, then `occ app:enable <app>`.

### 3.3 Match app versions where possible
For each installed app, compare versions:
```
occ app:list  # shows version per app on each server
```
- If the new server's app version is older than the old server's, run `occ app:update <app>` to bring it up.
- If the new server's app version is newer, document it — a newer schema can usually accept older data, but note any incompatibility.
- Record version mismatches that may affect table schema (these are handled in Phase 4.9).

### 3.4 Confirm parity
Re-run `occ app:list` on the new server and diff against the old server's list. The enabled-app sets should now match (ignoring `extra_on_new` informational extras). Record the final app/version table in the "App Parity Report" below.

## App Parity Report

> Fill in after running the subtasks.

| App | Old version | New version (before) | New version (after) | Action taken |
|-----|-------------|----------------------|---------------------|--------------|
| _<app>_ | _<ver>_ | _<ver>_ | _<ver>_ | _install/enable/update/copy_ |

## Exit Criteria
- [ ] Every app enabled on the old server is enabled on the new server
- [ ] App versions matched or mismatches documented
- [ ] Custom apps copied manually if not in the App Store
- [ ] `occ app:list` parity confirmed

## Notes
- Do NOT disable apps that exist only on the new server unless they directly conflict with a migrated app. Disabling them could remove their data.
- Enabling an app creates its DB tables (with the app's current schema). This is exactly what we want before Phase 4 imports the app's data rows.
