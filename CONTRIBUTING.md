# Contributing

Thanks for helping more people never manually download an invoice again. The most valuable contribution is a **provider recipe** — the markdown instructions that teach any AI agent how to fetch invoices from a specific billing portal.

## Contributing a provider recipe

### The easy way (recommended)

Just use the skill on a portal it doesn't know:

```
/get-invoices portal.vendor.com
```

Learn Mode navigates the portal, performs one verified fetch, and saves the recipe. If you have the [`gh` CLI](https://cli.github.com/) installed, the skill then offers to open a pull request with the generic recipe automatically. You review the exact file content before anything is submitted.

### The manual way

1. Copy [`providers/_template.md`](providers/_template.md) to `providers/<vendor>.md` (short lowercase name, e.g. `hetzner.md`).
2. Fill in navigation, loading behavior, download/button details, and known quirks.
3. Verify the recipe with at least one real successful fetch.
4. Run `node scripts/sync-plugin-skill.mjs && python3 scripts/lint-providers.py`.
5. Open a pull request.

## The one hard rule: recipes describe websites, not accounts

Bundled recipes may only contain the **shareable fields** listed in the template: `name`, `description`, `domain`, `url`, `download_pattern`, `extraction_bridge`, `billing_email_supported`, `billing_email_url` — plus body text about the portal itself.

Never include:

- email addresses, names, customer/contract/invoice numbers, amounts
- account state (`billing_email_set`, tag IDs, correspondent IDs)
- which browser profile you use, or dates of your own account actions
- anything you would not want a stranger to read

Per-account details belong in your personal recipe at `~/.config/get-invoices/providers/<vendor>.md`, which overrides the bundled recipe on your machine and never leaves it.

CI runs `scripts/lint-providers.py` on every pull request and rejects recipes with non-allowlisted frontmatter or personal-data patterns. Maintainers review on top of that — but please don't make the linter do the thinking.

## Other contributions

- **Interceptor/bridge improvements** (`references/interceptor.js`, `scripts/codex-cdp-bridge.mjs`): welcome — add or update a test in `tests/`.
- **New destinations** (beyond Paperless-ngx and local): add a section to `references/destinations.md` and a dispatch block in `SKILL.md` step 10; keep capture steps destination-agnostic.
- **New agent runtimes**: add a section to `references/browser-runtimes.md` describing the required capabilities.

## Development workflow

The repository root is the authoring source (also directly usable as a Claude Code skill). `skills/get-invoices/` is a generated mirror used for Codex skill installs and the ChatGPT plugin — never edit it by hand:

```bash
node scripts/sync-plugin-skill.mjs           # regenerate mirror after editing root files
node scripts/sync-plugin-skill.mjs --check   # CI fails if the mirror is stale
python3 scripts/lint-providers.py            # allowlist + personal-data lint
uv run --with pytest python -m pytest tests/ -q
```

All four must pass before a PR can merge.
