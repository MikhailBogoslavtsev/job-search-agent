import os
import json
import hashlib
import requests
from bs4 import BeautifulSoup
from datetime import datetime

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = "seen_jobs.json"

# Add target career pages here
CAREER_PAGES = [
    {
        "company": "Example Company",
        "url": "https://example.com/careers",
        "job_selector": "a.job-listing",  # CSS selector for job links/titles
    },
]


def load_seen_jobs() -> set:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen_jobs(seen: set) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f)


def fetch_jobs(page: dict) -> list[dict]:
    try:
        response = requests.get(page["url"], timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[{page['company']}] fetch error: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    jobs = []
    for element in soup.select(page["job_selector"]):
        title = element.get_text(strip=True)
        link = element.get("href", "")
        if not link.startswith("http"):
            base = page["url"].rstrip("/")
            link = base + "/" + link.lstrip("/")
        if title:
            jobs.append({"company": page["company"], "title": title, "url": link})
    return jobs


def job_id(job: dict) -> str:
    raw = f"{job['company']}|{job['title']}|{job['url']}"
    return hashlib.sha256(raw.encode()).hexdigest()


def send_telegram(message: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Telegram send error: {e}")


def main() -> None:
    seen = load_seen_jobs()
    new_jobs = []

    for page in CAREER_PAGES:
        jobs = fetch_jobs(page)
        for job in jobs:
            jid = job_id(job)
            if jid not in seen:
                seen.add(jid)
                new_jobs.append(job)

    if new_jobs:
        for job in new_jobs:
            msg = (
                f"New job at {job['company']}\n"
                f"{job['title']}\n"
                f"{job['url']}"
            )
            send_telegram(msg)
        print(f"[{datetime.utcnow().isoformat()}] Sent {len(new_jobs)} new job alert(s).")
    else:
        print(f"[{datetime.utcnow().isoformat()}] No new jobs found.")

    save_seen_jobs(seen)


if __name__ == "__main__":
    main()
