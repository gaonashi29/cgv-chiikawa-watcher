import asyncio, json, os, urllib.request
from datetime import datetime, timedelta
from urllib.parse import urlencode
from playwright.async_api import async_playwright

SITE_NO="0013"
CO_CD="A420"
KEYWORD="치이카와"
STATE="cgv_chiikawa_state.json"
BOOKING="https://cgv.co.kr/cnm/movieBook/cinema"

def walk(x):
    if isinstance(x,dict):
        yield x
        for v in x.values(): yield from walk(v)
    elif isinstance(x,list):
        for v in x: yield from walk(v)

def pick(d,names):
    for n in names:
        if d.get(n) not in (None,""): return str(d[n])
    return ""

def load():
    try: return set(json.load(open(STATE,encoding="utf-8")))
    except: return set()

def save(s):
    json.dump(sorted(s),open(STATE,"w",encoding="utf-8"),ensure_ascii=False,indent=2)

def rows(data,date):
    out={}
    for d in walk(data):
        movie=pick(d,["movNm","movieNm","movNmKor","movieName"])
        screen=pick(d,["scnNm","screenNm","screenName","scnNmKor"])
        start=pick(d,["scnStartTime","playStartTm","startTime","scnStTm"])
        end=pick(d,["scnEndTime","playEndTm","endTime","scnEndTm"])
        if KEYWORD in movie and (screen or start):
            key="|".join([date,movie,screen,start,end])
            out[key]=(date,movie,screen or "상영관 정보 없음",start or "시간 정보 없음",end)
    return out

async def telegram(msg):
    token=os.getenv("TELEGRAM_BOT_TOKEN"); chat=os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("Telegram secrets 없음"); return
    data=urlencode({"chat_id":chat,"text":msg,"disable_web_page_preview":"false"}).encode()
    req=urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",data=data,method="POST")
    urllib.request.urlopen(req,timeout=20).read()

async def main():
    old=load(); current={}
    async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True)
        page=await browser.new_page()
        await page.goto(BOOKING,wait_until="domcontentloaded",timeout=60000)
        for i in range(15):
            date=(datetime.now()+timedelta(days=i)).strftime("%Y-%m-%d")
            q=urlencode({"coCd":CO_CD,"siteNo":SITE_NO,"scnYmd":date.replace("-",""),"rtctlScopCd":"08"})
            url="https://cgv.co.kr/api/v1/booking/searchMovScnInfo?"+q
            try:
                data=await page.evaluate("""async u=>{let r=await fetch(u,{credentials:'include'});let t=await r.text();try{return JSON.parse(t)}catch(e){return {}}}""",url)
                current.update(rows(data,date))
            except Exception as e: print(date,e)
        await browser.close()
    save(set(current)|old)
    if not old:
        print("첫 실행 기준점 저장:",len(current)); return
    for k,(date,movie,screen,start,end) in sorted(current.items()):
        if k not in old:
            msg=f"🐰 치이카와 CGV 용산아이파크몰 상영 오픈 감지!\\n\\n📅 {date}\\n🎬 {movie}\\n🏟️ {screen}\\n⏰ {start}"
            if end: msg+=f" ~ {end}"
            msg+=f"\\n\\nCGV 예매\\n{BOOKING}"
            await telegram(msg)

asyncio.run(main())
