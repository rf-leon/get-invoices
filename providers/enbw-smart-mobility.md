---
name: EnBW Smart Mobility
description: EV charging — monthly invoices from the Smart Mobility business portal
domain: smartmobility.enbw.com
url: https://smartmobility.enbw.com/profile
download_pattern: in-page-fetch
extraction_bridge: clipboard
billing_email_supported: false
---

# EnBW Smart Mobility

Covers the **smartmobility.enbw.com** business portal. Note: EnBW's consumer product **mobility+** has NO web portal — those charging invoices are available only in the mobility+ app (Menü → Profil → Rechnungen; export/share each PDF from there). `meine.enbw.com` is Strom/Gas only and does not show charging contracts.

## Navigation

1. Go to `https://smartmobility.enbw.com/profile` → tabs **Stammdaten | Rechnungen | Datenschutz**.
2. "Rechnungen" tab shows a table of monthly invoices: Rechnungsdatum, Vorgangsnr, PDF/CSV links, Betrag.

## Auth (KEY)

Bearer JWT in `localStorage.getItem('ses_access_token')`. The API is Azure APIM (`enbw-emp.azure-api.net`), cross-origin to the portal, bearer-only — no cookie auth. A plain top-level navigation to a PDF URL returns 401. All fetching must happen **from the portal page context** with the Authorization header attached in-page. Never print the token into a tool result (see SKILL.md token rule).

## API

Base: `https://enbw-emp.azure-api.net/b2b/v1/api`

- List: `GET {base}/invoices?pageNumber=0&pageSize=200&sortBy=-invoiceDateTime` → `{invoices:[{invoiceNo, invoiceMonth ("YYYY-MM", = Leistungsmonat), totalInvoiceAmount, documents:[{id, documentDate (= Rechnungsdatum, ~2 months after invoiceMonth), csvDocumentId, type:"INVOICE"}]}]}`
- PDF: `GET {base}/invoices/{documents[0].id}/pdf` (bearer; returns `application/pdf`)
- CSV line items: `GET {base}/invoices/{csvDocumentId}/csv` — shows Positionstyp, kWh, Energiekosten, Grundgebühr, Ort
- Bulk ZIP: select rows → "herunterladen" → `PUT {base}/invoices/download?fileName=Rechnungen` — still subject to Chrome's download blocklist; prefer the per-file clipboard bridge.

## Download method

In-page fetch with bearer header, then the clipboard bridge (see SKILL.md § Extraction Bridges). Do NOT loop anchor[download] clicks: rapid loops trip Chrome's multi-download blocklist, and even when downloads are allowed, the tail of a long loop can silently never hit disk — verify counts on disk if the download manager is ever used.

## Naming

Issue date (Rechnungsdatum) lags the billing month (Leistungsmonat) by ~2 months. Title by issue date; the PDF's own date is what document systems auto-detect.
