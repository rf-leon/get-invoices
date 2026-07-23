---
name: EWE Go
description: EV charging — contract billing for charging cards and monthly usage
domain: portal.ewe-go.de
url: https://portal.ewe-go.de
billing_email_supported: true
billing_email_url: /contract/{contract_id}/details
download_pattern: fetch-blob
---

# EWE Go

## Navigation

1. Go directly to the contract invoices URL: `https://portal.ewe-go.de/contract/{contract_id}/invoices`
   - If multiple contracts exist, the contract ID is shown in the sidebar under "Vertrag"
   - From the dashboard, click "Rechnungsübersicht" in the left sidebar
2. The invoice table appears with columns: Name | Rechnungsnummer | Beleg | Einzelverbindungsnachweis

## Loading Behavior

SPA — on first load shows an "EWE Go" splash with "Daten werden geladen..." for ~5-7 seconds before the invoice table appears. The header bar with the logged-in email (top right) is visible while loading; the table only appears once data is ready. Wait until you see the column headers "Name | Rechnungsnummer | Beleg | Einzelverbindungsnachweis" before scraping.

## Download

Each invoice row has two clickable elements per document column:
- **Eye icon ("PDF anzeigen"):** opens preview — skip this
- **Download arrow + "PDF" label:** downloads the PDF

Two columns can each have a PDF:
- **Beleg** — the actual invoice (Rechnung)
- **Einzelverbindungsnachweis** — itemized charging session record (only present for monthly usage invoices, not for one-off purchases like Ladekarte orders)

A third button labeled "CSV" appears in the Einzelverbindungsnachweis column — skip unless explicitly requested.

**Button details:** Each "PDF" button has the icon + text label together. The Beleg PDF and Einzelverbindungsnachweis PDF buttons both have identical visible text "PDF" — `find` cannot reliably distinguish them by column. Disambiguate by **button index within the row**:

| In a full row | Idx | Element |
|---|---|---|
| 0 | aria="PDF anzeigen" (Beleg preview) |
| 1 | text="PDF" (Beleg download) ← |
| 2 | aria="PDF anzeigen" (Einzelverbindungsnachweis preview) |
| 3 | text="PDF" (Einzelverbindungsnachweis download) ← |
| 4 | text="CSV" (skip) |

Find the row by matching its Rechnungsnummer text, then `querySelectorAll('button')[1]` for Beleg or `[3]` for Einzelverbindungsnachweis.

**Interception pattern:** `fetch-blob`
- Page calls `fetch()` against an AWS S3 signed URL (`bax-prod-ego-application-bucket.s3.eu-central-1.amazonaws.com/...`).
- Response wrapped in `URL.createObjectURL(blob)` for a synthetic anchor download.
- Anchor click uses `dispatchEvent` (not `.click()`), bypassing the prototype hook — so the file still lands in Chrome's download folder. The captured blob in memory is identical to the disk file.

## Multiple PDFs per invoice

Monthly usage invoices produce two PDFs:
- **Beleg** → `YYYY-MM_EweGo_{Rechnungsnummer}.pdf`
- **Einzelverbindungsnachweis** → `YYYY-MM_EweGo_{Rechnungsnummer}_Einzelverbindungsnachweis.pdf`

One-off purchases (e.g. Ladekarte orders) only have a Beleg, no Einzelverbindungsnachweis.

## Filenames (raw downloads)

EWE Go names files inconsistently — the displayed Rechnungsnummer does NOT match the OS-download filename. Typical shapes:
- Ladekarte invoice → `YYYY_MM_DD_{vendor-reference}_rechnung_ladekarte.pdf`
- Monthly invoice Beleg → `YYYY_MM_{vendor-reference}_rechnung.pdf`
- Monthly invoice Einzelverbindungsnachweis → `{contract_uuid}-{date_range}-{invoice_no}-CDR.pdf`

Always rename based on the displayed invoice number in the table, not the file's raw name.

## Success Signal

No visible signal on the page — rely on the interceptor's `__capturedPdfs` array growing or the file appearing in download dir.

## Billing Email

- **Supported:** yes
- **Path to the setting:** `/contract/{contract_id}/details` → "Rechnungsempfang" section → "Bearbeiten" button
- **UI shape:** modal dialog with two top-level radio groups:
  - "Ich willige ein, dass die Rechnung zusätzlich an diese E‑Mail Adresse versandt wird." (consent)
    - "An meine Vertrags-E‑Mail versenden" (use contract email)
    - "An eine abweichende E‑Mail-Adresse versenden:" + free-text email field
  - "Ich will die Rechnungen nur im EWE Go Portal ansehen können." (portal-only, default)
- **Send-mode:** "additionally send" — invoices still appear in the portal AND get emailed. Good: skill can fall back to portal scrape if email delivery breaks.
- **Per-user state:** record the configured address/date only in a user provider override.

## Known Quirks

- Filenames are unrelated to the displayed Rechnungsnummer — always rename based on the table row.
- A single monthly invoice produces two PDFs (Beleg + Einzelverbindungsnachweis) plus a CSV.
- Contract IDs are UUIDs in the URL path — invoice URL is per-contract, so save the contract ID for repeat runs. Configure once per contract; multi-contract accounts need a contract selector in the sidebar.
- Session may be tied to a work Chrome profile; use the profile where the EWE Go account is already signed in.
- All invoices visible on one page (no pagination observed for small accounts).
- Anchor downloads use `dispatchEvent` — the interceptor cannot suppress the OS download, only mirror it in memory. Skill must clean up `~/Downloads/` after upload.
- The "PDF" download buttons in Beleg and Einzelverbindungsnachweis columns are visually identical; `find` returns whichever is first in DOM order. Always disambiguate by button index.
