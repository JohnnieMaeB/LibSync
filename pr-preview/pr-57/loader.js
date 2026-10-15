/*!
 * LibSync embeddable widget loader (Tier 6).
 *
 * Deliberately dependency-free vanilla JS — this has to load fast and
 * safely on a library website LibSync doesn't control (WordPress, Drupal,
 * LibGuides, a decade of accumulated global CSS), so it stays outside the
 * React bundle entirely and never touches the host page's own styles or
 * scripts. All visuals are inline styles (never a <style> tag or class
 * name) specifically so nothing here can collide with host-page CSS.
 *
 * Usage:
 *   <script src="https://embed.libsync.app/loader.js" data-library="example-library"
 *           data-accent="#ffd166" data-position="bottom-right" async></script>
 *
 * See TIER6_PLAN.md for the full design (iframe isolation, postMessage
 * contract, per-origin rate limiting on the backend).
 */
(function () {
  "use strict";

  var thisScript = document.currentScript;
  if (!thisScript) return;

  var libraryId = thisScript.getAttribute("data-library");
  if (!libraryId) {
    console.error("LibSync widget: missing required data-library attribute on the loader <script> tag.");
    return;
  }
  var accent = thisScript.getAttribute("data-accent") || "#ffd166";
  var position = thisScript.getAttribute("data-position") === "bottom-left" ? "bottom-left" : "bottom-right";
  var startOpen = thisScript.getAttribute("data-open") === "true";

  // The directory containing loader.js is the same directory that serves
  // the built React app (both come out of app/public + vite build into the
  // same dist root) — deriving from the script's own URL, not just its
  // origin, keeps this correct under a project-page subpath deployment
  // (e.g. https://user.github.io/LibSync/) and PR-preview subpaths
  // (.../pr-preview/pr-42/), not just a root domain.
  var baseUrl = new URL(".", thisScript.src).href;
  var iframeSrc = baseUrl + "?mode=widget&library=" + encodeURIComponent(libraryId);

  var SIDE_OFFSET = "20px";
  var sideStyle = position === "bottom-left" ? "left:" + SIDE_OFFSET : "right:" + SIDE_OFFSET;

  var launcher = document.createElement("button");
  launcher.type = "button";
  launcher.setAttribute("aria-label", "Open chat with LibSync");
  launcher.textContent = "💬"; // 💬
  launcher.style.cssText = [
    "position:fixed",
    "bottom:" + SIDE_OFFSET,
    sideStyle,
    "width:56px",
    "height:56px",
    "border-radius:50%",
    "border:none",
    "background-color:" + accent,
    "color:#000000",
    "font-size:24px",
    "line-height:56px",
    "text-align:center",
    "padding:0",
    "cursor:pointer",
    "box-shadow:0 4px 14px rgba(0,0,0,0.35)",
    "z-index:2147483000",
  ].join(";");

  var frame = null;
  var open = false;

  function frameStyle(isOpen) {
    return [
      "position:fixed",
      "bottom:" + SIDE_OFFSET,
      sideStyle,
      "width:min(400px, calc(100vw - 24px))",
      "height:min(680px, calc(100vh - 24px))",
      "border:none",
      "border-radius:16px",
      "box-shadow:0 8px 30px rgba(0,0,0,0.45)",
      "z-index:2147483000",
      "display:" + (isOpen ? "block" : "none"),
      "color-scheme:normal",
    ].join(";");
  }

  function ensureFrame() {
    if (frame) return frame;
    frame = document.createElement("iframe");
    frame.title = "LibSync chat";
    frame.src = iframeSrc;
    frame.style.cssText = frameStyle(false);
    // Same-origin as this loader's own host page would be a mistake here —
    // this intentionally points at LibSync's own domain, giving full
    // browsing-context isolation (see TIER6_PLAN.md §1) rather than a
    // same-document Shadow DOM mount.
    document.body.appendChild(frame);
    return frame;
  }

  function setOpen(next) {
    open = next;
    if (next) ensureFrame();
    if (frame) frame.style.cssText = frameStyle(open);
    launcher.style.display = open ? "none" : "block";
  }

  launcher.addEventListener("click", function () {
    setOpen(true);
  });

  window.addEventListener("message", function (event) {
    if (!frame || event.source !== frame.contentWindow) return;
    var data = event.data || {};
    if (data.type === "libsync:close") {
      setOpen(false);
    } else if (data.type === "libsync:resize" && data.height) {
      var height = Math.max(200, Math.min(Number(data.height) || 0, window.innerHeight - 24));
      if (height > 0) frame.style.height = height + "px";
    }
  });

  // `async` (the recommended attribute on the embed snippet) can execute
  // this script before document.body exists yet — defer the actual DOM
  // insertion until it does, rather than assuming script placement/timing.
  function whenBodyReady(fn) {
    if (document.body) {
      fn();
    } else {
      document.addEventListener("DOMContentLoaded", fn);
    }
  }

  whenBodyReady(function () {
    document.body.appendChild(launcher);
    if (startOpen) setOpen(true);
  });
})();
