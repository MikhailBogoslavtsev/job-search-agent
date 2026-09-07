"""Company Scout - find companies worth watching, before they post a job.

Exa semantic search -> dedupe by domain against known_companies.json ->
Claude scores each NEW company 0-10 against company_profile.md -> anything at
or above the threshold goes to Telegram. Every scored company is remembered so
it is never scored twice.

Optional: if EXA_API_KEY isn't set, this exits quietly. Role Scout still runs.

Your settings live in config.json, your rubric in company_profile.md, your
searches in company_queries.json. You never edit this file.
"""

import json
import os
import sys
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

from common import (HEADERS, call_claude, extract_json_object, load_config,
                    load_json_file, load_text, normalize_company_name,
                    require_env, save_json_file, send_telegram)

KNOWN_FILE = "known_companies.json"
STATE_FILE = "company_scout_state.json"
PROFILE_FILE = "company_profile.md"
QUERIES_FILE = "company_queries.json"


def normalize_domain(value):
    """overstory.ai, www.overstory.ai and https://overstory.ai/careers all
    normalize to 'overstory.ai'. Returns '' if nothing usable."""
    if not value:
        return ""
    value = value.strip().lower()
    if "://" not in value:
        value = "http://" + value
    netloc = urlparse(value).netloc
    if not netloc:
        return ""
    netloc = netloc.split(":")[0]
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def check_domain_alive(domain):
    """Exa's semantic search sometimes surfaces stale or parked pages, so a
    company is HTTP-checked before it is presented as a clean hit."""
    if not domain:
        return False
    for scheme in ("https://", "http://"):
        try:
            r = requests.get(scheme + domain, headers=HEADERS,
                             timeout=10, allow_redirects=True)
            if r.status_code < 400:
                return True
        except requests.exceptions.RequestException:
            continue
    return False


def get_next_query(state, queries):
    idx = state.get("query_index", 0) % len(queries)
    state["query_index"] = (idx + 1) % len(queries)
    return queries[idx]


def exa_search(api_key, query_obj, num_results, text_chars):
    payload = {
        "query": query_obj["query"],
        "numResults": num_results,
        "contents": {"text": {"maxCharacters": text_chars}},
    }
    if query_obj.get("category"):
        payload["category"] = query_obj["category"]
    r = requests.post(
        "https://api.exa.ai/search",
        headers={"x-api-key": api_key, "content-type": "application/json"},
        json=payload,
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("results", [])


def score_company(api_key, model, profile, result, max_tokens):
    prompt = f"""You are scoring ONE company against the profile below. The profile
is the candidate's own words about what they are looking for.

--- PROFILE ---
{profile}
--- END PROFILE ---

--- COMPANY PAGE ---
Title: {result.get('title', '')}
URL: {result.get('url', '')}
Text: {(result.get('text') or '')[:6000]}
--- END COMPANY PAGE ---

Score this company 0-10 against the profile.

Two hard rules from the profile: (1) if this mainly sells people's time
(consulting, agency, staffing, outsourcing, custom dev shop) it is NOT a fit -
score it low and set is_product_company to false, however interesting the
domain sounds; (2) apply any explicitly excluded industries named in the
profile. Everything else in the profile is a soft signal.

Respond with ONLY a JSON object, no prose, no markdown:
{{"score": 7, "name": "Company Name", "domain": "example.com", "summary": "One line on what they build and who they sell to.", "is_product_company": true, "reason": "Why this score, referencing the profile."}}
"""
    text = call_claude(api_key, model, prompt, max_tokens, timeout=120)
    return extract_json_object(text)


def format_company(verdict, domain, domain_alive):
    msg = f"🏢 <b>{verdict.get('name') or 'Unknown company'}</b>  ·  {verdict.get('score', 0)}/10\n"
    msg += f"🔗 {domain}\n\n"
    msg += f"💡 {verdict.get('summary', '') or ''}\n\n"
    msg += f"✅ Why: {verdict.get('reason', '') or ''}"
    if not domain_alive:
        msg += "\n\n⚠️ <i>Site didn't resolve when checked — verify before reaching out</i>"
    return msg


def main():
    token, chat_id, api_key = require_env(
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "ANTHROPIC_API_KEY")

    exa_key = os.environ.get("EXA_API_KEY")
    if not exa_key:
        print("EXA_API_KEY is not set — Company Scout is optional, skipping.")
        print("Add it as a repository secret if you want this half too.")
        sys.exit(0)

    config = load_config()
    threshold = config["score_threshold"]
    profile = load_text(PROFILE_FILE)
    with open(QUERIES_FILE, "r", encoding="utf-8") as f:
        all_queries = json.load(f)

    if not all_queries:
        send_telegram(token, chat_id,
                      "⚠️ <b>Company Scout</b> — company_queries.json is empty.")
        return

    known = load_json_file(KNOWN_FILE, {})
    state = load_json_file(STATE_FILE, {"query_index": 0})
    query_obj = get_next_query(state, all_queries)
    label = query_obj.get("category") or "job-posting"

    print(f"Known companies: {len(known)}")
    print(f"This run's query [{label}]: {query_obj['query']}")

    try:
        results = exa_search(exa_key, query_obj,
                             config["exa_results_per_query"],
                             config["exa_text_chars"])
    except Exception as e:
        print(f"Exa error: {e}")
        send_telegram(token, chat_id, f"⚠️ <b>Company Scout — Exa error</b>\n{e}")
        return

    # Advance rotation only after a successful search, so a failed run retries
    # the same query next time instead of silently skipping it.
    save_json_file(STATE_FILE, state)
    print(f"Exa returned {len(results)} results")

    # Name index for cross-domain dedupe: the same company shows up under its
    # own site, its ATS subdomain and third-party aggregators in one run, and
    # none of those match each other as domains.
    name_index = {}
    for dom, info in known.items():
        norm = normalize_company_name(info.get("name", ""))
        if norm:
            name_index.setdefault(norm, dom)

    hits = []
    scored = skipped_known = skipped_duplicate_name = 0

    for result in results:
        url_domain = normalize_domain(result.get("url", ""))
        if not url_domain:
            continue
        if url_domain in known:
            skipped_known += 1
            continue

        verdict = score_company(api_key, config["model"], profile, result,
                                config["max_output_tokens"])
        if not verdict:
            print(f"  Skipped {url_domain}: could not parse a verdict")
            continue

        scored += 1
        score = verdict.get("score", 0)
        if not isinstance(score, (int, float)):
            score = 0
        is_product = verdict.get("is_product_company", True)
        domain = normalize_domain(verdict.get("domain", "")) or url_domain
        norm_name = normalize_company_name(verdict.get("name", ""))

        canonical = name_index.get(norm_name) if norm_name else None
        if canonical and canonical not in (domain, url_domain):
            skipped_duplicate_name += 1
            known[domain] = known[canonical]
            known.setdefault(url_domain, known[canonical])
            print(f"  Skipped {domain}: same company as {canonical}")
            continue

        domain_alive = True
        if is_product and score >= threshold:
            domain_alive = check_domain_alive(domain)

        # Write EVERY scored company (any score) so it is never re-scored.
        known[domain] = {
            "name": verdict.get("name") or result.get("title", ""),
            "first_seen": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "score": score,
            "summary": verdict.get("summary", ""),
        }
        known.setdefault(url_domain, known[domain])
        if norm_name:
            name_index[norm_name] = domain

        if is_product and score >= threshold:
            hits.append((verdict, domain, domain_alive))
        print(f"  {domain}: {score}/10 product={is_product} alive={domain_alive}")

    save_json_file(KNOWN_FILE, known)
    print(f"Scored {scored} new, {skipped_known} known by domain, "
          f"{skipped_duplicate_name} duplicate by name, {len(hits)} above threshold")

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
    if hits:
        for verdict, domain, domain_alive in hits:
            send_telegram(token, chat_id,
                          format_company(verdict, domain, domain_alive),
                          preview=False)
        print(f"Sent {len(hits)} companies to Telegram")
    else:
        send_telegram(token, chat_id, (
            f"🏢 <b>Company Scout — nothing above {threshold}/10 this run</b>\n\n"
            f"Query [{label}]: {query_obj['query']}\n"
            f"Scored {scored} new companies — none cleared the threshold.\n\n"
            f"<i>{stamp} UTC</i>"), preview=False)
        print("Sent 'nothing new' summary to Telegram")


if __name__ == "__main__":
    main()
