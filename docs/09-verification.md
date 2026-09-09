# 09 — Phase 8: Verification

> **Depends on**: Phase 7 (new server live)
> **Blocks**: nothing (terminal phase)
> **Goal**: Prove the migration succeeded — users, files, shares, and apps all work at the new URL — and document the final confirmation.

## Subtasks

### 8.1 Confirm old users can log in with original passwords at the new URL
- Pick a sample of users (at least one admin + several regular users).
- For each, attempt a login at the new server's URL using their original (old server) password.
- Confirm the password hash ported correctly (Phase 4.4) — no password resets should be needed.
- Record pass/fail per test user in the "Verification Results" table below.

### 8.2 Confirm each test user sees their files
- For each test user, log in and verify:
  - Their file tree is present
  - File counts match what they had on the old server (cross-check with Phase 0.5 / 5.5)
  - A few sample files open/preview/download correctly
  - File modification times are preserved

### 8.3 Confirm group memberships and group shares are intact
- For each test user, verify their group memberships appear.
- Verify group-shared folders are visible to the right members.
- Cross-check against `oc_group_user` rows migrated in Phase 4.5.

### 8.4 Confirm shared links still resolve
- Take a few public share links from the old server (from `oc_share` where `share_type` = public link).
- Open them at the new URL and confirm they resolve to the correct file/folder with the correct permissions/password.
- Verify federated shares (`oc_share_external`) if any were in use.

### 8.5 Confirm installed apps behave correctly
- For each app installed in Phase 3, do a smoke test:
  - Calendar: view calendars
  - Contacts: view address books
  - Notes/Bookmarks/Tasks: view entries
  - Group folders: view group folders
- Confirm app data migrated (Phase 4.7) is visible.

### 8.6 Document the final table-sync list and user/file mapping confirmation
- The table-sync list is already in `docs/05-database-migration.md` §"Tables Synced" — confirm it is complete.
- In the "User/File Mapping Confirmation" section below, record for each test user:
  - UID
  - Confirmed login (yes/no)
  - File count (old → new)
  - Group memberships confirmed (yes/no)
  - Shares confirmed (yes/no)

### 8.7 Turn OFF maintenance mode on the OLD server (only if decommissioning)
- If the old server is being kept as a fallback, leave it in maintenance mode (or take it offline) to prevent split-brain usage.
- If the old server is being decommissioned, turn off maintenance mode for a final check, then shut it down / remove its DNS.
- Record the decision.

## Verification Results

> Fill in during execution.

### Login & Files

| UID | Login OK | File count (old) | File count (new) | Files match | Notes |
|-----|----------|------------------|------------------|-------------|-------|
| _<uid>_ | _y/n_ | _<n>_ | _<n>_ | _y/n_ | |

### Groups & Shares

| UID | Groups (old) | Groups (new) | Group shares OK | Link shares OK | Notes |
|-----|--------------|--------------|-----------------|----------------|-------|
| _<uid>_ | _<list>_ | _<list>_ | _y/n_ | _y/n_ | |

### Apps

| App | Smoke test result | Notes |
|-----|-------------------|-------|
| _<app>_ | _pass/fail_ | |

## User/File Mapping Confirmation

> Final sign-off that users and files are correctly mapped on the new server.

- Total users migrated: _<n>_
- Total files migrated: _<n>_
- All test users login with original passwords: _yes/no_
- All test users see their files: _yes/no_
- All group memberships intact: _yes/no_
- All tested share links resolve: _yes/no_
- All apps smoke-tested pass: _yes/no_

**Signed off by**: _<name>_  **Date**: _<date>_

## Exit Criteria
- [ ] All test users log in with original passwords
- [ ] All test users see their files (counts match)
- [ ] Group memberships and group shares intact
- [ ] Share links resolve
- [ ] Apps smoke-tested
- [ ] Tables-synced list in `docs/05-database-migration.md` complete
- [ ] User/file mapping confirmation above complete
- [ ] Old server disposition decided (decommission / keep as fallback)

## Notes
- If any check fails, do NOT turn off the old server's maintenance mode yet. Diagnose using the relevant phase's doc, fix, and re-verify. If unfixable, follow the rollback in `docs/00-overview.md` §7.
- Keep the Phase 2 backup until this phase is fully signed off.
