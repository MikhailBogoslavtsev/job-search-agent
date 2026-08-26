# Job Scout

A personal AI job-search agent that runs on autopilot: go discover companies I
don't know to watch yet, and score companies worth tracking even before they're
hiring — without burning LLM cost more than it needs.

Built solo with Claude Code + Python. Runs serverless on GitHub Actions, no
server, no database.

> **Level A — the Job Monitor (`monitor.py`) — has been retired** (2026-07-17).
> It tracked a fixed list of known companies via ATS APIs and hash-diffed their
> postings daily. It wasn't earning its keep, so it's been moved to
> [`archive/`](archive/) and its workflow no longer runs. The discovery agents
> below are what the search actually needs. The rules-vs-model reasoning it
> illustrated is preserved in the section below, since it's the design point
> the whole system is built around.

## Rules vs. model — the split the system is built on

Job search has two different problems that don't need the same tool:

- **"Did anything change at a company I already know?"** — high frequency,
  structured data, no ambiguity. This is a rules problem — no LLM needed. This
  was Level A (`monitor.py`, now retired): plain HTTP calls to ATS JSON APIs,
  hashed and diffed against the last known state.
- **"What companies should I even be watching?"** — open-ended, needs
  judgment and live web search. This is a model problem. This is what the
  active agents do.

The point that survives the monitor's retirement: don't pay model latency and
token cost to re-check the same known companies every day when a plain API diff
does it for free. Decide what actually needs a model, then put a budget and a
check on it.

| | `scout.py` (Level B) | `scout_company.py` (Level C) |
|---|---|---|
| Job | Discover companies hiring PMs | Discover companies worth tracking |
| Method | Claude (Sonnet) + web search tool | Exa semantic search + Claude (Sonnet) scoring |
| Cadence | 5x/week (weekdays) | 3x/week (Mon/Wed/Fri) + on demand |
| Cost | Bounded (see below) | Bounded (see below) |
| Trigger | New company matching the profile | Company scoring over threshold |

Both paths land in the same place: a Telegram message, only when there's
something worth seeing.

## Level C — Company Scout (`scout_company.py`)

`scout.py` looks for **open roles**. Company Scout looks
for **companies worth tracking even when they have no vacancy right now** — so
they're already on the radar the day they do start hiring.

Pipeline: [Exa](https://exa.ai) semantic search (18 rotating queries, one per
run) → dedupe by normalized domain against `known_companies.json` → Claude
Sonnet scores each *new* company 0–10 against an editable profile → companies
scoring `>=` the threshold go to Telegram; every scored company (any score) is
written to the state file so it's never re-scored.

Design choices worth calling out:

- **Semantic, not keyword.** Exa is a neural search engine, so the queries are
  rich natural-language descriptions of the ideal page, and the company
  queries use Exa's real `category: "company"` field.
- **Dedupe on domain, not name.** `overstory.ai`, `www.overstory.ai` and
  `overstory.ai/careers` all normalize to one key — name-based dedupe fails on
  "Overstory" vs "Overstory Inc.".
- **An LLM filter, because search can't tell product from services.** A SaaS
  company and a consulting agency describe themselves almost identically;
  only a model reading the page can separate them. That's one of two hard
  filters (the other is fintech, out of scope for this candidate); everything
  else is a soft signal for the score.
- **Live domain check before anything reaches Telegram.** Companies clearing
  the score threshold get their domain HTTP-checked (https then http) before
  being sent — Exa's semantic search sometimes surfaces stale or parked
  pages, and a company whose site doesn't resolve gets flagged in the message
  rather than presented as a clean hit.
- **The profile lives in `company_profile.md`, not the code.** Edit that one
  file to widen or narrow the funnel — the score threshold is a constant in
  `scout_company.py` (starts at 6, since the seed profile is deliberately broad).
- **Scheduled, plus on demand.** After running manually for a while to
  compare against Level B, the workflow now also fires on a cron: Mon/Wed/Fri
  at 10:00 Europe/Madrid time. GitHub Actions cron is always UTC and doesn't
  track DST on its own, so the workflow schedules both UTC times 10:00 Madrid
  can land on and has a step that checks the actual local hour and skips the
  run unless it's really 10:00 there — see `.github/workflows/scout_company.yml`.
  `workflow_dispatch` still works for a manual run any time.

## Cost & latency, as an explicit design choice

The LLM path is the expensive one, so it's the one with a budget:

- **3 rotating search queries per run**, drawn from a bank of 32 and cycled
  via persisted state (`scout_state.json`) — not 20 queries every week.
- **Capped output tokens** (2000) and a **mid-tier model** (Sonnet, not
  Opus) — discovery doesn't need the largest model, it needs decent judgment
  over search results.
- **Fixed, sparse schedule, not continuous.** Level B runs weekdays, Level C
  runs Mon/Wed/Fri — both fixed cadences, not "whenever something might have
  changed."

The retired rules path (`monitor.py`, now in [`archive/`](archive/)) had
effectively zero marginal cost per run: plain HTTP calls to ATS JSON APIs,
hashed and diffed against the last known state, no model in the loop at all.
That's the reference point for why the model paths get a budget — the cheap
work should never touch a model.

### What it actually costs

Real numbers, pulled from the Anthropic Console cost dashboard for Aug 1–25,
2026 (both scripts share one API key, Claude Sonnet — `claude-sonnet-5` — at
$2/$10 per 1M input/output tokens, web search at $10 per 1,000 searches) —
not a ceiling estimate, an actual bill:

- **Total for the 25 days: $17.65** ($15.16 in tokens, $2.49 in web search).
- **Aug 15 alone: $5.53** — 31% of the entire 25-day bill, in one run. That's
  the day an open-ended search loop got away from itself, before the
  `max_uses` cap on `scout.py`'s web search tool existed (see the comment
  next to `max_uses` in `scout.py` for the full story).
- **Every other day: ~$0.81 on average**, $1.84 max. Splitting before/after
  the fix: **$0.97/day average before** the search cap went in, **$0.56/day
  average after** — a ~42% drop, and no repeat of the Aug 15 spike since.
- **Steady-state, no incidents:** roughly **$15–20/month** — still well under
  most SaaS subscriptions for something that replaces hours of manual
  scrolling every week, but noticeably more than a back-of-envelope ceiling
  would suggest. The lesson: measure the real bill, don't just trust the caps
  in the code.

## Guardrails

- **Every URL the model returns gets a live HTTP check** before it's sent to
  me — LLMs confidently return job-posting links that don't resolve, and I'd
  rather see nothing than a dead link.
- **"Confirmed" vs. "unconfirmed" status on every find:** Scout finds roles
  via live web search, not a real-time ATS API, so it can surface listings
  that are already closed. A result is only tagged confirmed if the model
  says it saw a live application page AND the URL check finds no
  "no longer accepting applications" / "position filled" language on the
  page (a 200 status alone doesn't mean the role is still open). Anything
  else gets a ⚠️ "not confirmed" tag in the Telegram message instead of
  being dropped, since the company itself is still a useful signal.
- **Strict JSON-only prompting** with regex extraction and fallback parsing,
  because free-text responses from a "return JSON" prompt still sometimes
  wrap it in prose.
- **State as memory:** `seen_companies.json` / `seen_jobs.json` /
  `scout_state.json` are the entire persistence layer — no database. The
  GitHub Actions workflow commits updated state back to the repo after every
  run, so the repo itself is the source of truth between runs.

## Stack

Python, `requests`, the Anthropic Messages API (`web_search` tool),
Telegram Bot API, GitHub Actions (cron + `workflow_dispatch`).

## Scope note

This was built for my own search, so `scout.py`'s matching profile and
`company_profile.md`'s scoring rubric are tuned to my specific target — Senior/Lead PM
or Head of Product at Series A-C B2B SaaS startups (any vertical: industrial /
construction-tech / drone & CV SaaS, but also HR tech, devtools, cybersecurity,
supply chain, legal tech, climate tech, etc. — excluding fintech, which needs
domain-specific knowledge the candidate doesn't have) — not general-purpose.
The part that generalizes is the architecture: the rules-vs-model split, the
cost/latency budget on the LLM path, and the eval guardrail on model output.
That's the same reasoning I'd apply to designing any agentic workflow — decide
what actually needs a model, then put a budget and a check on it.

## Running it

Requires `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and `ANTHROPIC_API_KEY` as
environment variables / GitHub Actions secrets — both scripts call Claude.

`scout_company.py` additionally needs `EXA_API_KEY`.

```
pip install -r requirements.txt
python scout.py            # weekdays: discover companies hiring PMs
python scout_company.py    # Mon/Wed/Fri + on demand: discover companies worth tracking
```

(`monitor.py` — the retired Level A monitor — lives in [`archive/`](archive/)
and is no longer wired to a workflow.)
