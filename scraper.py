"""
HKD to INR remittance rate scraper.

Writes rates.json with:
  - mid_market_rate: live, from frankfurter.app (ECB-backed, free, keyless)
  - providers[].fee_flat_hkd / fx_margin_pct: live for providers with
    public APIs; omitted for the rest so the frontend falls back to curated
    values in index.html.

Design principles:

  1. Only claims a quote is "live" when it genuinely came from an API in
     this run.
  2. Tags every provider entry with source = "api" | "curated" | "unavailable"
     so the frontend can show the difference to the user.
  3. Never scrapes HTML. Fintech comparison pages change their DOM constantly,
     use client-side rendering, and often have ToS that prohibit scraping for
     competitive comparison. We only use endpoints the provider themselves
     publishes publicly.
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


def iso_now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Mid-market rate
# ---------------------------------------------------------------------------

def fetch_mid_market() -> float | None:
    """
    Fetch the HKD to INR mid-market rate from frankfurter.app.
    Free, keyless, ECB-backed. Returns None on failure.
    """
    try:
        r = requests.get(
            "https://api.frankfurter.app/latest",
            params={"from": "HKD", "to": "INR"},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        data = r.json()
        return float(data["rates"]["INR"])
    except Exception as e:
        print(f"[mid-market] failed: {e}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Wise comparison API
# ---------------------------------------------------------------------------

def fetch_wise_quote(mid: float) -> dict[str, Any] | None:
    """
    Wise publishes a comparison endpoint used by their own compare widget.
    We only trust the Wise row from the response - the other providers'
    numbers in it are Wise's estimates, not those providers' live data.
    """
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

        fx_margin_pct = (mid - float(rate)) / mid * 100
        fx_margin_pct = max(0.0, round(fx_margin_pct, 2))

        return {
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
# Curated-only providers
# ---------------------------------------------------------------------------

CURATED_ONLY = [
    "instarem", "panda", "remitly", "orbitremit", "xe",
    "wu", "mg", "hsbc", "dbs", "bochk",
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    mid = fetch_mid_market()
    if mid is None:
        print(
            "No mid-market rate; refusing to write rates.json with stale data.",
            file=sys.stderr,
        )
        return 1

    providers: list[dict[str, Any]] = []

    wise = fetch_wise_quote(mid)
    if wise:
        providers.append({"id": "wise", **wise})
    else:
        providers.append(
            {"id": "wise", "source": "unavailable", "fetched_at": iso_now()}
        )

    for pid in CURATED_ONLY:
        providers.append({"id": pid, "source": "curated"})

    payload = {
        "schema_version": 1,
        "updated_at": iso_now(),
        "mid_market_rate": round(mid, 6),
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
    print(f"Wrote {OUT_PATH} - mid={mid:.4f} - wise={'ok' if wise else 'failed'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
