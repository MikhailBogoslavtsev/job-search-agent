# Job Scout

A personal AI job-search agent that runs on autopilot: watch a known list of
companies for new roles, and separately go discover companies I don't know to
watch yet — without burning LLM cost on either one more than it needs.

Built solo with Claude Code + Python. Runs serverless on GitHub Actions, no
server, no database.

## Why two agents, not one

Job search has two different problems that don't need the same tool:

- **"Did anything change at a company I already know?"** — high frequency,
  structured data, no ambiguity. This is a rules problem.
- **"What companies should I even be watching?"** — open-ended, needs
  judgment and live web search. This is a model problem.

Using an LLM for both would mean paying model latency and token cost to
re-check the same ~30 known companies every day, for zero benefit over a
plain API diff. So the system is split on exactly that line:

| | `monitor.py` | `scout.py` |
|---|---|---|
| Job | Track known companies | Discover new ones |
| Method | Ashby / Greenhouse / Lever ATS APIs, hash-diffed | Claude (Sonnet) + web search tool |
| Cadence | Daily | 2x/week (Mon & Wed) |
| Cost | $0 (rules) | Bounded (see below) |
| Trigger | Any change in a known company's postings | New company matching the profile |

Both paths land in the same place: a Telegram message, only when there's
something worth seeing.

## Cost & latency, as an explicit design choice

The LLM path is the expensive one, so it's the one with a budget:

- **3 rotating search queries per run**, drawn from a bank of 20 and cycled
  via persisted state (`scout_state.json`) — not 20 queries every week.
- **Capped output tokens** (2000) and a **mid-tier model** (Sonnet, not
  Opus) — discovery doesn't need the largest model, it needs decent judgment
  over search results.
- **Twice-weekly cadence** (Mon & Wed), vs. the deterministic monitor's daily
  cadence — the free path runs every day, the paid path runs on a fixed,
  sparse schedule.

The rules path (`monitor.py`) has effectively zero marginal cost per run:
plain HTTP calls to ATS JSON APIs, hashed and diffed against the last known
state. No model in the loop at all for the 90% of "check if anything
changed" work.

## Guardrails

- **Every URL the model returns gets a live HTTP check** before it's sent to
  me — LLMs confidently return job-posting links that don't resolve, and I'd
  rather see nothing than a dead link.
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
`monitor.py`'s company list are tuned to my specific target (industrial /
construction-tech / drone & CV SaaS) — not general-purpose. The part that
generalizes is the architecture: the rules-vs-model split, the cost/latency
budget on the LLM path, and the eval guardrail on model output. That's the
same reasoning I'd apply to designing any agentic workflow — decide what
actually needs a model, then put a budget and a check on it.

## Running it

Requires `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, and (for `scout.py`)
`ANTHROPIC_API_KEY` as environment variables / GitHub Actions secrets.

```
pip install -r requirements.txt
python monitor.py   # daily: check known companies
python scout.py     # Mon/Wed: discover new ones
```
