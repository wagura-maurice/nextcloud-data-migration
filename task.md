# Nextcloud Mail (SMTP) Configuration — Your Tasks

## Investigation findings

The mail server for all Amaris email operations is **mail.amarissolutions.com**
(resolves to `144.91.109.222` — a separate VPS from both Nextcloud instances).

### What was found on the destination VPS (164.68.104.123)

| Location | What | Status |
|----------|------|--------|
| `oc_mail_accounts` (Nextcloud Mail app) | 20 per-user IMAP/SMTP accounts, all using `mail.amarissolutions.com` | Migrated and re-encrypted — passwords are SET and decrypt correctly |
| `oc_appconfig` (system-level SMTP) | `mail_smtpmode`, `mail_sendmailmode`, `mail_domain`, `mail_from_address` | Partially configured (non-secret values only) |
| BT Panel (`stmp_mail.json`, `mail_list.json`) | Panel-level mail config | Both empty `[]` |
| `/etc/` system mail (postfix, msmtp, ssmtp) | System mail transport | Not installed |

### What was found on the source VPS (38.242.141.240)

| Location | What | Status |
|----------|------|--------|
| `config.php` | `mail_smtpmode=smtp`, `mail_sendmailmode=smtp`, `mail_smtpsecure=ssl` | Basic settings only — no host, port, or credentials |
| `oc_appconfig` | Only `mail_providers_enabled=1` | No SMTP host or credentials were ever configured |
| System mail software | postfix, dovecot, msmtp | Not installed |

### Conclusion

**No system-level SMTP credentials for `mail.amarissolutions.com` are stored on
either VPS.** The source server never had a fully configured system-level SMTP.
The per-user Mail app credentials (IMAP/SMTP passwords) were migrated
successfully, but the system-level SMTP (for notifications, password resets,
etc.) needs to be configured from scratch.

The mail server at `144.91.109.222` is not accessible with the SSH credentials
available for the Nextcloud VPS instances.

---

## Already configured on destination

| Setting | Value |
|---------|-------|
| `mail_smtpmode` | `smtp` |
| `mail_sendmailmode` | `smtp` |
| `mail_domain` | `amarissolutions.com` |
| `mail_from_address` | `noreply` |

## What you need to do

### 1. Gather your SMTP credentials for mail.amarissolutions.com

You need the following from the mail server administrator or hosting provider
for `mail.amarissolutions.com` (`144.91.109.222`):

- **SMTP host**: `mail.amarissolutions.com`
- **SMTP port**: likely `465` (SSL) or `587` (STARTTLS) — confirm with your mail admin
- **Encryption type**: `ssl` or `tls` — confirm with your mail admin
- **SMTP username**: a mailbox address on the amarissolutions.com domain
  (e.g. `noreply@amarissolutions.com` or a dedicated account)
- **SMTP password**: the password for that mailbox

### 2. Apply the settings in Nextcloud

Log in to **https://cloud.amarisstock.com** as an admin, then go to:

**Settings → Administration → Basic settings → Email server**

Enter the SMTP host, port, security, username, and password in the form.

Alternatively, run these commands on the destination server
(replace the `<...>` placeholders with your values):

```bash
cd /www/wwwroot/cloud.amarisstock.com

sudo -u www php occ config:app:set core mail_smtphost --value="mail.amarissolutions.com"
sudo -u www php occ config:app:set core mail_smtpport --value="<465_or_587>"
sudo -u www php occ config:app:set core mail_smtpsecure --value="<ssl_or_tls>"
sudo -u www php occ config:app:set core mail_smtpauth --value=1
sudo -u www php occ config:app:set core mail_smtpname --value="<SMTP_USERNAME>"
sudo -u www php occ config:app:set core mail_smtppassword --value="<SMTP_PASSWORD>"
```

### 3. Send a test email

In **Basic settings → Email server**, click **Send email** to verify the
configuration works.

Or via CLI:

```bash
cd /www/wwwroot/cloud.amarisstock.com
sudo -u www php occ user:setting <your_admin_username> settings email <your_email@amarissolutions.com>
sudo -u www php occ test:mail <your_admin_username>
```

Check the inbox for the test message from `noreply@amarissolutions.com`.

### 4. Verify

- Confirm the test email arrives in your inbox.
- Check the Nextcloud log for any SMTP errors:

```bash
tail -20 /www/wwwroot/cloud.amarisstock.com-data/nextcloud.log
```

- Re-run setup checks — the "Email test" informational item should disappear:

```bash
cd /www/wwwroot/cloud.amarisstock.com
sudo -u www php occ setupchecks
```

## Security notes

- Do **not** commit SMTP credentials to the repository.
- The `mail_smtppassword` is stored encrypted in the Nextcloud database
  (`oc_appconfig`), not in `config.php`.
- If your mail server supports app-specific passwords, use one instead of a
  main account password.
