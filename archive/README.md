# Archive

Retired components, kept for reference but no longer running.

## Level A — Job Monitor (`monitor.py`)

**Retired 2026-07-17.** The rules-based monitor that watched a fixed list of
known companies via Ashby / Greenhouse / Lever ATS APIs (plus a couple of HTML
scrapes), hash-diffed their PM postings, and pushed changes to Telegram daily.

Why it was retired: not enough value to justify keeping it on. The discovery
agents (Level B `scout.py`, Level C `scout_company.py`) cover the part of the
search that actually needed automation.

Files here:

- `monitor.py` — the monitor script.
- `monitor.yml` — its GitHub Actions workflow (was `.github/workflows/monitor.yml`).
  Moving it out of `.github/workflows/` is what stops it from running; GitHub
  only schedules workflows that live in that directory.
- `seen_jobs.json` — its state file (hash of the last-seen postings per company).

To bring it back, move `monitor.py` and `seen_jobs.json` to the repo root and
`monitor.yml` back to `.github/workflows/`.
