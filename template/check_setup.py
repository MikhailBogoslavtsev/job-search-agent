"""Test my setup - run this first, and any time something looks broken.

Checks every secret and every config file, one at a time, and says in plain
language what is wrong and where to fix it. Costs about one cent to run.

In GitHub: Actions -> "Test my setup" -> Run workflow.
"""

import json
import os
import sys

import requests

from common import load_config

OK = "PASS"
BAD = "FAIL"
SKIP = "SKIP"

results = []


def record(status, label, detail=""):
    results.append((status, label, detail))
    line = f"[{status}] {label}"
    if detail:
        line += f"\n       {detail}"
    print(line)


def check_files():
    for name in ("config.json", "profile.md", "queries.txt"):
        if not os.path.exists(name):
            record(BAD, f"{name} exists", f"{name} is missing from the repo.")
            continue
        if os.path.getsize(name) == 0:
            record(BAD, f"{name} has content", f"{name} is empty.")
            continue
        record(OK, f"{name} exists")

    if os.path.exists("profile.md"):
        with open("profile.md", encoding="utf-8") as f:
            profile = f.read()
        if "REPLACE THIS" in profile:
            record(BAD, "profile.md is filled in",
                   "profile.md still has the placeholder text in it. Edit it "
                   "to describe yourself, or the scout will search for nobody.")
        else:
            record(OK, "profile.md is filled in", f"{len(profile.split())} words")

    try:
        load_config()
        record(OK, "config.json is valid")
    except (ValueError, OSError) as e:
        record(BAD, "config.json is valid", f"Could not read it: {e}")


def check_telegram():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token:
        record(BAD, "TELEGRAM_BOT_TOKEN is set",
               "Add it in Settings -> Secrets and variables -> Actions.")
        return
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=20)
        data = r.json()
        if not data.get("ok"):
            record(BAD, "Telegram bot token works",
                   "Telegram rejected the token. Copy it again from @BotFather - "
                   "it looks like 123456789:AAxxxxxxxxxxxxxxxxxxxxxxxxxxxxx")
            return
        record(OK, "Telegram bot token works", f"bot @{data['result'].get('username')}")
    except requests.exceptions.RequestException as e:
        record(BAD, "Telegram bot token works", f"Could not reach Telegram: {e}")
        return

    if not chat_id:
        record(BAD, "TELEGRAM_CHAT_ID is set",
               "Add it in Settings -> Secrets and variables -> Actions.")
        return
    try:
        int(chat_id)
    except ValueError:
        record(BAD, "TELEGRAM_CHAT_ID is a number",
               f"It is '{chat_id}'. It must be a number like 123456789 - not "
               "your @username. The setup page can find it for you.")
        return

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": int(chat_id),
                  "text": "✅ Job Scout setup test - if you can read this, "
                          "Telegram is wired up correctly."},
            timeout=20)
        if r.json().get("ok"):
            record(OK, "Test message delivered", "Check your Telegram now.")
        else:
            record(BAD, "Test message delivered",
                   "The token works but this chat ID doesn't. Send your bot a "
                   f"message first, then re-check the ID. Telegram said: {r.text[:150]}")
    except requests.exceptions.RequestException as e:
        record(BAD, "Test message delivered", f"Could not reach Telegram: {e}")


def check_anthropic():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        record(BAD, "ANTHROPIC_API_KEY is set",
               "Add it in Settings -> Secrets and variables -> Actions.")
        return
    config = load_config()
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": config["model"], "max_tokens": 10,
                  "messages": [{"role": "user", "content": "Reply with the word OK."}]},
            timeout=60)
        data = r.json()
        if data.get("error"):
            err = data["error"].get("message", "")
            hint = ""
            if "credit" in err.lower() or "billing" in err.lower():
                hint = " Add credit at console.anthropic.com -> Billing."
            elif "authentication" in err.lower() or r.status_code == 401:
                hint = " The key is wrong or was revoked. Make a new one."
            record(BAD, "Anthropic API key works", err + hint)
            return
        record(OK, "Anthropic API key works", f"model {config['model']} responded")
    except requests.exceptions.RequestException as e:
        record(BAD, "Anthropic API key works", f"Could not reach Anthropic: {e}")


def check_exa():
    key = os.environ.get("EXA_API_KEY")
    if not key:
        record(SKIP, "Exa API key (optional)",
               "Not set. Role Scout works fine without it; Company Scout stays off.")
        return
    try:
        r = requests.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": key, "content-type": "application/json"},
            json={"query": "b2b saas startup", "numResults": 1},
            timeout=40)
        if r.status_code >= 400:
            record(BAD, "Exa API key works",
                   f"Exa rejected it ({r.status_code}). Check the key at exa.ai.")
            return
        record(OK, "Exa API key works")
    except requests.exceptions.RequestException as e:
        record(BAD, "Exa API key works", f"Could not reach Exa: {e}")

    for name in ("company_profile.md", "company_queries.json"):
        if not os.path.exists(name):
            record(BAD, f"{name} exists", f"{name} is missing.")
        else:
            record(OK, f"{name} exists")
    if os.path.exists("company_queries.json"):
        try:
            with open("company_queries.json", encoding="utf-8") as f:
                queries = json.load(f)
            if not queries:
                record(BAD, "company_queries.json has queries", "The list is empty.")
            else:
                record(OK, "company_queries.json has queries", f"{len(queries)} queries")
        except ValueError as e:
            record(BAD, "company_queries.json is valid JSON", str(e))


def main():
    print("=" * 62)
    print("  Job Scout - setup check")
    print("=" * 62)
    print()
    print("--- Your files ---")
    check_files()
    print()
    print("--- Telegram ---")
    check_telegram()
    print()
    print("--- Anthropic (Claude) ---")
    check_anthropic()
    print()
    print("--- Exa (optional) ---")
    check_exa()

    failed = [r for r in results if r[0] == BAD]
    print()
    print("=" * 62)
    if failed:
        print(f"  {len(failed)} problem(s) to fix:")
        for _, label, detail in failed:
            print(f"   - {label}: {detail}")
        print("=" * 62)
        sys.exit(1)
    print("  Everything checks out. You're ready to run the scouts.")
    print("=" * 62)


if __name__ == "__main__":
    main()
