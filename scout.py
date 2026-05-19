import os
import json
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobMonitorBot/1.0)"}
SEEN_FILE = "seen_companies.json"

PROFILE = """
PM candidate profile for job matching:
- Role: Senior/Lead/Staff PM or Head of Product
- Current: PM at TraceAir (construction tech, drone mapping SaaS, US homebuilders)
- Background: 11 yrs Spraying Systems Co — industrial verticals: pulp/paper, food/beverage, dairy, meat, bakery, wood products, metallurgy, automotive, mining, oil/gas
- Skills: 0-to-1 products, enterprise B2B discovery, cross-functional delivery, computer vision products
- CV/drone angle: looking for companies applying drone/CV/aerial/satellite imagery tech in ANY domain (agriculture, infrastructure inspection, insurance, mining, utilities, environmental)
- Location: Spain, remote preferred. Open to EOR (Deel/Remote). EU HQ ok. Northern Europe hybrid possible.
- Target: Series A-C startups
- NOT: US on-site only, pure consumer apps
"""

SEARCH_QUERIES = [
    "senior product manager remote Europe industrial SaaS 2026 hiring",
    "lead PM construction tech startup hiring remote 2026",
    "head of product manufacturing IoT startup Europe 2026",
    "YC startup industrial AI product manager 2026",
    "food traceability SaaS senior PM remote 2026",
    "physical operations AI startup product manager hiring 2026",
    "senior PM B2B SaaS Netherlands Germany remote 2026",
    "Wellfound senior product manager industrial tech remote Europe",
    "Otta lead PM construction manufacturing startup",
    "site:ycombinator.com/jobs product manager industrial construction",
    "computer vision AI startup agriculture crop monitoring product manager 2026",
    "drone analytics startup senior PM remote Europe 2026",
    "aerial imagery AI platform product manager hiring 2026",
    "precision agriculture computer vision SaaS product manager 2026",
    "geospatial AI startup senior product manager 2026",
    "remote sensing analytics startup PM Europe hiring 2026",
    "AI inspection startup computer vision product manager 2026",
    "infrastructure inspection drone AI startup hiring PM 2026",
    "satellite imagery analytics startup senior PM remote 2026",
    "site:wellfound.com senior product manager computer vision drone",
]

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return []

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f, indent=2)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    # Split long messages
    if len(message) > 4000:
        chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
        for chunk in chunks:
            requests.post(url, json={
                "chat_id": int(TELEGRAM_CHAT_ID),
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            })
    else:
        requests.post(url, json={
            "chat_id": int(TELEGRAM_CHAT_ID),
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        })

def validate_url(url):
    if not url:
        return False
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        return r.status_code < 400
    except Exception:
        return False

def run_claude_scout(seen_companies):
    prompt = f"""
You are a job scout. Search the web and find companies hiring Senior/Lead/Staff PM or Head of Product.

Candidate: PM with TraceAir (construction drone SaaS) + 11 yrs industrial background (food, pulp/paper, manufacturing, mining). Based in Spain, remote. Open to EU companies or US via EOR.

Target: Series A-C startups in industrial tech, construction tech, IIoT, computer vision, drone/aerial analytics, food traceability, physical operations AI.

Search using these queries:
{chr(10).join(f'- {q}' for q in SEARCH_QUERIES[:5])}

Find 3-8 real companies actively hiring PM roles that match.

YOU MUST respond with ONLY a valid JSON array. No text before or after. No markdown. No explanation.

Example format:
[{{"company":"Acme","role":"Senior PM","product":"Construction SaaS","why":"Matches TraceAir domain","url":"https://acme.com/careers","location":"Remote EU"}}]

Already known companies to skip: {', '.join(seen_companies[:5]) if seen_companies else 'none'}

Return [] if nothing found. Return ONLY JSON.
"""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-6",
            "max_tokens": 4000,
            "tools": [{"type": "web_search_20250305", "name": "web_search"}],
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )

    data = response.json()

    # Extract text from response
    text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")
    print(f"DEBUG - Response blocks: {len(data.get('content', []))}")
    print(f"DEBUG - Raw text: {text[:500]}")
    print(f"DEBUG - API error: {data.get('error', 'none')}")

    import re

    # Find all JSON array candidates and try each one
    json_matches = re.finditer(r'\[.*?\]', text, re.DOTALL)
    for match in json_matches:
        json_str = match.group(0).strip()
        if not json_str or json_str == "[]":
            continue
        try:
            result = json.loads(json_str)
            if isinstance(result, list) and len(result) > 0:
                return result
        except Exception:
            continue

    # Try greedy match as fallback
    json_match = re.search(r'\[.*\]', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0).strip())
        except Exception:
            pass

    print("No valid JSON array found in response")
    return []

def main():
    seen = load_seen()
    print(f"Known companies: {len(seen)}")

    print("Running AI scout...")
    try:
        results = run_claude_scout(seen)
    except Exception as e:
        print(f"Scout error: {e}")
        send_telegram(f"⚠️ Scout error: {e}")
        return

    print(f"Found {len(results)} new matches")

    if not results:
        msg = (
            f"🤖 <b>AI Scout — no new finds</b>\n\n"
            f"Searched {len(SEARCH_QUERIES)} queries — nothing new matching your profile.\n\n"
            f"<i>{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</i>"
        )
        send_telegram(msg)
        return

    # Validate URLs
    print("Validating URLs...")
    for r in results:
        if r.get("url"):
            valid = validate_url(r["url"])
            if not valid:
                print(f"  Invalid URL for {r['company']}: {r['url']}")
                r["url"] = ""

    # Update seen list
    new_companies = [r["company"] for r in results]
    seen.extend(new_companies)
    save_seen(seen)

    # Build message
    msg = f"🤖 <b>AI Scout — {len(results)} new {'find' if len(results)==1 else 'finds'}</b>\n\n"
    for r in results:
        msg += f"🏢 <b>{r['company']}</b>\n"
        msg += f"📌 {r['role']}\n"
        msg += f"🏭 {r['product']}\n"
        msg += f"✅ {r['why']}\n"
        msg += f"📍 {r['location']}\n"
        if r.get("url"):
            msg += f"🔗 {r['url']}\n"
        else:
            msg += f"🔍 <i>No verified link — search manually</i>\n"
        msg += "\n"

    msg += f"<i>{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</i>"
    send_telegram(msg)
    print("Telegram sent!")

if __name__ == "__main__":
    main()
