# 08 — Phase 7: Rescan & Activate

> **Depends on**: Phase 6 (DB + filesystem consistent)
> **Blocks**: Phase 8 (verification needs the server live)
> **Goal**: Register the newly transferred files in Nextcloud's file cache and bring the new server back online.

## Subtasks

### 7.1 Run files:scan --all on the new server
```
occ files:scan --all
```
- This walks the data directory and reconciles `oc_filecache` with what is actually on disk.
- If `oc_filecache` was migrated in Phase 4, the scan is fast (it only updates drift). If it was dropped, the scan rebuilds it fully (slower).
- For a specific user: `occ files:scan <username>`.

> Note: some Nextcloud versions use `occ files:rescan --all`. Use whichever your version supports (`occ files:scan --help`).

### 7.2 Confirm the scan completes cleanly
- Check the exit code and the summary line (files scanned, errors).
- Verify `oc_filecache` row count is reasonable:
  ```
  SELECT COUNT(*) FROM oc_filecache;
  ```
- Compare against the old server's count from Phase 0.5 if `oc_filecache` was migrated; if it was dropped, just confirm the count is non-zero and roughly matches the number of files on disk (Phase 5.5).
- Resolve any per-file errors (e.g. encoding issues, name collisions) and re-scan the affected users.

### 7.3 Turn OFF maintenance mode on the new server
```
occ maintenance:mode --off
```
- Verify with `occ maintenance:mode` → "Maintenance mode is currently disabled".
- Confirm the web UI loads at the new URL.

### 7.4 Re-enable cron and background jobs on the new server
- Re-enable the cron job / systemd timer / cron container that was quiesced in Phase 1.4.
- Trigger one manual run to confirm it works:
  ```
  occ cron:run    # or: php -f cron.php
  ```
- Confirm background jobs resume (e.g. `occ background:status`).

## Exit Criteria
- [ ] `occ files:scan --all` completes with no errors
- [ ] `oc_filecache` row count is sane
- [ ] New server maintenance mode: OFF
- [ ] New server web UI loads at the new URL
- [ ] Cron / background jobs re-enabled and running

## Notes
- The OLD server remains in maintenance mode at this point. It is turned off only in Phase 8.7 if/when the old server is being decommissioned. Keeping it in maintenance mode prevents users from accidentally using the old instance during verification.
- If the scan finds files that don't belong to any known user (orphaned), it will report them; decide whether to assign or delete.
