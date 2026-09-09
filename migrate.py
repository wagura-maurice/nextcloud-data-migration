#!/usr/bin/env python3
"""
Nextcloud Data Migration Script
================================
Migrates users, groups, shares, passwords, preferences, and app data
from the OLD Nextcloud server (38.242.141.240) to the NEW Nextcloud server
(164.68.104.123) using paramiko as the SSH/transfer transport.

Usage:
  python3 migrate.py --dry-run          # validate only, no mutations
  python3 migrate.py --phase apps       # Phase 3: install missing apps
  python3 migrate.py --phase db         # Phase 4: migrate database tables
  python3 migrate.py --phase storage    # Phase 6: rewrite storage paths
  python3 migrate.py --phase all        # run all phases in order

Requirements:
  - paramiko installed (pip3 install paramiko)
  - SSH key at /root/.ssh/id_ed25519 with access to both servers
  - Both servers' Nextcloud in maintenance mode (for db/storage phases)
  - Phase 3 (apps) must run before Phase 4 (db)
"""
import paramiko
import sys
import os
import io
import time
import argparse
import json
from pathlib import Path

# ============================================================================
# CONFIGURATION — loaded from .env file
# ============================================================================

def load_env():
    """Load credentials from .env file in the same directory as this script."""
    env_path = Path(__file__).parent / ".env"
    env = {}
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    env[key.strip()] = value.strip()
    return env

_env = load_env()

OLD_SERVER = {
    "host": _env.get("OLD_SERVER_HOST", "38.242.141.240"),
    "port": int(_env.get("OLD_SERVER_PORT", "22")),
    "user": _env.get("OLD_SERVER_USER", "root"),
    "key": "/root/.ssh/id_ed25519",
    "webroot": _env.get("OLD_SERVER_WEBROOT", "/var/www/nextcloud"),
    "datadir": _env.get("OLD_SERVER_DATADIR", "/var/www/nextcloud/data"),
    "web_user": _env.get("OLD_SERVER_WEB_USER", "www-data"),
    "db_host": _env.get("OLD_SERVER_DB_HOST", "127.0.0.1"),
    "db_name": _env.get("OLD_SERVER_DB_NAME", "nextcloud"),
    "db_user": _env.get("OLD_SERVER_DB_USER", "nextcloud"),
    "db_pass": _env.get("OLD_SERVER_DB_PASS", ""),
    "instanceid": _env.get("OLD_SERVER_INSTANCEID", "oczvho61glg2"),
}
OLD_SERVER["occ"] = f"cd {OLD_SERVER['webroot']} && sudo -u {OLD_SERVER['web_user']} php occ"

NEW_SERVER = {
    "host": _env.get("NEW_SERVER_HOST", "164.68.104.123"),
    "port": int(_env.get("NEW_SERVER_PORT", "22")),
    "user": _env.get("NEW_SERVER_USER", "root"),
    "key": "/root/.ssh/id_ed25519",
    "webroot": _env.get("NEW_SERVER_WEBROOT", "/www/wwwroot/cloud.amarisstock.com"),
    "datadir": _env.get("NEW_SERVER_DATADIR", "/www/wwwroot/cloud.amarisstock.com-data"),
    "web_user": _env.get("NEW_SERVER_WEB_USER", "www"),
    "db_host": _env.get("NEW_SERVER_DB_HOST", "127.0.0.1"),
    "db_name": _env.get("NEW_SERVER_DB_NAME", "sql_cloud_amarisstock_com"),
    "db_user": _env.get("NEW_SERVER_DB_USER", "sql_cloud_amarisstock_com"),
    "db_pass": _env.get("NEW_SERVER_DB_PASS", ""),
    "instanceid": _env.get("NEW_SERVER_INSTANCEID", "ocmu0qdk9tdd"),
}
NEW_SERVER["occ"] = f"cd {NEW_SERVER['webroot']} && sudo -u {NEW_SERVER['web_user']} php occ"

# Tables to SKIP (system config — must NOT be overwritten on the new server)
SKIP_TABLES = {
    "oc_appconfig",        # system + app config — new server has its own
    "oc_jobs",              # background job queue
    "oc_migrations",        # migration tracking
    "oc_recent_contacts",   # auto-generated
    "oc_addressbookchanges",  # auto-generated sync table
    "oc_calendarchanges",   # auto-generated sync table
    "oc_cards_properties",  # will be rebuilt by occ maintenance:repair
    "oc_systemtag",         # system tags (keep new server's)
    "oc_systemtag_group",
    "oc_systemtag_object_mapping",
}

# Core tables to migrate (always)
CORE_TABLES = [
    "oc_users",
    "oc_accounts",
    "oc_accounts_data",
    "oc_preferences",
    "oc_authtoken",
    "oc_groups",
    "oc_group_user",
    "oc_group_admin",
    "oc_share",
    "oc_share_external",
    "oc_filecache",
    "oc_storages",
    "oc_mounts",
]

# Apps to install on the new server (Phase 3)
# Derived from the investigation: apps enabled on old but not on new
APPS_TO_INSTALL = [
    "admin_audit",
    "admincockpit",
    "announcementcenter",
    "astrolabe",
    "calendar",
    "call_summary_bot",
    "collectives",
    "command_bot",
    "contacts",
    "electronicsignatures",
    "epubviewer",
    "event_update_notification",
    "files_accesscontrol",
    "files_automatedtagging",
    "files_external",
    "files_mindmap",
    "files_retention",
    "forms",
    "formulabase",
    "forum",
    "groupfolders",
    "mail",
    "maps",
    "mastermind",
    "notes",
    "notify_push",
    "officeonline",
    "polls",
    "printer",
    "profile_fields",
    "recognize",
    "sketch_picker",
    "socialsharing_whatsapp",
    "suspicious_login",
    "tables",
    "teamhub",
    "terms_of_service",
    "tickbuddy",
    "transfer_quota_monitor",
    "twofactor_nextcloud_notification",
    "user_external",
    "user_ldap",
    "userrightsoverview",
    "webhooks",
    "workflow_ocr",
    "workflow_script",
]

# Tables on the new server that must NOT be overwritten (app config for
# OnlyOffice, Talk signaling, etc. — these are new-server-specific)
PROTECTED_APPCONFIG_KEYS = {
    "onlyoffice": ["DocumentServerUrl", "jwt_secret", "server_address"],
    "spreed": ["signaling_servers", "secret", "signaling_ticket_secret"],
    "core": ["instanceid", "passwordsalt", "secret", "datadirectory"],
}

# ============================================================================
# SSH HELPERS
# ============================================================================

def connect(server_config, label=""):
    """Connect to a server via paramiko SSH."""
    print(f"  [{label}] Connecting to {server_config['user']}@{server_config['host']}...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=server_config["host"],
        port=server_config["port"],
        username=server_config["user"],
        key_filename=server_config["key"],
        timeout=15,
    )
    print(f"  [{label}] Connected.")
    return client

def run(client, cmd, label="", timeout=120, quiet=False):
    """Run a command via SSH, return (stdout, stderr, exit_code)."""
    if not quiet:
        print(f"  [{label}] Running: {cmd[:120]}{'...' if len(cmd) > 120 else ''}")
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    code = stdout.channel.recv_exit_status()
    if not quiet:
        status = "OK" if code == 0 else f"FAIL (exit {code})"
        print(f"  [{label}] {status}")
        if out and len(out) < 1000:
            for line in out.split("\n")[:20]:
                print(f"    {line}")
        elif out:
            print(f"    {out[:200]}... ({len(out)} bytes)")
        if err and code != 0:
            print(f"    STDERR: {err[:500]}")
    return out, err, code

def get_tables(client, db_config, label=""):
    """Get list of all tables in the database."""
    cmd = f"mysql -u {db_config['db_user']} -p'{db_config['db_pass']}' -h {db_config['db_host']} {db_config['db_name']} -N -e 'SHOW TABLES;' 2>/dev/null"
    out, _, code = run(client, cmd, f"{label} table list", quiet=True)
    if code != 0:
        return []
    return [t.strip() for t in out.split("\n") if t.strip()]

def get_row_count(client, db_config, table, label=""):
    """Get row count for a table."""
    cmd = f"mysql -u {db_config['db_user']} -p'{db_config['db_pass']}' -h {db_config['db_host']} {db_config['db_name']} -N -e \"SELECT COUNT(*) FROM {table};\" 2>/dev/null"
    out, _, code = run(client, cmd, f"{label} count {table}", quiet=True)
    if code != 0:
        return -1
    try:
        return int(out.strip())
    except ValueError:
        return -1

# ============================================================================
# PHASE 3: APP INSTALLATION
# ============================================================================

def phase_apps(old_client, new_client, dry_run=False):
    """Install missing apps on the new server to match the old server."""
    print("\n" + "=" * 70)
    print("PHASE 3: APP DISCOVERY & INSTALLATION")
    print("=" * 70)

    # Get app lists from both servers
    old_out, _, _ = run(old_client, f"{OLD_SERVER['occ']} app:list --enabled --output=json", "OLD app:list", quiet=True)
    new_out, _, _ = run(new_client, f"{NEW_SERVER['occ']} app:list --enabled --output=json", "NEW app:list", quiet=True)

    try:
        old_data = json.loads(old_out) if old_out else {}
        new_data = json.loads(new_out) if new_out else {}
        old_enabled = set(old_data.get("enabled", {}).keys()) if isinstance(old_data, dict) else set()
        new_enabled = set(new_data.get("enabled", {}).keys()) if isinstance(new_data, dict) else set()
    except json.JSONDecodeError:
        # Fallback: parse text output
        old_enabled = set()
        new_enabled = set()
        for line in old_out.split("\n"):
            line = line.strip().lstrip("- ")
            if ":" in line and line:
                app = line.split(":")[0].strip()
                if app and not app.startswith("Enabled") and not app.startswith("Disabled"):
                    old_enabled.add(app)
        for line in new_out.split("\n"):
            line = line.strip().lstrip("- ")
            if ":" in line and line:
                app = line.split(":")[0].strip()
                if app and not app.startswith("Enabled") and not app.startswith("Disabled"):
                    new_enabled.add(app)
    to_install = old_enabled - new_enabled

    print(f"\n  Old server enabled apps: {len(old_enabled)}")
    print(f"  New server enabled apps: {len(new_enabled)}")
    print(f"  Apps to install on new: {len(to_install)}")
    if to_install:
        print(f"  Missing: {sorted(to_install)}")

    if dry_run:
        print("\n  [DRY RUN] Would install these apps on the new server:")
        for app in sorted(to_install):
            print(f"    - {app}")
        return True

    installed = []
    failed = []
    for app in sorted(to_install):
        print(f"\n  Installing {app}...")
        _, _, code = run(new_client, f"{NEW_SERVER['occ']} app:install {app}", f"install {app}", timeout=120)
        if code == 0:
            run(new_client, f"{NEW_SERVER['occ']} app:enable {app}", f"enable {app}", timeout=60)
            installed.append(app)
        else:
            print(f"    WARNING: Failed to install {app} from App Store — trying manual copy from old server...")
            # Fallback: copy app folder from old server via SFTP
            old_app_path = f"{OLD_SERVER['webroot']}/apps/{app}"
            new_app_path = f"{NEW_SERVER['webroot']}/apps/{app}"
            # Check if app exists on old server
            _, _, check_code = run(old_client, f"test -d {old_app_path} && echo EXISTS", quiet=True)
            if check_code == 0:
                # Tar the app on old server, pull, push, untar on new
                run(old_client, f"cd {OLD_SERVER['webroot']}/apps && tar czf /tmp/app_{app}.tar.gz {app}", quiet=True)
                sftp_old = old_client.open_sftp()
                sftp_old.get(f"/tmp/app_{app}.tar.gz", f"/tmp/app_{app}.tar.gz")
                sftp_old.close()
                run(old_client, f"rm -f /tmp/app_{app}.tar.gz", quiet=True)
                sftp_new = new_client.open_sftp()
                sftp_new.put(f"/tmp/app_{app}.tar.gz", f"/tmp/app_{app}.tar.gz")
                sftp_new.close()
                os.remove(f"/tmp/app_{app}.tar.gz")
                run(new_client, f"cd {NEW_SERVER['webroot']}/apps && tar xzf /tmp/app_{app}.tar.gz && rm /tmp/app_{app}.tar.gz", quiet=True)
                run(new_client, f"chown -R {NEW_SERVER['web_user']}:{NEW_SERVER['web_user']} {new_app_path}", quiet=True)
                _, _, enable_code = run(new_client, f"{NEW_SERVER['occ']} app:enable {app}", f"enable {app} (manual)", timeout=60)
                if enable_code == 0:
                    installed.append(app)
                    print(f"    OK: {app} copied from old server and enabled")
                else:
                    failed.append(app)
                    print(f"    FAIL: {app} copied but could not enable — check app compatibility")
            else:
                failed.append(app)
                print(f"    FAIL: {app} not found on old server apps/ either — skipping")

    print(f"\n  Installed: {len(installed)} apps")
    if failed:
        print(f"  Failed (need manual install): {len(failed)} apps: {failed}")

    # After installing apps, reconcile schema (caveat: newer app versions may have extra columns)
    print(f"\n  Running db:add-missing-columns to reconcile app schemas...")
    run(new_client, f"{NEW_SERVER['occ']} db:add-missing-columns", "add-missing-columns", timeout=120)
    run(new_client, f"{NEW_SERVER['occ']} db:add-missing-indices", "add-missing-indices", timeout=120)
    run(new_client, f"{NEW_SERVER['occ']} db:add-missing-primary-keys", "add-missing-pks", timeout=120)

    # Verify parity
    new_out2, _, _ = run(new_client, f"{NEW_SERVER['occ']} app:list --enabled --output=json", "NEW app:list (after)", quiet=True)
    try:
        new_data2 = json.loads(new_out2) if new_out2 else {}
        new_apps2 = set(new_data2.get("enabled", {}).keys()) if isinstance(new_data2, dict) else set()
    except json.JSONDecodeError:
        new_apps2 = set()
    still_missing = old_enabled - new_apps2
    if still_missing:
        print(f"  Still missing after install: {sorted(still_missing)}")
    else:
        print(f"  App parity achieved!")

    return len(failed) == 0

# ============================================================================
# PHASE 4: DATABASE MIGRATION
# ============================================================================

def phase_db(old_client, new_client, dry_run=False):
    """Migrate database tables from old to new server via paramiko SFTP."""
    print("\n" + "=" * 70)
    print("PHASE 4: DATABASE MIGRATION")
    print("=" * 70)

    old_db = OLD_SERVER
    new_db = NEW_SERVER

    # Get table lists
    old_tables = set(get_tables(old_client, old_db, "OLD"))
    new_tables = set(get_tables(new_client, new_db, "NEW"))

    print(f"\n  Old server tables: {len(old_tables)}")
    print(f"  New server tables: {len(new_tables)}")

    # Determine which tables to migrate
    # Migrate: all tables EXCEPT skip list
    tables_to_migrate = sorted(old_tables - SKIP_TABLES)
    tables_to_migrate_set = set(tables_to_migrate)

    # Separate into: exists-on-both (data only) and old-only (need schema)
    tables_both = sorted(tables_to_migrate_set & new_tables)
    tables_old_only = sorted(tables_to_migrate_set - new_tables)

    print(f"\n  Tables to migrate: {len(tables_to_migrate)}")
    print(f"    - Exists on both (data-only import): {len(tables_both)}")
    print(f"    - Old-only (need schema+data): {len(tables_old_only)}")
    if tables_old_only:
        print(f"    - Old-only tables: {tables_old_only[:20]}{'...' if len(tables_old_only) > 20 else ''}")
        print(f"    WARNING: {len(tables_old_only)} tables don't exist on new server.")
        print(f"    Run Phase 3 (apps) first to create app tables, or these will be skipped.")

    if dry_run:
        print("\n  [DRY RUN] Would migrate these tables:")
        print(f"\n  Core tables (data-only):")
        for t in CORE_TABLES:
            if t in tables_both:
                cnt = get_row_count(old_client, old_db, t, "OLD")
                print(f"    {t}: {cnt} rows")
        print(f"\n  App tables (data-only, exists on both):")
        app_tables = [t for t in tables_both if t not in CORE_TABLES]
        for t in app_tables[:30]:
            cnt = get_row_count(old_client, old_db, t, "OLD")
            if cnt > 0:
                print(f"    {t}: {cnt} rows")
        if len(app_tables) > 30:
            print(f"    ... and {len(app_tables) - 30} more tables")
        print(f"\n  Tables to SKIP (system config): {sorted(SKIP_TABLES)}")
        print(f"\n  [DRY RUN] Pre-import cleanup:")
        print(f"    Would DELETE 'support' user from new server (throwaway user)")
        print(f"    Would TRUNCATE: oc_users, oc_accounts, oc_accounts_data, oc_preferences,")
        print(f"                    oc_authtoken, oc_groups, oc_group_user, oc_group_admin,")
        print(f"                    oc_share, oc_share_external, oc_storages, oc_mounts,")
        print(f"                    oc_filecache")
        print(f"    Would use plain INSERT (not INSERT IGNORE) for truncated tables")
        return True

    # --- Pre-import cleanup: delete throwaway 'support' user and truncate data tables ---
    # This prevents ID collisions between old and new server data
    # (see docs/collision-analysis.md for full analysis)
    print("\n  --- Pre-import cleanup ---")
    print("  Deleting 'support' user from new server (throwaway user)...")
    run(new_client, f"{NEW_SERVER['occ']} user:delete support", "delete support user", timeout=60)

    # Tables to TRUNCATE before import (removes all new server's existing data)
    TRUNCATE_TABLES = [
        "oc_users", "oc_accounts", "oc_accounts_data", "oc_preferences",
        "oc_authtoken", "oc_groups", "oc_group_user", "oc_group_admin",
        "oc_share", "oc_share_external", "oc_storages", "oc_mounts",
        "oc_filecache",
    ]
    print(f"  Truncating {len(TRUNCATE_TABLES)} tables on new server...")
    truncate_list = ", ".join(TRUNCATE_TABLES)
    truncate_cmd = (
        f"mysql -u {new_db['db_user']} -p'{new_db['db_pass']}' -h {new_db['db_host']} "
        f"{new_db['db_name']} -e \"SET FOREIGN_KEY_CHECKS=0; "
    )
    for t in TRUNCATE_TABLES:
        truncate_cmd += f"TRUNCATE TABLE {t}; "
    truncate_cmd += "SET FOREIGN_KEY_CHECKS=1;\" 2>/dev/null"
    run(new_client, truncate_cmd, "truncate tables", timeout=60)

    # --- Migration execution ---
    migrated = []
    skipped = []
    errors = []

    # Order: core tables first (respecting FK dependencies), then app tables
    migration_order = [
        # Identity
        "oc_users", "oc_accounts", "oc_accounts_data", "oc_preferences",
        # Credentials
        "oc_authtoken",
        # Groups
        "oc_groups", "oc_group_user", "oc_group_admin",
        # Storages (before filecache)
        "oc_storages",
        # Mounts
        "oc_mounts",
        # Shares
        "oc_share", "oc_share_external",
        # Filecache (after storages)
        "oc_filecache",
    ]

    # Add remaining tables (app tables) in sorted order
    remaining = [t for t in tables_both if t not in migration_order]
    full_order = migration_order + sorted(remaining)

    # Also add old-only tables that have schema (we'll dump with --create-info)
    full_order = full_order + tables_old_only

    for table in full_order:
        if table in SKIP_TABLES:
            skipped.append(table)
            continue

        old_count = get_row_count(old_client, old_db, table, "OLD")
        if old_count == 0:
            print(f"\n  [{table}] Skipping (0 rows on old server)")
            skipped.append(table)
            continue

        exists_on_new = table in new_tables

        # Step 1: Dump from old server
        print(f"\n  [{table}] Dumping {old_count} rows from old server...")

        if exists_on_new:
            # Data only — new server already has the schema
            dump_cmd = (
                f"mysqldump --no-create-info --skip-add-locks --skip-disable-keys "
                f"--skip-triggers --default-character-set=utf8mb4 "
                f"--single-transaction "
                f"-u {old_db['db_user']} -p'{old_db['db_pass']}' -h {old_db['db_host']} "
                f"{old_db['db_name']} {table} 2>/dev/null"
            )
        else:
            # Schema + data — table doesn't exist on new server
            dump_cmd = (
                f"mysqldump --default-character-set=utf8mb4 --single-transaction "
                f"-u {old_db['db_user']} -p'{old_db['db_pass']}' -h {old_db['db_host']} "
                f"{old_db['db_name']} {table} 2>/dev/null"
            )

        # Dump to file on old server
        old_dump_path = f"/tmp/migrate_{table}.sql"
        run(old_client, f"{dump_cmd} > {old_dump_path}", f"dump {table}", quiet=True)

        # Step 2: SFTP pull to local
        sftp_old = old_client.open_sftp()
        local_path = f"/tmp/migrate_{table}.sql"
        sftp_old.get(old_dump_path, local_path)
        sftp_old.close()
        file_size = os.path.getsize(local_path)

        # Step 3: SFTP push to new server
        sftp_new = new_client.open_sftp()
        new_dump_path = f"/tmp/migrate_{table}.sql"
        sftp_new.put(local_path, new_dump_path)
        sftp_new.close()

        # Clean up temp files
        run(old_client, f"rm -f {old_dump_path}", quiet=True)
        os.remove(local_path)

        # Step 4: Import on new server
        print(f"  [{table}] Importing {file_size} bytes to new server...")

        # Use INSERT IGNORE to avoid clobbering existing rows (e.g. the 'support' user)
        import_cmd = (
            f"mysql --default-character-set=utf8mb4 "
            f"-u {new_db['db_user']} -p'{new_db['db_pass']}' -h {new_db['db_host']} "
            f"{new_db['db_name']} -e \"SET FOREIGN_KEY_CHECKS=0; "
            f"SOURCE {new_dump_path}; "
            f"SET FOREIGN_KEY_CHECKS=1;\" 2>&1"
        )

        # Actually, SOURCE only works in interactive mysql. Use < redirect.
        import_cmd = (
            f"mysql --default-character-set=utf8mb4 "
            f"-u {new_db['db_user']} -p'{new_db['db_pass']}' -h {new_db['db_host']} "
            f"{new_db['db_name']} < {new_dump_path} 2>&1"
        )

        # Prepend FK disable
        # For truncated tables, use plain INSERT (no IGNORE needed — tables are empty)
        # For non-truncated app tables, use INSERT IGNORE to avoid clobbering
        if table in TRUNCATE_TABLES:
            # Plain INSERT — table was truncated, no conflicts possible
            pass
        elif exists_on_new:
            # Convert INSERT to INSERT IGNORE for app tables that weren't truncated
            sed_cmd = f"sed -i 's/^INSERT INTO/INSERT IGNORE INTO/' {new_dump_path}"
            run(new_client, sed_cmd, quiet=True)

        # Wrap with FK checks disabled
        fk_prefix = f"echo 'SET FOREIGN_KEY_CHECKS=0;' > /tmp/migrate_import_{table}.sql && cat {new_dump_path} >> /tmp/migrate_import_{table}.sql && echo 'SET FOREIGN_KEY_CHECKS=1;' >> /tmp/migrate_import_{table}.sql"
        run(new_client, fk_prefix, quiet=True)

        import_cmd = (
            f"mysql --default-character-set=utf8mb4 "
            f"-u {new_db['db_user']} -p'{new_db['db_pass']}' -h {new_db['db_host']} "
            f"{new_db['db_name']} < /tmp/migrate_import_{table}.sql 2>&1"
        )

        _, err, code = run(new_client, import_cmd, f"import {table}", timeout=300, quiet=True)

        # Clean up
        run(new_client, f"rm -f {new_dump_path} /tmp/migrate_import_{table}.sql", quiet=True)

        if code == 0:
            new_count = get_row_count(new_client, new_db, table, "NEW")
            match = "MATCH" if new_count == old_count else f"MISMATCH (old={old_count}, new={new_count})"
            print(f"  [{table}] OK — old={old_count}, new={new_count} {match}")
            migrated.append({"table": table, "old": old_count, "new": new_count})
        else:
            print(f"  [{table}] ERROR — {err[:200]}")
            errors.append({"table": table, "error": err[:200]})

    # --- Reset auto-increment values on truncated tables ---
    # After importing old data, auto-increment must be set above the max imported ID
    # to prevent future inserts from colliding with imported IDs
    print("\n  --- Resetting auto-increment values ---")
    ai_tables = {
        "oc_filecache": "fileid",
        "oc_share": "id",
        "oc_storages": "numeric_id",
        "oc_mounts": "id",
        "oc_authtoken": "id",
    }
    for table, col in ai_tables.items():
        ai_cmd = (
            f"mysql -u {new_db['db_user']} -p'{new_db['db_pass']}' -h {new_db['db_host']} "
            f"{new_db['db_name']} -e \"SET @max_id = (SELECT COALESCE(MAX({col}),0)+1 FROM {table}); "
            f"SET @sql = CONCAT('ALTER TABLE {table} AUTO_INCREMENT = ', @max_id); "
            f"PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;\" 2>/dev/null"
        )
        run(new_client, ai_cmd, f"auto-increment {table}", quiet=True)

    # --- Summary ---
    print("\n" + "=" * 70)
    print("DATABASE MIGRATION SUMMARY")
    print("=" * 70)
    print(f"  Migrated: {len(migrated)} tables")
    print(f"  Skipped:  {len(skipped)} tables (0 rows or system config)")
    print(f"  Errors:   {len(errors)} tables")

    if errors:
        print("\n  Tables with errors:")
        for e in errors:
            print(f"    {e['table']}: {e['error']}")

    # Write table-sync report
    report_path = os.path.join(os.path.dirname(__file__), "docs", "05-database-migration-report.md")
    with open(report_path, "w") as f:
        f.write("# Database Migration Report\n\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("## Tables Synced\n\n")
        f.write("| Table | Old rows | New rows | Status |\n")
        f.write("|-------|----------|----------|--------|\n")
        for m in migrated:
            status = "OK" if m["old"] == m["new"] else "MISMATCH"
            f.write(f"| `{m['table']}` | {m['old']} | {m['new']} | {status} |\n")
        f.write(f"\n## Skipped ({len(skipped)} tables)\n\n")
        for s in skipped:
            f.write(f"- `{s}`\n")
        if errors:
            f.write(f"\n## Errors ({len(errors)} tables)\n\n")
            for e in errors:
                f.write(f"- `{e['table']}`: {e['error']}\n")
    print(f"\n  Report written to: {report_path}")

    return len(errors) == 0

# ============================================================================
# PHASE 6: STORAGE PATH REWRITE
# ============================================================================

def phase_storage(old_client, new_client, dry_run=False):
    """Rewrite oc_storages paths on the new server to point at the new data dir."""
    print("\n" + "=" * 70)
    print("PHASE 6: STORAGE PATH REWRITE")
    print("=" * 70)

    old_path = OLD_SERVER["datadir"]   # /var/www/nextcloud/data
    new_path = NEW_SERVER["datadir"]   # /www/wwwroot/cloud.amarisstock.com-data
    old_instance = OLD_SERVER["instanceid"]  # oczvho61glg2
    new_instance = NEW_SERVER["instanceid"]  # ocmu0qdk9tdd

    print(f"\n  Old data path: {old_path}")
    print(f"  New data path: {new_path}")
    print(f"  Old instanceid: {old_instance}")
    print(f"  New instanceid: {new_instance}")

    # Show current storages
    db = NEW_SERVER
    show_cmd = (
        f"mysql -u {db['db_user']} -p'{db['db_pass']}' -h {db['db_host']} "
        f"{db['db_name']} -e \"SELECT id, available, last_scan FROM oc_storages WHERE id LIKE 'local::%' LIMIT 30;\" 2>/dev/null"
    )
    run(new_client, show_cmd, "current storages")

    if dry_run:
        print("\n  [DRY RUN] Would execute these UPDATEs on oc_storages:")
        print(f"    UPDATE oc_storages SET id = REPLACE(id, '{old_path}', '{new_path}') WHERE id LIKE 'local::%{old_path}%';")
        print(f"    UPDATE oc_storages SET id = REPLACE(id, '::{old_path}', '::{new_path}') WHERE id LIKE '%{old_path}%';")
        # Also fix appdata references
        print(f"    -- Fix appdata path: appdata_{old_instance} -> appdata_{new_instance}")
        print(f"    UPDATE oc_storages SET id = REPLACE(id, 'appdata_{old_instance}', 'appdata_{new_instance}') WHERE id LIKE '%appdata_{old_instance}%';")
        print(f"\n  [DRY RUN] Would re-encrypt 20 mail account passwords")
        print(f"    (decrypt with old server secret, re-encrypt with new server secret)")
        print(f"    Affects: oc_mail_accounts.inbound_password, outbound_password, sieve_password")
        return True

    # Execute the rewrites
    updates = [
        f"UPDATE oc_storages SET id = REPLACE(id, '{old_path}', '{new_path}') WHERE id LIKE 'local::%{old_path}%'",
        f"UPDATE oc_storages SET id = REPLACE(id, '::{old_path}', '::{new_path}') WHERE id LIKE '%{old_path}%'",
        f"UPDATE oc_storages SET id = REPLACE(id, 'appdata_{old_instance}', 'appdata_{new_instance}') WHERE id LIKE '%appdata_{old_instance}%'",
    ]

    for sql in updates:
        cmd = (
            f"mysql -u {db['db_user']} -p'{db['db_pass']}' -h {db['db_host']} "
            f"{db['db_name']} -e \"{sql}\" 2>/dev/null"
        )
        run(new_client, cmd, "UPDATE storages")

    # Verify
    run(new_client, show_cmd, "storages after rewrite")

    # --- Re-encrypt Mail app passwords (old secret → new secret) ---
    # The Mail app stores IMAP/SMTP passwords encrypted with the server's `secret`.
    # Since old and new servers have different secrets, we must re-encrypt.
    # See docs/encrypted-credentials.md for full analysis.
    print(f"\n  --- Re-encrypting Mail app passwords (old secret → new secret) ---")
    reencrypt_php = r'''<?php
// Re-encrypt Mail app passwords from old server secret to new server secret
// Uses Nextcloud's own OC\Security\Crypto class via full framework bootstrap
// Nextcloud 34 uses PSR container: OC::$server->get(IConfig::class)
require_once "lib/base.php";

$newSecret = \OC::$server->get(\OCP\IConfig::class)->getSystemValue("secret");
$oldSecret = getenv("OLD_NC_SECRET");
if (!$oldSecret) {
    echo "ERROR: OLD_NC_SECRET environment variable not set\n";
    exit(1);
}

echo "Old secret length: " . strlen($oldSecret) . "\n";
echo "New secret length: " . strlen($newSecret) . "\n";

$crypto = \OC::$server->get(\OCP\Security\ICrypto::class);
$db = \OC::$server->get(\OCP\IDBConnection::class);

try {
    $count = $db->executeQuery("SELECT COUNT(*) FROM oc_mail_accounts")->fetchColumn();
    echo "Mail accounts found: " . $count . "\n";
} catch (Exception $e) {
    echo "ERROR: oc_mail_accounts table not found - Mail app not installed yet?\n";
    echo $e->getMessage() . "\n";
    exit(1);
}

if ($count == 0) {
    echo "No mail accounts to re-encrypt - skipping\n";
    exit(0);
}

$accounts = $db->executeQuery("SELECT id, inbound_password, outbound_password, sieve_password FROM oc_mail_accounts")->fetchAll();

$reencrypted = 0;
$errors = 0;

foreach ($accounts as $account) {
    $id = $account["id"];
    $newInbound = null;
    $newOutbound = null;
    $newSieve = null;

    try {
        if (!empty($account["inbound_password"])) {
            $decrypted = $crypto->decrypt($account["inbound_password"], $oldSecret);
            $newInbound = $crypto->encrypt($decrypted, $newSecret);
        }
        if (!empty($account["outbound_password"])) {
            $decrypted = $crypto->decrypt($account["outbound_password"], $oldSecret);
            $newOutbound = $crypto->encrypt($decrypted, $newSecret);
        }
        if (!empty($account["sieve_password"])) {
            $decrypted = $crypto->decrypt($account["sieve_password"], $oldSecret);
            $newSieve = $crypto->encrypt($decrypted, $newSecret);
        }

        $db->executeQuery(
            "UPDATE oc_mail_accounts SET inbound_password = ?, outbound_password = ?, sieve_password = ? WHERE id = ?",
            [$newInbound, $newOutbound, $newSieve, $id]
        );
        $reencrypted++;
        echo "  Account id=$id: OK\n";
    } catch (Exception $e) {
        $errors++;
        echo "  Account id=$id: FAILED - " . $e->getMessage() . "\n";
    }
}

echo "\nRe-encrypted: $reencrypted accounts, Errors: $errors\n";
if ($errors > 0) {
    exit(1);
}
?>'''

    if dry_run:
        print("    [DRY RUN] Would re-encrypt 20 mail account passwords")
        print("    (decrypt with old secret, re-encrypt with new secret)")
        print(r"    Uses Nextcloud's OC\Security\Crypto via lib/base.php bootstrap")
        return True

    # Write the PHP script to the new server
    sftp = new_client.open_sftp()
    with sftp.file("/tmp/reencrypt_mail.php", "w") as f:
        f.write(reencrypt_php)
    sftp.close()

    # Get the old server's secret
    old_secret_out, _, _ = run(
        old_client,
        f"grep -oP \"\\'secret\\' => '\\K[^']*'\" {OLD_SERVER['webroot']}/config/config.php",
        "get old secret", quiet=True,
    )
    old_secret = old_secret_out.strip()

    if not old_secret:
        print("    ERROR: Could not read old server's secret — skipping re-encryption")
        print("    Mail passwords will need manual re-entry after migration")
    else:
        print(f"    Old secret read ({len(old_secret)} chars)")
        # Run on new server: cd to webroot, export env var, use sudo -E to preserve it for www
        cmd = (
            f"cd {NEW_SERVER['webroot']} && "
            f"export OLD_NC_SECRET='{old_secret}' && "
            f"sudo -E -u {NEW_SERVER['web_user']} php /tmp/reencrypt_mail.php 2>&1"
        )
        run(new_client, cmd, "re-encrypt mail passwords", timeout=120)

    # Clean up
    run(new_client, "rm -f /tmp/reencrypt_mail.php", quiet=True)

    # Run maintenance:repair
    print(f"\n  Running occ maintenance:repair...")
    run(new_client, f"{NEW_SERVER['occ']} maintenance:repair", "repair", timeout=300)

    # Add missing indices
    run(new_client, f"{NEW_SERVER['occ']} db:add-missing-indices", "add-indices", timeout=120)
    run(new_client, f"{NEW_SERVER['occ']} db:add-missing-columns", "add-columns", timeout=120)
    run(new_client, f"{NEW_SERVER['occ']} db:add-missing-primary-keys", "add-pks", timeout=120)

    return True

# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Nextcloud Data Migration via paramiko")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, no mutations")
    parser.add_argument("--phase", choices=["apps", "db", "storage", "all"], default="all",
                        help="Which phase to run")
    args = parser.parse_args()

    print("=" * 70)
    print("NEXTCLOUD DATA MIGRATION")
    print("=" * 70)
    print(f"  Old server: {OLD_SERVER['host']} ({OLD_SERVER['webroot']})")
    print(f"  New server: {NEW_SERVER['host']} ({NEW_SERVER['webroot']})")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"  Phase: {args.phase}")

    # Connect to both servers
    old_client = connect(OLD_SERVER, "OLD")
    new_client = connect(NEW_SERVER, "NEW")

    success = True

    if args.phase in ("apps", "all"):
        success = phase_apps(old_client, new_client, dry_run=args.dry_run) and success

    if args.phase in ("db", "all"):
        success = phase_db(old_client, new_client, dry_run=args.dry_run) and success

    if args.phase in ("storage", "all"):
        success = phase_storage(old_client, new_client, dry_run=args.dry_run) and success

    print("\n" + "=" * 70)
    print(f"MIGRATION {'COMPLETE' if success else 'COMPLETED WITH ERRORS'}")
    print("=" * 70)

    old_client.close()
    new_client.close()

    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
