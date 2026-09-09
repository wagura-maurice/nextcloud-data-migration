#!/usr/bin/env python3
"""Neutralize static-asset regex locations in the office.amarisstock.com nginx vhost.

The vhost is a pure reverse proxy to the OnlyOffice Document Server on
127.0.0.1:8000. Two regex `location` blocks for images and js/css have no
proxy_pass, and because nginx prefers regex locations over the prefix
`location /`, every .js/.css/.png request was served from local disk and
returned 404. That broke web-apps/apps/api/documents/api.js, which the
OnlyOffice editor loads in the browser.
"""

import re
import shutil
import subprocess
import sys

VHOST = "/www/server/panel/vhost/nginx/office.amarisstock.com.conf"
BACKUP = VHOST + ".bak-before-static-fix"

BLOCK_RE = re.compile(
    r"^[ \t]*location\s+~\s+\.\*\\\.\((?:gif\|jpg\|jpeg\|png\|bmp\|swf|js\|css)\)\??\$[^\n]*\n"
    r"[ \t]*\{\n"
    r"(?:[^\n]*\n)*?"
    r"[ \t]*\}\n",
    re.MULTILINE,
)

MARKER = "# STATIC-ASSET LOCATIONS DISABLED (reverse-proxy site)"


def comment_block(match: re.Match) -> str:
    body = match.group(0)
    commented = "".join("    #" + line.lstrip() + "\n" for line in body.splitlines())
    return f"    {MARKER}\n{commented}"


def main() -> int:
    with open(VHOST, encoding="utf-8") as handle:
        original = handle.read()

    if MARKER in original:
        print("Already patched; nothing to do.")
        return 0

    patched, count = BLOCK_RE.subn(comment_block, original)
    if count == 0:
        print("ERROR: no static-asset location blocks matched.", file=sys.stderr)
        return 1

    shutil.copy2(VHOST, BACKUP)
    with open(VHOST, "w", encoding="utf-8") as handle:
        handle.write(patched)
    print(f"Commented out {count} static-asset location block(s).")
    print(f"Backup written to {BACKUP}")

    test = subprocess.run(
        ["nginx", "-t"], capture_output=True, text=True, check=False
    )
    print(test.stderr.strip())
    if test.returncode != 0:
        shutil.copy2(BACKUP, VHOST)
        print("nginx config test FAILED - reverted.", file=sys.stderr)
        return 1

    reload_result = subprocess.run(
        ["nginx", "-s", "reload"], capture_output=True, text=True, check=False
    )
    if reload_result.returncode != 0:
        print(reload_result.stderr.strip(), file=sys.stderr)
        return 1
    print("nginx reloaded successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
