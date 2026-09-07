"""Role Scout - find companies that are hiring right now.

Claude runs a handful of live web searches, returns candidate roles as JSON,
and every URL it returns is checked before anything reaches Telegram.

What makes this yours rather than mine: the candidate profile is read from
profile.md and the searches from queries.txt. You never edit this file.
"""

from datetime import datetime, timezone

import requests

from common import (HEADERS, call_claude, extract_json_array, load_config,
                    load_json_file, load_queries, load_text,
                    normalize_company_name, require_env, save_json_file,
                    send_telegram)

SEEN_FILE = "seen_companies.json"
STATE_FILE = "scout_state.json"
PROFILE_FILE = "profile.md"
QUERIES_FILE = "queries.txt"

# Signals that a page is a real posting but the role is already gone. A 200
# status alone does not mean the role is still open.
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


def get_next_queries(state, queries, n):
    idx = state.get("query_index", 0) % len(queries)
    picked = queries[idx:idx + n]
    if len(picked) < n:
        picked += queries[:n - len(picked)]
    state["query_index"] = (idx + n) % len(queries)
    return picked


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
    except requests.exceptions.RequestException:
        return False, False


def build_prompt(profile, queries, seen_companies):
    return f"""
You are a job scout. Search the web and find companies hiring for the roles
described in the profile below.

{profile}

Search using ONLY these queries:
{chr(10).join(f'- {q}' for q in queries)}

Find 3-6 real companies actively hiring roles that match the candidate.

Skip these already known companies: {', '.join(seen_companies[:5]) if seen_companies else 'none'}

For each result, set "status" to "confirmed" only if you directly saw a live
application page for that exact role with an active "Apply" button (e.g. the
company's own careers page or its ATS listing). Set "status" to "unconfirmed"
if you found the role via a secondary source (news article, LinkedIn mention,
aggregator, cached page, or you're unsure the posting is still live) - do not
guess "confirmed" to sound more useful.

YOU MUST respond with ONLY a valid JSON array. No text before or after. No markdown. No explanation.

Format:
[{{"company":"Name","role":"Role title","product":"Product in 5 words","why":"One sentence why it fits","url":"https://careers-url-or-empty","location":"Remote/City/Country","status":"confirmed|unconfirmed"}}]

Return [] if nothing found. JSON only.
"""


def main():
    token, chat_id, api_key = require_env(
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "ANTHROPIC_API_KEY")
    config = load_config()
    profile = load_text(PROFILE_FILE)
    all_queries = load_queries(QUERIES_FILE)

    if not all_queries:
        send_telegram(token, chat_id,
                      "⚠️ <b>Role Scout</b> — queries.txt is empty, nothing to search.")
        return

    seen = load_json_file(SEEN_FILE, [])
    state = load_json_file(STATE_FILE, {"query_index": 0})
    queries = get_next_queries(state, all_queries, config["queries_per_run"])

    print(f"Known companies: {len(seen)}")
    print(f"This run's queries: {queries}")

    try:
        text = call_claude(
            api_key,
            config["model"],
            build_prompt(profile, queries, seen),
            config["max_output_tokens"],
            # max_uses caps how many searches the model can run per call.
            # Without it, an open-ended search loop can re-feed growing page
            # content back into context every round and cost several dollars
            # in a single run.
            tools=[{"type": "web_search_20260209", "name": "web_search",
                    "max_uses": config["max_web_searches"]}],
        )
    except Exception as e:
        print(f"Scout error: {e}")
        send_telegram(token, chat_id, f"⚠️ Role Scout error: {e}")
        return

    save_json_file(STATE_FILE, state)
    results = extract_json_array(text)
    print(f"Found {len(results)} matches")

    # Hard-filter against companies already tracked, on normalized name. The
    # prompt asks the model to skip known companies, but it's a soft
    # instruction over a 5-name sample, so this is the real guard against
    # re-sending "Wingtra AG" when "Wingtra" is already known.
    seen_norm = {normalize_company_name(c) for c in seen}
    deduped = []
    for r in results:
        norm = normalize_company_name(r.get("company", ""))
        if norm and norm in seen_norm:
            print(f"  Skipped {r.get('company')}: already known")
            continue
        if norm:
            seen_norm.add(norm)
        deduped.append(r)
    results = deduped

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")

    if not results:
        send_telegram(token, chat_id, (
            f"🤖 <b>Role Scout — nothing new</b>\n\n"
            f"Searched {len(queries)} queries, no new matching roles.\n\n"
            f"<i>{stamp} UTC</i>"))
        return

    print("Validating URLs...")
    for r in results:
        url_ok, url_confirmed = check_listing(r.get("url", ""))
        if r.get("url") and not url_ok:
            print(f"  Invalid URL for {r.get('company')}: {r['url']}")
            r["url"] = ""
        model_confirmed = r.get("status") == "confirmed"
        r["status"] = "confirmed" if (url_confirmed and model_confirmed) else "unconfirmed"

    existing_norm = {normalize_company_name(c) for c in seen}
    for r in results:
        name = r.get("company", "")
        norm = normalize_company_name(name)
        if norm and norm not in existing_norm:
            seen.append(name)
            existing_norm.add(norm)
    save_json_file(SEEN_FILE, seen)

    msg = f"🤖 <b>Role Scout — {len(results)} new {'find' if len(results) == 1 else 'finds'}</b>\n\n"
    for r in results:
        msg += f"🏢 <b>{r.get('company', '?')}</b>\n"
        msg += f"📌 {r.get('role', '')}\n"
        msg += f"🏭 {r.get('product', '')}\n"
        msg += f"✅ {r.get('why', '')}\n"
        msg += f"📍 {r.get('location', '')}\n"
        msg += f"🔗 {r['url']}\n" if r.get("url") else "🔍 <i>Search manually</i>\n"
        if r.get("status") != "confirmed":
            msg += "⚠️ <i>Not confirmed still open — verify before applying</i>\n"
        msg += "\n"
    msg += f"<i>{stamp} UTC</i>"

    send_telegram(token, chat_id, msg)
    print("Telegram sent.")


if __name__ == "__main__":
    main()
