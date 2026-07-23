// PDF download interceptor for in-browser capture.
//
// Install this IIFE before clicking a download button. It mirrors PDF bytes into
// window.__capturedBlobs and exposes bounded chunk readers so browser agents can
// extract PDFs without Chrome's multiple-download manager.

(() => {
  if (window.__hooksInstalled) return "already installed";

  const originals = {
    anchorClick: HTMLAnchorElement.prototype.click,
    createObjectURL: URL.createObjectURL,
    fetch: window.fetch,
    open: XMLHttpRequest.prototype.open,
    send: XMLHttpRequest.prototype.send,
    windowOpen: window.open,
  };

  let captureSequence = 0;

  const reset = () => {
    window.__capturedPdfs = [];
    window.__capturedBlobs = {};
    captureSequence = 0;
    return "cleared";
  };

  const isPdfish = (contentType, disposition, url = "") =>
    (contentType || "").toLowerCase().includes("pdf") ||
    (contentType || "").toLowerCase().includes("octet-stream") ||
    (disposition || "").toLowerCase().includes("attachment") ||
    /\.pdf(?:$|[?#])/i.test(url);

  const event = (details) => {
    window.__capturedPdfs.push({ ...details, t: Date.now() });
  };

  const stashBlob = (blob, source, details = {}) => {
    if (!(blob instanceof Blob)) return null;
    const key = details.key || `capture-${++captureSequence}`;
    window.__capturedBlobs[key] = blob;
    event({
      type: "blob",
      source,
      capture_key: key,
      ct: blob.type || details.ct || "",
      size: blob.size,
    });
    return key;
  };

  const captureResponse = async (response, source, url) => {
    try {
      const clone = response.clone();
      const blob = await clone.blob();
      stashBlob(blob, source, {
        ct: response.headers.get("content-type") || "",
      });
    } catch (error) {
      event({ type: "capture-error", source, message: String(error) });
    }
  };

  const captureUrl = async (url, source) => {
    try {
      const response = await originals.fetch.call(window, url, {
        credentials: "include",
      });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const blob = await response.blob();
      stashBlob(blob, source, {
        ct: response.headers.get("content-type") || "",
      });
    } catch (error) {
      event({ type: "capture-error", source, message: String(error) });
    }
  };

  reset();

  HTMLAnchorElement.prototype.click = function () {
    const href = this.href || "";
    if (
      this.download ||
      href.startsWith("blob:") ||
      href.startsWith("data:") ||
      /\.pdf(?:$|[?#])/i.test(href)
    ) {
      event({ type: "anchor", download: this.download || "" });
      if (!href.startsWith("blob:") || !window.__capturedBlobs[href]) {
        void captureUrl(href, "anchor");
      }
      return;
    }
    return originals.anchorClick.call(this);
  };

  window.fetch = async function (...args) {
    const response = await originals.fetch.apply(this, args);
    try {
      const contentType = response.headers.get("content-type") || "";
      const disposition = response.headers.get("content-disposition") || "";
      const url = typeof args[0] === "string" ? args[0] : args[0]?.url || "";
      if (isPdfish(contentType, disposition, url)) {
        event({ type: "fetch", ct: contentType, cd: disposition });
        void captureResponse(response, "fetch", url);
      }
    } catch (error) {
      event({ type: "capture-error", source: "fetch", message: String(error) });
    }
    return response;
  };

  XMLHttpRequest.prototype.open = function (method, url, ...rest) {
    this.__getInvoicesUrl = url;
    return originals.open.call(this, method, url, ...rest);
  };

  XMLHttpRequest.prototype.send = function (...args) {
    this.addEventListener("load", () => {
      const contentType = this.getResponseHeader("content-type") || "";
      const disposition = this.getResponseHeader("content-disposition") || "";
      if (!isPdfish(contentType, disposition, this.__getInvoicesUrl || "")) return;

      event({ type: "xhr", ct: contentType, cd: disposition });
      if (this.response instanceof Blob) {
        stashBlob(this.response, "xhr", { ct: contentType });
      } else if (this.response instanceof ArrayBuffer) {
        stashBlob(new Blob([this.response], { type: contentType }), "xhr", {
          ct: contentType,
        });
      }
    });
    return originals.send.apply(this, args);
  };

  URL.createObjectURL = function (object) {
    const url = originals.createObjectURL.call(this, object);
    if (
      object instanceof Blob &&
      isPdfish(object.type, "", url)
    ) {
      stashBlob(object, "createObjectURL", { key: url, ct: object.type });
    }
    return url;
  };

  window.open = function (url, ...rest) {
    if (
      url &&
      (/\.pdf(?:$|[?#])/i.test(url) ||
        /invoice|rechnung|beleg/i.test(url) ||
        url.startsWith("blob:"))
    ) {
      event({ type: "window.open" });
      if (!url.startsWith("blob:") || !window.__capturedBlobs[url]) {
        void captureUrl(url, "window.open");
      }
      return null;
    }
    return originals.windowOpen.call(this, url, ...rest);
  };

  window.__resetCapturedPdfs = reset;

  window.__getCapturedPdfMeta = async () => {
    const captures = [];
    for (const [key, blob] of Object.entries(window.__capturedBlobs || {})) {
      const headerBytes = new Uint8Array(await blob.slice(0, 8).arrayBuffer());
      captures.push({
        key,
        size: blob.size,
        type: blob.type,
        header: new TextDecoder().decode(headerBytes),
      });
    }
    return {
      count: captures.length,
      event_types: (window.__capturedPdfs || []).map((item) => item.type),
      captures,
    };
  };

  window.__readCapturedPdfChunk = async (key, offset, length) => {
    const blob = window.__capturedBlobs?.[key];
    if (!(blob instanceof Blob)) throw new Error(`Unknown capture key: ${key}`);
    const start = Math.max(0, Number(offset) || 0);
    const size = Math.max(1, Math.min(Number(length) || 262144, 1048576));
    const bytes = new Uint8Array(await blob.slice(start, start + size).arrayBuffer());
    let binary = "";
    for (let index = 0; index < bytes.length; index += 32768) {
      binary += String.fromCharCode(...bytes.subarray(index, index + 32768));
    }
    return btoa(binary);
  };

  window.__hooksInstalled = true;
  return "hooks installed";
})()
