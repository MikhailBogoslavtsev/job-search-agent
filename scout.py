import os
import json
import re
import requests
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SEEN_FILE = "seen_companies.json"
STATE_FILE = "scout_state.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobMonitorBot/1.0)"}

PROFILE = """
PM candidate profile for job matching:
- Role: Senior/Lead/Staff PM or Head of Product
- Current: PM at TraceAir (construction tech, drone mapping SaaS, US homebuilders)
- Background: 11 yrs Spraying Systems Co — industrial verticals: pulp/paper, food/beverage, dairy, meat, bakery, wood products, metallurgy, automotive, mining, oil/gas
- Skills: 0-to-1 products, enterprise B2B discovery, cross-functional delivery, computer vision products
- CV/drone angle: looking for companies applying drone/CV/aerial/satellite imagery tech in ANY domain (agriculture, infrastructure inspection, insurance, mining, utilities, environmental)
- Industry scope: ANY B2B SaaS vertical is fair game (HR tech, martech, devtools/infra, legal tech, supply chain/logistics, cybersecurity, healthtech ops, climate/energy, real estate tech, vertical AI tools, industrial/construction) — not limited to construction or industrial
- Location: Spain, remote preferred. Open to EOR (Deel/Remote). EU HQ ok. Northern Europe hybrid possible.
- Target: Series A-C startups
- NOT: US on-site only, pure consumer apps, fintech (requires domain-specific regulatory/financial knowledge the candidate doesn't have)
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
    "senior product manager B2B SaaS startup remote Europe 2026 hiring",
    "head of product B2B SaaS Series B startup remote 2026",
    "YC startup B2B SaaS senior product manager hiring 2026 -fintech",
    "lead product manager HR tech SaaS startup remote Europe 2026",
    "senior PM devtools infrastructure startup remote 2026 hiring",
    "senior product manager cybersecurity SaaS startup remote Europe 2026",
    "lead PM supply chain logistics SaaS startup hiring remote 2026",
    "senior product manager legal tech SaaS startup remote 2026",
    "head of product climate tech energy SaaS startup remote Europe 2026",
    "senior PM vertical AI B2B SaaS startup hiring remote 2026",
    "Wellfound senior product manager B2B SaaS remote Europe -fintech",
    "Otta lead product manager B2B SaaS startup remote Europe",
]

def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, "r") as f:
            return json.load(f)
    return []

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(seen, f, indent=2)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"query_index": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def get_next_queries(state, n=3):
    idx = state.get("query_index", 0)
    queries = SEARCH_QUERIES[idx:idx+n]
    if len(queries) < n:
        queries += SEARCH_QUERIES[:n-len(queries)]
    state["query_index"] = (idx + n) % len(SEARCH_QUERIES)
    return queries

CLOSED_LISTING_SIGNALS = [
    "no longer accepting applications",
    "no longer accepting new applicants",
    "position has been filled",
    "this position is no longer available",
    "this role is no longer available",
    "job has been closed",
    "posting has expired",
    "this posting has expired",
    "not currently accepting applications",
    "this role is closed",
    "no longer open",
    "job is no longer active",
    "this job is no longer active",
    "we are no longer hiring for this role",
]

def check_listing(url):
    """Returns (url_ok, confirmed). confirmed=False means the URL either
    doesn't resolve or its page text suggests the role may already be closed
    - not proof either way, just what we could check automatically."""
    if not url:
        return False, False
    try:
        r = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        if r.status_code >= 400:
            return False, False
        body = r.text.lower()
        if any(signal in body for signal in CLOSED_LISTING_SIGNALS):
            return True, False
        return True, True
    except Exception:
        return False, False

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
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

def run_claude_scout(queries, seen_companies):
    prompt = f"""
You are a job scout. Search the web and find companies hiring Senior/Lead/Staff PM or Head of Product.

{PROFILE}

Search using ONLY these 3 queries:
{chr(10).join(f'- {q}' for q in queries)}

Find 3-6 real companies actively hiring PM roles that match the candidate.
Do NOT include fintech companies.

Skip these already known companies: {', '.join(seen_companies[:5]) if seen_companies else 'none'}

For each result, set "status" to "confirmed" only if you directly saw a live
application page for that exact role with an active "Apply" button (e.g. the
company's own careers page or its ATS listing). Set "status" to "unconfirmed"
if you found the role via a secondary source (news article, LinkedIn mention,
aggregator, cached page, or you're unsure the posting is still live) — do not
guess "confirmed" to sound more useful.

YOU MUST respond with ONLY a valid JSON array. No text before or after. No markdown. No explanation.

Format:
[{{"company":"Name","role":"Role title","product":"Product in 5 words","why":"One sentence why it fits","url":"https://careers-url-or-empty","location":"Remote/City/Country","status":"confirmed|unconfirmed"}}]

Return [] if nothing found. JSON only.
"""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-5",
            "max_tokens": 2000,
            "thinking": {"type": "disabled"},
            "tools": [{"type": "web_search_20260209", "name": "web_search"}],
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=120,
    )

    data = response.json()

    if data.get("error"):
        print(f"API error: {data['error']}")
        return []

    text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")

    print(f"Raw text preview: {text[:300]}")

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

    json_match = re.search(r'\[.*\]', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0).strip())
        except Exception:
            pass

    return []

def main():
    seen = load_seen()
    state = load_state()

    queries = get_next_queries(state, n=3)
    print(f"Known companies: {len(seen)}")
    print(f"This week's queries: {queries}")

    try:
        results = run_claude_scout(queries, seen)
    except Exception as e:
        print(f"Scout error: {e}")
        send_telegram(f"⚠️ Scout error: {e}")
        return

    save_state(state)
    print(f"Found {len(results)} matches")

    if not results:
        msg = (
            f"🤖 <b>AI Scout — nothing new this week</b>\n\n"
            f"Searched 3 queries — no new PM roles matching your profile.\n\n"
            f"<i>{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</i>"
        )
        send_telegram(msg)
        return

    print("Validating URLs...")
    for r in results:
        url_ok, url_confirmed = check_listing(r.get("url", ""))
        if r.get("url") and not url_ok:
            print(f"  Invalid URL for {r['company']}: {r['url']}")
            r["url"] = ""
        model_confirmed = r.get("status") == "confirmed"
        r["status"] = "confirmed" if (url_confirmed and model_confirmed) else "unconfirmed"

    new_companies = [r["company"] for r in results]
    for c in new_companies:
        if c not in seen:
            seen.append(c)
    save_seen(seen)

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
            msg += f"🔍 <i>Search manually</i>\n"
        if r.get("status") != "confirmed":
            msg += f"⚠️ <i>Not confirmed still open — verify before applying</i>\n"
        msg += "\n"

    msg += f"<i>{datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC</i>"
    send_telegram(msg)
    print("Telegram sent!")

if __name__ == "__main__":
    main()
