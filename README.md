# get-invoices

**Let your AI agent collect your invoices.** get-invoices is a skill for AI coding agents (Claude Code, Codex / ChatGPT desktop) that fetches invoice PDFs from billing portals using *your own signed-in Chrome* — no credentials shared, no API keys per vendor — verifies the bytes, deduplicates, and files them in [Paperless-ngx](https://docs.paperless-ngx.com/) or a local folder.

```
/get-invoices hetzner                # fetch new Hetzner invoices
/get-invoices --all --month 2026-07
/get-invoices portal.newvendor.com   # never seen it? the agent learns the portal
```

## How it works

1. Your agent drives your existing Chrome session (Claude in Chrome, or the Codex/ChatGPT browser runtime) — so vendor logins, 2FA, and cookies are already in place.
2. A small in-page interceptor captures the PDF **bytes inside the browser** the moment the portal produces them — no fragile "watch the Downloads folder" automation, no Chrome download-manager blocklists.
3. The bytes are verified (`%PDF` header, size), checked against a run registry and your document archive for duplicates, then uploaded to Paperless-ngx or saved locally with a clean filename.
4. For portals the skill doesn't know yet, **Learn Mode** navigates the site, finds the invoice list, performs one verified fetch, and saves a reusable provider recipe. It also checks whether the vendor supports a billing email — the highest-leverage discovery, because a configured billing email means you may never need to fetch manually again.

Provider recipes are plain markdown — human-readable, agent-executable, and easy to contribute.

## Install

### Claude Code

```bash
git clone https://github.com/rf-leon/get-invoices.git ~/.claude/skills/get-invoices
```

Available as `/get-invoices`. Requires the Claude in Chrome extension (`claude --chrome`).

### Codex CLI (skill)

```text
$skill-installer Install get-invoices from the GitHub repository rf-leon/get-invoices, path skills/get-invoices, using the git method.
```

Available as `$get-invoices`. Restart Codex if it does not appear immediately.

### ChatGPT desktop (plugin)

```bash
codex plugin marketplace add rf-leon/get-invoices
codex plugin add get-invoices@get-invoices
```

Then restart the ChatGPT app, open Plugins, and install **Get Invoices**.

## First run

The skill walks you through a short setup and stores your configuration outside the installed package, at `~/.config/get-invoices/`:

- `config.md` — destination (Paperless-ngx or local folder), preferred billing email, filing metadata. Keep API tokens in environment variables (`env:VARNAME` references are supported).
- `providers/` — your personal provider recipes and per-account state (login profile notes, tag mappings). These never leave your machine and survive plugin upgrades.

## Bundled providers

| Provider | Portal |
|----------|--------|
| ClickUp | app.clickup.com |
| Cloudflare | dash.cloudflare.com |
| DigitalOcean | cloud.digitalocean.com |
| E WIE EINFACH | mein.e-wie-einfach.de |
| EnBW Smart Mobility | smartmobility.enbw.com |
| EWE Go | portal.ewe-go.de |
| Placetel | web.placetel.de |
| SendGrid (Twilio) | app.sendgrid.com |
| Webflow | webflow.com |

Any portal not listed: run the skill with the URL and let Learn Mode figure it out — then consider [contributing the recipe](CONTRIBUTING.md) so the next person gets that portal for free.

## Contributing

Provider recipes are the heart of this project. After Learn Mode masters a new portal, the skill offers to open a pull request with the **generic** recipe automatically (if you have the `gh` CLI installed) — personal details are structurally excluded via a shareable-field allowlist, you review the exact content before anything is submitted, and CI lints every contribution again. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Security & privacy model

- **Your credentials never leave your browser.** The agent reuses existing sessions; it does not receive, store, or transmit passwords.
- **Bearer tokens stay in the page.** For API-driven portals, tokens are read and used *inside* page JavaScript; the skill explicitly forbids returning them into the agent transcript.
- **Signed URLs are never printed.** Only capture keys, sizes, and PDF headers cross the browser boundary — plus the PDF bytes themselves, transferred via clipboard or bounded chunks.
- **Side effects require confirmation.** Changing a billing email, saving consent, or submitting any account setting is asked about immediately before it happens.
- **Contributions are allowlisted.** Shared recipes describe websites, not accounts.

Use this only on accounts you own or administer.

## Development

Root files are the authoring source; `skills/get-invoices/` is a generated mirror for Codex/plugin packaging:

```bash
node scripts/sync-plugin-skill.mjs           # refresh the mirror
node scripts/sync-plugin-skill.mjs --check   # verify consistency (CI runs this)
python3 scripts/lint-providers.py            # privacy/allowlist lint (CI runs this)
uv run --with pytest python -m pytest tests/ -q
```

## License

[MIT](LICENSE)
