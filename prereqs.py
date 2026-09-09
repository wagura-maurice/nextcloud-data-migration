#!/usr/bin/env python3
"""
Pre-Migration Prerequisites Script
===================================
Run this BEFORE starting the migration. It performs one-time system
configuration fixes on the NEW server that the migration script (migrate.py)
should not be responsible for.

These are infrastructure-level fixes that:
  - Need to be done once, not as part of data migration
  - Require root-level system changes (groups, services, config files)
  - Should persist after the migration is complete

Usage:
    python3 prereqs.py --dry-run    # Show what would be done
    python3 prereqs.py             # Execute all fixes
    python3 prereqs.py --check     # Only verify current state (no changes)

Based on findings in docs/final-sweep-report.md
"""

import argparse
import subprocess
import sys
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

# --- Server config (loaded from .env) ---
NEW_SERVER = {
    "host": _env.get("NEW_SERVER_HOST", "164.68.104.123"),
    "port": int(_env.get("NEW_SERVER_PORT", "22")),
    "user": _env.get("NEW_SERVER_USER", "root"),
    "password": _env.get("NEW_SERVER_SSH_PASS", ""),
    "web_user": _env.get("NEW_SERVER_WEB_USER", "www"),
    "webroot": _env.get("NEW_SERVER_WEBROOT", "/www/wwwroot/cloud.amarisstock.com"),
    "datadir": _env.get("NEW_SERVER_DATADIR", "/www/wwwroot/cloud.amarisstock.com-data"),
    "php_fpm_service": _env.get("NEW_SERVER_PHP_FPM_SERVICE", "php-fpm-84"),
    "nginx_conf": _env.get("NEW_SERVER_NGINX_CONF", "/www/server/nginx/conf/nginx.conf"),
    "nginx_vhost": "/www/server/panel/vhost/nginx/cloud.amarisstock.com.conf",
}


def ssh_run(cmd, dry_run=False, quiet=False):
    """Run a command on the new server via SSH."""
    full_cmd = (
        f"sshpass -p '{NEW_SERVER['password']}' "
        f"ssh -o StrictHostKeyChecking=no -p {NEW_SERVER['port']} "
        f"{NEW_SERVER['user']}@{NEW_SERVER['host']} '{cmd}'"
    )
    if dry_run:
        if not quiet:
            print(f"    [DRY] {cmd}")
        return "", "", 0
    result = subprocess.run(
        full_cmd, shell=True, capture_output=True, text=True, timeout=60
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def check_state():
    """Verify current state of all prerequisites on the new server."""
    print("=" * 70)
    print("PREREQUISITES CHECK — New Server State")
    print("=" * 70)

    all_ok = True

    # Check 1: www in docker group
    print("\n1. Docker group membership for www user")
    out, _, _ = ssh_run("id www")
    print(f"   {out}")
    if "docker" in out:
        print("   STATUS: OK")
    else:
        print("   STATUS: NEEDS FIX")
        all_ok = False

    # Check 2: www can access docker.sock
    print("\n2. www can access /var/run/docker.sock")
    out_r, _, _ = ssh_run("sudo -u www test -r /var/run/docker.sock && echo YES || echo NO")
    out_w, _, _ = ssh_run("sudo -u www test -w /var/run/docker.sock && echo YES || echo NO")
    print(f"   Read: {out_r}, Write: {out_w}")
    if out_r == "YES" and out_w == "YES":
        print("   STATUS: OK")
    else:
        print("   STATUS: NEEDS FIX")
        all_ok = False

    # Check 3: PHP-FPM running
    print(f"\n3. PHP-FPM service ({NEW_SERVER['php_fpm_service']})")
    out, _, _ = ssh_run(f"systemctl is-active {NEW_SERVER['php_fpm_service']}")
    print(f"   {out}")
    if out == "active":
        print("   STATUS: OK")
    else:
        print("   STATUS: NEEDS FIX (restart)")
        all_ok = False

    # Check 4: Nginx client_max_body_size
    print("\n4. Nginx client_max_body_size")
    out, _, _ = ssh_run(
        f"grep 'client_max_body_size' {NEW_SERVER['nginx_conf']}"
    )
    print(f"   {out}")
    if "16g" in out.lower():
        print("   STATUS: OK")
    else:
        print("   STATUS: OPTIONAL FIX (50m → 16g for large file uploads)")

    # Check 5: Docker containers running
    print("\n5. Docker containers on new server")
    out, _, _ = ssh_run("sudo -u www docker ps --format table")
    print(f"   {out}")
    if "onlyoffice" in out and "nats" in out:
        print("   STATUS: OK (OnlyOffice + NATS running)")
    else:
        print("   STATUS: WARNING — expected onlyoffice-ds and nats-server")

    # Check 6: Signaling service
    print("\n6. Signaling service (Talk HPB)")
    out, _, _ = ssh_run("systemctl is-active signaling")
    print(f"   {out}")
    if out == "active":
        print("   STATUS: OK")
    else:
        print("   STATUS: NEEDS FIX")

    # Check 7: app_api daemon
    print("\n7. app_api daemon configuration")
    out, _, _ = ssh_run(
        f"cd {NEW_SERVER['webroot']} && sudo -u www php occ app_api:daemon:list 2>&1 | head -3"
    )
    print(f"   {out}")
    if "No registered daemon" in out:
        print("   STATUS: NEEDS SETUP (post-migration — see Issue #2 in sweep report)")
    elif "harp" in out.lower():
        print("   STATUS: OK")
    else:
        print(f"   STATUS: UNKNOWN — check manually")

    # Check 8: Maintenance mode
    print("\n8. Maintenance mode")
    out, _, _ = ssh_run(
        f"cd {NEW_SERVER['webroot']} && sudo -u www php occ maintenance:mode 2>&1"
    )
    print(f"   {out}")
    if "disabled" in out:
        print("   STATUS: OK (should be off before Phase 1)")
    elif "enabled" in out:
        print("   STATUS: WARNING — maintenance mode is ON")
    else:
        print("   STATUS: UNKNOWN")

    print("\n" + "=" * 70)
    if all_ok:
        print("ALL PREREQUISITES MET — ready to start Phase 1")
    else:
        print("SOME PREREQUISITES NEED FIXING — run: python3 prereqs.py")
    print("=" * 70)

    return all_ok


def fix_docker_group(dry_run=False):
    """Fix 1: Add www to docker group and restart PHP-FPM."""
    print("\n--- Fix 1: Add www to docker group ---")

    # Check if already fixed
    out, _, _ = ssh_run("id www")
    if "docker" in out and not dry_run:
        print("   Already in docker group — skipping")
        return

    print("   Adding www to docker group...")
    ssh_run("usermod -aG docker www", dry_run=dry_run)

    print("   Restarting PHP-FPM...")
    ssh_run(
        f"systemctl restart {NEW_SERVER['php_fpm_service']} 2>/dev/null || "
        f"/etc/init.d/{NEW_SERVER['php_fpm_service']} restart 2>/dev/null",
        dry_run=dry_run,
    )

    if not dry_run:
        # Verify
        out, _, _ = ssh_run("id www")
        print(f"   Verify: {out}")
        out_r, _, _ = ssh_run(
            "sudo -u www test -r /var/run/docker.sock && echo YES || echo NO"
        )
        out_w, _, _ = ssh_run(
            "sudo -u www test -w /var/run/docker.sock && echo YES || echo NO"
        )
        print(f"   docker.sock access: read={out_r}, write={out_w}")
        if "docker" in out and out_r == "YES" and out_w == "YES":
            print("   STATUS: FIXED")
        else:
            print("   STATUS: FAILED — check manually")


def fix_nginx_upload_limit(dry_run=False):
    """Fix 2 (optional): Increase Nginx client_max_body_size for large uploads."""
    print("\n--- Fix 2 (optional): Nginx upload limit ---")

    # Check current value
    out, _, _ = ssh_run(
        f"grep 'client_max_body_size' {NEW_SERVER['nginx_conf']}"
    )
    if "16g" in out.lower() and not dry_run:
        print("   Already set to 16g — skipping")
        return

    print(f"   Current: {out}")
    print("   Changing 50m → 16g...")
    ssh_run(
        f"sed -i s/client_max_body_size\\ 50m/client_max_body_size\\ 16g/ "
        f"{NEW_SERVER['nginx_conf']}",
        dry_run=dry_run,
    )
    print("   Reloading Nginx...")
    ssh_run("nginx -s reload 2>/dev/null || systemctl reload nginx", dry_run=dry_run)

    if not dry_run:
        out, _, _ = ssh_run(
            f"grep 'client_max_body_size' {NEW_SERVER['nginx_conf']}"
        )
        print(f"   Verify: {out}")


def fix_php_fpm_restart(dry_run=False):
    """Fix 3: Ensure PHP-FPM is running."""
    print("\n--- Fix 3: Ensure PHP-FPM is running ---")

    out, _, _ = ssh_run(f"systemctl is-active {NEW_SERVER['php_fpm_service']}")
    print(f"   Current: {out}")

    if out == "active" and not dry_run:
        print("   Already running — skipping")
        return

    print("   Starting PHP-FPM...")
    ssh_run(
        f"systemctl start {NEW_SERVER['php_fpm_service']} 2>/dev/null || "
        f"/etc/init.d/{NEW_SERVER['php_fpm_service']} start 2>/dev/null",
        dry_run=dry_run,
    )

    if not dry_run:
        out, _, _ = ssh_run(f"systemctl is-active {NEW_SERVER['php_fpm_service']}")
        print(f"   Verify: {out}")


def run_all_fixes(dry_run=False):
    """Run all prerequisite fixes."""
    print("=" * 70)
    print("PREREQUISITES FIX — New Server Setup")
    print("=" * 70)
    print(f"  Server: {NEW_SERVER['host']}")
    print(f"  Web user: {NEW_SERVER['web_user']}")
    if dry_run:
        print("  Mode: DRY RUN (no changes)")

    fix_docker_group(dry_run)
    fix_php_fpm_restart(dry_run)
    fix_nginx_upload_limit(dry_run)

    print("\n" + "=" * 70)
    if dry_run:
        print("DRY RUN COMPLETE — run without --dry-run to apply")
    else:
        print("ALL FIXES APPLIED — verifying...")
        check_state()
    print("=" * 70)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pre-migration prerequisites fix for the new server"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Show what would be done without changes"
    )
    parser.add_argument(
        "--check", action="store_true", help="Only check state, don't fix anything"
    )
    args = parser.parse_args()

    if args.check:
        ok = check_state()
        sys.exit(0 if ok else 1)
    else:
        run_all_fixes(dry_run=args.dry_run)
