"""Fail loudly when the live rate feeds have silently degraded.

Run after the rates commit step. A failing job makes GitHub email the repo owner.
Checks: Wise supplied the mid-market rate, and the Instarem API entry is live.
"""
import json, sys

d = json.load(open("rates.json"))
problems = []
if d.get("mid_source") != "wise":
    problems.append("mid_source is %r (expected 'wise'): Wise feed fell back" % d.get("mid_source"))
inst = next((p for p in d.get("providers", []) if p.get("id") == "instarem"), {})
if inst.get("source") != "api":
    problems.append("Instarem source is %r (expected 'api')" % inst.get("source"))
if problems:
    print("RATE FEED DEGRADED:\n- " + "\n- ".join(problems))
    sys.exit(1)
print("Rate feeds healthy: mid_source=wise, instarem=api")
