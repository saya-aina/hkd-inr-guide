import re, json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",locale="en-HK")
    pg=ctx.new_page()
    seen=[]
    def on_resp(r):
        try:
            u=r.url
            if not any(d in u for d in ["remitindex","firebase","amazonaws","api."]) : return
            body=""
            try: body=r.text()[:3000]
            except: pass
            seen.append({"s":r.status,"u":u,"ct":r.headers.get("content-type","")[:40],"b":body})
        except: pass
    pg.on("response",on_resp)
    pg.goto("https://www.remitindex.com/remittance",wait_until="networkidle",timeout=60000)
    pg.wait_for_timeout(15000)
    txt=pg.inner_text("body")
    for l in txt.splitlines():
        if re.search(r'(?i)moneygram|11\.7\d|HK\$',l) and len(l)<300:
            print("TXT>",l.strip())
    print("\n=== Network ===")
    for e in seen:
        print(f"{e['s']} {e['u'][:200]} ct={e['ct']}")
        if e['b'] and ('moneygram' in e['b'].lower() or '11.7' in e['b'] or 'rate' in e['b'].lower() or 'fee' in e['b'].lower()):
            print("  B:",re.sub(r'\s+',' ',e['b'])[:600])
    b.close()
