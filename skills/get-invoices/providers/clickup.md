---
name: ClickUp
description: Project management tool — workspace billing invoices
domain: app.clickup.com
url: https://app.clickup.com/settings/billing
billing_email_supported: unknown
billing_email_url:
download_pattern: unknown
---

# ClickUp

## Navigation

1. Go to https://app.clickup.com/settings/billing (redirects to workspace-specific URL)
2. Click the "Invoices" tab in the top tab bar (next to Plans, Add-ons, Billing)
3. The invoice list shows a table with columns: Date, Invoice (number as link), Amount, and a download icon

## Loading Behavior

Page loads quickly after redirect. No spinner observed — the invoice table is rendered server-side. Safe to scrape immediately after the Invoices tab is active.

## Download

Each invoice row has a download icon button on the far right side of the row. Click it to trigger a PDF download. The file is named `T{workspace_id}-{date_code}.pdf` by default.

**Button details:** The download icon is small and positioned at the far right edge of each row. Coordinate-based clicking is more reliable than ref-based clicking due to the small target size.

## Success Signal

Successfully downloaded invoices show a green checkmark instead of the download arrow.

## Known Quirks

- The URL redirects from /settings/billing to /{workspace_id}/settings/billing
- Invoice number links (e.g. `T{workspace_id}-{date_code}`) are clickable but have empty href — they use JS click handlers
- Download buttons also use JS handlers, no direct PDF URLs available
- All invoices are visible on one page (no pagination observed for ~13 invoices)
- Invoices are Stripe-powered
