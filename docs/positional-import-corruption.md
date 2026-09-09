# Positional Import Corruption and Repair

## Incident

During the initial Nextcloud data migration, database tables were imported
using `mysqldump` **without** the `--complete-insert` flag. This produces
`INSERT INTO table VALUES (...)` statements that rely on positional column
ordering. When the source and destination schemas have different column orders
(due to different app versions or migration histories), values are silently
written to the wrong columns.

## Affected Tables

Three tables were corrupted:

| Table | Rows | Positions Differing | Symptoms |
|-------|-----:|---------------------|----------|
| `oc_mail_accounts` | 20 | 41 | `user_id` contained email addresses; all password fields empty |
| `oc_tables_columns` | 129 | 16 | `usergroup_default` contained integer `0` instead of empty string/NULL |
| `oc_tables_shares` | 20 | 9 | `created_at` became `0000-00-00 00:00:00`; `token` became `1` |

### Specific corruption examples

- `oc_mail_accounts.user_id` contained an email address instead of the user ID
- `oc_mail_accounts.email` contained the inbound host
- `oc_mail_accounts.inbound_port` contained `ssl`
- `oc_mail_accounts.outbound_host` contained a timestamp
- All 20 inbound and outbound Mail password fields were empty
- `oc_tables_columns.usergroup_default` contained `0` (integer), causing:
  ```
  Return value must be of type array, int returned
  ```
- `oc_tables_shares.created_at` contained `0000-00-00 00:00:00`
- `oc_tables_shares.token` contained `1` instead of `NULL`

## Root Cause

`mysqldump` without `--complete-insert` generates:

```sql
INSERT INTO `oc_mail_accounts` VALUES (1,'user@example.com','imap.host.com',...);
```

If the destination table has columns in a different order, each value lands in
the wrong column with no error — MySQL does not validate column-name alignment
for positional inserts.

## Fix Applied

1. Enabled maintenance mode on both servers to freeze data.
2. Backed up corrupted destination rows to
   `/root/backup-corrupt-tables-2026-09-09-173012.sql`.
3. Re-dumped the three source tables with `mysqldump --complete-insert`, which
   generates explicit column lists:
   ```sql
   INSERT INTO `oc_mail_accounts` (`id`,`user_id`,`email`,...) VALUES (...);
   ```
4. Verified dump integrity and expected row counts.
5. Truncated the three affected destination tables.
6. Imported the explicit-column dumps.
7. Re-encrypted all Mail account passwords (source secret → destination
   secret) using Nextcloud's `ICrypto` service.
8. Verified all three tables against source (row counts + key column values).
9. Confirmed no corrupted integer values remain in `usergroup_default`.
10. Ran cron and setup checks — no errors in log.
11. Disabled maintenance mode on destination.

## Prevention

The migration script (`migrate.py`) has been updated to:

- Use `--complete-insert` on all `mysqldump` commands.
- Run a column-order audit before importing, comparing `SHOW COLUMNS` output
  from source and destination to detect schema mismatches.

## Mail Password Re-encryption

Mail app passwords are encrypted with the instance `secret` from `config.php`.
Since source and destination have different secrets, imported ciphertext
cannot be decrypted on the destination until re-encrypted:

1. Decrypt each password with the source instance secret.
2. Re-encrypt the plaintext with the destination instance secret.
3. Update `inbound_password`, `outbound_password`, and `sieve_password`.

The source secret is transferred via a 0600 temporary file and deleted
immediately after use. Plaintext is never printed or logged.
