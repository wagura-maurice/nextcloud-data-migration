#!/usr/bin/env python3
"""
Readiness sweep — verifies all prerequisites for the paramiko migration script.
Does NOT mutate anything on either server.
"""
import paramiko
import sys
import json
from pathlib import Path

# --- Load credentials from .env ---
def load_env():
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

# --- Connection config (loaded from .env) ---
OLD_HOST = _env.get("OLD_SERVER_HOST", "38.242.141.240")
NEW_HOST = _env.get("NEW_SERVER_HOST", "164.68.104.123")
SSH_PORT = int(_env.get("OLD_SERVER_PORT", "22"))
SSH_USER = _env.get("OLD_SERVER_USER", "root")
SSH_KEY = "/root/.ssh/id_ed25519"

# Old server (local) DB
OLD_DB = {
    "host": _env.get("OLD_SERVER_DB_HOST", "127.0.0.1"),
    "name": _env.get("OLD_SERVER_DB_NAME", "nextcloud"),
    "user": _env.get("OLD_SERVER_DB_USER", "nextcloud"),
    "password": _env.get("OLD_SERVER_DB_PASS", ""),
}

# New server DB
NEW_DB = {
    "host": _env.get("NEW_SERVER_DB_HOST", "127.0.0.1"),
    "name": _env.get("NEW_SERVER_DB_NAME", "sql_cloud_amarisstock_com"),
    "user": _env.get("NEW_SERVER_DB_USER", "sql_cloud_amarisstock_com"),
    "password": _env.get("NEW_SERVER_DB_PASS", ""),
}

# occ invocation
_old_webroot = _env.get("OLD_SERVER_WEBROOT", "/var/www/nextcloud")
_old_web_user = _env.get("OLD_SERVER_WEB_USER", "www-data")
_new_webroot = _env.get("NEW_SERVER_WEBROOT", "/www/wwwroot/cloud.amarisstock.com")
_new_web_user = _env.get("NEW_SERVER_WEB_USER", "www")
OLD_OCC = f"cd {_old_webroot} && sudo -u {_old_web_user} php occ"
NEW_OCC = f"cd {_new_webroot} && sudo -u {_new_web_user} php occ"

def ssh_connect(host, port, user, password, label):
    """Connect via paramiko and return the client."""
    print(f"\n{'='*60}")
    print(f"[{label}] Connecting to {user}@{host}:{port} ...")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, port=port, username=user, key_filename=SSH_KEY, timeout=15)
        print(f"  SSH: OK")
        return client
    except Exception as e:
        print(f"  SSH: FAILED — {e}")
        return None

def run_cmd(client, cmd, label="", timeout=30):
    """Run a command via SSH and return (stdout, stderr, exit_code)."""
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace").strip()
        err = stderr.read().decode("utf-8", errors="replace").strip()
        code = stdout.channel.recv_exit_status()
        if label:
            status = "OK" if code == 0 else "FAIL"
            print(f"  [{label}] {status} (exit {code})")
            if out and len(out) < 500:
                print(f"    {out}")
            elif out:
                print(f"    {out[:200]}... ({len(out)} bytes)")
            if err and code != 0:
                print(f"    STDERR: {err[:300]}")
        return out, err, code
    except Exception as e:
        print(f"  [{label}] ERROR — {e}")
        return "", str(e), -1

def main():
    results = {}

    # --- 1. SSH connectivity ---
    print("\n" + "="*60)
    print("PHASE A: SSH CONNECTIVITY")
    old_client = ssh_connect(OLD_HOST, SSH_PORT, SSH_USER, None, "OLD SERVER")
    new_client = ssh_connect(NEW_HOST, SSH_PORT, SSH_USER, None, "NEW SERVER")
    results["ssh_old"] = old_client is not None
    results["ssh_new"] = new_client is not None

    if not results["ssh_old"] or not results["ssh_new"]:
        print("\nFATAL: Cannot connect to one or both servers. Aborting sweep.")
        sys.exit(1)

    # --- 2. occ invocation ---
    print("\n" + "="*60)
    print("PHASE B: OCC INVOCATION")
    old_status, _, _ = run_cmd(old_client, f"{OLD_OCC} status", "OLD occ status")
    new_status, _, _ = run_cmd(new_client, f"{NEW_OCC} status", "NEW occ status")
    results["occ_old"] = "version" in old_status.lower()
    results["occ_new"] = "version" in new_status.lower()

    # --- 3. DB access ---
    print("\n" + "="*60)
    print("PHASE C: DATABASE ACCESS")
    old_db_cmd = f"mysql -u {OLD_DB['user']} -p'{OLD_DB['password']}' -h {OLD_DB['host']} {OLD_DB['name']} -e 'SELECT COUNT(*) AS user_count FROM oc_users;'"
    new_db_cmd = f"mysql -u {NEW_DB['user']} -p'{NEW_DB['password']}' -h {NEW_DB['host']} {NEW_DB['name']} -e 'SELECT COUNT(*) AS user_count FROM oc_users;'"
    old_db, old_db_err, old_db_code = run_cmd(old_client, old_db_cmd, "OLD DB query")
    new_db, new_db_err, new_db_code = run_cmd(new_client, new_db_cmd, "NEW DB query")
    results["db_old"] = old_db_code == 0
    results["db_new"] = new_db_code == 0

    # --- 4. mysqldump availability ---
    print("\n" + "="*60)
    print("PHASE D: MYSQLDUMP AVAILABILITY")
    run_cmd(old_client, "which mysqldump && mysqldump --version", "OLD mysqldump")
    run_cmd(new_client, "which mysqldump && mysqldump --version", "NEW mysqldump")

    # --- 5. SFTP (file transfer) test ---
    print("\n" + "="*60)
    print("PHASE E: SFTP (file transfer) test")
    try:
        sftp_old = old_client.open_sftp()
        print("  [OLD SFTP] OK")
        sftp_old.close()
        results["sftp_old"] = True
    except Exception as e:
        print(f"  [OLD SFTP] FAIL — {e}")
        results["sftp_old"] = False
    try:
        sftp_new = new_client.open_sftp()
        print("  [NEW SFTP] OK")
        sftp_new.close()
        results["sftp_new"] = True
    except Exception as e:
        print(f"  [NEW SFTP] FAIL — {e}")
        results["sftp_new"] = False

    # --- 6. Disk space on new server ---
    print("\n" + "="*60)
    print("PHASE F: DISK SPACE (NEW SERVER)")
    run_cmd(new_client, "df -h /www/wwwroot/cloud.amarisstock.com-data", "NEW free space")

    # --- 7. Enumerate tables on old server ---
    print("\n" + "="*60)
    print("PHASE G: TABLE ENUMERATION (OLD SERVER)")
    tables_cmd = f"mysql -u {OLD_DB['user']} -p'{OLD_DB['password']}' -h {OLD_DB['host']} {OLD_DB['name']} -N -e 'SHOW TABLES;'"
    old_tables_out, _, _ = run_cmd(old_client, tables_cmd, "OLD table list", timeout=30)
    old_tables = [t for t in old_tables_out.split("\n") if t.strip()]
    print(f"  Total tables on old server: {len(old_tables)}")

    # Check which of our target tables exist
    target_tables = [
        "oc_users", "oc_accounts", "oc_preferences",
        "oc_authtoken",
        "oc_groups", "oc_group_user", "oc_group_admin",
        "oc_share", "oc_share_external", "oc_filecache", "oc_storages", "oc_mounts",
    ]
    print(f"\n  Core target tables:")
    for t in target_tables:
        exists = t in old_tables
        print(f"    {'YES' if exists else 'MISSING'}  {t}")
        results[f"table_{t}"] = exists

    # App-specific tables (check a sample)
    app_table_patterns = [
        "oc_calendar", "oc_addressbooks", "oc_cards", "oc_cards_properties",
        "oc_notes", "oc_bookmarks", "oc_group_folders",
        "oc_polls", "oc_forms", "oc_tables",
        "oc_mail", "oc_maps", "oc_collectives",
        "oc_systemtags", "oc_systemtag",
    ]
    print(f"\n  App-specific tables (sample check):")
    found_app_tables = []
    for pat in app_table_patterns:
        matches = [t for t in old_tables if t.startswith(pat)]
        if matches:
            print(f"    {pat}*  -> {len(matches)} tables: {matches[:5]}{'...' if len(matches)>5 else ''}")
            found_app_tables.extend(matches)
        else:
            print(f"    {pat}*  -> none")
    results["app_tables_found"] = len(found_app_tables)

    # --- 8. Check new server tables exist (schema parity) ---
    print("\n" + "="*60)
    print("PHASE H: NEW SERVER TABLE SCHEMA (sample)")
    new_tables_cmd = f"mysql -u {NEW_DB['user']} -p'{NEW_DB['password']}' -h {NEW_DB['host']} {NEW_DB['name']} -N -e 'SHOW TABLES;'"
    new_tables_out, _, _ = run_cmd(new_client, new_tables_cmd, "NEW table list", timeout=30)
    new_tables = [t for t in new_tables_out.split("\n") if t.strip()]
    print(f"  Total tables on new server: {len(new_tables)}")
    for t in target_tables:
        exists = t in new_tables
        print(f"    {'YES' if exists else 'MISSING'}  {t}")

    # --- 9. Check for user UID collision ---
    print("\n" + "="*60)
    print("PHASE I: USER UID COLLISION CHECK")
    old_uids_cmd = f"mysql -u {OLD_DB['user']} -p'{OLD_DB['password']}' -h {OLD_DB['host']} {OLD_DB['name']} -N -e 'SELECT uid FROM oc_users;'"
    new_uids_cmd = f"mysql -u {NEW_DB['user']} -p'{NEW_DB['password']}' -h {NEW_DB['host']} {NEW_DB['name']} -N -e 'SELECT uid FROM oc_users;'"
    old_uids_out, _, _ = run_cmd(old_client, old_uids_cmd, "OLD uids")
    new_uids_out, _, _ = run_cmd(new_client, new_uids_cmd, "NEW uids")
    old_uids = set(u.strip() for u in old_uids_out.split("\n") if u.strip())
    new_uids = set(u.strip() for u in new_uids_out.split("\n") if u.strip())
    collisions = old_uids & new_uids
    if collisions:
        print(f"  COLLISION: {collisions}")
    else:
        print(f"  No UID collisions (old={len(old_uids)}, new={len(new_uids)})")
    results["uid_collisions"] = len(collisions)

    # --- 10. Maintenance mode status ---
    print("\n" + "="*60)
    print("PHASE J: MAINTENANCE MODE STATUS (current)")
    run_cmd(old_client, f"{OLD_OCC} maintenance:mode", "OLD maintenance")
    run_cmd(new_client, f"{NEW_OCC} maintenance:mode", "NEW maintenance")

    # --- Summary ---
    print("\n" + "="*60)
    print("SWEEP SUMMARY")
    all_ok = True
    for key, val in results.items():
        if isinstance(val, bool):
            status = "OK" if val else "FAIL"
            if not val:
                all_ok = False
            print(f"  {key}: {status}")
        elif isinstance(val, int) and key == "uid_collisions":
            status = "OK" if val == 0 else "WARN"
            if val > 0:
                all_ok = False
            print(f"  {key}: {val} ({status})")
        elif isinstance(val, int):
            print(f"  {key}: {val}")
    print(f"\n  Overall: {'ALL CHECKS PASSED' if all_ok else 'ISSUES FOUND — review above'}")

    old_client.close()
    new_client.close()
    print("\nSweep complete.")

if __name__ == "__main__":
    main()
