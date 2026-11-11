/* helpers shared by the screenshot scenes (prepended to every scene) */
const W = ms => new Promise(r => setTimeout(r, ms));
async function until(f, n = 100) { for (let i = 0; i < n; i++) { if (f()) return; await W(50); } }
function done() {
  if (window.__errs && window.__errs.length) {
    const d = document.createElement("div");
    d.style.cssText = "position:fixed;top:0;left:0;right:0;background:#c00;color:#fff;z-index:99;font:12px monospace;padding:4px";
    d.textContent = "JS ERRORS: " + window.__errs.join(" | ");
    document.body.append(d);
  }
}
async function pick(selId, value) {
  const s = document.querySelector(selId); s.value = value; s.dispatchEvent(new Event("change"));
}
