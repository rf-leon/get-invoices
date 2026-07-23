---
name: E WIE EINFACH
description: Stromrechnungen und Vertragsdokumente aus dem E-WIE-EINFACH-Kundenportal
domain: mein.e-wie-einfach.de
url: https://mein.e-wie-einfach.de/inbox
download_pattern: fetch-blob
billing_email_supported: false
---

# E WIE EINFACH

## Navigation

1. The signed-in portal starts at `https://mein.e-wie-einfach.de/dashboard`.
2. Open `https://mein.e-wie-einfach.de/inbox` or click **Mitteilungen & Rechnungen**.
3. The timeline mixes invoices, readings, and other documents. Invoice entries are labelled **Rechnung** and show issue date, payment/refund amount, due date, and **PDF herunterladen**.
4. Use **Mehr laden** to reveal older entries when needed.

## Loading Behavior

- The portal is an SPA. After direct navigation, wait until the invoice timeline or page heading appears.
- Authentication redirects through `portal.e-wie-einfach.de/login`; if redirected there, ask the user to sign in in Chrome.

## Download

- Invoice anchors use an opaque `/invoice/<hash>/contract/<hash>` path.
- Install the interceptor on the inbox page, find the invoice link by the surrounding entry text (date and amount), and run an authenticated same-origin `fetch(link.href, {credentials: "include"})`.
- The reliable capture contains both `fetch` and `blob` events and returns `application/pdf` with a `%PDF` header.
- Verify the human invoice number, invoice date, amount, and billing period from the PDF before upload.

## Billing Email

- **Supported:** no separate billing-email setting found (checked `/inbox`, `/contract-details`, `/my-data`). `/my-data` → **Versandarten** only offers the delivery method (e.g. "online"); there is no separate invoice-recipient email field.

## Known Quirks

- The dashboard's estimated annual consumption can differ from the last billed annual consumption. Use the invoice's billed kWh for any tariff comparison.
- The authenticated XHR `/ewiapi/contract/<contract-number>/changePossibilities` exposes contract details (product change dates, prices, contract periods, linked AGB). A plain same-origin `fetch` to it can return 401 because the app adds authorization in its own interceptor — capture the already-authorized response through network events after loading the page instead.
- `/contract-details` shows current gross work price, annual base price, price-valid-from date, notice period, and next cancellable date.
