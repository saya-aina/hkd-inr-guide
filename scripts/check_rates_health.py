"""Fail loudly when the live rate feeds have silently degraded.

Run after the rates commit step. A failing job makes GitHub email the repo owner.
Checks: Wise supplied the mid-market rate, and every live provider has a fresh
(under 6 hours old) quote from its own source.
"""
import json, sys, datetime as dt

LIVE = ["wise", "instarem", "ofx", "wu"]
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
if problems:
    print("RATE FEED DEGRADED:\n- " + "\n- ".join(problems))
    sys.exit(1)
print("Rate feeds healthy: mid_source=wise, live = " + ", ".join(LIVE))
