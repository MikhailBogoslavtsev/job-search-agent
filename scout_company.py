import os
import json
import re
import requests
from datetime import datetime
from urllib.parse import urlparse

# --- Secrets (injected by GitHub Actions from repo secrets) ---
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
EXA_API_KEY = os.environ["EXA_API_KEY"]

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobMonitorBot/1.0)"}

# --- State / config files ---
KNOWN_FILE = "known_companies.json"        # dedupe memory, keyed by domain
STATE_FILE = "company_scout_state.json"    # rotation pointer
PROFILE_FILE = "company_profile.md"        # editable scoring rubric

# --- Tunable constants ---
SCORE_THRESHOLD = 6            # companies scoring >= this get sent to Telegram
EXA_RESULTS_PER_QUERY = 10     # how many results Exa returns per run
EXA_TEXT_CHARS = 6000          # cap of page text we hand to Claude (token budget)
CLAUDE_MODEL = "claude-sonnet-5"

# --- The rotating queries (one runs per execution) ---
# Exa is a SEMANTIC engine: queries are rich natural-language descriptions of
# the ideal page, not keyword lists. The company-discovery queries use Exa's
# real `category` field (value "company") rather than an inline "category:"
# prefix; the job-posting queries use no category.
#
# The "Augury cluster" queries at the end add coverage for another shape
# (see augury_profile.md): industrial AI with agents/copilots for plant and
# operations personas — the intersection of physical-operations domain and
# agentic AI. Included alongside the others, not prioritized above them.
COMPANY_QUERIES = [
    {"category": "company", "query": "startups turning drone or satellite imagery into operational decisions for construction and infrastructure field teams"},
    {"category": "company", "query": "companies building computer vision products for industrial inspection of energy assets, utilities, mining sites and manufacturing plants"},
    {"category": "company", "query": "vertical SaaS companies digitizing physical field operations for contractors, surveyors and civil engineers"},
    {"category": "company", "query": "European startups applying machine learning to physical operations — logistics, energy, agriculture, the built environment — with a product-led B2B SaaS model"},
    {"category": "company", "query": "startups building AI agents or copilots embedded inside workflow software for engineering and operations teams"},
    {"category": None, "query": "job posting for a senior or lead product manager at a remote-first European startup building a SaaS platform that turns imagery or sensor data into decisions for field teams"},
    {"category": None, "query": "job posting for a head of product or director of product at a Series A to C startup applying AI to construction, infrastructure or industrial operations"},
    {"category": None, "query": "job posting for a product manager at a company hiring remotely across Europe, building ML products from geospatial, earth observation or camera data"},
    {"category": "company", "query": "B2B SaaS startups building vertical software products for HR, legal, supply chain or logistics teams, payroll, benefits, or global employment teams not fintech"},
    {"category": "company", "query": "startups building developer tools or infrastructure software sold to engineering teams"},
    {"category": "company", "query": "climate tech or energy SaaS startups selling software products to operations teams, not fintech"},
    {"category": None, "query": "job posting for a senior or lead product manager at a Series A to C B2B SaaS startup remote in Europe, any industry except fintech"},
    {"category": None, "query": "job posting for a head of product at a remote-first B2B SaaS startup building a vertical software platform, not a fintech company"},
    # --- Augury cluster: industrial AI + agents/copilots for operations personas ---
    {"category": "company", "query": "startups building industrial AI agents or copilots for manufacturing operations, reliability and maintenance teams — machine health, process health, predictive maintenance on live plant data"},
    {"category": "company", "query": "companies building an industrial data platform that unifies fragmented operational sources — historians, CMMS, MES, ERP, sensors — and layers AI agents or copilots on top for plant engineers"},
    {"category": "company", "query": "vertical SaaS for frontline manufacturing operations and maintenance — CMMS, machine health, process optimization for process engineers, reliability engineers and plant managers — adding AI copilots"},
    {"category": None, "query": "job posting for a product manager or head of product at an industrial AI startup building agents or copilots for manufacturing, predictive maintenance, machine health or plant operations, remote"},
]


# --- State helpers (same pattern as scout.py) ---
def load_known():
    if os.path.exists(KNOWN_FILE):
        with open(KNOWN_FILE, "r") as f:
            return json.load(f)
    return {}

def save_known(known):
    with open(KNOWN_FILE, "w") as f:
        json.dump(known, f, indent=2, ensure_ascii=False)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"query_index": 0}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def load_profile():
    with open(PROFILE_FILE, "r") as f:
        return f.read()

def get_next_query(state):
    """Return one query and advance the rotation pointer by one."""
    idx = state.get("query_index", 0) % len(COMPANY_QUERIES)
    query = COMPANY_QUERIES[idx]
    state["query_index"] = (idx + 1) % len(COMPANY_QUERIES)
    return query


# --- Domain normalization (the key to dedupe) ---
def normalize_domain(value):
    """overstory.ai, www.overstory.ai and https://overstory.ai/careers
    all normalize to 'overstory.ai'. Returns '' if nothing usable."""
    if not value:
        return ""
    value = value.strip().lower()
    if "://" not in value:
        value = "http://" + value
    netloc = urlparse(value).netloc
    if not netloc:
        return ""
    netloc = netloc.split(":")[0]        # drop any port
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


# --- Name normalization (second dedupe key) ---
# The same company routinely shows up in Exa results under several different
# domains in one run: its own site, its ATS subdomain (job-boards.eu.
# greenhouse.io, apply.workable.com, ...) and third-party aggregators (join.com,
# remoterocketship.com, builtin.com, ...). None of those match each other as
# domains, so domain-only dedupe lets the same company get re-scored and
# re-sent to Telegram multiple times in a single run. Claude's returned
# "name" field is consistent across those pages, so use it as a second key.
_NAME_SUFFIXES = (" inc", " llc", " gmbh", " ltd", " limited", " corp",
                   " co", " ag", " sa", " bv", " plc", " group")

def normalize_company_name(name):
    if not name:
        return ""
    name = name.lower().strip()
    name = re.sub(r"\(.*?\)", "", name)      # drop "(YC W19)"-style notes
    name = re.sub(r"[^a-z0-9]+", " ", name).strip()
    for suffix in _NAME_SUFFIXES:
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
    return name


# --- URL validation ---
def check_domain_alive(domain):
    """HTTP-check a normalized domain (tries https then http). Exa's semantic
    search sometimes surfaces stale or parked pages; this catches domains
    that no longer resolve at all before we tell the user to go look at them."""
    for scheme in ("https://", "http://"):
        try:
            r = requests.get(scheme + domain, headers=HEADERS, timeout=10, allow_redirects=True)
            if r.status_code < 400:
                return True
        except Exception:
            continue
    return False


# --- Exa semantic search ---
def exa_search(query_obj):
    body = {
        "query": query_obj["query"],
        "type": "auto",
        "numResults": EXA_RESULTS_PER_QUERY,
        "contents": {"text": True},
    }
    if query_obj.get("category"):
        body["category"] = query_obj["category"]

    r = requests.post(
        "https://api.exa.ai/search",
        headers={"x-api-key": EXA_API_KEY, "Content-Type": "application/json"},
        json=body,
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("results", [])


# --- Defensive JSON parsing for Claude's reply ---
def parse_json_object(text):
    """Claude is asked for strict JSON, but sometimes wraps it in ```fences```
    or prose. Strip fences, then fall back to grabbing the first {...} block.
    Returns a dict or None — never raises."""
    if not text:
        return None
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            return None
    return None


# --- Claude scoring: reads a company page, returns a structured verdict ---
def score_company(profile, result):
    title = result.get("title", "") or ""
    url = result.get("url", "") or ""
    text = (result.get("text") or "")[:EXA_TEXT_CHARS]

    prompt = f"""You are scoring ONE company against the profile below. The profile
is the source of truth for what counts as interesting.

--- PROFILE ---
{profile}
--- END PROFILE ---

Here is the company's web page, discovered by a semantic search engine:

Title: {title}
URL: {url}
Page text:
{text}

Score this company 0-10 against the profile.

Two hard rules from the profile: (1) if this is a services / consulting /
outsourcing / staffing agency rather than a product (SaaS / platform)
company, set is_product_company to false and give it a low score — semantic
search cannot tell these apart, that judgment is your job; (2) if this is a
fintech company (banking, payments, lending, trading, insurance
infrastructure), give it a low score regardless of how well it otherwise
fits. Everything else in the profile is a soft signal.

Do NOT filter by country.

Respond with ONLY valid JSON — no markdown fences, no preamble, no text after:
{{"score": 7, "name": "Company Name", "domain": "example.com", "summary": "One line on what they build and who they sell to.", "is_product_company": true, "reason": "Why this score, referencing the profile."}}
"""

    # Timeouts/connection errors happen occasionally and are transient — retry
    # once before giving up, and never let this propagate out of the function.
    # An uncaught exception here used to kill the whole run mid-loop (losing
    # every company already scored, since state is only saved after the loop).
    data = None
    for attempt in range(2):
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": 1000,
                    "thinking": {"type": "disabled"},
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=90,
            )
            data = response.json()
            break
        except requests.exceptions.RequestException as e:
            print(f"  Claude API request failed (attempt {attempt + 1}/2): {e}")
    if data is None:
        return None
    if data.get("error"):
        print(f"  Claude API error: {data['error']}")
        return None

    text_out = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text_out += block.get("text", "")

    return parse_json_object(text_out)


# --- Telegram (same bot / chat / pattern as scout.py) ---
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    if len(message) > 4000:
        chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    else:
        chunks = [message]
    for chunk in chunks:
        # Same failure mode as the old score_company() bug: this runs after
        # all the scoring work, so an uncaught network error here would still
        # crash the whole run. Log and move on instead.
        try:
            requests.post(url, json={
                "chat_id": int(TELEGRAM_CHAT_ID),
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }, timeout=30)
        except requests.exceptions.RequestException as e:
            print(f"  Telegram send failed: {e}")


def format_company(verdict, domain, domain_alive):
    name = verdict.get("name") or "Unknown company"
    score = verdict.get("score", 0)
    summary = verdict.get("summary", "") or ""
    reason = verdict.get("reason", "") or ""
    msg = f"🏢 <b>{name}</b>  ·  {score}/10\n"
    msg += f"🔗 {domain}\n\n"
    msg += f"💡 {summary}\n\n"
    msg += f"✅ Why: {reason}"
    if not domain_alive:
        msg += "\n\n⚠️ <i>Site didn't resolve when checked — verify before reaching out</i>"
    return msg


def main():
    known = load_known()
    state = load_state()
    profile = load_profile()

    query_obj = get_next_query(state)
    label = query_obj.get("category") or "job-posting"
    print(f"Known companies: {len(known)}")
    print(f"This run's query [{label}]: {query_obj['query']}")

    try:
        results = exa_search(query_obj)
    except Exception as e:
        print(f"Exa error: {e}")
        send_telegram(f"⚠️ <b>Company Scout — Exa error</b>\n{e}")
        return

    # Advance rotation only after a successful search, so a failed run retries
    # the same query next time instead of silently skipping it.
    save_state(state)
    print(f"Exa returned {len(results)} results")

    # Name index for cross-domain dedupe, seeded from everything already known.
    name_index = {}
    for dom, info in known.items():
        norm = normalize_company_name(info.get("name", ""))
        if norm:
            name_index.setdefault(norm, dom)

    hits = []          # product companies scoring >= threshold -> Telegram
    scored = 0
    skipped_known = 0
    skipped_duplicate_name = 0

    for result in results:
        url_domain = normalize_domain(result.get("url", ""))
        if not url_domain:
            continue
        if url_domain in known:
            skipped_known += 1
            continue

        verdict = score_company(profile, result)
        if not verdict:
            print(f"  Skipped {url_domain}: could not parse a verdict")
            continue

        scored += 1
        score = verdict.get("score", 0)
        if not isinstance(score, (int, float)):
            score = 0
        is_product = verdict.get("is_product_company", True)

        # Prefer the domain Claude cleaned; fall back to the URL's domain.
        domain = normalize_domain(verdict.get("domain", "")) or url_domain
        norm_name = normalize_company_name(verdict.get("name", ""))

        # Same company already known under a different domain (own site vs.
        # ATS page vs. aggregator) -> alias this domain to the existing
        # record instead of re-scoring/re-sending it as if it were new.
        canonical_domain = name_index.get(norm_name) if norm_name else None
        if canonical_domain and canonical_domain not in (domain, url_domain):
            skipped_duplicate_name += 1
            known[domain] = known[canonical_domain]
            if url_domain not in known:
                known[url_domain] = known[canonical_domain]
            print(f"  Skipped {domain}: duplicate of '{verdict.get('name')}' already known via {canonical_domain}")
            continue

        # Only worth the live HTTP check for companies we're about to surface.
        domain_alive = True
        if is_product and score >= SCORE_THRESHOLD:
            domain_alive = check_domain_alive(domain)

        # Write EVERY scored company (any score) so it never gets re-scored.
        known[domain] = {
            "name": verdict.get("name") or result.get("title", ""),
            "first_seen": datetime.utcnow().strftime("%Y-%m-%d"),
            "score": score,
            "summary": verdict.get("summary", ""),
        }
        # Also guard against the URL-domain differing from Claude's domain, so
        # this company is deduped on either key next time.
        if url_domain not in known:
            known[url_domain] = known[domain]
        if norm_name:
            name_index[norm_name] = domain

        # Hard filter (product, not services) + score gate for Telegram.
        if is_product and score >= SCORE_THRESHOLD:
            hits.append((verdict, domain, domain_alive))
        print(f"  {domain}: {score}/10 product={is_product} alive={domain_alive}")

    save_known(known)
    print(f"Scored {scored} new companies, {skipped_known} already known by domain, "
          f"{skipped_duplicate_name} duplicate by name, {len(hits)} above threshold")

    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M")

    if hits:
        for verdict, domain, domain_alive in hits:
            send_telegram(format_company(verdict, domain, domain_alive))
        print(f"Sent {len(hits)} companies to Telegram")
    else:
        send_telegram(
            f"🏢 <b>Company Scout — nothing above {SCORE_THRESHOLD}/10 this run</b>\n\n"
            f"Query [{label}]: {query_obj['query']}\n"
            f"Scored {scored} new companies — none cleared the threshold.\n\n"
            f"<i>{timestamp} UTC</i>"
        )
        print("Sent 'nothing new' summary to Telegram")


if __name__ == "__main__":
    main()
