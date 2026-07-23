# Destinations

Once the skill has captured PDF bytes (via [interceptor.js](interceptor.js) or, as a fallback, from the Chrome download folder), it dispatches them to the destination set in `config.md`.

Adding a new destination = a new section here + a new dispatch block in [SKILL.md](../SKILL.md) under workflow step 10.

## paperless

POST the PDF to Paperless-ngx's document-ingest endpoint. The endpoint returns a **task UUID** (string) and processes the upload asynchronously — Paperless's consumer worker handles OCR, hash-dedup, and tag application after the response returns.

### Endpoint
`POST {PAPERLESS_URL}/api/documents/post_document/`

Authentication: `Authorization: Token {PAPERLESS_TOKEN}`. The skill expects these in environment variables — never inline secrets into config.md.

### Request

`multipart/form-data` with:

| Field | Notes |
|---|---|
| `document` | The PDF file. With curl: `-F "document=@/path/to/file.pdf"`. With raw bytes: send as a file part. |
| `title` | Display title in Paperless. Use the skill's naming pattern, e.g. `2026-04_ExampleProvider_INV-1234` (no `.pdf` extension — Paperless adds it). |
| `tags` | Tag IDs as integers. Repeat the field for multiple tags: `-F "tags=123" -F "tags=456"`. |
| `correspondent` | Optional integer ID from the user's `Provider correspondents` mapping. Never guess or embed account-specific IDs in a bundled provider. |
| `document_type` | Optional integer ID from `Paperless > Default document type`; invoices can be filed as the user's existing Rechnung type. |
| `created` | Optional ISO date if you can scrape it from the invoice list. Otherwise Paperless infers from content. |

### Tags policy

The skill applies only the "obviously true" tags at upload:

- **Default tags from config.md** (for example, the user's invoice tag) — applied to every upload.
- **Provider tag from user config** — applied per provider. A legacy `company_tag` in a user provider file is a fallback; bundled recipes should not contain account-specific tag IDs.

After Paperless finishes ingestion, reconcile the document to the configured default document type/provider correspondent and `(current tags ∪ default/provider tags) − cleanup tags`. Preserve every unrelated tag, including classifications added by Paperless workflows. Use `scripts/paperless-reconcile.py` so this mutation is deterministic and idempotent.

The skill does NOT apply:
- Transient workflow tags such as `inbox` — omit them on upload and remove them after ingestion when their IDs are listed in `Remove tags after ingest`.
- Unconfigured classification tags, custom fields, storage paths, or ownership changes.

### Curl example

```bash
source ~/.env.secrets   # exports PAPERLESS_URL, PAPERLESS_TOKEN
curl -sS -X POST \
  -H "Authorization: Token $PAPERLESS_TOKEN" \
  -F "document=@/path/to/invoice.pdf" \
  -F "title=2026-04_ExampleProvider_INV-1234" \
  -F "tags=123" -F "tags=456" \
  "$PAPERLESS_URL/api/documents/post_document/"
# → "<task-uuid>"   (task UUID, async)
```

### Duplicate handling

Paperless rejects byte-identical uploads via SHA-256 checksum — the task moves to "Failed Tasks" with a `it is a duplicate of …` message. The skill should:

1. Pre-check via the skill's own log (`get-invoices.log`) — if the invoice ID was previously uploaded successfully, skip.
2. Before downloading, query Paperless by invoice number and compare the computed title when available. Accept only one unambiguous result containing both provider and exact invoice number; allow a different title for a manually uploaded document. When that document exists, skip the upload and reconcile its configured document type/correspondent and tags, then record the Paperless document ID.
3. Trust Paperless's checksum dedup as a safety net — if the task fails as a byte-identical duplicate, resolve the existing document and log it as a skip rather than an error.

### Verification

The POST returns a task UUID immediately, but queueing is not completion. For every upload:

1. Poll the task endpoint or query documents by exact invoice number/title until the new document is available. Use the user's `paperless` MCP when available; otherwise use `GET {PAPERLESS_URL}/api/tasks/?task_id=<uuid>` and the document API.
2. Require exactly one confirmed document for the provider and invoice number. Do not guess when results are ambiguous.
3. Run `scripts/paperless-reconcile.py` with the resolved document ID, required default/provider tag IDs, cleanup tag IDs, and configured correspondent/document-type IDs. The helper reads current metadata before patching, adds missing required tags, removes only cleanup tags, preserves every unrelated tag, and sets only explicitly configured classification fields.
4. Re-read the document and confirm the cleanup IDs are absent, required tags remain, and configured classification IDs match.
5. Append the dedup log with the verified Paperless document ID.

If verification or configured cleanup fails, report the upload as incomplete and keep the temporary PDF for a retry. Do not append a success row to the dedup log.

## local

Save the PDF bytes to a renamed file under `{download_path}/{provider}/`.

### Pattern

1. Decode the captured base64 to bytes (or use the file in Chrome's download dir as a fallback).
2. Compute the destination filename using `File Naming` from config.md. Provider files can override.
3. Create the provider subdirectory if missing.
4. Write the bytes.
5. Append a line to `Log File`:
   ```
   YYYY-MM-DD HH:MM | provider | invoice_number | invoice_date | amount | filename
   ```

### Naming examples

| Pattern | Result |
|---|---|
| `YYYY-MM_Provider_InvoiceNumber.pdf` | `2026-04_ExampleProvider_INV-1234.pdf` |
| `YYYY-MM-DD_Provider_InvoiceNumber.pdf` | `2026-04-08_ExampleProvider_INV-1234.pdf` |

For invoices that produce multiple PDFs (e.g. Beleg + Einzelverbindungsnachweis), append a suffix from the provider file's `extra_documents` list.

### Duplicate handling

Skip when either durable duplicate signal matches:

1. **Log file**: row with same `provider | invoice_number`.
2. **File system**: file with the computed destination name already exists.

If the log doesn't exist yet, the file-system check alone is enough. If the log matches but the file is missing, report the inconsistency and skip unless the user explicitly requests restoration.
