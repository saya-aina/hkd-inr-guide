/* Shared provider model: used by the home page widget and the remittance page. */
const PROVIDERS = [
  // ===== Fintechs — verified from provider sites on 2026-10-31 (HKD 10,000 → INR) =====
  { id: "wise", name: "Wise", host: "wise.com", avatar: "W", fee_flat_hkd: 60.63, aff: true, fee_curve: [[1000, 13.18], [10000, 60.63], [50000, 271.51]], fee_note: "Fee scales with the amount (about 1.3% at HK$1,000, 0.6% at 10,000, 0.5% at 50,000). Mid-market rate. Bank transfer or FPS; paying by debit card costs far more (about 4.8% at HK$10,000).", fx_margin_pct: 0.00, delivery_minutes: 1, delivery_label: "Seconds", max_single_transfer_hkd: 1000000, high_value_friendly: true, iam_smart: false, nre: true, firc: true, weekend_processing: true, instant_imps: true, affiliate_url: "https://wise.prf.hn/click/camref:1100l6zoeY", last_verified: "2026-11-18" },
  { id: "instarem", name: "Instarem", host: "instarem.com", avatar: "I", fee_flat_hkd: 59, fee_pct: 0.59, aff: true, fee_note: "Fee is 0.59% of the amount sent (bank transfer, checked 4, 7 and 18 Nov 2026). A first-transfer fee waiver may apply; it is not included in these figures. Debit card carries a higher fee.", fx_margin_pct: 0.01, delivery_minutes: 60, delivery_label: "1 Hr", max_single_transfer_hkd: 1000000, high_value_friendly: true, iam_smart: false, nre: true, firc: true, weekend_processing: true, instant_imps: true, affiliate_url: "https://instarem.prf.hn/click/camref:1110lSAw4", last_verified: "2026-11-18" },
  { id: "wu", name: "Western Union", host: "westernunion.com", avatar: "W", fee_flat_hkd: 5, fx_margin_pct: 0.10, fee_note: "Indicative only. The quote we saw on 7 Nov was a new-customer offer (fee waived, better rate at small amounts), so we cannot confirm the standard price. Standard fee appears to be about HK$5.", delivery_minutes: 1, delivery_label: "Real-time", max_single_transfer_hkd: 15000, high_value_friendly: false, iam_smart: false, nre: true, firc: true, weekend_processing: true, instant_imps: true, affiliate_url: "https://www.westernunion.com/", last_verified: null },
  { id: "panda", name: "Panda Remit", host: "pandaremit.com", avatar: "P", aff: true, cta_note: "New customers only", fee_flat_hkd: 100, fx_margin_pct: 0.42, fee_note: "Indicative only. Panda Remit shows rates and fees only to new customers (promo pricing), so we cannot confirm the standard price. Standard fee appears to be about HK$100.", delivery_minutes: 120, delivery_label: "2 Hrs", max_single_transfer_hkd: 100000, high_value_friendly: false, iam_smart: false, nre: true, firc: false, weekend_processing: true, instant_imps: true, affiliate_url: "https://pandaremit.sjv.io/yZ1YQB", last_verified: null },
  { id: "ofx", name: "OFX", host: "ofx.com", avatar: "O", fee_flat_hkd: 60, fee_steps: [[0, 60], [50000, 0]], margin_curve: [[1000, 4.31], [10000, 3.65], [50000, 3.16]], fee_note: "HK$60 fee below HK$50,000, none above. The rate is 3–4% below mid-market, much worse than the fintechs (checked 18 Nov 2026, bank transfer).", fx_margin_pct: 3.65, delivery_minutes: 1440, delivery_label: "1–2 Days", max_single_transfer_hkd: 1000000, high_value_friendly: true, iam_smart: false, nre: true, firc: false, weekend_processing: false, instant_imps: false, affiliate_url: "https://www.ofx.com/", last_verified: "2026-11-18" },
  { id: "mg", name: "MoneyGram", host: "moneygram.com", avatar: "M", fee_flat_hkd: 8, fx_margin_pct: 1.06, fee_note: "Flat HK$8 fee. Rate is about 1.1% below mid-market (checked 18 Nov 2026, bank transfer).", delivery_minutes: 1440, delivery_label: "1 Day", max_single_transfer_hkd: 1500000, high_value_friendly: true, iam_smart: false, nre: true, firc: true, weekend_processing: true, instant_imps: true, affiliate_url: "https://www.moneygram.com/", last_verified: "2026-11-18" },
  // ===== Indian bank NRI remittance services — INDICATIVE (needs manual verification) =====
  { id: "currencyfair", name: "CurrencyFair", host: "currencyfair.com", avatar: "C", fee_flat_hkd: 10, fx_margin_pct: 0.74, fee_note: "Indicative only. Rate and a fee of about HK$10 come from the provider's converter page (18 Nov 2026). We have not confirmed that Hong Kong residents can open an account.", delivery_minutes: 1440, delivery_label: "1–2 Days", max_single_transfer_hkd: 1000000, high_value_friendly: true, iam_smart: false, nre: false, firc: false, weekend_processing: false, instant_imps: false, affiliate_url: "https://www.currencyfair.com/", last_verified: null },
  { id: "axisremit", group: "bank", name: "Axis Remit", host: "axisbank.com", avatar: "A", fee_note: "Indicative, based on Axis Bank's published TT buying rate for inward remittance (11.55 INR per HKD, published 19 Nov 2026, 09:23 IST), about 2.9% below mid-market. It is a board rate, not a quote; account holders may get better. Check with your bank.", fee_flat_hkd: 0, fx_margin_pct: 2.9, delivery_minutes: 1440, delivery_label: "1 Day", max_single_transfer_hkd: 2500000, high_value_friendly: true, iam_smart: false, nre: true, firc: true, weekend_processing: false, instant_imps: false, affiliate_url: null, last_verified: null },
  { id: "hdfc", group: "bank", name: "HDFC RemitNow", host: "hdfcbank.com", avatar: "H", fee_note: "Indicative, based on HDFC Bank's published TT buying rate for inward remittance (11.54 INR per HKD, sheet dated 18 Nov 2026, 09:21 IST), about 3.2% below mid-market. It is a board rate, not a quote; account holders may get better. Check with your bank.", fee_flat_hkd: 0, fx_margin_pct: 3.2, delivery_minutes: 1440, delivery_label: "1 Day", max_single_transfer_hkd: 2500000, high_value_friendly: true, iam_smart: false, nre: true, firc: true, weekend_processing: false, instant_imps: false, affiliate_url: null, last_verified: null },
  { id: "kotak", group: "bank", name: "Kotak Remit", host: "kotak.com", avatar: "K", fee_note: "Indicative, based on Kotak Mahindra Bank's published TT buying rate for inward remittance (11.56 INR per HKD, card rates valid 19 Nov 2026, set at 9am), about 2.8% below mid-market. It is a board rate, not a quote; account holders may get better. Check with your bank.", fee_flat_hkd: 0, fx_margin_pct: 2.8, delivery_minutes: 1440, delivery_label: "1 Day", max_single_transfer_hkd: 2500000, high_value_friendly: true, iam_smart: false, nre: true, firc: true, weekend_processing: false, instant_imps: false, affiliate_url: null, last_verified: null },
  { id: "icici", group: "bank", name: "ICICI Money2India", host: "money2india.com", avatar: "I", fee_note: "Indicative, based on ICICI Bank's published TT buying rate for inward remittance (11.56 INR per HKD, last updated 19 Nov 2026, 09:16 IST), about 2.8% below mid-market. It is a board rate, not a quote; account holders may get better. Check with your bank.", fee_flat_hkd: 0, fx_margin_pct: 2.8, delivery_minutes: 1440, delivery_label: "1 Day", max_single_transfer_hkd: 2500000, high_value_friendly: true, iam_smart: false, nre: true, firc: true, weekend_processing: false, instant_imps: false, affiliate_url: null, last_verified: null },
  { id: "federalbank", group: "bank", name: "Federal Bank NRI", host: "federalbank.co.in", avatar: "F", fee_note: "Indicative, based on Federal Bank's published TT buying rate for inward remittance (11.70 INR per HKD, published 19 Nov 2026, 09:00 IST), about 1.6% below mid-market. It is a board rate, not a quote; account holders may get better. Check with your bank.", fee_flat_hkd: 0, fx_margin_pct: 1.6, delivery_minutes: 1440, delivery_label: "1 Day", max_single_transfer_hkd: 2500000, high_value_friendly: true, iam_smart: false, nre: true, firc: true, weekend_processing: false, instant_imps: false, affiliate_url: null, last_verified: null },
  // ===== HK banks — indicative only (existing-customer product; sites require login for live quote) =====
  { id: "hsbc", group: "bank", name: "HSBC Global Transfers", host: "hsbc.com.hk", avatar: "H", fee_note: "Ballpark only, not a quote. Estimated from the Hong Kong Association of Banks reference selling rate for INR (HK$9.05 per 100 INR, 19 Nov 2026); HSBC HK's USD board rates sit within about 0.05% of the same reference. Roughly 7.1% below mid-market. HSBC's online transfer rate may be better. Check with your bank.", fee_flat_hkd: 0, fx_margin_pct: 7.1, delivery_minutes: 60, delivery_label: "1 Hr", max_single_transfer_hkd: 5000000, high_value_friendly: true, iam_smart: true, nre: true, firc: true, weekend_processing: false, instant_imps: false, affiliate_url: null, last_verified: null },
  { id: "dbs", group: "bank", name: "DBS Remit (DBS HK)", host: "dbs.com.hk", avatar: "D", fee_note: "Ballpark only, not a quote. Estimated from the Hong Kong Association of Banks reference selling rate for INR (HK$9.05 per 100 INR, 19 Nov 2026); DBS HK's USD board rates sit within about 0.05% of the same reference. Roughly 7.1% below mid-market. Check with your bank.", fee_flat_hkd: 0, fx_margin_pct: 7.1, delivery_minutes: 60, delivery_label: "1 Hr", max_single_transfer_hkd: 3000000, high_value_friendly: true, iam_smart: true, nre: true, firc: true, weekend_processing: false, instant_imps: false, affiliate_url: null, last_verified: null },
  { id: "bochk", group: "bank", name: "Bank of China (HK)", host: "bochk.com", avatar: "B", fee_note: "Ballpark only, not a quote. Estimated from BOCHK's remittance rate sheet (1 USD = 91.7893 INR, 19 Nov 2026), converting HKD to USD at the HKAB reference USD selling rate (7.876). Roughly 2.0% below mid-market. The HK$50 fee is not sourced. Check with your bank.", fee_flat_hkd: 50, fx_margin_pct: 2.0, delivery_minutes: 1440, delivery_label: "1 Day", max_single_transfer_hkd: 3000000, high_value_friendly: true, iam_smart: true, nre: true, firc: true, weekend_processing: false, instant_imps: false, affiliate_url: null, last_verified: null }
];
let liveOverrides = {};
function interpClamp(c, x) {
  const n = c.length;
  if (x <= c[0][0]) return c[0][1];
  for (let i = 1; i < n; i++) if (x <= c[i][0]) return c[i-1][1] + (x - c[i-1][0]) * (c[i][1] - c[i-1][1]) / (c[i][0] - c[i-1][0]);
  return c[n-1][1];
}
function marginFor(p, hkd) { return p.margin_curve ? +interpClamp(p.margin_curve, hkd).toFixed(2) : p.fx_margin_pct; }
function feeFor(p, hkd) {
  if (p.fee_steps) { let f = p.fee_steps[0][1]; p.fee_steps.forEach(st => { if (hkd >= st[0]) f = st[1]; }); return f; }
  if (p.fee_curve) {
    const c = p.fee_curve, n = c.length;
    if (hkd <= c[0][0]) return +(c[0][1] * hkd / c[0][0]).toFixed(2);
    for (let i = 1; i < n; i++) {
      if (hkd <= c[i][0]) return +(c[i-1][1] + (hkd - c[i-1][0]) * (c[i][1] - c[i-1][1]) / (c[i][0] - c[i-1][0])).toFixed(2);
    }
    const slope = (c[n-1][1] - c[n-2][1]) / (c[n-1][0] - c[n-2][0]);
    return +(c[n-1][1] + (hkd - c[n-1][0]) * slope).toFixed(2);
  }
  if (p.fee_pct != null) return +(hkd * p.fee_pct / 100).toFixed(2);
  return p.fee_flat_hkd;
}
async function loadLiveOverrides() {
  try {
    const r = await fetch("rates.json?t=" + Date.now(), { cache: "no-store" });
    if (!r.ok) return;
    const data = await r.json();
    if (data && data.providers) liveOverrides = Object.fromEntries(data.providers.map(p => [p.id, p]));
  } catch (_) {}
}
// Providers whose live feed carries fee/margin points at several amounts (OFX, Western Union): interpolate between them.
function liveFromPoints(id, hkd) {
  const o = liveOverrides[id];
  if (!o || o.source !== "api" || !Array.isArray(o.points) || !o.points.length || !o.fetched_at) return null;
  if (Date.now() - new Date(o.fetched_at).getTime() > 36 * 3600 * 1000) return null;
  const pts = o.points.slice().sort((a, b) => a.amount_hkd - b.amount_hkd);
  const lerp = (k) => {
    if (hkd <= pts[0].amount_hkd) return pts[0][k];
    for (let i = 1; i < pts.length; i++) {
      if (hkd <= pts[i].amount_hkd) { const a = pts[i - 1], b = pts[i], t = (hkd - a.amount_hkd) / (b.amount_hkd - a.amount_hkd); return a[k] + (b[k] - a[k]) * t; }
    }
    return pts[pts.length - 1][k];
  };
  // Fees step with the amount (e.g. OFX waives its fee from HK$50,000), so take the nearest point at or below; margin is interpolated.
  let fee = pts[0].fee_hkd;
  for (const q of pts) if (hkd >= q.amount_hkd) fee = q.fee_hkd;
  return { flat: +fee.toFixed(2), margin: lerp("fx_margin_pct"), at: o.fetched_at };
}
// Bank board rates (ICICI, Axis, Federal, and HKAB-based HSBC / DBS): a daily published rate, not a quote.
function liveFromBoard(p) {
  const o = liveOverrides[p.id];
  if (!o || o.source !== "board" || o.fx_margin_pct == null || !o.published_at) return null;
  if (Date.now() - new Date(o.published_at).getTime() > 7 * 24 * 3600 * 1000) return null;
  const when = new Date(o.published_at).toLocaleString("en-GB", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: o.kind === "hkab_reference" ? "Asia/Hong_Kong" : "Asia/Kolkata" }) + (o.kind === "hkab_reference" ? " HKT" : " IST");
  const m = o.fx_margin_pct.toFixed(1);
  const note = o.kind === "hkab_reference"
    ? "Ballpark only, not a quote. Estimated from the Hong Kong Association of Banks reference selling rate for INR (HK$" + o.hkab_selling_hkd_per_100_inr.toFixed(2) + " per 100 INR, " + when + "); " + p.name.replace(/ \(.*\)$/, "") + "'s own board rates are expected to sit close to it. Roughly " + m + "% below mid-market. Check with your bank."
    : "Indicative, based on the bank's published TT buying rate for inward remittance (" + o.rate_inr_per_hkd.toFixed(2) + " INR per HKD, published " + when + "), about " + m + "% below mid-market. It is a board rate, not a quote; account holders may get better. Check with your bank.";
  return { margin: o.fx_margin_pct, note: note, at: o.published_at };
}
// Panda Remit - live promo rate (new customers only). Shown but not crowned.
function livePandaPromo(p) {
  if (p.id !== "panda") return null;
  const o = liveOverrides.panda;
  if (!o || o.source !== "api_promo" || o.fx_margin_pct == null || !o.fetched_at) return null;
  if (Date.now() - new Date(o.fetched_at).getTime() > 36 * 3600 * 1000) return null;
  return { flat: o.fee_flat_hkd, margin: o.fx_margin_pct, at: o.fetched_at, published_at: o.published_at };
}
function effectiveINR(p, hkdIn) {
  const hkd = hkdIn != null ? hkdIn : (parseFloat(document.getElementById("hkd").value) || 0);
  const midRate = window.__midRate;
  if (!midRate || !hkd) return null;
  const pp = livePandaPromo(p);
  if (pp) { return { net_inr: Math.max(0, hkd - pp.flat) * midRate * (1 - pp.margin / 100), rate: midRate * (1 - pp.margin / 100), flat: pp.flat, margin: pp.margin, live_source: "api_promo", live_at: pp.at, live_published: pp.published_at }; }
  const bd = liveFromBoard(p);
  if (bd) { const f = p.fee_flat_hkd || 0; return { net_inr: Math.max(0, hkd - f) * midRate * (1 - bd.margin / 100), rate: midRate * (1 - bd.margin / 100), flat: f, margin: bd.margin, live_source: "board", live_at: null }; }
  const pts = liveFromPoints(p.id, hkd);
  if (pts) return { net_inr: Math.max(0, hkd - pts.flat) * midRate * (1 - pts.margin / 100), rate: midRate * (1 - pts.margin / 100), flat: pts.flat, margin: pts.margin, live_source: "api", live_at: pts.at };
  const iLive = p.id === "instarem" ? liveOverrides.instarem : null;
  const iOk = !!(iLive && iLive.source === "api" && iLive.fee_pct != null && iLive.fetched_at && (Date.now() - new Date(iLive.fetched_at).getTime()) < 36 * 3600 * 1000);
  const scaled = !!(p.fee_curve || p.fee_pct != null || p.fee_steps);
  // Amount-based providers use our checked fee/margin model; the hourly feed is a single 10k snapshot and its margin is distorted by a different mid-market source.
  const live = scaled ? {} : (liveOverrides[p.id] || {});
  const flat = iOk ? +(hkd * iLive.fee_pct / 100).toFixed(2) : (scaled ? feeFor(p, hkd) : (live.fee_flat_hkd != null ? live.fee_flat_hkd : p.fee_flat_hkd));
  const margin = iOk ? iLive.fx_margin_pct : (p.margin_curve ? marginFor(p, hkd) : (live.fx_margin_pct != null ? live.fx_margin_pct : p.fx_margin_pct));
  return { net_inr: Math.max(0, hkd - flat) * midRate * (1 - margin / 100), rate: midRate * (1 - margin / 100), flat, margin, live_source: iOk ? "api" : live.source, live_at: iOk ? iLive.fetched_at : null };
}
