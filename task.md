# Nextcloud Mail (SMTP) Configuration — Status

## SMTP is now fully configured

All SMTP settings have been applied to the destination Nextcloud server.
A test email was sent and confirmed delivered to `admin@amarissolutions.com`.

### Configured settings

| Setting | Value |
|---------|-------|
| `mail_smtpmode` | `smtp` |
| `mail_sendmailmode` | `smtp` |
| `mail_smtpsecure` | `ssl` |
| `mail_smtphost` | `mail.amarissolutions.com` |
| `mail_smtpport` | `465` |
| `mail_smtpauth` | `1` |
| `mail_smtpname` | `noreply@amarissolutions.com` |
| `mail_smtppassword` | *(set — stored encrypted in database)* |
| `mail_domain` | `amarissolutions.com` |
| `mail_from_address` | `noreply` |

### Mail server setup

A dedicated mailbox `noreply@amarissolutions.com` was created on the mail
server (`144.91.109.222`) via the aaPanel PostfixAdmin SQLite database for
Nextcloud system notifications (password resets, activity notifications, etc.).

### Verification results

- SMTP authentication: **235 2.7.0 Authentication successful**
- Test email sent via Nextcloud `IMailer`: **delivered**
- Mail log on `144.91.109.222` confirms delivery to `admin@amarissolutions.com`
- Setup checks: **Mail Transport configuration: PASS**, **Mail connection performance: PASS**

## What you still need to do

### 1. Verify email in the Nextcloud web UI (browser-only step)

The "Email test" informational item in setup checks can only be cleared by
sending a test email through the web interface:

1. Log in to **https://cloud.amarisstock.com** as admin
2. Go to **Settings → Administration → Basic settings → Email server**
3. Click **Send email**

This will mark the SMTP configuration as verified and remove the
informational warning from the admin overview.

### 2. Set your admin email address

If you want notifications and password resets to reach you, ensure your admin
account has a valid email address set:

1. Go to **Profile picture (top right) → Personal settings → Email**
2. Enter your email address (e.g. `admin@amarissolutions.com`)
3. Click **Save**

Or via CLI:

```bash
cd /www/wwwroot/cloud.amarisstock.com
sudo -u www php occ user:setting admin settings email admin@amarissolutions.com
```

### 3. Check other users' email addresses

Migrated users should already have their email addresses from the source
server. Verify a few key users have correct emails set in their Nextcloud
profile settings.

## Security notes

- The `mail_smtppassword` is stored encrypted in the Nextcloud database
  (`oc_appconfig`), not in `config.php`.
- The `noreply@amarissolutions.com` mailbox password is set on the mail server
  and should not be shared with end users.
- Do **not** commit SMTP credentials to the repository.
