---
# ── Shareable fields ─────────────────────────────────────────────────────────
# These are the ONLY fields allowed in bundled/contributed recipes (they
# describe the website, not any user's account). See SKILL.md § Contribute.

# Required
name: Provider Name
description: One-line description of what this provider bills for
domain: provider.example.com
url: https://provider.example.com/billing

# Recommended — billing email capability, discovered by Learn Mode
billing_email_supported: unknown   # true | false | unknown
billing_email_url:                 # path or full URL where the setting lives

# Recommended — interception pattern (filled in by Learn Mode after first successful run)
download_pattern:                  # fetch-blob | anchor-direct | anchor-blob | window-open |
                                   # anchor-redirect-pdf-viewer | os-download
                                   # which interceptor hook captured the bytes
extraction_bridge:                 # clipboard | chunked-base64 | direct-nav | cdp-bridge | os-download
                                   # how the bytes crossed from page to disk (see SKILL.md § Extraction Bridges)

# ── Personal fields ──────────────────────────────────────────────────────────
# Only valid in a user's own provider file (~/.config/get-invoices/providers/).
# NEVER in bundled recipes or contributions.

billing_email_set:                 # YYYY-MM-DD (when configured) | no | not-supported

# Legacy — prefer the user config's Provider tags mapping
company_tag:           # Optional per-user Paperless tag ID.
---

# Provider Name

## Navigation

1. Go to https://provider.example.com/billing
2. Click "Invoices" in the sidebar
3. The invoice list shows date, number, amount, and a download button per row

## Loading Behavior

(Optional: describe what to wait for before scraping)
- Example: "Page is a SPA — wait for the invoice table to appear (~3-5s)"
- Example: "Shows a loading spinner for 1-2 seconds after navigation"
- If the page loads instantly with server-rendered HTML, you can omit this section.

## Download

Each row has a PDF download icon/link. Click it to download the invoice.

**Button details:** Describe size and position of the download button. If multiple buttons in a row share the same visible text (e.g. two "PDF" buttons for Beleg vs Einzelverbindungsnachweis), document the column order — `find` cannot disambiguate them by column hint and the skill will need to use button-index in the row.

**Interception pattern** (filled in after Learn Mode):
- What the page does when the button is clicked. Examples:
  - `fetch-blob`: page calls `fetch()` against a (signed) URL, wraps response in `URL.createObjectURL`, then synthetic anchor click. Captured by both `fetch` and `blob` hooks.
  - `anchor-direct`: button is itself an `<a>` with a direct PDF href. Captured by `anchor` hook (and the hook can suppress the OS download).
  - `anchor-blob`: page generates a Blob client-side from already-loaded data (e.g. Stripe). Captured by `blob` hook only.
  - `window-open`: page calls `window.open(pdfUrl)`. Captured by `window.open` hook.
  - `os-download`: nothing is captured in-browser — file goes straight to OS download manager. Fall back to filesystem polling.

## Multiple PDFs per invoice

(Optional: only if a single invoice row produces more than one downloadable PDF)

Example: EWE Go monthly invoices have both Beleg (the invoice) and Einzelverbindungsnachweis (itemized charging records).

Document each:
- **Beleg** — column position, button index in row
- **Einzelverbindungsnachweis** — column position, button index in row
- (Skip CSV columns unless explicitly requested)

Naming suffixes used by the skill:
- Primary: `YYYY-MM_Provider_InvoiceNumber.pdf`
- Secondary: `YYYY-MM_Provider_InvoiceNumber_Einzelverbindungsnachweis.pdf` (or whatever label fits)

## Filenames (raw downloads)

(Optional: if Chrome's default filenames are unhelpful for renaming)

Some providers' OS-download filenames don't include the invoice number you see in the table. Document the observed naming and the rename rule. The skill renames based on the table row, not the raw filename.

## Success Signal

(Optional: how to confirm a download succeeded on the page itself)
- Example: "Download icon changes to a green checkmark"
- Example: "A toast notification appears saying 'Download started'"

## Billing Email

(Filled in by Learn Mode — see SKILL.md §"Billing email side-quest")

- **Supported:** yes / no
- **Path to the setting:** e.g. `/account/notifications` or `/contract/{id}/details → Rechnungsempfang section`
- **UI shape:** describe — single field? consent radio + email field? per-document toggle?
- **Send-mode options:** if the site offers "replace portal" vs "additionally send", note which.
- **Currently set to:** the configured address, or "not set" if disabled.

If supported but not set, the skill nudges the user once per run with the `preferred_billing_email` from config.md.

## Known Quirks

- (Optional: note any site-specific behavior)
- Examples:
  - "URL redirects to workspace-specific path"
  - "Date picker defaults to current month only"
  - "Requires scrolling to load older invoices"
  - "Download buttons use JS handlers, no direct PDF URLs"
  - "Session tied to a specific Chrome profile — use Work Chrome"
  - "Multiple identical-text buttons in same row — disambiguate by index, not by find"
