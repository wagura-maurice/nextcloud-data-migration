# Encrypted Credentials Migration — Critical Finding

> Investigated: 2026-09-09
> Finding: The Mail app stores IMAP/SMTP passwords **encrypted with the server's `secret`** from `config.php`.
> The old and new servers have **different secrets**, so these passwords CANNOT be directly copied.

---

## The Problem

Nextcloud's `OC\Security\Crypto` class encrypts sensitive data using the server's `secret`
(from `config.php`). The encryption format is: `iv|ciphertext|hmac` (visible as hex with `|` separators).

| Server | Secret (first 20 chars) |
|--------|------------------------|
| Old | `$OLD_SERVER_SECRET` (redacted) |
| New | `$NEW_SERVER_SECRET` (redacted) |

When `oc_mail_accounts` is copied to the new server, the `inbound_password` and `outbound_password`
columns contain ciphertext encrypted with the **old** secret. The new server's Mail app will try to
decrypt with the **new** secret and **fail** — users won't be able to sync email.

---

## Affected Tables (with data)

| Table | Rows | Encrypted columns | Severity |
|-------|------|-------------------|----------|
| `oc_mail_accounts` | 20 | `inbound_password`, `outbound_password` | **CRITICAL** — 20 mail accounts will break |
| `oc_talk_bots_server` | 9 | `secret` | **No issue** — these are plain bot API secrets (base64), not encrypted with server secret |
| `oc_talk_rooms` | 73 | `password` | **No issue** — 0 rooms have passwords set |
| `oc_talk_attendees` | 84 | `access_token` | **No issue** — all tokens are NULL |

Tables checked and confirmed empty (no encrypted data to worry about):
- `oc_mail_provisionings` (0 rows)
- `oc_twofactor_totp_secrets` (0 rows — no TOTP users)
- `oc_login_flow_v2` (0 rows — no pending login flows)
- `oc_oauth2_access_tokens` (0 rows)
- `oc_oauth2_clients` (0 rows)
- `oc_trusted_servers` (0 rows — no federated servers)
- `oc_ex_apps` (0 rows)
- `oc_circles_token` (0 rows)
- `oc_sms_relent_settings` (0 rows)

---

## The 20 Affected Mail Accounts

```
id  user_id                        email
1   Amaris Chemical Solutions      chem@amarissolutions.com
2   Amaris Hardware Solutions      hardware@amarissolutions.com
3   Amaris Chemical Solutions      chemsales@amarissolutions.com
4   Amaris Chemical Solutions      chemimport@amarissolutions.com
5   Amaris FMCG Solutions          fmcg@amarissolutions.com
6   Amaris Beauty Solutions        beauty@amarissolutions.com
7   Amaris Medical Solutions       med@amarissolutions.com
8   Amaris Digital Solutions       digital@amarissolutions.com
9   Victor Mwangi Mbuthia          victor@amarissolutions.com
10  Hilda Nyambura Rubiro          hilda@amarissolutions.com
11  Justus Weru Irungu             justus@amarissolutions.com
12  Faith Mutethya Mwendwa         faithmutethya1@amarissolutions.com
13  Amaris Beauty Solutions        beautysuppliers@amarissolutions.com
14  Onesmus kyalo Kithuku          onesmus@amarissolutions.com
15  Onesmus kyalo Kithuku          onesmus@amarissolutions.com
16  Amaris Medical Solutions       medsales@amarissolutions.com
17  Robert G Irungu                robert@amarissolutions.com
18  Colin                          colin@amarissolutions.com
19  Justus Weru Irungu             chemsuppliers@amarissolutions.com
20  Mike Mbithi Mbithuka           mikembithi@amarissolutions.com
```

All use `@amarissolutions.com` mail servers. The IMAP/SMTP host/port/user configs are plain text
and will migrate fine — only the passwords need re-encryption.

---

## The Fix: Re-encrypt Passwords During Migration

After Phase 4 (DB import) and before Phase 7 (activation), run a PHP script on the
**new server** that:

1. Reads each encrypted password from `oc_mail_accounts` (still encrypted with old secret)
2. Decrypts using the **old** server's secret
3. Re-encrypts using the **new** server's secret
4. Updates the row

This must run on the new server because it needs access to the new server's `secret` and
Nextcloud's `OC\Security\Crypto` class.

### Implementation

The fix is added to `migrate.py` as Phase 6.5 (after storage rewrite, before repair):

```php
// PHP script run via occ on the new server
// 1. Get old secret (passed as parameter)
// 2. For each mail account:
//    a. Read encrypted password (encrypted with OLD secret)
//    b. Decrypt with OLD secret using OC\Security\Crypto
//    c. Re-encrypt with NEW secret (the new server's config secret)
//    d. UPDATE oc_mail_accounts SET inbound_password = ?, outbound_password = ? WHERE id = ?
```

### Why Not Copy the Old Secret?

Copying the old server's `secret` to the new server would:
- Violate the migration requirement (don't overwrite new server's system config)
- Compromise security (the secret protects all encrypted data on the server)
- Break other encrypted data on the new server (oc_appconfig, etc.)

Re-encryption is the only correct approach.

---

## Other Encrypted Data (Not Affected)

| Data type | Where | Encrypted? | Issue? |
|-----------|-------|-----------|--------|
| User login passwords | `oc_users.password` | Yes (argon2id hash, NOT encrypted with secret) | No — hashes are self-contained |
| Share passwords | `oc_share.password` | No (plain or hashed) | No |
| App passwords (oc_authtoken) | `oc_authtoken.password` | Yes, but... | No — these are hash, not encrypted |
| Talk room passwords | `oc_talk_rooms.password` | No | No (0 rooms have passwords) |
| Talk bot secrets | `oc_talk_bots_server.secret` | No (plain base64) | No |
| OAuth tokens | `oc_oauth2_access_tokens` | Yes, but 0 rows | No |
| TOTP secrets | `oc_twofactor_totp_secrets` | Yes, but 0 rows | No |
| Federated server secrets | `oc_trusted_servers.shared_secret` | Yes, but 0 rows | No |

**Only `oc_mail_accounts` has encrypted data that needs re-encryption.**
