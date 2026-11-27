import re, json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",locale="en-HK",viewport={"width":1366,"height":900})
    pg=ctx.new_page()
    seen=[]
    def on_resp(r):
        try:
            u=r.url
            if "moneygram" in u:
                body=""
                try:
                    if r.status<400 or "fee" in u.lower() or "rate" in u.lower() or "api" in u.lower():
                        body=r.text()[:2000]
                except: pass
                seen.append({"status":r.status,"url":u,"ct":r.headers.get("content-type",""),"body":body})
        except Exception as e: pass
    pg.on("response",on_resp)
    pg.goto("https://www.moneygram.com/hk/en/corridor/india",wait_until="networkidle",timeout=90000)
    pg.wait_for_timeout(25000)
    # Interact with the form: look for a Send money button
    try:
        pg.get_by_role("link",name=re.compile("Send money",re.I)).first.click(timeout=3000)
        pg.wait_for_timeout(10000)
    except Exception as e: print("no CTA click:",e)
    print("\n=== Visible text containing a number ===")
    txt=pg.inner_text("body")
    for l in txt.splitlines():
        if re.search(r'\d',l) and re.search(r'(?i)HKD|INR|rate|fee|receive|send|₹|HK\$',l) and len(l)<300:
            print("TXT>",l.strip())
    print("\n=== All moneygram network calls ===")
    for e in seen:
        print(f"{e['status']} {e['url'][:200]} ct={e['ct'][:60]}")
        if e['body']:
            print("  BODY:",re.sub(r'\s+',' ',e['body'])[:500])
    b.close()
