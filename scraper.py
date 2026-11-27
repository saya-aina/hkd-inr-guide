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
        out = {
            "fee_pct": round(fee_pct, 3),
            "fx_margin_pct": round(max(margin, 0.0), 3),
            "reference_amount_hkd": AMOUNT_HKD,
            "source": "api",
            "fetched_at": iso_now(),
        }
        # First-transfer offer: shown beside the regular price, never as the ranked figure
        # (agreed with Instarem, 24-25 Nov 2026).
        promo = cfg.get("total_fee_percent")
        print(f"[instarem] regular fee {fee_pct}% / current total_fee_percent {promo}", file=sys.stderr)
        try:
            promo = float(promo) if promo is not None else None
        except (TypeError, ValueError):
            promo = None
        if promo is not None and 0 <= promo < fee_pct - 0.001:
            out["promo_fee_pct"] = round(promo, 3)
        return out
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
# CurrencyFair public comparisonQuotes endpoint (the call its own calculator makes)
# ---------------------------------------------------------------------------

CF_URL = "https://api.currencyfair.com/comparisonQuotes"
CF_HEADERS = {
    **UA,
    "Accept": "application/hal+json",
    "Content-Type": "application/json",
    "Origin": "https://www.currencyfair.com",
    "Referer": "https://www.currencyfair.com/send-money-online/india",
}


def _cf_body(amount: int) -> dict[str, Any]:
    return {"currencyFrom": "HKD", "currencyTo": "INR",
            "amountInfo": {"amount": amount, "scale": 0}, "type": "SELL"}


def fetch_currencyfair_quote(mid: float) -> dict[str, Any] | None:
    """
    Quotes at HK$1,000 / 10,000 / 50,000. CurrencyFair's fee is quoted in
    INR (flat 120 INR as of 27 Nov), so we convert to HKD via the returned
    rate so the comparison math stays in HKD; margin is measured against
    the run's mid-market rate.
    """
    try:
        points = []
        for amt in COMPARE_AMOUNTS:
            r = requests.post(CF_URL, headers=CF_HEADERS, json=_cf_body(amt), timeout=TIMEOUT)
            r.raise_for_status()
            d = (r.json() or {}).get("currencyFair") or {}
            fee_inr = float(d.get("transferFee", 0))
            rate = float((d.get("rateInfo") or {}).get("rate", 0))
            if not rate:
                print(f"[currencyfair] no rate at {amt}", file=sys.stderr); return None
            fee_hkd = fee_inr / rate
            margin = (1 - rate / mid) * 100
            if not (0 <= fee_hkd <= amt * 0.1) or not (-0.5 <= margin <= 6):
                print(f"[currencyfair] implausible fee {fee_hkd:.2f} HKD / margin {margin:.2f}% at {amt}", file=sys.stderr); return None
            points.append({"amount_hkd": amt, "fee_hkd": round(fee_hkd, 2), "fx_margin_pct": round(max(margin, 0.0), 3),
                           "fee_inr_flat": round(fee_inr, 2)})
        ref = next(p for p in points if p["amount_hkd"] == AMOUNT_HKD)
        return {
            "fee_flat_hkd": ref["fee_hkd"], "fx_margin_pct": ref["fx_margin_pct"],
            "points": points, "reference_amount_hkd": AMOUNT_HKD,
            "source": "api", "via": "currencyfair-comparisonQuotes",
            "fetched_at": iso_now(),
        }
    except Exception as e:
        print(f"[currencyfair] failed: {e}", file=sys.stderr); return None


# ---------------------------------------------------------------------------
# Panda Remit public pricing endpoint (p.pandaremit.com, unauthenticated).
# Returns the promo rate Panda shows to new customers; label it clearly.
# ---------------------------------------------------------------------------

PANDA_URL = "https://p.pandaremit.com/pricing/rate/all/HKD/INR"


def fetch_panda_promo(mid: float) -> dict[str, Any] | None:
    """
    Panda publishes the rate it shows to new-customer sign-ups. The API has
    no concept of a 'standard' price - what the site shows is this promo rate
    (behind a login for everyone else). Clearly flagged as new-customer only.
    """
    try:
        r = requests.get(PANDA_URL,
                         headers={**UA, "Origin": "https://www.pandaremit.com",
                                  "Referer": "https://www.pandaremit.com/en/hkg/india/hkd-inr-converter?amount=10000"},
                         timeout=TIMEOUT)
        r.raise_for_status()
        d = (r.json() or {}).get("model") or {}
        row = next((x for x in (d.get("rates") or []) if x.get("platform") == "panda"), None)
        if not row:
            print("[panda] no panda row in response", file=sys.stderr); return None
        rate = float(row.get("rate") or 0)
        fee_src = float(row.get("fee") or 0)  # flat, in source currency (HKD)
        if not rate:
            print("[panda] no rate in response", file=sys.stderr); return None
        margin = (1 - rate / mid) * 100
        if not (-0.5 <= margin <= 6) or not (0 <= fee_src <= 500):
            print(f"[panda] implausible rate {rate} / margin {margin:.2f}% / fee {fee_src}", file=sys.stderr)
            return None
        pub_ms = row.get("publishDate")
        published_at = None
        if pub_ms:
            try:
                published_at = dt.datetime.fromtimestamp(int(pub_ms) / 1000, tz=dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass
        return {
            "fee_flat_hkd": round(fee_src, 2),
            "fx_margin_pct": round(max(margin, 0.0), 3),
            "reference_amount_hkd": AMOUNT_HKD,
            "source": "api_promo",
            "promo_label": "new_customer_only",
            "published_at": published_at,
            "fetched_at": iso_now(),
        }
    except Exception as e:
        print(f"[panda] failed: {e}", file=sys.stderr); return None

# ---------------------------------------------------------------------------
# Bank board rates (published daily by each bank; indicative, not quotes)
# ---------------------------------------------------------------------------
# Indian banks: published TT buying rate for inward remittance, INR per HKD.
# HSBC / DBS (HK): estimated from the HKAB reference selling rate for INR
# (HK$ per 100 INR), as set out in each card's note. Margin vs the run's mid.

import re
import io

IST = dt.timezone(dt.timedelta(hours=5, minutes=30))
HKT = dt.timezone(dt.timedelta(hours=8))
BROWSER_UA = {"User-Agent": "Mozilla/5.0 (compatible; hkd-inr-comparison/1.0; informational directory)",
              "Accept": "*/*", "Accept-Language": "en"}


def _txt(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html))


def _board_entry(rate_inr_per_hkd: float, mid: float, published: dt.datetime, kind: str, **extra) -> dict[str, Any] | None:
    margin = (1 - rate_inr_per_hkd / mid) * 100
    age_days = (dt.datetime.now(dt.timezone.utc) - published).total_seconds() / 86400
    if not (0.2 <= margin <= 12) or age_days > 7 or age_days < -1:
        print(f"[board] implausible: rate {rate_inr_per_hkd} margin {margin:.2f}% age {age_days:.1f}d", file=sys.stderr)
        return None
    return {
        "source": "board", "kind": kind,
        "rate_inr_per_hkd": round(rate_inr_per_hkd, 4),
        "fx_margin_pct": round(margin, 3),
        "published_at": published.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fetched_at": iso_now(), **extra,
    }


def fetch_icici(mid: float) -> dict[str, Any] | None:
    try:
        h = requests.get("https://www.icici.bank.in/business-banking/global-markets/forex/forex-card-rates",
                         headers=BROWSER_UA, timeout=TIMEOUT).text
        row = re.search(r"<tr[^>]*>(?:(?!</tr>).)*Hong Kong Dollar\s*\(HKD\)(?:(?!</tr>).)*</tr>", h, re.S | re.I)
        nums = re.findall(r"\d+\.\d+", _txt(row.group(0))) if row else []
        d = re.search(r"Last Updated on:\s*(\d{2})-(\d{2})-(\d{4})\|\s*(\d{2}):(\d{2}):(\d{2})\s*([AP]M)", _txt(h))
        if not nums or not d:
            print("[icici] HKD row or date not found", file=sys.stderr); return None
        dd, mm, yy, hh, mi, ss, ap = d.groups()
        hour = int(hh) % 12 + (12 if ap == "PM" else 0)
        pub = dt.datetime(int(yy), int(mm), int(dd), hour, int(mi), int(ss), tzinfo=IST)
        return _board_entry(float(nums[0]), mid, pub, "tt_buying")
    except Exception as e:
        print(f"[icici] failed: {e}", file=sys.stderr); return None


def fetch_axis(mid: float) -> dict[str, Any] | None:
    try:
        h = requests.get("https://application.axis.bank.in/webforms/corporatecardrate/index.aspx",
                         headers=BROWSER_UA, timeout=TIMEOUT).text
        i = h.find("<th>Hong Kong Dollar")
        seg = _txt(re.sub(r"<!--|-->", " ", h[i:i + 900])) if i >= 0 else ""
        nums = re.findall(r"\d+\.\d+", seg)
        d = re.search(r"published on\s*([A-Za-z]{3})\s*(\d{1,2}),\s*(\d{4})\s*at\s*(\d{1,2}):(\d{2})\s*([AP]M)", _txt(h))
        if not nums or not d:
            print("[axis] HKD row or date not found", file=sys.stderr); return None
        mon, dd, yy, hh, mi, ap = d.groups()
        month = dt.datetime.strptime(mon, "%b").month
        pub = dt.datetime(int(yy), month, int(dd), int(hh) % 12 + (12 if ap == "PM" else 0), int(mi), tzinfo=IST)
        return _board_entry(float(nums[0]), mid, pub, "tt_buying")
    except Exception as e:
        print(f"[axis] failed: {e}", file=sys.stderr); return None


def fetch_federal(mid: float) -> dict[str, Any] | None:
    try:
        from pypdf import PdfReader
        page = requests.get("https://www.federal.bank.in/forex-rates", headers=BROWSER_UA, timeout=TIMEOUT).text
        u = re.search(r'href="(https://www\.federal\.bank\.in/documents/[^"]+\.pdf[^"]*)"', page)
        if not u:
            print("[federal] pdf link not found", file=sys.stderr); return None
        t = ""
        for attempt in range(3):  # the CDN occasionally truncates this PDF; retry on a bad read
            pdf = requests.get(u.group(1).replace("&amp;", "&"), headers=BROWSER_UA, timeout=TIMEOUT).content
            if not pdf.startswith(b"%PDF"):
                print(f"[federal] not a PDF ({len(pdf)} bytes): bot challenge or error page; will retry on the next scheduled fetch", file=sys.stderr)
                return None
            try:
                t = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(pdf), strict=False).pages)
            except Exception as e:
                print(f"[federal] pypdf attempt {attempt + 1} failed ({len(pdf)} bytes, tail {pdf[-12:]!r}): {e}", file=sys.stderr)
                try:  # fall back to poppler's pdftotext
                    import subprocess
                    t = subprocess.run(["pdftotext", "-layout", "-", "-"], input=pdf, capture_output=True, timeout=30).stdout.decode("utf-8", "replace")
                except Exception as e2:
                    print(f"[federal] pdftotext fallback failed: {e2}", file=sys.stderr)
            if re.search(r"^\s*HKD\s+\d", t, re.M):
                break
        row = re.search(r"^\s*HKD\s+(\d+\.\d+)", t, re.M)
        d = re.search(r"EXCHANGE RATES\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})\s*\|\s*Published at\s*(\d{2}):(\d{2}):(\d{2})", t)
        if not row or not d:
            print("[federal] HKD row or date not found", file=sys.stderr); return None
        day = dt.datetime.strptime(d.group(1), "%d %B %Y")
        pub = day.replace(hour=int(d.group(2)), minute=int(d.group(3)), second=int(d.group(4)), tzinfo=IST)
        return _board_entry(float(row.group(1)), mid, pub, "tt_buying")
    except Exception as e:
        print(f"[federal] failed: {e}", file=sys.stderr); return None



def fetch_hdfc(mid: float) -> dict[str, Any] | None:
    """HDFC Treasury Forex Card Rates PDF. HKD row has 9 numbers; TT Buying (Inw Rem) is the 5th."""
    try:
        from pypdf import PdfReader
        pdf = requests.get("https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/personal-banking/discover-products/interest-rates/hdfc-bank-treasury-forex-card-rates.pdf",
                           headers=BROWSER_UA, timeout=TIMEOUT).content
        if not pdf.startswith(b"%PDF"):
            print(f"[hdfc] not a PDF ({len(pdf)} bytes): bot challenge or error page; will retry on the next scheduled fetch", file=sys.stderr)
            return None
        t = "\n".join((p.extract_text() or "") for p in PdfReader(io.BytesIO(pdf), strict=False).pages)
        row = re.search(r"Hong Kong Dollar\s+HKD\s+([\d\.\s]+)", t)
        d = re.search(r"DATE:?\s*(\d{2})-(\d{2})-(\d{4})\s*TIME:?\s*(\d{2}):(\d{2}):(\d{2})\s*([AP]M)", t)
        if not row or not d:
            print("[hdfc] HKD row or date not found", file=sys.stderr); return None
        nums = re.findall(r"\d+\.\d+", row.group(1))
        if len(nums) < 5:
            print(f"[hdfc] HKD row has only {len(nums)} numbers: {nums}", file=sys.stderr); return None
        tt_buying = float(nums[4])  # 5th column: T.T. Buying (Inw Rem)
        dd, mm, yy, hh, mi, ss, ap = d.groups()
        pub = dt.datetime(int(yy), int(mm), int(dd), int(hh) % 12 + (12 if ap == "PM" else 0), int(mi), int(ss), tzinfo=IST)
        return _board_entry(tt_buying, mid, pub, "tt_buying")
    except Exception as e:
        print(f"[hdfc] failed: {e}", file=sys.stderr); return None


def fetch_kotak(mid: float) -> dict[str, Any] | None:
    """
    Kotak Mahindra forex rates. Its page loads via get_forex_rates_data2.php,
    which returns a document.write() with a four-column 'We Buy' table
    (Cash, Forex Card, Bills, Telegraphic Transfer) per currency. No date in
    the response, so the fetch time is used; the sheet is published once a
    forex working day, so this gets refreshed every 3-6h in any case.
    """
    try:
        r = requests.get("https://www.kotak.bank.in/bank/mailers/intrates/get_forex_rates_data2.php",
                         headers={**BROWSER_UA, "Referer": "https://www.kotak.bank.in/en/rates/forex-rates.html"},
                         timeout=TIMEOUT)
        buy_half = r.text.split("We Sell", 1)[0] if "We Sell" in r.text else r.text
        row = re.search(r"<b>HKD</b>(.*?)(?:<tr|<b>[A-Z]{3}</b>)", buy_half, re.S | re.I)
        if not row:
            print("[kotak] HKD row not found in buy table", file=sys.stderr); return None
        nums = re.findall(r"\d+\.\d+", row.group(1))
        if len(nums) < 4:
            print(f"[kotak] HKD row has only {len(nums)} numbers: {nums}", file=sys.stderr); return None
        tt_buying = float(nums[3])  # 4th column: Telegraphic Transfer
        pub = dt.datetime.now(dt.timezone.utc).astimezone(IST).replace(microsecond=0)
        return _board_entry(tt_buying, mid, pub, "tt_buying")
    except Exception as e:
        print(f"[kotak] failed: {e}", file=sys.stderr); return None



def _parse_hkab_usd_selling() -> float | None:
    """HKAB USD selling in HK$ per 100 USD; return USD/HKD rate (HKD per 1 USD)."""
    try:
        h = requests.get("https://www.hkab.org.hk/en/rates/exchange-rates", headers=BROWSER_UA, timeout=TIMEOUT).text
        m = re.search(r"USD\s*Currency:\s*US Dollars\s*Selling:\s*(\d+\.\d+)", _txt(h))
        return float(m.group(1)) / 100.0 if m else None
    except Exception as e:
        print(f"[hkab-usd] failed: {e}", file=sys.stderr); return None


def fetch_bochk(mid: float) -> dict[str, Any] | None:
    """
    BOCHK publishes a Non Major Currency rate sheet (USD -> X, for remittance).
    We find the INR row, then convert to HKD->INR via the HKAB USD selling rate.
    Returns None when the sheet is blank (BOCHK occasionally publishes with
    #VALUE! errors); the carry-forward or the existing curated note then stands.
    """
    try:
        import pdfplumber
        pdf = requests.get("https://www.bochk.com/dam/rmbservice/Ratesheet_ENG.pdf",
                           headers=BROWSER_UA, timeout=TIMEOUT).content
        if not pdf.startswith(b"%PDF"):
            print(f"[bochk] not a PDF ({len(pdf)} bytes)", file=sys.stderr); return None
        usd_inr = None
        with pdfplumber.open(io.BytesIO(pdf)) as doc:
            for pg in doc.pages:
                for tbl in pg.extract_tables() or []:
                    for row in tbl:
                        cells = [str(c).strip() if c else "" for c in row]
                        if any(c == "INR" for c in cells):
                            nums = [c for c in cells if re.fullmatch(r"\d+\.\d+", c)]
                            if nums:
                                usd_inr = float(nums[0])
                                break
                    if usd_inr: break
                if usd_inr: break
        if not usd_inr:
            print("[bochk] INR row has no rate (sheet empty or #VALUE! today)", file=sys.stderr)
            return None
        usd_hkd = _parse_hkab_usd_selling()  # HKD per 1 USD
        if not usd_hkd:
            print("[bochk] could not get HKAB USD selling rate", file=sys.stderr); return None
        rate = usd_inr / usd_hkd  # INR per HKD
        pub = dt.datetime.now(dt.timezone.utc).astimezone(HKT).replace(microsecond=0)
        return _board_entry(rate, mid, pub, "bochk_remittance_ratesheet",
                            usd_inr_from_bochk=round(usd_inr, 4),
                            usd_hkd_from_hkab=round(usd_hkd, 4))
    except Exception as e:
        print(f"[bochk] failed: {e}", file=sys.stderr); return None

def fetch_hkab_inr(mid: float) -> dict[str, Any] | None:
    """HKAB reference selling rate for INR (HK$ per 100 INR), used as the HSBC / DBS ballpark."""
    try:
        h = requests.get("https://www.hkab.org.hk/en/rates/exchange-rates", headers=BROWSER_UA, timeout=TIMEOUT).text
        t = _txt(h)
        m = re.search(r"Currency Code:\s*INR\s*Currency:\s*Indian Rupees\s*Selling:\s*(\d+\.\d+)", t)
        d = re.search(r"Last updated:\s*(\d{4})-(\d{2})-(\d{2})\s+(\d{2}):(\d{2}):(\d{2})", t)
        if not m or not d:
            print("[hkab] INR row or date not found", file=sys.stderr); return None
        sell = float(m.group(1))
        pub = dt.datetime(*(int(x) for x in d.groups()), tzinfo=HKT)
        return _board_entry(100.0 / sell, mid, pub, "hkab_reference", hkab_selling_hkd_per_100_inr=sell)
    except Exception as e:
        print(f"[hkab] failed: {e}", file=sys.stderr); return None


# Banks publish once or a few times a day, so do not hit their sites every hour.
BOARD_REFRESH_HOURS = {"icici": 3, "axisremit": 6, "federalbank": 6, "hdfc": 3, "kotak": 3, "hkab": 3, "bochk": 6}


def _load_prev() -> dict[str, dict[str, Any]]:
    try:
        return {p["id"]: p for p in json.loads(OUT_PATH.read_text(encoding="utf-8")).get("providers", [])}
    except Exception:
        return {}


def board_cached_or_fetch(key: str, fn, mid: float, prev: dict[str, dict[str, Any]], prev_id: str) -> dict[str, Any] | None:
    old = prev.get(prev_id)
    if old and old.get("source") == "unavailable" and old.get("fetched_at"):
        age_h = (dt.datetime.now(dt.timezone.utc) - dt.datetime.strptime(old["fetched_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)).total_seconds() / 3600
        if age_h < 1:  # back off briefly after a failed fetch; try again next hour
            return None
    if old and old.get("source") == "board" and old.get("rate_inr_per_hkd") and old.get("fetched_at"):
        age_h = (dt.datetime.now(dt.timezone.utc) - dt.datetime.strptime(old["fetched_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)).total_seconds() / 3600
        if age_h < BOARD_REFRESH_HOURS[key]:
            out = {k: v for k, v in old.items() if k != "id"}
            out["fx_margin_pct"] = round((1 - old["rate_inr_per_hkd"] / mid) * 100, 3)  # re-measure against today's mid
            return out
    return fn(mid)

# ---------------------------------------------------------------------------
# Curated-only providers
# ---------------------------------------------------------------------------

CURATED_ONLY = [
    "mg",
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

    cf = fetch_currencyfair_quote(mid)
    providers.append(
        {"id": "currencyfair", **cf} if cf
        else {"id": "currencyfair", "source": "unavailable", "fetched_at": iso_now()}
    )
    live_more = {**live_more, **({"currencyfair": cf} if cf else {})}

    panda = fetch_panda_promo(mid)
    providers.append(
        {"id": "panda", **panda} if panda
        else {"id": "panda", "source": "unavailable", "fetched_at": iso_now()}
    )
    live_more = {**live_more, **({"panda": panda} if panda else {})}

    prev0 = _load_prev()
    board_feeds = {
        "icici": board_cached_or_fetch("icici", fetch_icici, mid, prev0, "icici"),
        "axisremit": board_cached_or_fetch("axisremit", fetch_axis, mid, prev0, "axisremit"),
        "federalbank": board_cached_or_fetch("federalbank", fetch_federal, mid, prev0, "federalbank"),
        "hdfc": board_cached_or_fetch("hdfc", fetch_hdfc, mid, prev0, "hdfc"),
        "kotak": board_cached_or_fetch("kotak", fetch_kotak, mid, prev0, "kotak"),
    }
    # HSBC and DBS share one HKAB read; reuse the cached one if recent.
    hk = board_cached_or_fetch("hkab", fetch_hkab_inr, mid, prev0, "hsbc")
    board_feeds["hsbc"] = board_feeds["dbs"] = hk
    board_feeds["bochk"] = board_cached_or_fetch("bochk", fetch_bochk, mid, prev0, "bochk")
    for pid, ent in board_feeds.items():
        providers.append(
            {"id": pid, **ent} if ent
            else {"id": pid, "source": "unavailable", "fetched_at": iso_now()}
        )
    live_more = {**live_more, **{k: v for k, v in board_feeds.items() if v}}

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
        if p.get("source") == "unavailable" and old and old.get("source") in ("api", "api_promo", "board") and old.get("fetched_at"):
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
