---
name: DigitalOcean
description: Cloud hosting — monthly usage invoices
domain: cloud.digitalocean.com
url: https://cloud.digitalocean.com/account/billing/history
download_pattern: in-page-fetch
extraction_bridge: clipboard
billing_email_supported: false
---

# DigitalOcean

## Navigation / invoice list

- Billing history: `https://cloud.digitalocean.com/account/billing/history` — **paginated**, use `?page=N` (page 1 ≈ 10 invoices). Rows alternate: "Payment ..." (skip) and "Invoice for {Month} {Year}" (links).
- Each invoice link href = `/account/billing/{invoice_uuid}`. Extract the UUID from the href (pure DOM read).
- The list's "Invoice for {Month}" label can differ from the PDF's billing month by up to one month — do NOT trust it for naming. Use the PDF's own filename or auto-detected date instead.

## PDF URL

`https://cloud.digitalocean.com/v2/customers/do:team:{team_id}/invoices/{invoice_uuid}/pdf`

`{team_id}` is the hex team identifier visible in dashboard URLs/requests for the logged-in team. Auth = cookie (same-origin). The response is served **inline** — a top-level navigation renders it in the PDF viewer and does NOT save. The old `/api/v1/invoices/{uuid}/pdf` path 404s.

## Download method

Because direct navigation renders inline, fetch **from a `cloud.digitalocean.com` page context** (same-origin, cookie auth):

```js
const r = await fetch(base + uuid + '/pdf');
const cd = r.headers.get('content-disposition');   // DO's own filename incl. month
const fn = (cd.match(/filename\*?=(?:UTF-8''|")?([^";]+)/) || [])[1];
const b = await r.blob();
```

Then hand the Blob to an extraction bridge (clipboard preferred — see SKILL.md). An in-page fetch from a different origin, or `credentials:'include'` cross-origin, fails with "Failed to fetch" — you must be on a DO page. Files are named `DigitalOcean Invoice {YYYY} {Mon} ({invoice_no}).pdf`.

## What did NOT work (don't retry)

- Direct tab navigation to `/pdf`: renders inline, no save (unlike cross-origin attachment portals).
- Rapid same-tab or parallel-tab nav-downloads: DO generates PDFs slowly; the next navigation aborts the prior pending download.
- Real clicks on the app's own Download→PDF while the site was download-blocklisted.

## Quirks

- If the anchor[download] fallback is ever used, Chrome's automatic-downloads permission must be allowed first.
- Paperless auto-detects the invoice date from the PDF reliably — use it as the authoritative month.
- macOS bash 3.2 has no `declare -A` (it silently misbehaves) — avoid associative arrays in upload helper scripts.
