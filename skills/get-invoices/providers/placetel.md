---
name: Placetel
description: Cloud telephony — monthly service and usage invoices
domain: web.placetel.de
url: https://web.placetel.de/invoices
billing_email_supported: true
billing_email_url: /invoices
download_pattern: anchor-redirect-pdf-viewer
---

# Placetel

## Navigation

1. Open `https://web.placetel.de/invoices` in the signed-in browser profile.
2. The page is under **Stammdaten** → **Rechnungen & EVN**.
3. The invoice table is server-rendered and contains up to 50 rows per page.

## Pagination and date filtering

Follow the numbered page links or **Weiter ›** until no next-page link remains. Collect every qualifying row before downloading. For `--month` and `--since`, use **Rechnungsmonat** as the canonical month; use **Erstellt am** only as invoice metadata.

## Invoice rows

Each row shows the invoice number, billing month, total amount, creation date, and document links.

- **Rechnung runterladen** — invoice PDF; collect this by default.
- **XML herunterladen** — machine-readable invoice; skip unless explicitly requested.
- **EVN** — itemized call record; skip unless explicitly requested.

The PDF anchor has the relative form `/invoices/{internal_id}/download`. Use the displayed invoice number for filenames and deduplication, not the internal ID.

## Download

**Pattern:** `anchor-redirect-pdf-viewer`

The same-origin invoice link redirects to a signed Google Cloud Storage URL and opens the browser's PDF viewer in a new tab. The redirect does not permit an in-page CORS fetch, so the standard fetch interceptor may record no blob.

Codex/Chrome procedure:

1. Click exactly one `Rechnung runterladen` link after confirming the invoice number and unique row.
2. Claim the newly opened PDF tab.
3. Use the tab's `pageAssets` capability and take its `pageUrl` as the final signed PDF URL.
4. Keep the signed URL private. Store it in a mode-0600 temporary curl config, download the PDF with `curl --config`, and delete the config immediately afterward.
5. Validate the file begins with `%PDF` before uploading.

If the PDF tab does not expose `pageAssets`, stop and report the missing capability. Do not print the signed URL or retry the known-failing cross-origin page fetch.

For a batch, process one invoice at a time and close each PDF viewer tab after successful upload so invoice-to-tab matching stays unambiguous.

## Billing email

- **Supported:** yes.
- **Location:** top of `/invoices`, under **E-Mail Adresse für Rechnungen**.
- **Edit control:** the toggle/edit link next to the displayed address.
- **UI shape:** one email field labeled **Abweichende E-Mail Adresse für Rechnungen** and a submit control labeled **Mitarbeiter aktualisieren**.
- **Send mode:** the alternate address replaces the previous invoice-email recipient; invoices remain available in the portal.
- Save configured addresses only in a private user override.

## Success signal

The portal does not show a download success state. Confirm the PDF viewer tab, validate the `%PDF` header, and verify the destination with an exact invoice-number lookup.

## Known quirks

- Direct page `fetch()` follows the storage redirect but fails at the cross-origin boundary.
- The browser may expose the final storage URL with short-lived signing parameters. Never log or display it.
- The session can be tied to the browser profile where Placetel is already signed in.
