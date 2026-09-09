# Forms App Migration — Investigation & Verification Report

**Date:** 2026-09-09
**Source (old):** https://cloud.amarissolutions.com/ — `38.242.141.240` — Forms app **v5.3.5**
**Target (new):** https://cloud.amarisstock.com/ — `164.68.104.123` — Forms app **v5.3.6**

---

## 1. Storage architecture (path correction)

The request referenced files "located at `https://cloud.amarissolutions.com/apps/forms/`".
That URL is the **web route** to the Forms application, not a file-storage location.

The Forms app does **not** store user files under `apps/forms/`. Per the app source
(`apps/forms/lib/Helper/FilePathHelper.php` and `apps/forms/lib/Constants.php`),
uploaded files are written into the **form owner's** home directory under a top-level
`Forms/` folder, with this layout:

```
<datadir>/<owner>/Forms/<formId> - <title>/<submissionId>/<questionId> - <questionName>/<uploaded_file>
```

Constants of note:
- `Constants::FILES_FOLDER = 'Forms'`
- `Constants::UNSUBMITTED_FILES_FOLDER = 'Forms/unsubmitted'` (in-progress uploads before submit)
- `oc_forms_v2_uploaded_files` table tracks each uploaded file (form_id, original_file_name, file_id, question_id, upload_token)

There is **no** `apps/forms/` directory inside user data on either server.

---

## 2. Old server findings (cloud.amarissolutions.com)

### 2.1 Forms database tables

| Table | Rows | Notes |
|-------|------|-------|
| `oc_forms_v2_forms` | 4 | All have empty `title`/`description`; `file_id`/`file_format` NULL |
| `oc_forms_v2_questions` | 0 | No questions — therefore no `file`-type upload questions |
| `oc_forms_v2_options` | 0 | — |
| `oc_forms_v2_submissions` | 0 | — |
| `oc_forms_v2_answers` | 0 | — |
| `oc_forms_v2_uploaded_files` | 0 | No uploaded files |
| `oc_forms_v2_shares` | 1 | Form 1, `share_type=3` (link), token `fC3f34YzrdiWojHbLQpJp45K`, perms `["submit"]` |

### 2.2 Form owners (the users who "have existing forms")

| Form ID | Hash | Owner |
|---------|------|-------|
| 1 | `E28RmpK6F4THSLof` | Amaris Admin |
| 2 | `mS86PgzHRWg9Jgm3` | Justus Weru Irungu |
| 3 | `NJxAxp3Y9oSmn3Tk` | Justus Weru Irungu |
| 4 | `rDkzFwT5wB3dGZWW` | Lilian wacuka Nguru |

Three distinct users own forms: **Amaris Admin**, **Justus Weru Irungu**, **Lilian wacuka Nguru**.

### 2.3 On-disk file check (old)

- `find /var/www/nextcloud/data -maxdepth 3 -iname "Forms"` → **none**
- `oc_filecache` rows with `path LIKE 'Forms%'` or `LIKE '%/Forms/%'` → **0**
- `appdata_oczvho61glg2` forms content → **none**

**There are zero Forms-uploaded files on disk.** The 4 forms are empty skeletons
(created but never given questions, submissions, or file uploads).

---

## 3. New server findings (cloud.amarisstock.com)

The Forms database tables have **already been migrated** (as part of the broader
Phase 4 DB migration). Forms 1–4 are present with identical hashes and owners, plus
a 5th form created on the new server itself.

| Form ID | Hash | Owner | Origin |
|---------|------|-------|--------|
| 1 | `E28RmpK6F4THSLof` | Amaris Admin | migrated from old |
| 2 | `mS86PgzHRWg9Jgm3` | Justus Weru Irungu | migrated from old |
| 3 | `NJxAxp3Y9oSmn3Tk` | Justus Weru Irungu | migrated from old |
| 4 | `rDkzFwT5wB3dGZWW` | Lilian wacuka Nguru | migrated from old |
| 5 | `6M9m52p3tQPQyJTr` | Amaris Admin | new (created on target) |

All three form-owner users exist on the new server. The link share for form 1 is
present with the identical token. No questions, submissions, or uploaded files on
the new server; no `Forms/` folders on disk.

---

## 4. Row-by-row verification (forms 1–4)

A full `SELECT *` comparison of `oc_forms_v2_forms` (ids 1–4) and `oc_forms_v2_shares`
(form_id 1–4) was performed between both servers. **Every column matches exactly**,
including: `hash`, `title`, `description`, `owner_id`, `created`, `expires`,
`is_anonymous`, `submit_multiple`, `show_expiration`, `last_updated`,
`submission_message`, `file_id`, `file_format`, `state`, `access_enum`,
`allow_edit_submissions`, `locked_by`, `locked_until`, `max_submissions`,
`confirmation_email_*`, `allow_comments`, and the share's `permissions_json`.

| Check | Old | New | Match |
|-------|-----|-----|-------|
| `oc_forms_v2_forms` rows 1–4 (all columns) | 4 | 4 | identical |
| `oc_forms_v2_shares` (form 1) | 1 | 1 | identical |
| `oc_forms_v2_questions` count | 0 | 0 | identical |
| `oc_forms_v2_options` count | 0 | 0 | identical |
| `oc_forms_v2_submissions` count | 0 | 0 | identical |
| `oc_forms_v2_answers` count | 0 | 0 | identical |
| `oc_forms_v2_uploaded_files` count | 0 | 0 | identical |
| Forms app enabled | yes | yes | identical |
| Forms app version | 5.3.5 | 5.3.6 | expected diff (target newer) |

**Result: zero drift. No reconciliation was required.**

Note: form 1 carries a stale, expired edit lock (`locked_by = Amaris Admin`,
`locked_until = 1783439035`, already in the past). It is identical on both servers
and harmless, so it was left as-is.

Form 5 on the new server (hash `6M9m52p3tQPQyJTr`, owner `Amaris Admin`) does not
exist on the old server. Per the approved decision it is **preserved untouched**.

---

## 5. File-mapping guarantee (file transfer)

**No file transfer is required**, because there are no Forms-uploaded files on the
old server to transfer. This was confirmed on both servers:

- No `Forms/` directory exists in any user's data directory.
- `oc_filecache` contains zero `Forms`-related rows.
- `oc_forms_v2_uploaded_files` is empty on both servers.

The file-mapping guarantee is therefore trivially satisfied: the per-user
`<datadir>/<owner>/Forms/...` tree is empty on the source, so the corresponding
target tree is also correctly empty. The form **definitions** (which determine
where any future uploaded files would be written) are already present on the
target and owned by the correct users, so any files uploaded after cutover will
automatically land in the correct user's `Forms/` folder on the new instance.

---

## 6. Recommendations

1. **No file-migration action needed.** There are no Forms-uploaded files on the
   source. The forms DB tables are already migrated and verified identical.
2. **No further DB reconciliation needed.** Forms 1–4 and the share match exactly;
   form 5 is preserved as a new-server-native form.
3. **App version parity is acceptable.** Target runs Forms v5.3.6 (one patch newer
   than source v5.3.5); schema is compatible (same `oc_forms_v2_*` tables/columns).
4. **Optional cleanup:** the stale expired lock on form 1 (`locked_by`/`locked_until`)
   could be cleared on both servers for tidiness, but it has no functional impact.
5. **Forward-looking note:** if users add `file`-type questions and collect
   submissions **before** the old server is decommissioned, those uploads would
   appear under `<datadir>/<owner>/Forms/...` on the old server and would need an
   rsync of the per-user `Forms/` tree to the new server's matching user directory,
   followed by `occ files:scan --path="<owner>/Forms"` on the target. As of this
   report, that tree is empty, so no such step is scheduled.

---

## 7. Conclusion

The Forms app migration is effectively complete:
- Form definitions and shares: migrated and verified identical (forms 1–4).
- Form-owner users: present on the target.
- Uploaded files: none exist on either server — no file transfer required.
- File-mapping guarantee: satisfied (source tree empty → target tree correctly empty;
  definitions already owned by correct users for any future uploads).

No further action is required for the Forms app unless new file-upload submissions
are collected on the old server before it is decommissioned.
