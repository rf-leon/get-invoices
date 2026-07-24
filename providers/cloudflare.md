---
name: Cloudflare
description: Cloudflare account, domains, Workers, storage, and media billing
domain: dash.cloudflare.com
url: https://dash.cloudflare.com/{account_id}/billing
download_pattern: xhr-blob
billing_email_supported: true
billing_email_url: /{account_id}/billing
---

# Cloudflare

## Navigation

1. Go to the account billing page (`https://dash.cloudflare.com/{account_id}/billing` — the account ID is in every dashboard URL after login).
2. Wait for the subscriptions table and billing details to finish loading.
3. Select the "Invoices and documents" tab.
4. The invoice table shows date, type, invoice number, amount, status, and row actions.

## Loading Behavior

- The dashboard is a SPA. Billing and invoice tables initially render skeleton rows; wait about 2-3 seconds for invoice numbers to appear.
- Changing invoice pages also renders skeleton rows before the records appear.

## Download

Each invoice row has a "Row actions" button. Open it and select "Download".

**Button details:** Locate the row by its complete accessible name: `<date> Invoice <invoice-number> <amount> Paid Row actions`. Then click the single "Row actions" button scoped to that row and the single "Download" menu item.

**Interception pattern:** `xhr-blob`. The page retrieves the PDF through XHR, creates a PDF Blob, and triggers a Blob download. Capture metadata reports `xhr` and `blob` events.

Always wait about 3.8-4.8 seconds after the download click before selecting the capture — some requests complete late and can be mistaken for the next row's capture. Before dispatch, extract the PDF text and confirm the printed invoice number matches the table row.

## Success Signal

The interceptor capture must have a `%PDF` header. There is no reliable visible success toast.

## Billing Email

- **Supported:** yes — the billing details panel on the account billing page shows the current billing email plus an "Edit billing email" button.

## Known Quirks

- Invoice number formats changed over the platform's history: recent invoices use `IN-xxxxxxxx`; earlier ones `CFUSA...`; the oldest portal rows expose a full UUID while the PDF prints only a shortened `INV-` prefix plus the first six UUID characters — validate by prefix for those.
- Pagination: "Next page" is enabled until the last page, where it renders disabled.
