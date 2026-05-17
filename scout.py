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
You are a job scout helping a Product Manager find relevant companies and roles.

Candidate profile:
- Senior/Lead/Staff PM or Head of Product
- Currently PM at TraceAir (construction tech, drone mapping, SaaS for US homebuilders)
- 11 years at Spraying Systems Co — deep knowledge of industrial verticals: pulp & paper, food & beverage, dairy, meat, bakery, confectionery, wood products (MDF/OSB/DSP), metallurgy, automotive, mining, oil & gas
- Built 0-to-1 products, enterprise B2B discovery, cross-functional delivery
- Based in Spain, works remotely
- Open to: US companies hiring via EOR (Deel/Remote.com), EU-headquartered companies, remote or hybrid in Northern Europe
- NOT looking for: roles requiring US presence, on-site only, consumer apps with no industrial/B2B angle

Target companies:
- Series A to C startups
- Industrial tech, IIoT, manufacturing SaaS, construction tech, food traceability, physical operations AI
- Companies where understanding how a factory or construction site works is an advantage
- YC-backed companies in these domains are especially interesting
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
{PROFILE}

Your task: Search the web for companies and PM roles that match this candidate's profile.

Use these search queries one by one:
{chr(10).join(f'- {q}' for q in SEARCH_QUERIES)}

For each company you find:
1. Check if it matches the candidate profile
2. Skip if company name contains any of these (already known): {', '.join(seen_companies[:30]) if seen_companies else 'none yet'}
3. For matching companies return:
   - Company name
   - Role title
   - Why it fits (1 sentence, specific)
   - Product description (3-5 words)
   - Job URL if found
   - Remote/location info

Return a JSON array like this:
[
  {{
    "company": "Company Name",
    "role": "Senior Product Manager",
    "product": "Construction analytics SaaS",
    "why": "Direct overlap with TraceAir domain and industrial background",
    "url": "https://...",
    "location": "Remote / Netherlands"
  }}
]

Return ONLY the JSON array, no other text. If nothing found return [].
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

    # Parse JSON
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    text = text.strip()

    if not text or text == "[]":
        return []

    return json.loads(text)

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
