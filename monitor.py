import os
import json
import hashlib
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
STATE_FILE = "seen_jobs.json"

KEYWORDS = [
    "senior product manager",
    "staff product manager",
    "lead product manager",
    "head of product",
    "principal product manager",
    "senior pm",
    "lead pm",
]

COMPANIES = [
    {"name": "Squint", "ats": "ashby", "slug": "squint"},
    {"name": "Sierra Platform", "ats": "ashby", "slug": "sierra"},
    {"name": "Greenlite", "ats": "ashby", "slug": "greenlite"},
    {"name": "Valon", "ats": "greenhouse", "slug": "valon"},
    {"name": "Engine", "ats": "greenhouse", "slug": "engine"},
    {"name": "OpenSpace", "ats": "greenhouse", "slug": "openspace"},
    {"name": "PermitFlow", "ats": "greenhouse", "slug": "permitflow"},
    {"name": "MaintainX", "ats": "greenhouse", "slug": "maintainx"},
    {"name": "MoonPay", "ats": "lever", "slug": "moonpay"},
    {"name": "Preply", "ats": "html", "url": "https://preply.com/en/careers"},
    {"name": "Sword Health", "ats": "html", "url": "https://jobs.lever.co/swordhealth"},
    {"name": "Revolut", "ats": "html", "url": "https://www.revolut.com/careers"},
    {"name": "Linear", "ats": "html", "url": "https://linear.app/careers"},
    {"name": "Navan", "ats": "html", "url": "https://navan.com/careers"},
    {"name": "Trunk Tools", "ats": "html", "url": "https://trunktools.com/careers"},
    {"name": "Buildots", "ats": "html", "url": "https://buildots.com/careers"},
    {"name": "DroneDeploy", "ats": "html", "url": "https://www.dronedeploy.com/company/careers"},
    {"name": "Propeller Aerobotics", "ats": "html", "url": "https://www.propelleraero.com/careers"},
    {"name": "Tulip Interfaces", "ats": "html", "url": "https://tulip.co/careers"},
    {"name": "Augury", "ats": "html", "url": "https://www.augury.com/careers"},
    {"name": "Cognite", "ats": "html", "url": "https://www.cognite.com/en/careers"},
    {"name": "CoLab", "ats": "html", "url": "https://www.colabsoftware.com/careers"},
    {"name": "HappyRobot", "ats": "html", "url": "https://www.happyrobot.ai/careers"},
    {"name": "Nominal", "ats": "html", "url": "https://www.nominal.so/careers"},
    {"name": "iFoodDS", "ats": "html", "url": "https://www.ifoodds.com/about-us/careers"},
    {"name": "SafetyChain", "ats": "html", "url": "https://www.safetychain.com/company/careers"},
    {"name": "Alto Pharmacy", "ats": "html", "url": "https://alto.wd1.myworkdayjobs.com/en-US/FuzeHealthCareerSite"},
]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobMonitorBot/1.0)"}

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def make_hash(text):
    return hashlib.md5(text.encode()).hexdigest()

def keywords_match(text):
    text = text.lower()
    return [kw for kw in KEYWORDS if kw in text]

def fetch_ashby(slug):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{slug}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        jobs = data.get("jobPostings", [])
        return [j["title"] for j in jobs if any(kw in j["title"].lower() for kw in KEYWORDS)]
    except Exception as e:
        print(f"  Ashby error: {e}")
        return []

def fetch_greenhouse(slug):
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        data = r.json()
        jobs = data.get("jobs", [])
        return [j["title"] for j in jobs if any(kw in j["title"].lower() for kw in KEYWORDS)]
    except Exception as e:
        print(f"  Greenhouse error: {e}")
        return []

def fetch_lever(slug):
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        jobs = r.json()
        return [j["text"] for j in jobs if any(kw in j["text"].lower() for kw in KEYWORDS)]
    except Exception as e:
        print(f"  Lever error: {e}")
        return []

def fetch_html(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        return keywords_match(r.text)
    except Exception as e:
        print(f"  HTML error: {e}")
        return []

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": int(TELEGRAM_CHAT_ID),
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    })

def main():
    state = load_state()
    new_findings = []

    for company in COMPANIES:
        name = company["name"]
        ats = company["ats"]
        print(f"Checking {name} ({ats})...")

        if ats == "ashby":
            matches = fetch_ashby(company["slug"])
        elif ats == "greenhouse":
            matches = fetch_greenhouse(company["slug"])
        elif ats == "lever":
            matches = fetch_lever(company["slug"])
        else:
            matches = fetch_html(company["url"])

        if not matches:
            print(f"  No PM roles found")
            continue

        current_hash = make_hash(" ".join(matches))
        previous_hash = state.get(name)

        if current_hash != previous_hash:
            state[name] = current_hash
            new_findings.append({
                "name": name,
                "url": company.get("url", ""),
                "matches": matches,
            })
            print(f"  NEW or CHANGED: {matches}")
        else:
            print(f"  No change ({len(matches)} roles)")

    save_state(state)

    if new_findings:
        msg = "🔍 <b>Job Scout Alert</b>\n\n"
        for f in new_findings:
            msg += f"🏢 <b>{f['name']}</b>\n"
            if f["url"]:
                msg += f"🔗 {f['url']}\n"
            for role in f["matches"]:
                msg += f"📌 {role}\n"
            msg += "\n"
        msg += f"<i>{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</i>"
        send_telegram(msg)
        print("Telegram alert sent!")
    else:
        msg = (
            f"😴 <b>Ничего нового</b>\n\n"
            f"Проверил {len(COMPANIES)} компаний — новых PM ролей не появилось.\n\n"
            f"<i>{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</i>"
        )
        send_telegram(msg)
        print("No new findings.")

if __name__ == "__main__":
    main()
