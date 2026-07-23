# Browser runtimes

Choose the runtime that is actually available. Reuse the user's signed-in browser; do not switch to web search or another browser to bypass authentication.

## Codex and ChatGPT desktop

Use the installed Chrome-control skill because invoice portals depend on the user's existing Chrome profile.

1. Read and follow the Chrome-control skill before browser work.
2. Connect to Chrome, name the browser session, and claim a matching open tab or create a fresh tab.
3. Navigate the tab to the provider's HTTP or HTTPS page before the first CDP command.
4. Inspect the DOM before each interaction and follow the browser skill's locator and confirmation rules.
5. Use the tab's `cdp` capability for interceptor installation and PDF extraction. Playwright evaluation is read-only in Codex and must not be used to install hooks. When a provider documents `anchor-redirect-pdf-viewer`, use the PDF tab's `pageAssets` capability to resolve the already-loaded final asset without exposing its signed URL.
6. Resolve this skill's absolute directory from the `SKILL.md` path exposed in the active skills list. Import `scripts/codex-cdp-bridge.mjs` by absolute path in the persistent JavaScript browser session.

Example after a controllable `tab` exists:

```js
var captureBridge = await import("/absolute/path/to/get-invoices/scripts/codex-cdp-bridge.mjs");
await captureBridge.installInterceptor(
  tab,
  "/absolute/path/to/get-invoices/references/interceptor.js"
);
```

Before each invoice click:

```js
await captureBridge.resetCaptures(tab);
```

After the click and a targeted wait/state check:

```js
var captureState = await captureBridge.getCaptureMeta(tab);
```

Select a capture whose `header` starts with `%PDF`, then extract it to a private temporary file in bounded chunks:

```js
var extracted = await captureBridge.writeCapture(tab, {
  captureKey: captureState.captures[0].key,
  destination: "/private/tmp/get-invoices/provider-invoice.pdf"
});
```

The bridge validates the `%PDF` header and byte count. Never print or return signed invoice URLs. Delete temporary files after a successful dispatch. Finalize browser tabs according to the Chrome-control skill.

### CDP limitations

- CDP is scoped to the current tab and origin. Reinstall the interceptor after a navigation or reload.
- Hooks do not reach cross-origin iframe execution contexts. Use a directly controlled invoice frame/tab or the OS-download fallback.
- If the `cdp` tab capability is unavailable, do not attempt writable JavaScript through Playwright. Use the OS-download fallback or report that the in-memory path is unavailable.
- If a provider requires `pageAssets` and that capability is unavailable, stop that provider safely. Do not print a signed URL, retry a cross-origin fetch known to fail, or guess at an undocumented download path.

## Claude Code with Claude in Chrome

Use Claude in Chrome's browser tools:

1. Initialize browser context and select the Chrome profile that owns the provider session.
2. Claim a matching existing tab or open a fresh one, and navigate with the browser tools.
3. Paste the complete `references/interceptor.js` IIFE into `javascript_tool` before clicking an invoice.
4. Reset captures with `window.__resetCapturedPdfs()`.
5. Read metadata with `await window.__getCapturedPdfMeta()`.
6. Read the selected Blob through `window.__readCapturedPdfChunk(key, offset, size)` in bounded chunks, or use a data URL only for small PDFs.

Do not return signed URLs from `javascript_tool`; return only event types, capture keys, sizes, MIME types, and PDF headers.

## Other browser agents

The runtime must provide all of these capabilities:

- Control of a signed-in browser tab.
- Writable page JavaScript or an equivalent debugging protocol.
- A safe way to transfer captured bytes to a local temporary file.
- Normal DOM or visual interaction for navigating invoice lists.

If any capability is missing, fall back to the OS download manager for one invoice at a time and document the limitation in the provider file.

## Confirmation boundary

Reading invoice lists and downloading invoices requested by the user are within the fetch workflow. Ask immediately before any separate external side effect, including changing a billing email, saving consent preferences, submitting account settings, or uploading to a destination the user did not already authorize for this run.
