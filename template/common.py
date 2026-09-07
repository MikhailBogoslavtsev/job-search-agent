"""Shared helpers for both scouts.

Everything here used to be duplicated between scout.py and scout_company.py.
It also holds the two things that make this repo reusable by someone who is
not the person who wrote it: config lives in config.json, and the candidate
profile lives in Markdown files rather than inside the Python source.
"""

import json
import os
import re
import sys

import requests

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; JobScoutBot/1.0)"}

DEFAULT_CONFIG = {
    "score_threshold": 6,
    "model": "claude-sonnet-5",
    "max_web_searches": 10,
    "max_output_tokens": 2000,
    "queries_per_run": 3,
    "exa_results_per_query": 10,
    "exa_text_chars": 6000,
}


def load_config(path="config.json"):
    """config.json overrides DEFAULT_CONFIG. A missing file is fine."""
    config = dict(DEFAULT_CONFIG)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            config.update(json.load(f))
    return config


def load_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def load_queries(path):
    """One search query per line. Blank lines and #-comments are ignored."""
    queries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                queries.append(line)
    return queries


def load_json_file(path, default):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json_file(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# --- Secrets -----------------------------------------------------------------

def require_env(*names):
    """Read required secrets, and fail with a message a human can act on.

    The original scripts used os.environ["..."], which on a missing secret
    raises a bare KeyError in the Actions log — accurate, and useless to
    someone who has never seen a Python traceback.
    """
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        print("\n".join([
            "",
            "MISSING SETUP: this run needs secrets that aren't set yet.",
            "",
            "Missing: " + ", ".join(missing),
            "",
            "Add them under: your repo -> Settings -> Secrets and variables",
            "  -> Actions -> New repository secret.",
            "Names must match exactly, including capitals.",
            "",
        ]))
        sys.exit(1)
    return [os.environ[n] for n in names]


# --- Telegram ----------------------------------------------------------------

TELEGRAM_LIMIT = 4000


def send_telegram(token, chat_id, message, preview=True):
    """Send a message, split if long. Never raises — a delivery failure
    should not lose the work the run already did."""
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    chunks = [message[i:i + TELEGRAM_LIMIT]
              for i in range(0, len(message), TELEGRAM_LIMIT)] or [""]
    for chunk in chunks:
        try:
            r = requests.post(url, json={
                "chat_id": int(chat_id),
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": not preview,
            }, timeout=30)
            if r.status_code >= 400:
                print(f"  Telegram rejected the message ({r.status_code}): {r.text[:200]}")
        except requests.exceptions.RequestException as e:
            print(f"  Telegram send failed: {e}")


# --- Anthropic ---------------------------------------------------------------

def call_claude(api_key, model, prompt, max_tokens, tools=None, timeout=280):
    """One Messages API call, retried once on a network hiccup.
    Returns the concatenated text blocks, or '' on an API error."""
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "thinking": {"type": "disabled"},
        "messages": [{"role": "user", "content": prompt}],
    }
    if tools:
        body["tools"] = tools

    for attempt in range(2):
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=body,
                timeout=timeout,
            )
            break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if attempt == 0:
                print(f"Anthropic request failed ({e.__class__.__name__}), retrying once...")
                continue
            raise

    data = response.json()
    if data.get("error"):
        print(f"Anthropic API error: {data['error']}")
        return ""
    return "".join(b.get("text", "") for b in data.get("content", [])
                   if b.get("type") == "text")


# --- Name normalization (dedupe key) -----------------------------------------
# The model returns the same company under slightly different names across
# runs -- "Wingtra" one week, "Wingtra AG" the next, "Confido" vs.
# "Confido (YC S21)" -- and an exact-string check doesn't catch any of that,
# so the same company gets re-sent.

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


# --- JSON extraction ---------------------------------------------------------
# "Return JSON" prompts still sometimes come back wrapped in prose.

def extract_json_array(text):
    for match in re.finditer(r"\[.*?\]", text, re.DOTALL):
        candidate = match.group(0).strip()
        if not candidate or candidate == "[]":
            continue
        try:
            result = json.loads(candidate)
            if isinstance(result, list) and result:
                return result
        except ValueError:
            continue
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0).strip())
        except ValueError:
            pass
    return []


def extract_json_object(text):
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except ValueError:
        return None
