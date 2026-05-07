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
    {"name": "Preply", "url": "https://preply.com/en/careers"},
    {"name": "Squint", "url": "https://www.squint.ai/jobs"},
    {"name": "Sword Health", "url": "https://jobs.lever.co/swordhealth"},
    {"name": "Revolut", "url": "https://www.revolut.com/careers"},
    {"name": "Sierra Platform", "url": "https://sierra.ai/careers"},
    {"name": "Valon", "url": "https://www.valon.com/careers"},
    {"name": "Engine", "url": "https://engine.com/careers"},
    {"name": "Navan", "url": "https://navan.com/careers"},
    {"name": "OpenSpace", "url": "https://www.openspace.ai/careers"},
    {"name": "Trunk Tools", "url": "https://trunktools.com/careers"},
    {"name": "PermitFlow", "url": "https://www.permitflow.com/careers"},
    {"name": "Buildots", "url": "https://buildots.com/careers"},
    {"name": "DroneDeploy", "url": "https://www.dronedeploy.com/company/careers"},
    {"name": "Propeller Aerobotics", "url": "https://www.propelleraero.com/careers"},
    {"name": "MaintainX", "url": "https://www.getmaintainx.com/careers"},
    {"name": "Tulip Interfaces", "url": "https://tulip.co/careers"},
    {"name": "Augury", "url": "https://www.augury.com/careers"},
    {"name": "Cognite", "url": "https://www.cognite.com/en/careers"},
    {"name": "CoLab", "url": "https://www.colabsoftware.com/careers"},
    {"name": "HappyRobot", "url": "https://www.happyrobot.ai/careers"},
    {"name": "Nominal", "url": "https://www.nominal.so/careers"},
    {"name": "Greenlite", "url": "https://www.greenlite.ai/careers"},
    {"name": "iFoodDS", "url": "https://www.ifoodds.com/about-us/careers"},
    {"name": "SafetyChain", "url": "https://www.safetychain.com/company/careers"},
    {"name": "MoonPay", "url": "https://jobs.lever.co/moonpay"},
    {"name": "Linear", "url": "https://linear.app/careers"},
    {"name": "Alto Pharmacy", "url": "https://alto.wd1.myworkdayjobs.com/en-US/FuzeHealthCareerSite"},
]

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def fetch_page(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; JobMonitorBot/1.0)"}
        r = requests.get(url, headers=headers, timeout=15)
        return r.text.lower()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def find_matches(text, keywords):
    return [kw for kw in keywords if kw in text]

def make_hash(text):
    return hashlib.md5(text.encode()).hexdigest()

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    })

def main():
    state = load_state()
    new_findings = []

    for company in COMPANIES:
        name = company["name"]
        url = company["url"]
        print(f"Checking {name}...")

        text = fetch_page(url)
        if not text:
            continue

        matches = find_matches(text, KEYWORDS)
        if not matches:
            print(f"  No PM roles found at {name}")
            continue

        current_hash = make_hash(" ".join(matches))
        previous_hash = state.get(name)

        if current_hash != previous_hash:
            state[name] = current_hash
            new_findings.append({
                "name": name,
                "url": url,
                "matches": matches
            })
            print(f"  NEW or CHANGED: {matches}")
        else:
            print(f"  No change at {name}")

    save_state(state)

    if new_findings:
        msg = "🔍 <b>Job Scout Alert</b>\n\n"
        for f in new_findings:
            msg += f"🏢 <b>{f['name']}</b>\n"
            msg += f"🔗 {f['url']}\n"
            roles = ", ".join(f['matches'])
            msg += f"📌 Found: {roles}\n\n"
        msg += f"<i>Checked: {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</i>"
        send_telegram(msg)
        print("Telegram alert sent!")
    else:
        print("No new findings. No message sent.")

if __name__ == "__main__":
    main()
