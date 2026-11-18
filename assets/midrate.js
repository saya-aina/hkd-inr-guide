/* Shared mid-market rate loader for pages with a transfer widget */
(function() {
  const FALLBACK_RATE = 12.14;

  const widgetSend = document.getElementById("widgetSendDisplay");
  const widgetReceive = document.getElementById("widgetReceiveDisplay");
  const widgetRateChip = document.getElementById("widgetRateChip");
  const hkdEl = document.getElementById("hkd");
  if (!widgetSend && !hkdEl) return; // no widget on this page

  let midRate = null;

  function fmtPlain(n, d) {
    if (!isFinite(n)) return "—";
    return n.toLocaleString("en-IN", { maximumFractionDigits: d, minimumFractionDigits: d });
  }
  function fmtRate(n) {
    return n.toLocaleString("en-IN", { minimumFractionDigits: 4, maximumFractionDigits: 4 });
  }
  function recalc() {
    const hkd = hkdEl ? (parseFloat(hkdEl.value) || 0) : 10000;
    if (widgetSend) widgetSend.textContent = fmtPlain(hkd, 0);
    if (midRate && widgetReceive) widgetReceive.textContent = fmtPlain(hkd * midRate, 2);
    if (midRate && widgetRateChip) widgetRateChip.innerHTML = '1 HKD <span class="arrow">→</span> ' + fmtRate(midRate) + ' INR';
    if (window.__onRateUpdate) window.__onRateUpdate(midRate);
  }

  const labelEl = document.getElementById("midRateLabel");
  function setLabel(text) { if (labelEl) labelEl.textContent = text; }

  async function loadRate() {
    // 1. rates.json: written by the hourly job from Wise's mid-market rate.
    try {
      const rj = await fetch("rates.json?t=" + Date.now(), { cache: "no-store" });
      if (rj.ok) {
        const j = await rj.json();
        const ts = j && j.updated_at ? new Date(j.updated_at) : null;
        const ageH = ts ? (Date.now() - ts.getTime()) / 3600000 : Infinity;
        if (j && j.mid_market_rate > 0 && ageH < 24) {
          midRate = j.mid_market_rate;
          setLabel(j.mid_source === "wise" ? "Mid-market · updated " + ts.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Mid-market · daily feed");
          window.__midRate = midRate;
          recalc();
          return;
        }
      }
    } catch (e) { /* fall through to the daily feed */ }
    // 2. Fallback: daily currency feed.
    const url = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/hkd.json?t=" + Date.now();
    try {
      const r = await fetch(url, { cache: "no-store" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const data = await r.json();
      midRate = (data && data.hkd && data.hkd.inr) || FALLBACK_RATE;
      setLabel("Mid-market · daily feed");
    } catch (e) {
      midRate = FALLBACK_RATE;
      setLabel("Mid-market · approximate");
    }
    window.__midRate = midRate;
    recalc();
  }

  if (hkdEl) hkdEl.addEventListener("input", recalc);
  const refreshBtn = document.getElementById("refreshBtn");
  if (refreshBtn) refreshBtn.addEventListener("click", loadRate);

  loadRate();
})();
