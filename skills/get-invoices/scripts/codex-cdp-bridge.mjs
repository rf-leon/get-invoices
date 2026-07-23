import { mkdir, open, readFile } from "node:fs/promises";
import { dirname } from "node:path";

const DEFAULT_CHUNK_SIZE = 256 * 1024;

function remoteValue(reply) {
  const payload = reply?.result?.result ?? reply?.result ?? reply;
  const exception = reply?.result?.exceptionDetails ?? reply?.exceptionDetails;

  if (exception) {
    const description =
      exception.exception?.description ||
      exception.text ||
      "CDP Runtime.evaluate failed";
    throw new Error(description);
  }

  if (payload?.subtype === "error") {
    throw new Error(payload.description || "CDP returned an error object");
  }

  if (Object.prototype.hasOwnProperty.call(payload || {}, "value")) {
    return payload.value;
  }

  if (payload?.unserializableValue != null) {
    return payload.unserializableValue;
  }

  return payload;
}

async function runtimeEvaluate(tab, expression) {
  const cdp = await tab.capabilities.get("cdp");
  const reply = await cdp.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
    userGesture: true,
  });
  return remoteValue(reply);
}

export async function installInterceptor(tab, interceptorPath) {
  const source = await readFile(interceptorPath, "utf8");
  return runtimeEvaluate(tab, `${source}\n//# sourceURL=get-invoices-interceptor.js`);
}

export async function resetCaptures(tab) {
  return runtimeEvaluate(
    tab,
    `window.__resetCapturedPdfs ? window.__resetCapturedPdfs() : "interceptor not installed"`,
  );
}

export async function getCaptureMeta(tab) {
  const value = await runtimeEvaluate(
    tab,
    `window.__getCapturedPdfMeta ? window.__getCapturedPdfMeta() : null`,
  );

  if (!value) {
    throw new Error("PDF interceptor is not installed in the current page");
  }

  return value;
}

export async function writeCapture(
  tab,
  { captureKey, destination, chunkSize = DEFAULT_CHUNK_SIZE },
) {
  if (!captureKey) throw new Error("captureKey is required");
  if (!destination) throw new Error("destination is required");
  if (!Number.isInteger(chunkSize) || chunkSize < 16 * 1024 || chunkSize > 1024 * 1024) {
    throw new Error("chunkSize must be an integer between 16 KiB and 1 MiB");
  }

  const state = await getCaptureMeta(tab);
  const capture = state.captures.find((item) => item.key === captureKey);
  if (!capture) throw new Error(`Unknown capture key: ${captureKey}`);
  if (!String(capture.header || "").startsWith("%PDF")) {
    throw new Error(`Capture ${captureKey} does not start with %PDF`);
  }

  await mkdir(dirname(destination), { recursive: true });
  const file = await open(destination, "w", 0o600);
  let written = 0;

  try {
    while (written < capture.size) {
      const requested = Math.min(chunkSize, capture.size - written);
      const expression = `window.__readCapturedPdfChunk(${JSON.stringify(
        captureKey,
      )}, ${written}, ${requested})`;
      const base64 = await runtimeEvaluate(tab, expression);
      const bytes = Buffer.from(base64, "base64");

      if (bytes.length === 0) {
        throw new Error(`Capture ${captureKey} returned an empty chunk at byte ${written}`);
      }

      await file.write(bytes, 0, bytes.length, written);
      written += bytes.length;
    }
  } finally {
    await file.close();
  }

  if (written !== capture.size) {
    throw new Error(`Capture size mismatch: expected ${capture.size}, wrote ${written}`);
  }

  const verify = await open(destination, "r");
  const headerBuffer = Buffer.alloc(8);
  try {
    await verify.read(headerBuffer, 0, headerBuffer.length, 0);
  } finally {
    await verify.close();
  }

  const header = headerBuffer.toString("latin1");
  if (!header.startsWith("%PDF")) {
    throw new Error(`Extracted file does not start with %PDF: ${destination}`);
  }

  return {
    destination,
    size: written,
    type: capture.type,
    header,
  };
}
