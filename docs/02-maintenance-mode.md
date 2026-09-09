# 02 — Phase 1: Maintenance Mode

> **Depends on**: Phase 0 (investigation complete; `occ` invocation method known)
> **Blocks**: Phases 2–8
> **Goal**: Freeze both Nextcloud instances so no writes occur during migration, preventing data corruption.

Both servers must be in maintenance mode before any data is read or written. This stops the web UI, cron-triggered file operations, and most background jobs from mutating the database or filesystem.

## Subtasks

### 1.1 Enable maintenance mode on the OLD server
Run as the correct user (per Phase 0.1 installation type):
```
# Manual install:
sudo -u www-data php /path/to/nextcloud/occ maintenance:mode --on

# Docker:
docker exec --user www-data <container> occ maintenance:mode --on

# Snap:
sudo nextcloud.occ maintenance:mode --on
```

### 1.2 Enable maintenance mode on the NEW server
Same command pattern as 1.1, against the new server.

### 1.3 Verify both servers report maintenance mode active
On each server:
```
occ maintenance:mode
# Expected: "Maintenance mode is currently enabled"
```
Also confirm the web UI on each server shows the maintenance screen (optional sanity check).

### 1.4 (Optional) Quiesce cron and background workers
- Stop/disable the Nextcloud cron job on both servers (e.g. comment out the `cron.php` crontab line, or stop the systemd timer/cron container).
- Stop any long-running background jobs (preview generation, cleanup) that might still be running.
- This prevents a scheduled job from firing during the window between maintenance mode being enabled and the DB/files being touched.

## Exit Criteria
- [ ] Old server maintenance mode: ON (verified)
- [ ] New server maintenance mode: ON (verified)
- [ ] Cron/background workers quiesced on both servers

## Notes
- Maintenance mode is a soft lock; it blocks the web UI and most cron tasks but does not freeze the DB at the MySQL level. Do not rely on it alone — Phase 2 (backup) and the dependency ordering provide the real safety.
- Leave maintenance mode ON through Phase 6. It is turned OFF in Phase 7 (Rescan & Activate) on the new server, and only turned off on the old server in Phase 8 if the old server is being decommissioned.
