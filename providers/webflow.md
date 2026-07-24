---
name: Webflow
description: Webflow Workspace, Site plan, and marketplace purchase invoices
domain: webflow.com
url: https://webflow.com/dashboard/workspace/{workspace-slug}/billing?ref=billing_tab
download_pattern: fetch-blob
billing_email_supported: true
billing_email_url: /dashboard/workspace/{workspace-slug}/billing?ref=billing_tab
---

# Webflow

## Navigation

1. Go to the Workspace billing page (`/dashboard/workspace/{workspace-slug}/billing`). The workspace slug is visible in the dashboard URL after login, or via the workspace switcher in the top-left of the dashboard.
2. Wait for the billing page progress indicator to disappear.
3. Find the `All invoices` table. It contains Workspace-plan invoices, Site-plan invoices, and marketplace/template purchases combined.
4. Click `Show more`, wait about 3.2 seconds, and repeat until the button disappears — the row count changes only after roughly 3 seconds per click.
5. Per-site billing pages (`/dashboard/sites/{site-slug}/billing`) show the current Site plan but no separate invoice archive; their invoice settings link back to Workspace billing. Deduplicate by the Webflow invoice ID in the PDF link.

## Download

Each invoice row has a `Download PDF` link with one of these relative paths:

- `/dashboard/invoice/pdf/<customer-id>/<invoice-id>.pdf`
- `/dashboard/charge/pdf/<charge-id>.pdf` for marketplace purchases

Clicking the link opens a new PDF tab and does NOT produce an interceptor capture in the billing tab. Instead, keep the interceptor installed on the billing tab and fetch the known relative link in-page with `credentials: 'include'` — the interceptor captures the authenticated response as a PDF Blob (`fetch` + `blob` events).

Before dispatch:

1. Require a `%PDF` header.
2. Extract text (e.g. `pdftotext -layout`).
3. Confirm the invoice ID matches the final path component from the billing row.
4. Read the human `Invoice Number`, `Date`, and `Total` from the PDF — use the human invoice number for duplicate checks, titles, and the registry (the visible table does not show it).

## Billing Email

- **Supported:** yes — Workspace billing → `Invoice settings` → `Billing email` textbox plus Save button.

## Known Quirks

- Webflow may show a `What's new` modal on the dashboard; direct navigation to the stable Workspace billing URL avoids it.
- The combined archive mixes Workspace, Site, zero-dollar, credit, and purchase documents. Do not filter out zero or negative totals.
- The first click on a PDF link opens a PDF tab — close it after the run; use authenticated in-page fetches for bulk capture.
