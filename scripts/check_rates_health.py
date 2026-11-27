"""Fail loudly when the live rate feeds have silently degraded.

Run after the rates commit step. A failing job makes GitHub email the repo owner.
Checks: Wise supplied the mid-market rate, and every live provider has a fresh
(under 6 hours old) quote from its own source.
"""
import json, sys, datetime as dt

LIVE = ["wise", "instarem", "ofx", "wu", "currencyfair"]
LIVE_WARN = ["panda"]  # promo-only; warn if missing
BOARD = ["icici", "axisremit", "hdfc", "kotak", "hsbc", "dbs"]  # daily bank board rates (failure if missing)
BOARD_WARN = ["federalbank", "bochk"]  # warn only: its site sometimes serves a bot-challenge page
MAX_AGE_H = 6

d = json.load(open("rates.json"))
problems = []
if d.get("mid_source") != "wise":
    problems.append("mid_source is %r (expected 'wise'): Wise feed fell back" % d.get("mid_source"))
now = dt.datetime.now(dt.timezone.utc)
by_id = {p.get("id"): p for p in d.get("providers", [])}
for pid in LIVE:
    p = by_id.get(pid, {})
    if p.get("source") != "api":
        problems.append("%s source is %r (expected 'api')" % (pid, p.get("source")))
        continue
    try:
        age = (now - dt.datetime.strptime(p["fetched_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)).total_seconds() / 3600
    except Exception:
        problems.append("%s has no valid fetched_at" % pid)
        continue
    if age > MAX_AGE_H:
        problems.append("%s live quote is %.1f h old (limit %d h)" % (pid, age, MAX_AGE_H))
for pid in BOARD:
    p = by_id.get(pid, {})
    if p.get("source") != "board":
        problems.append("%s board rate is %r (expected 'board')" % (pid, p.get("source")))
        continue
    try:
        age = (now - dt.datetime.strptime(p["fetched_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)).total_seconds() / 3600
        pub = (now - dt.datetime.strptime(p["published_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)).total_seconds() / 86400
    except Exception:
        problems.append("%s has no valid fetched_at/published_at" % pid)
        continue
    if age > MAX_AGE_H:
        problems.append("%s board rate last fetched %.1f h ago (limit %d h)" % (pid, age, MAX_AGE_H))
    elif pub > 5:
        problems.append("%s published board rate is %.1f days old" % (pid, pub))
for pid in LIVE_WARN:
    if by_id.get(pid, {}).get("source") not in ("api", "api_promo"):
        print("WARNING: %s promo rate unavailable (source=%r); site falls back to indicative" % (pid, by_id.get(pid, {}).get("source")))
for pid in BOARD_WARN:
    if by_id.get(pid, {}).get("source") != "board":
        print("WARNING: %s board rate unavailable (source=%r); site falls back to its checked figure" % (pid, by_id.get(pid, {}).get("source")))
if problems:
    print("RATE FEED DEGRADED:\n- " + "\n- ".join(problems))
    sys.exit(1)
print("Rate feeds healthy: mid_source=wise, live = " + ", ".join(LIVE) + "; board = " + ", ".join(BOARD))
