"""
HKD to INR remittance rate scraper.

Writes rates.json with:
  - mid_market_rate: Wise's quoted rate (its mid-market rate, no markup) when
    the Wise comparison call works; otherwise fawazahmed0/currency-api via
    jsDelivr (free, keyless, updated daily). mid_source says which one.
  - providers[].fee_flat_hkd / fx_margin_pct: live for providers with
    public APIs; omitted for the rest so the frontend falls back to curated
    values in index.html.
"""

from __future__ import annotations

import json
import sys
import datetime as dt
from pathlib import Path
from typing import Any

import requests

AMOUNT_HKD = 10_000
TIMEOUT = 15
OUT_PATH = Path("rates.json")

FX_PRIMARY = (
    "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/"
    "v1/currencies/hkd.json"
)
FX_FALLBACK = (
    "https://latest.currency-api.pages.dev/v1/currencies/hkd.json"
)


def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Mid-market rate
# ---------------------------------------------------------------------------

def _fetch_from(url: str) -> float | None:
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    inr = data.get("hkd", {}).get("inr")
    if inr is None:
        return None
    return float(inr)


def fetch_mid_market() -> float | None:
    """
    Fetch the HKD to INR mid-market rate from fawazahmed0/currency-api,
    served through jsDelivr. Falls back to the Cloudflare Pages mirror
    if jsDelivr is unavailable. Returns None if both fail.
    """
    for url in (FX_PRIMARY, FX_FALLBACK):
        try:
            rate = _fetch_from(url)
            if rate:
                return rate
        except Exception as e:
            print(f"[mid-market] {url} failed: {e}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Wise comparison API
# ---------------------------------------------------------------------------

def fetch_wise_quote(mid: float) -> dict[str, Any] | None:
    try:
        r = requests.get(
            "https://api.wise.com/v4/comparisons/",
            params={
                "sourceCurrency": "HKD",
                "targetCurrency": "INR",
                "sendAmount": AMOUNT_HKD,
            },
            timeout=TIMEOUT,
            headers={
                "User-Agent": "hkd-inr-comparison/1.0 (informational directory)"
            },
        )
        r.raise_for_status()
        data = r.json()

        providers = data.get("providers") or data.get("comparisons") or []
        wise_row = next(
            (
                p
                for p in providers
                if (p.get("alias") or p.get("name") or "").lower() == "wise"
            ),
            None,
        )
        if not wise_row:
            print("[wise] no Wise row in comparison response", file=sys.stderr)
            return None

        quotes = wise_row.get("quotes") or [wise_row]
        q = quotes[0]

        fee = q.get("fee")
        rate = q.get("rate")
        if fee is None or rate is None:
            print("[wise] fee/rate missing in quote", file=sys.stderr)
            return None

        # Wise's quoted rate is its mid-market rate with no markup (checked 7 Nov 2026),
        # so its cost is the fee alone. Measuring the gap against currency-api's mid
        # gave a spurious ~0.5% margin, so we pin it to 0.
        fx_margin_pct = 0.0

        return {
            "_rate": float(rate),
            "fee_flat_hkd": round(float(fee), 2),
            "fx_margin_pct": fx_margin_pct,
            "reference_amount_hkd": AMOUNT_HKD,
            "source": "api",
            "fetched_at": iso_now(),
        }
    except Exception as e:
        print(f"[wise] failed: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Instarem public retail API (shared by Instarem's partnerships team, 17 Nov 2026)
# ---------------------------------------------------------------------------

INSTAREM_BASE = "https://www.instarem.com/api/v1/public"
UA = {"User-Agent": "hkd-inr-comparison/1.0 (informational directory)"}


def fetch_instarem_quote(mid: float) -> dict[str, Any] | None:
    """
    Two calls: payment-method (to find the bank-transfer key), then
    computed-value for HKD 10,000. Uses the REGULAR (non-promo) fee percent, and
    derives the FX margin against the mid-market rate. Returns None on any
    surprise so the site falls back to its curated figures.
    """
    try:
        r = requests.get(
            f"{INSTAREM_BASE}/payment-method/fee",
            params={
                "source_currency": "HKD",
                "source_amount": AMOUNT_HKD,
                "destination_currency": "INR",
            },
            timeout=TIMEOUT, headers=UA,
        )
        r.raise_for_status()
        methods = (r.json() or {}).get("data") or []
        bank = next(
            (m for m in methods
             if not m.get("is_pg") and "bank" in (m.get("text") or "").lower()),
            None,
        ) or next((m for m in methods if not m.get("is_pg")), None)
        if not bank or bank.get("key") is None:
            print("[instarem] no bank-transfer payment method found", file=sys.stderr)
            return None

        r = requests.get(
            f"{INSTAREM_BASE}/transaction/computed-value",
            params={
                "device": "web",
                "source_currency": "HKD",
                "destination_currency": "INR",
                "instarem_bank_account_id": bank["key"],
                "source_amount": AMOUNT_HKD,
            },
            timeout=TIMEOUT, headers=UA,
        )
        r.raise_for_status()
        data = (r.json() or {}).get("data") or {}
        cfg = data.get("transaction_config") or {}
        fx = data.get("instarem_fx_rate") or data.get("fx_rate") or cfg.get("fx_rate")
        fee_pct = cfg.get("regular_total_fee_percent")
        if fee_pct is None:
            fee_pct = cfg.get("total_fee_percent")
        if not fx or fee_pct is None:
            print("[instarem] fx_rate or fee percent missing", file=sys.stderr)
            return None
        fx, fee_pct = float(fx), float(fee_pct)
        margin = (1 - fx / mid) * 100
        # Sanity bounds: a bad parse should never reach the site.
        if not (0 <= fee_pct <= 3) or not (-0.5 <= margin <= 3):
            print(f"[instarem] implausible fee {fee_pct}% or margin {margin:.2f}%", file=sys.stderr)
            return None
        return {
            "fee_pct": round(fee_pct, 3),
            "fx_margin_pct": round(max(margin, 0.0), 3),
            "reference_amount_hkd": AMOUNT_HKD,
            "source": "api",
            "fetched_at": iso_now(),
        }
    except Exception as e:
        print(f"[instarem] failed: {e}", file=sys.stderr)
        return None



# ---------------------------------------------------------------------------
# Other providers via the same public Wise comparison endpoint
# ---------------------------------------------------------------------------

COMPARE_AMOUNTS = (1_000, 10_000, 50_000)

# site provider id -> aliases the comparison endpoint uses. For HKD to INR the
# endpoint lists only Wise, Instarem and OFX (checked 27 Nov 2026).
COMPARE_ALIASES = {
    "ofx": ("ofx",),
}


def _fetch_comparison(amount: int) -> list[dict[str, Any]] | None:
    try:
        r = requests.get(
            "https://api.wise.com/v4/comparisons/",
            params={"sourceCurrency": "HKD", "targetCurrency": "INR", "sendAmount": amount},
            timeout=TIMEOUT, headers=UA,
        )
        r.raise_for_status()
        data = r.json()
        return data.get("providers") or data.get("comparisons") or []
    except Exception as e:
        print(f"[compare] {amount} failed: {e}", file=sys.stderr)
        return None


def fetch_comparison_providers() -> dict[str, dict[str, Any]]:
    """
    For each provider in COMPARE_ALIASES, build fee/margin points at three
    amounts from Wise's public comparison data. Margin is measured against the
    Wise row in the same response, so both sides share one mid-market source.
    A provider is only returned when every point passes sanity checks.
    """
    per_amount: dict[int, list[dict[str, Any]]] = {}
    for amt in COMPARE_AMOUNTS:
        rows = _fetch_comparison(amt)
        if rows is None:
            continue
        per_amount[amt] = rows
        print(f"[compare] {amt}: aliases = {sorted((p.get('alias') or p.get('name') or '?') for p in rows)}", file=sys.stderr)

    out: dict[str, dict[str, Any]] = {}
    for pid, aliases in COMPARE_ALIASES.items():
        points, collected = [], []
        for amt in COMPARE_AMOUNTS:
            rows = per_amount.get(amt)
            if not rows:
                continue
            wise = next((p for p in rows if (p.get("alias") or "").lower() == "wise"), None)
            row = next((p for p in rows if (p.get("alias") or p.get("name") or "").lower().replace(" ", "-") in aliases), None)
            if not wise or not row:
                continue  # provider not quoted at this amount (e.g. below its minimum)
            wq = (wise.get("quotes") or [wise])[0]
            quotes = row.get("quotes") or []
            q = quotes[0] if quotes else None
            if not q or q.get("rate") is None or q.get("fee") is None or not wq.get("rate"):
                continue
            rate, fee, mid = float(q["rate"]), float(q["fee"]), float(wq["rate"])
            margin = (1 - rate / mid) * 100
            if not (0 <= fee <= amt * 0.1) or not (-0.5 <= margin <= 6):
                print(f"[compare] {pid} @ {amt}: implausible fee {fee} / margin {margin:.2f}%", file=sys.stderr)
                continue
            points.append({"amount_hkd": amt, "fee_hkd": round(fee, 2), "fx_margin_pct": round(max(margin, 0.0), 3)})
            if q.get("dateCollected"):
                collected.append(q["dateCollected"])
        ref = next((p for p in points if p["amount_hkd"] == AMOUNT_HKD), None)
        if ref:
            out[pid] = {
                "fee_flat_hkd": ref["fee_hkd"],
                "fx_margin_pct": ref["fx_margin_pct"],
                "points": points,
                "reference_amount_hkd": AMOUNT_HKD,
                "source": "api",
                "via": "wise-comparison",
                "quote_collected_at": min(collected) if collected else None,
                "fetched_at": iso_now(),
            }
        else:
            print(f"[compare] {pid}: not live this run", file=sys.stderr)
    return out


# ---------------------------------------------------------------------------
# Western Union public price catalog (the call its own price estimator makes)
# ---------------------------------------------------------------------------

WU_URL = "https://www.westernunion.com/wuconnect/prices/catalog"


def _wu_body(amount: int) -> dict[str, Any]:
    return {
        "header_request": {"version": "0.5", "request_type": "PRICECATALOG"},
        "sender": {"client": "WUCOM", "channel": "WWEB", "funds_in": "*",
                   "curr_iso3": "HKD", "cty_iso2_ext": "HK", "send_amount": amount},
        "receiver": {"curr_iso3": "INR", "cty_iso2_ext": "IN", "cty_iso2": "IN"},
    }


def fetch_wu_quote(mid: float) -> dict[str, Any] | None:
    """
    Bank-account funded (fund_in TG) transfer paid out Direct to Bank
    (service 500), at three amounts. Fee = gross_fee; margin is measured
    against the mid-market rate used for the whole run.
    """
    try:
        points = []
        for amt in COMPARE_AMOUNTS:
            r = requests.post(WU_URL, json=_wu_body(amt), timeout=TIMEOUT,
                              headers={**UA, "Accept": "application/json"})
            r.raise_for_status()
            d = r.json()
            grp = next((g for g in d.get("services_groups", []) if g.get("service") == "500"), None)
            row = next((p for p in (grp or {}).get("pay_groups", []) if p.get("fund_in") == "TG"), None)
            if not row:
                print(f"[wu] no bank-funded Direct to Bank row at {amt}", file=sys.stderr)
                return None
            fee, fx = float(row["gross_fee"]), float(row["fx_rate"])
            margin = (1 - fx / mid) * 100
            if not (0 <= fee <= amt * 0.1) or not (-0.5 <= margin <= 6):
                print(f"[wu] implausible fee {fee} / margin {margin:.2f}% at {amt}", file=sys.stderr)
                return None
            points.append({"amount_hkd": amt, "fee_hkd": round(fee, 2), "fx_margin_pct": round(max(margin, 0.0), 3)})
        ref = next(p for p in points if p["amount_hkd"] == AMOUNT_HKD)
        return {
            "fee_flat_hkd": ref["fee_hkd"], "fx_margin_pct": ref["fx_margin_pct"],
            "points": points, "reference_amount_hkd": AMOUNT_HKD,
            "source": "api", "via": "western-union-catalog", "fetched_at": iso_now(),
        }
    except Exception as e:
        print(f"[wu] failed: {e}", file=sys.stderr)
        return None

# ---------------------------------------------------------------------------
# Curated-only providers
# ---------------------------------------------------------------------------

CURATED_ONLY = [
    "panda", "mg", "currencyfair", "axisremit", "hdfc", "kotak",
    "icici", "federalbank", "hsbc", "dbs", "bochk",
]  # must match PROVIDERS in assets/providers.js (15 in total with the four live ones)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    feed_mid = fetch_mid_market()

    providers: list[dict[str, Any]] = []

    wise = fetch_wise_quote(feed_mid or 0.0)
    wise_rate = wise.pop("_rate", None) if wise else None

    # Prefer Wise's own rate: it is the mid-market rate and fresher than the
    # daily feed. Sanity check it against the feed (within 1%) when we have both.
    mid, mid_source = feed_mid, "currency-api"
    if wise_rate and wise_rate > 0:
        if feed_mid is None or abs(wise_rate / feed_mid - 1) <= 0.01:
            mid, mid_source = wise_rate, "wise"
        else:
            print(
                f"[mid-market] Wise rate {wise_rate} differs >1% from feed {feed_mid}; using feed",
                file=sys.stderr,
            )
    if mid is None:
        print(
            "No mid-market rate; refusing to write rates.json with stale data.",
            file=sys.stderr,
        )
        return 1

    if wise:
        providers.append({"id": "wise", **wise})
    else:
        providers.append(
            {"id": "wise", "source": "unavailable", "fetched_at": iso_now()}
        )

    inst = fetch_instarem_quote(mid)
    providers.append(
        {"id": "instarem", **inst} if inst
        else {"id": "instarem", "source": "unavailable", "fetched_at": iso_now()}
    )

    live_more = fetch_comparison_providers()
    for pid in COMPARE_ALIASES:
        providers.append(
            {"id": pid, **live_more[pid]} if pid in live_more
            else {"id": pid, "source": "unavailable", "fetched_at": iso_now()}
        )

    wu = fetch_wu_quote(mid)
    providers.append(
        {"id": "wu", **wu} if wu
        else {"id": "wu", "source": "unavailable", "fetched_at": iso_now()}
    )
    live_more = {**live_more, **({"wu": wu} if wu else {})}

    for pid in CURATED_ONLY:
        providers.append({"id": pid, "source": "curated"})

    # Carry the last good live quote forward when a fetch fails this run, so a
    # single hiccup doesn't drop a provider. Its old fetched_at is kept, so the
    # site's 36-hour freshness window and the health check still see its age.
    try:
        prev = {p["id"]: p for p in json.loads(OUT_PATH.read_text(encoding="utf-8")).get("providers", [])}
    except Exception:
        prev = {}
    for i, p in enumerate(providers):
        old = prev.get(p["id"])
        if p.get("source") == "unavailable" and old and old.get("source") == "api" and old.get("fetched_at"):
            print(f"[carry] {p['id']}: keeping previous live quote from {old['fetched_at']}", file=sys.stderr)
            providers[i] = old

    payload = {
        "schema_version": 1,
        "updated_at": iso_now(),
        "mid_market_rate": round(mid, 6),
        "mid_source": mid_source,
        "reference_amount_hkd": AMOUNT_HKD,
        "providers": providers,
        "note": (
            "Live per-provider fees are populated only where a public API "
            "exists. 'curated' entries read their fee/margin from the "
            "PROVIDERS table in index.html; 'unavailable' entries attempted "
            "a live fetch and failed."
        ),
    }

    OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT_PATH} - mid={mid:.4f} - wise={'ok' if wise else 'failed'} - instarem={'ok' if inst else 'failed'} - more={sorted(live_more)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
