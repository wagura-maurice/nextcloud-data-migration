# Nextcloud Mail (SMTP) Configuration — Your Tasks

The non-secret SMTP settings have already been configured on the destination
server. The remaining steps require credentials only you can provide.

## Already configured

| Setting | Value |
|---------|-------|
| `mail_smtpmode` | `smtp` |
| `mail_sendmailmode` | `smtp` |
| `mail_domain` | `amarisstock.com` |
| `mail_from_address` | `noreply` |

## What you need to do

### 1. Gather your SMTP credentials

You need the following from your email provider (e.g. your hosting provider,
Google Workspace, Microsoft 365, etc.):

- **SMTP host** (e.g. `smtp.gmail.com`, `smtp.office365.com`)
- **SMTP port** (typically `465` for SSL, or `587` for STARTTLS)
- **Encryption type** (`ssl` or `tls`)
- **SMTP username** (usually the full email address)
- **SMTP password** (or app-specific password if 2FA is enabled on the mail account)

### 2. Apply the settings in Nextcloud

Log in to **https://cloud.amarisstock.com** as an admin, then go to:

**Profile picture (top right) → Personal settings → Email**

Or configure via the admin panel:

**Settings → Administration → Basic settings → Email server**

Enter the SMTP host, port, security, username, and password in the form.

Alternatively, run these commands on the destination server
(replace the `<...>` placeholders with your values):

```bash
cd /www/wwwroot/cloud.amarisstock.com

sudo -u www php occ config:app:set core mail_smtphost --value="<SMTP_HOST>"
sudo -u www php occ config:app:set core mail_smtpport --value="<SMTP_PORT>"
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
sudo -u www php occ user:setting <your_admin_username> settings email <your_email@example.com>
sudo -u www php occ test:mail <your_admin_username>
```

Check the inbox for the test message from `noreply@amarisstock.com`.

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
- If your email provider supports app-specific passwords (e.g. Gmail), use one
  instead of your main account password.
