---
name: get-invoices
description: >
  Fetch invoices from signed-in billing portals with Chrome browser automation,
  verify and deduplicate the PDF bytes, and upload them to Paperless-ngx or save
  them locally. Learn new providers, handle multi-provider runs, and discover
  billing-email settings. Use when the user says "get invoices", "fetch invoices",
  "download invoices", "Rechnungen holen", names a billing provider or portal URL,
  or asks to collect historical invoices. Supports Claude in Chrome and the
  ChatGPT/Codex Chrome browser runtime.
---

# Get Invoices

Fetch invoices from a billing portal, capture PDF bytes inside Chrome, and dispatch them to the configured destination. Reuse existing browser logins instead of asking for credentials.

## Prerequisites

1. **A controllable signed-in Chrome is available.** Read [browser-runtimes.md](references/browser-runtimes.md), select the current harness, and follow its browser-control skill.
2. **Use the right Chrome profile.** If multiple profiles or connected browsers are available, use the provider file's session note or ask the user before continuing.
3. **A user config exists.** Resolve it in this order: `GET_INVOICES_CONFIG`, `~/.config/get-invoices/config.md`, then `config.md` beside this skill for backward compatibility. See [first-run setup](#first-run-setup).

The OS download manager is a **fallback only** — the main path is in-browser fetch via [interceptor.js](references/interceptor.js). Chrome's "Ask where to save each file" setting only matters if the in-browser path fails.

## Argument Parsing

`$get-invoices [target...] [--month YYYY-MM] [--since YYYY-MM] [--destination paperless|local] [--dry-run]` in Codex, or `/get-invoices ...` in Claude Code.

Determine mode from target:
- **Named provider** (`hetzner`) — resolve `hetzner.md` from the user provider directory first, then bundled `providers/` → follow its steps.
- **Multiple providers** (`hetzner vodafone`) — process each sequentially.
- **All** (`--all`) — merge user and bundled provider files by filename (user wins), skip `_template.md`, and process each.
- **List** (`--list`) — show available providers with name + description from frontmatter.
- **URL/domain** (`portal.example.com`) — no matching provider → [Learn Mode](#workflow-learn-mode).
- **No argument** — show available providers and ask which to fetch.

Optional flags:
- `--month YYYY-MM` — only invoices from this month.
- `--since YYYY-MM` — invoices from this month onwards.
- `--destination paperless|local` — override config.md for this run.
- `--dry-run` — identify invoices and preview duplicate/tag decisions without side effects. Do not download PDFs, upload or patch documents, change billing settings, append the registry, or save provider/config changes. Paperless and browser reads are allowed when needed to produce the preview.

## First Run Setup

If no config is found or it is incomplete, walk through setup before any fetching. See [config template](references/config-template.md) for the full structure. The key questions:

1. **Destination** — `paperless` to upload via API, or `local` to save renamed PDFs in a folder.
2. **If paperless** — URL and token. Prefer `env:VARNAME` references so secrets stay in `~/.env.secrets`.
3. **If local** — destination folder, file-naming pattern, and Chrome's download directory (default `~/Downloads/`).
4. **Preferred billing email** — used in Learn Mode when the skill discovers a billing-email setting. Typically a Paperless email-ingest address or the user's accountant.
5. **Paperless filing metadata** — optional default invoice document-type ID plus transient cleanup tag IDs.
6. **Provider mappings** — optional Paperless company tag and correspondent IDs keyed by provider slug. Keep these in user config, not bundled provider recipes.

Write to `~/.config/get-invoices/config.md` by default, creating its parent directory if needed. Use `GET_INVOICES_CONFIG` only when the user requests another location. Never write user secrets into the installed skill/plugin directory.

## Workflow: Fetch from Provider

For each provider:

### 1. Read provider file
Resolve the provider file in this order:

1. `GET_INVOICES_PROVIDER_DIR/<name>.md`
2. `~/.config/get-invoices/providers/<name>.md`
3. bundled `providers/<name>.md`

Read its navigation and frontmatter (`billing_email_*`, `download_pattern`, `extraction_bridge`, and legacy `company_tag`). Resolve Paperless default document type, provider tag, provider correspondent, and cleanup tags from user config. User config overrides a legacy bundled/provider `company_tag`.

### 2. Initialize Chrome
- Read [browser-runtimes.md](references/browser-runtimes.md) and use the matching runtime.
- Select the Chrome profile that owns the provider session.
- Prefer claiming a matching existing tab. Otherwise open a fresh tab.
- Keep one controllable tab per provider and reuse it throughout that provider's run.

If Chrome control is unavailable, ask the user to connect or enable it. Do not substitute a logged-out browser or web search.

### 3. Navigate to invoices
Go to the provider's start URL and follow its numbered steps. Inspect current DOM or visual state before every interaction and use the runtime's stable locator rules.

### 4. Handle obstacles before proceeding
- **Cookie banners:** prefer a visible reject/necessary-only option. Saving a consent preference is an external side effect; follow the active browser runtime's confirmation rules.
- **Session expired / login page:** ask the user to log in manually, wait for confirmation.
- **CAPTCHA:** pause, ask the user to solve it.
- **Unexpected page:** screenshot, assess, navigate back to invoices.

When running multiple providers (`--all` or several names), do NOT abort the whole run on one obstacle. Skip the current provider, continue, and report failures at the end (see step 12).

### 5. Install the interceptor
Before any download click, install [interceptor.js](references/interceptor.js) with the selected runtime. It hooks `fetch`, `XMLHttpRequest`, `URL.createObjectURL`, `HTMLAnchorElement.prototype.click`, and `window.open`. It stores event metadata in `window.__capturedPdfs`, Blob objects in `window.__capturedBlobs`, and exposes reset, metadata, and bounded chunk-reader helpers.

- **Codex/ChatGPT desktop:** use the tab's CDP capability through `scripts/codex-cdp-bridge.mjs`. Do not use read-only Playwright evaluation to install hooks.
- **Claude in Chrome:** evaluate the complete interceptor IIFE with `javascript_tool`.

The interceptor is the difference between "we have the bytes in-memory" and "we're polling the filesystem hoping Chrome cooperates." Always install before clicking — the one exception is providers documented `download_pattern: os-download`, where the interceptor can't help (see [OS-download fallback](#os-download-fallback)).

### 6. Identify invoices
On the invoice list page, extract for each invoice:
- Date, invoice number, amount (if visible)
- Which buttons to click for which PDFs (Beleg, Einzelverbindungsnachweis, etc.)

**Wait for SPAs:** if the provider file notes a loading state, wait for the documented table/header state. Take a screenshot if the table appears empty; a splash screen may still be active.

**Disambiguating buttons:** if a row has multiple buttons with identical visible text (e.g. two "PDF" buttons in Beleg vs Einzelverbindungsnachweis columns), `find` cannot reliably tell them apart by column. Use a JS snippet to locate the row by invoice number, then click by button index:

```js
let row;
document.querySelectorAll('tr, [role="row"]').forEach(r => {
  if (r.textContent.includes(INVOICE_NUMBER)) row = r;
});
row.querySelectorAll('button')[BUTTON_INDEX].click();
```

The provider file documents the right `BUTTON_INDEX` per column.

**Pagination:** check if all invoices are visible. Some providers show all on one page, others paginate. Document this in the provider file's Known Quirks.

### 7. Filter by date range
- `--month YYYY-MM` → only that month
- `--since YYYY-MM` → that month and newer
- No flag → all available invoices

Use the invoice's billing/service month when the portal exposes one. Use the creation/issue date only when no billing period is available. Use the same chosen month for filtering, filenames, and exact-title duplicate checks.

### 8. Check duplicates

Run two checks. Skip when the registry matches. Also skip when the destination already contains the computed document, unless the user explicitly requests reprocessing:

1. **Skill log** (`get-invoices.log`, under `Local > Download Path` from the resolved config — used as a registry even when `Destination: paperless`). Skip if `provider | invoice_number` is already logged.
2. **Destination-specific:**
   - `paperless` — required: query the API by invoice number before downloading and compare the computed title when available. Accept only one unambiguous result that contains both the provider and exact invoice number; a matching title is a strong signal but not mandatory for manually uploaded documents. Skip the upload when that document already exists, but reconcile it to the configured default document type/provider correspondent and `(current tags ∪ default/provider tags) − cleanup tags`. Preserve every unrelated tag and never guess an unmapped ID. Use checksum deduplication as a final safety net, not the primary check.
   - `local` — file matching the computed destination name already exists.

In `--dry-run`, calculate and report the reconciliation but never call a mutating helper or append the registry. If using `scripts/paperless-reconcile.py` for a preview, always pass `--dry-run`.

### 9. Fetch each invoice (in-browser)

**Before clicking:** reset captures with `window.__resetCapturedPdfs()` or the runtime bridge. Hooks stay installed until navigation/reload.

**Click the download button** via the disambiguation strategy from step 6.

**Wait** for the provider's download success signal or 2-4 seconds when no signal exists. The page typically does `fetch → blob → synthetic click` in under a second; budget for slower sites.

**Read capture metadata** without returning URLs (signed URLs may contain sensitive query strings):

```js
await window.__getCapturedPdfMeta()
```

If no blob was captured but the provider notes `download_pattern: os-download` or your captures are empty, fall back to filesystem polling on the Chrome download directory (see "OS-download fallback" below).

**Verify the bytes:** choose only a capture whose metadata header starts with `%PDF`. If none does, the page may have returned an error/login page or a non-PDF attachment; do not upload.

**Extract bytes for upload** — if the provider file specifies `extraction_bridge`, prefer it (some portals only work one way, e.g. direct-nav). Otherwise use the [extraction bridge](#extraction-bridges) matching the runtime:
- **Claude in Chrome:** clipboard bridge first (zero context cost, zero download manager), chunked base64 only for 1-3 small files, download manager only as last resort.
- **Codex/ChatGPT desktop:** use `writeCapture()` from `scripts/codex-cdp-bridge.mjs`. It reads bounded base64 chunks, writes a private temporary file, verifies the final byte count, and re-checks `%PDF`.
- If Chrome happened to also write the file to the download directory (the `dispatchEvent` gap — see [interceptor.js](references/interceptor.js)), validate it independently, use it, and delete it after successful dispatch.

### 10. Dispatch to destination

See [destinations.md](references/destinations.md) for the full spec of each destination. Quick summary:

- **paperless:** `POST {PAPERLESS_URL}/api/documents/post_document/` with the file, title, tags = `default_tags ∪ {configured provider tag}`, and configured document type/correspondent IDs. Do not submit transient cleanup tags. Wait for ingestion, resolve the created document, and run `scripts/paperless-reconcile.py` to enforce the configured type/correspondent plus `(current tags ∪ required upload tags) − cleanup tags`. Treat the upload as complete only after an exact invoice-number lookup confirms one document with the final metadata.
- **local:** write the bytes to `{download_path}/{provider}/{computed_filename}`.

For both: append to the skill log (`get-invoices.log`):
```
YYYY-MM-DD HH:MM | provider | invoice_number | invoice_date | amount | destination_id
```
For paperless, `destination_id` is the verified Paperless document ID. For local, it's the filename. Append the log only after destination verification succeeds.

### 11. Clean up
- Delete only temporary or download files created by this run, and only after successful dispatch.
- Close the tab opened in step 2. This prevents tab buildup during `--all` runs.

### 12. Report results

After all providers, summarize:

```
✓ example-provider: 2 new, 1 skipped
  + 2026-04_ExampleProvider_INV-1234 → paperless document <document-id>
  + 2026-05_ExampleProvider_INV-1278 → paperless document <document-id>

✗ hetzner: FAILED — login required
✗ vodafone: FAILED — CAPTCHA encountered
```

If any provider failed, suggest re-running just those interactively:
> "hetzner and vodafone need manual login/CAPTCHA. Want to retry interactively? I'll pause at each for you to handle auth."

If a provider has `billing_email_supported: true` and `billing_email_set: no`, nudge once:
> "FYI: EWE Go supports billing email and yours isn't set. Want me to set it to the preferred billing address from your config? Then future invoices can arrive automatically."

## Workflow: Learn Mode

When the target doesn't match any provider file and looks like a URL/domain:

1. Open a new tab, navigate to the site.
2. Take a screenshot to understand the layout.
3. Search the visible/accessible page for "billing", "invoices", "Rechnungen", "account", "orders", and "payments".
4. Navigate step by step, noting each action and any quirks (redirects, login walls, JS-only buttons).
5. Once the invoice list is visible, install [interceptor.js](references/interceptor.js) and run the standard fetch+dispatch (steps 5-11 above) on at least one invoice. Verify the bytes are a real PDF before saving the provider file.

### Billing-email side-quest

**Before saving the provider file**, do a short detour to check whether this vendor supports a billing-email setting. This is the single highest-leverage discovery — if supported and configured, future invoices arrive automatically and the skill becomes a one-time setup rather than a recurring fetch.

Where to look (in order):
1. The same area as the invoices (some sites put the toggle right on the invoice list).
2. Account settings / Profil.
3. Notifications / E-Mail preferences.
4. Contract / subscription details.

Search terms (German + English): "billing email", "Rechnungs-E-Mail", "Rechnungsempfang", "Rechnungsempfänger", "send invoices to", "Rechnung per E-Mail", "invoice notifications", "Empfänger".

When found:
1. Note the URL path and the UI shape (single field? consent radio + email? per-document toggle?).
2. Note the send-mode: does enabling email *replace* the portal record, or *additionally* send? The "additionally" mode is preferred — it preserves a fallback.
3. Ask the user: *"This vendor supports a billing email at `<path>`. Want me to set it to `<preferred_billing_email>` (from your config)?"*
4. If yes: fill the form, submit, verify the saved state shows the new value.
5. Record in the provider file:
   ```yaml
   billing_email_supported: true
   billing_email_url: <path>
   billing_email_set: YYYY-MM-DD   # or "no" if user declined
   ```

If not found after a reasonable search (3-4 plausible pages checked): set `billing_email_supported: false`.

### Save the provider file

**Only after at least one invoice was successfully fetched and the billing-email check is complete**, save the learned recipe to `~/.config/get-invoices/providers/<name>.md` (or `GET_INVOICES_PROVIDER_DIR`) using the [template](providers/_template.md):

- Use the site's short name as the filename (e.g. `hetzner.md`, not `accounts.hetzner.com.md`).
- Document each navigation step that worked.
- Fill in `download_pattern` (which interceptor hook caught the PDF) and any disambiguation rules.
- Fill in the billing-email section.
- Note quirks: loading splashes, multi-row identical buttons, login walls, profile pinning.

Tell the user which user-provider path was saved and that the next run will prefer it over the bundled recipe. Do not modify an installed plugin cache. Only edit bundled providers when the user is explicitly developing this repository.

### Contribute the recipe (optional)

After saving a newly learned provider, check whether the `gh` CLI is installed and authenticated (`gh auth status`). If not, skip this step silently. If yes, offer once:

> "Want to contribute the generic Telekom recipe to the public get-invoices project? Future users get this portal for free. I'll show you exactly what would be shared first — none of your personal details."

If the user agrees, derive a **generic recipe** from the saved one using the shareable-field allowlist:

**Shareable (allowlist — nothing else may appear):**
- Frontmatter: `name`, `description`, `domain`, `url`, `download_pattern`, `extraction_bridge`, `billing_email_supported`, `billing_email_url`
- Body: navigation steps, loading behavior, download/button details, known quirks — phrased about **the website**, never about the user's account

**Never contribute (personal — stays in the user's provider file):**
- `company_tag`, `billing_email_set`, Paperless tag/correspondent/document-type IDs
- Session notes (which Chrome profile, which login email), account emails, customer/contract numbers, invoice amounts, dates tied to the user's account actions

Before showing it, self-check the derived recipe: no email addresses, no `@`, no digit runs that look like customer/contract IDs or IBANs, no values copied from the user's config, no personal names or non-public domains. If any check fails, fix the recipe — do not just delete the offending line if it carries navigation info; rephrase it generically.

Then display the **full derived file content** to the user and ask for explicit confirmation. Only after confirmation:

```bash
FORK_OWNER=$(gh api user -q .login)
gh repo fork rf-leon/get-invoices --clone=false        # no-op if the fork exists
gh repo sync "$FORK_OWNER/get-invoices" --source rf-leon/get-invoices || true
DIR=$(mktemp -d)/get-invoices
git clone --depth 1 "https://github.com/$FORK_OWNER/get-invoices.git" "$DIR"
cd "$DIR"
BRANCH="add-<provider>-$(date +%Y%m%d%H%M)"            # unique — avoids collisions with earlier PRs
git checkout -b "$BRANCH"
# write providers/<provider>.md, then regenerate the packaged mirror and validate —
# CI rejects PRs with a stale mirror or lint findings:
node scripts/sync-plugin-skill.mjs
node scripts/sync-plugin-skill.mjs --check
python3 scripts/lint-providers.py
git add providers/ skills/ && git commit -m "Add provider: <name>"
git push -u origin "$BRANCH"
gh pr create --repo rf-leon/get-invoices --head "$FORK_OWNER:$BRANCH" \
  --title "Add provider: <name>" \
  --body "New provider recipe learned and verified with at least one successful fetch. No account-specific data included."
```

If the lint fails, fix the recipe before pushing — do not submit a failing PR. Report the PR URL to the user and delete the temporary clone. Never submit without the confirmation step, and never include the user's personal provider file or config in the PR.

## Destinations

The skill dispatches captured PDFs to one of:

- `paperless` — POST to Paperless-ngx with tags + title. See [destinations.md § paperless](references/destinations.md#paperless).
- `local` — write to a renamed file under `{download_path}/{provider}/`. See [destinations.md § local](references/destinations.md#local).

Adding a new destination: add a section to `references/destinations.md` and a dispatch block to step 10 above. Keep capture steps 5-9 destination-agnostic.

## Extraction Bridges

Once the PDF bytes exist as a Blob inside the page (interceptor capture or explicit in-page `fetch`), they must cross from page to disk without (a) Chrome's download manager and (b) flooding the model context. Pick the highest bridge that works, and record it as `extraction_bridge` in the provider file. (`download_pattern` is a separate field: it records which interceptor hook captured the bytes, not how they crossed to disk.)

### 1. Clipboard bridge (preferred — zero context cost, zero download manager)

Three steps per file:

1. **Source + encode the Blob in the page.** Prefer the Blob the interceptor already captured (`window.__capturedBlobs[CAPTURE_KEY]`, key from `__getCapturedPdfMeta()`). Fall back to an explicit in-page `fetch` only for API-driven portals where there is no clickable download to intercept. If the call does network, its tool result is blocked as `{}` — stash everything in window vars either way:
   ```js
   let b = window.__capturedBlobs?.[CAPTURE_KEY];
   if (!b) {   // API-driven portal, no interceptor capture
     const r = await fetch(PDF_URL /*, {headers: …} for bearer portals, see token rule */);
     b = await r.blob();
   }
   window.__b64 = await new Promise(res => {
     const fr = new FileReader();
     fr.onload = () => res(fr.result.split(',')[1]);
     fr.readAsDataURL(b);
   });
   window.__meta = { size: b.size, type: b.type };
   ```
2. **Copy to clipboard in a separate pure call** (no network → result comes through):
   ```js
   await navigator.clipboard.writeText(window.__b64); window.__meta
   ```
   If this throws `Document is not focused`, bring Chrome to front first (`osascript -e 'tell application "Google Chrome" to activate'` in Bash) and retry.
3. **Drain the clipboard in Bash:**
   ```bash
   pbpaste | base64 -d > "$OUT" && head -c 5 "$OUT"   # must print %PDF-
   ```

Loop the three steps per invoice. Works identically for cookie-auth and bearer-auth endpoints. Caveats: clobbers the user's clipboard during the run (warn if the user is actively working); the tab must stay focused between steps 2 and 3; `pbpaste`/`osascript` are macOS-only — on other platforms use chunked base64 or, on Codex/ChatGPT, the CDP bridge instead.

### 2. Chunked base64 through the tool result (fallback — costs context)

If clipboard writes fail, return `window.__b64` in slices (≤50k chars per `javascript_tool` call: `window.__b64.slice(0, 50000)` …), concatenate in Bash, decode. Fine for 1-3 small PDFs. Do NOT use for bulk runs — 20 invoices ≈ several MB pushed through the model context.

### 3. direct-nav (single top-level navigations)

Navigate the tab straight to each PDF URL (works on portals whose invoice links are plain cookie-auth attachments). Each navigation counts as a single user-style download and is NOT subject to the automatic-multi-download block. Only works when the endpoint is cookie-auth AND served `Content-Disposition: attachment` (a navigation can't carry a bearer header; inline-rendered PDFs won't save).

### 4. anchor[download] / OS downloads (last resort)

Goes through the download manager; requires the user to allow `chrome://settings/content/automaticDownloads` for the site. Even when allowed, rapid loops silently drop files (observed in practice: the last ~4 of a 26-file loop never hit disk although the loop reported success) — space clicks ≥2.5s apart and verify counts on disk, never trust the loop. See [OS-download fallback](#os-download-fallback) and the blocklist warning in Troubleshooting.

### Bearer-token portals (e.g. EV-charging or mobile-app-first portals)

When the invoice API needs `Authorization: Bearer`, the token lives in localStorage/sessionStorage. Read it INSIDE the page code and attach the header there:
```js
const t = localStorage.getItem('TOKEN_KEY');   // inspect shape first — may be JSON-wrapped
await fetch(API_URL, { headers: { Authorization: 'Bearer ' + t } });
```
NEVER return the token into a tool result or paste it into Bash — the credential guard blocks it (correctly), and the bridges above make it unnecessary: only PDF bytes ever leave the page.

## OS-download fallback

Some sites really do trigger a native browser download with no interceptable JS path (`download_pattern: os-download` in the provider file). For these:

1. Don't bother installing the interceptor — it won't help.
2. Click the download button.
3. Poll the Chrome download dir (`{chrome_download_dir}` from config):
   ```bash
   ls -lt {chrome_download_dir}/ | head -5
   ```
   A `.crdownload` suffix means the download is in progress — wait and re-poll.
4. Once a non-`.crdownload` file appears (timeout 30s), validate with `head -c 4 <file>` — must be `%PDF`.
5. Dispatch to destination, then delete the OS file.

The reason this is a fallback rather than the default: it's fragile (different download dirs across users, Chrome's "ask where to save" setting, race conditions on concurrent downloads, raw filenames that don't match invoice numbers). The in-browser path avoids all of that.

**Hard rule: never trigger script-downloads in a loop.** More than ~1 script-initiated download trips Chrome's "automatic multiple downloads" block and silently blocklists the site for the rest of the session (see Troubleshooting). One download, verify it landed, only then consider a second.

## Browser runtime reference

Read [browser-runtimes.md](references/browser-runtimes.md) once per run before browser work. It contains the Codex/ChatGPT CDP bridge, Claude in Chrome path, fallback behavior, and confirmation boundary.

### Chrome MCP Tools Quick Reference (Claude in Chrome)

| Tool | Purpose |
|------|---------|
| `tabs_context_mcp` | Initialize tab group (required first call!) |
| `list_connected_browsers` + `select_browser` | Pick the right Chrome if multiple are connected |
| `tabs_create_mcp` | Open new tab |
| `navigate` | Go to URL, back, forward |
| `read_page` | Accessibility tree with element refs |
| `find` | Find elements by natural language |
| `computer` | Click, scroll, type, screenshot, wait |
| `form_input` | Set form values by ref |
| `get_page_text` | Extract plain text |
| `javascript_tool` | Execute JS in the page (this is where interceptor.js lives) |
| `browser_batch` | Run a sequence of the above in ONE round trip — significantly faster |

All Chrome MCP tools are deferred — load them via `ToolSearch` with `select:mcp__claude-in-chrome__<tool_name>` before first use (server name exactly as it appears in the deferred-tools list; batch all needed tools into ONE select).

## Troubleshooting

### "Cannot access a chrome-extension:// URL of different extension"
Another browser-automation extension is holding the tab handle (e.g. `Control_Chrome` is installed alongside `Claude_in_Chrome`). Either disable the other extension, or ask the user to perform the failing action manually. The form will usually be fully filled — only the final submit click breaks.

### Multiple Chromes connected
Confirm which profile has the relevant session unless the provider file contains a reliable "Session is tied to..." note. Use the active runtime's supported browser-selection flow.

### `find` returns the wrong button when multiple share text
Use the row-then-index JS pattern from step 6. The provider file should document the index per column for any row that has duplicate-text buttons.

### Signed URLs in tool results get blocked
Do not return signed URLs from page JavaScript or CDP. Return only event types, capture keys, sizes, content types, and PDF headers; keep the fetch inside the page.

### Downloads "succeed" (HTTP 200) but no file lands — multi-download blocklist
Triggering more than one script-initiated download on a site trips Chrome's "automatic multiple downloads" block. From then on the site is silently blocklisted: every further script download — even a single bundle-ZIP — completes on the network (200) but is never written to disk. A page reload does NOT reset it; only the user can, via `chrome://settings/content/automaticDownloads` (allow globally or add `[*.]<domain>`). Discovered the hard way (26-file loop → even the select-all ZIP was swallowed). Prevention: use the clipboard bridge; if the download manager is unavoidable, one download at a time, verify on disk before the next.

### Captured blob count doesn't match clicks
Check `window.__capturedPdfs` for the hook and `capture-error` events. The fetch hook clones PDF responses and should create a capture even when the page never calls `createObjectURL`. If no Blob appears, record the observed pattern, use the OS fallback, and set `download_pattern: os-download` unless the failure is a cross-origin iframe limitation.

## Provider Files

Provider recipes are markdown files. User-specific recipes override bundled [providers/](providers/) by filename. See [_template.md](providers/_template.md) for the format. Keep bundled recipes free of account emails, contract IDs, destination tag IDs, and per-user completion state.

- `company_tag` — legacy Paperless tag ID; prefer the user config's `Provider tags` mapping.
- `billing_email_*` — capability/navigation metadata plus user state when stored in a user override.
- `download_pattern` — tells future runs which interceptor hook to expect.

## Reference Files

- [config-template.md](references/config-template.md) — structure for the user's `config.md`.
- [browser-runtimes.md](references/browser-runtimes.md) — Codex/ChatGPT, Claude, and fallback browser procedures.
- [interceptor.js](references/interceptor.js) — the PDF download interception hooks.
- [destinations.md](references/destinations.md) — paperless and local destination specs; add new destinations here.
- [_template.md](providers/_template.md) — provider file template.
