"""Daily HKD->INR rate alert sender (Brevo).

Reads subscribers from a Brevo list, sends one transactional email each.
- No TARGET_RATE: daily digest.
- TARGET_RATE set: email only when the mid-market rate is at or above it.
Env: BREVO_API_KEY, BREVO_LIST_ID, ALERT_SENDER_EMAIL, ALERT_SENDER_NAME (optional), DRY_RUN=1 to print only.
Brevo's free plan caps sends at 300/day, so MAX_SENDS defaults to 250.
"""
import json, os, sys, urllib.request, urllib.error

API = "https://api.brevo.com/v3"
KEY = os.environ.get("BREVO_API_KEY", "")
LIST_ID = os.environ.get("BREVO_LIST_ID", "")
SENDER = os.environ.get("ALERT_SENDER_EMAIL", "")
SENDER_NAME = os.environ.get("ALERT_SENDER_NAME", "NRI Remit")
DRY = os.environ.get("DRY_RUN") == "1"
MAX_SENDS = int(os.environ.get("MAX_SENDS", "250"))
SITE = "https://nriremit.com/remittance.html"


def call(method, path, body=None):
    req = urllib.request.Request(API + path, method=method, headers={"api-key": KEY, "accept": "application/json", "content-type": "application/json"},
                                 data=json.dumps(body).encode() if body is not None else None)
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def contacts():
    off = 0
    while True:
        d = call("GET", "/contacts/lists/%s/contacts?limit=500&offset=%d" % (LIST_ID, off))
        batch = d.get("contacts", [])
        for c in batch:
            if not c.get("emailBlacklisted"):
                yield c
        if len(batch) < 500:
            return
        off += 500


def best_provider(rates):
    """Best checked provider at HK$10,000 from rates.json, if the scraper recorded one."""
    for k in ("wise", "instarem"):
        e = rates.get(k) or {}
        if k == "instarem" and e.get("source") == "api" and e.get("fee_pct") is not None:
            return "Instarem", 10000 * (1 - e["fee_pct"] / 100) * rates["mid_market_rate"] * (1 - (e.get("fx_margin_pct") or 0) / 100)
    return None, None


def build(rate, target, prov, inr):
    line = "<p>Best checked provider today for HK$10,000: <strong>%s</strong>, about ₹%s.</p>" % (prov, format(round(inr), ",")) if prov else ""
    hit = "<p><strong>Your target of %.2f has been reached.</strong></p>" % target if target else ""
    return ("<div style='font-family:Arial,sans-serif;max-width:520px'>" + hit +
            "<h2>HKD to INR: %.4f</h2><p>Mid-market rate today.</p>%s"
            "<p><a href='%s'>Compare providers and send money now</a></p>"
            "<p style='font-size:12px;color:#666'>Indicative only, not a quote. We may earn a commission if you send money via our links, at no cost to you. "
            "You are receiving this because you subscribed at nriremit.com. To stop, use the unsubscribe link below or reply UNSUBSCRIBE.</p>"
            "<p style='font-size:12px'><a href='{{ unsubscribe }}'>Unsubscribe</a></p></div>") % (rate, line, SITE)


def main():
    if not (KEY and LIST_ID and SENDER):
        print("Alerts not configured (BREVO_API_KEY / BREVO_LIST_ID / ALERT_SENDER_EMAIL); skipping.")
        return 0
    rates = json.load(open("rates.json"))
    rate = rates.get("mid_market_rate")
    if not rate:
        print("No mid_market_rate; skipping."); return 0
    prov, inr = best_provider(rates)
    sent = skipped = 0
    for c in contacts():
        if sent >= MAX_SENDS:
            print("Reached MAX_SENDS; remaining subscribers wait for tomorrow."); break
        att = c.get("attributes") or {}
        try:
            target = float(att.get("TARGET_RATE")) if att.get("TARGET_RATE") not in (None, "") else None
        except ValueError:
            target = None
        if target and rate < target:
            skipped += 1; continue
        subj = ("Target reached: HKD to INR %.2f" % rate) if target else ("HKD to INR today: %.2f" % rate)
        if DRY:
            print("DRY", c["email"], subj); sent += 1; continue
        try:
            call("POST", "/smtp/email", {"sender": {"email": SENDER, "name": SENDER_NAME}, "to": [{"email": c["email"]}],
                                         "subject": subj, "htmlContent": build(rate, target, prov, inr),
                                         "headers": {"List-Unsubscribe": "<mailto:%s?subject=unsubscribe>" % SENDER}})
            sent += 1
        except urllib.error.HTTPError as e:
            print("send failed", e.code, e.read()[:200])
    print("sent=%d below_target=%d rate=%.4f" % (sent, skipped, rate))
    return 0


if __name__ == "__main__":
    sys.exit(main())
