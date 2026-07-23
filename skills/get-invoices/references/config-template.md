# Config Template

Resolve the user's config in this order:

1. `GET_INVOICES_CONFIG`
2. `~/.config/get-invoices/config.md`
3. `config.md` beside `SKILL.md` for backward compatibility

When creating a config for a new user, use `~/.config/get-invoices/config.md` with this structure:

```markdown
# Get Invoices Config

## Destination
paperless

## Paperless
- URL: env:PAPERLESS_URL
- Token: env:PAPERLESS_TOKEN
- Default tags: <invoice-tag-id>
- Default document type: <invoice-document-type-id>
- Remove tags after ingest: <transient-tag-id>
- API endpoint: {url}/api/documents/post_document/

## Provider tags
- provider-slug: <provider-tag-id>

## Provider correspondents
- provider-slug: <correspondent-id>

## Local
- Chrome Download Directory: ~/Downloads/
- Download Path: ~/Downloads/invoices/
- File Naming: YYYY-MM_Provider_InvoiceNumber.pdf
- Log File: {download_path}/get-invoices.log

## Preferred Billing Email
billing@example.com
```

## Fields

| Field | What it does |
|---|---|
| `Destination` | `paperless` to upload via Paperless-ngx API; `local` to save renamed PDFs in a folder. The skill dispatches to one of the matching blocks below. |
| `Paperless > URL / Token` | Use `env:VARNAME` references so secrets remain in the user's environment. Do not store tokens inside a distributed skill or plugin. |
| `Paperless > Default tags` | Comma-separated tag IDs added to every uploaded document. The inbox tag can be added by a Paperless workflow; don't duplicate it here. |
| `Paperless > Default document type` | Optional existing Paperless document-type ID used for every fetched invoice. Do not create or guess IDs automatically. |
| `Paperless > Remove tags after ingest` | Optional comma-separated transient tag IDs to remove after Paperless finishes processing. Preserve all other tags. Use this for workflow-added inbox/review-queue tags that should not remain on filed invoices. |
| `Provider tags` | Optional per-user Paperless company tag IDs keyed by provider slug. This overrides a legacy `company_tag` in a provider recipe. |
| `Provider correspondents` | Optional existing Paperless correspondent IDs keyed by provider slug. Resolve or create them only with user authorization, then keep IDs in user config. |
| `Local > Chrome Download Directory` | Only used as a fallback. The in-browser fetch path doesn't depend on it. |
| `Local > Download Path` | Where renamed PDFs end up when `Destination: local`. |
| `Local > File Naming` | Pattern for renamed files. Provider files can override. |
| `Local > Log File` | Source of truth for duplicate detection across runs. |
| `Preferred Billing Email` | The email Learn Mode offers when it discovers a billing-email setting on a new provider. Often a Paperless email-ingest address or an accountant's inbox. |

## First Run Setup

Ask the user during first run:
1. **Destination** — `paperless` or `local`? Default: `local`.
2. **If paperless:** URL and token (or env var names). Confirm the token has document-upload permission.
3. **If Paperless:** ask for the existing invoice document-type ID and whether ingestion workflows add transient tags that should be removed after filing.
4. **If local:** download path, Chrome download directory (if non-default), naming pattern.
5. **Preferred billing email** — used in Learn Mode prompts. Skip if the user prefers to always paste a fresh one.
6. **Provider tags and correspondents** — add them as providers are learned; do not put user-specific IDs into bundled provider files.

Create the config outside the installed skill/plugin directory so plugin upgrades cannot overwrite it. Restrict its filesystem permissions when it contains private paths or email addresses. Keep the adjacent `config.md` lookup only for existing Claude Code installations.
