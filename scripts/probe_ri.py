import re, requests
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36","Accept-Language":"en"}
urls=["https://www.remitindex.com/remittance","https://remitindex.com/remittance","https://www.remitindex.com/"]
for u in urls:
    try:
        r=requests.get(u,headers=UA,timeout=25,allow_redirects=True)
        print(f"\n== {u} -> {r.status_code} len={len(r.text)} final={r.url}")
        t=r.text
        for m in list(re.finditer(r'(?i)moneygram',t))[:5]:
            s=max(0,m.start()-200); e=min(len(t),m.end()+300)
            print("MG>",re.sub(r'\s+',' ',t[s:e])[:500])
        for pat in [r'(?i)11\.7\d{2,}',r'(?i)HK\$8',r'(?i)11,7\d{2}']:
            hits=[h for h in re.findall(pat,t)][:5]
            if hits: print("NUM",pat,hits)
        for m in list(re.finditer(r'https?://[^"\'\s<>]*(?:api|rates|quote|providers)[^"\'\s<>]*',t))[:15]:
            print("API?",m.group(0)[:200])
    except Exception as e:
        print(f"\n== {u} ERR {e}")
