# Packaging Job Scout for someone else to use

Written 2026-09-06, after a request from someone who saw the AI-tinkerers
presentation. This is a decision doc, not an implementation — nothing in the
running agent has changed.

## What "packaged" has to overcome

The agent works, but it is welded to one person. Four things block a second user:

1. **The candidate profile is inside the code.** `scout.py` holds the CV
   (`PROFILE`) and all 32 search queries as Python constants. Someone else has to
   edit source to use it. `scout_company.py` already got this right — it reads
   `company_profile.md` at runtime — so the fix is "make `scout.py` behave like
   `scout_company.py`", not new architecture.
2. **The repo is full of personal search data.** `known_companies.json` (39 KB of
   scored findings), `seen_companies.json`, and `augury_profile.md` — which names
   companies applied to and references visa constraints. **32 of the 65 commits
   touch these files**, so deleting them in a new commit does not remove them; they
   stay in git history. Any shared copy must start from a fresh `git init`, not a
   fork or a branch of this repo.
3. **Setup has two walls.** Creating a Telegram bot and finding a numeric
   `chat_id` is the classic place non-developers stall. And a fork gets scheduled
   workflows disabled by default, so the cron silently never fires.
4. **It costs real money on someone else's card.** ~$15–20/month steady state,
   and one un-capped run burned $5.53 in a day before `max_uses` existed. Shipping
   this without a spend limit in the setup instructions is the actual risk.

## The options, cheapest first

### Option 0 — Send the repo read-only, don't package
Give him the link and the README, which already explains the rules-vs-model split
and the real cost numbers. He reads the architecture; he doesn't run it.
**Effort: ~0.** Good if what impressed him at the talk was the *design*, which is
the part that generalizes — the profile and queries never will.

### Option 1 — "Use this template" repo  ← recommended
A separate public repo, fresh history, personal data gone, profile in a config
file, one setup guide, one self-check command. He clicks *Use this template*, adds
4 secrets, edits `profile.md`, done.
**Effort: ~6–9 hours** (1–2 evenings with Claude Code).

Deliberately a **template, not a fork**: GitHub disables scheduled workflows on
forks by default, and cron on a fork dies after 60 days of inactivity. *Use this
template* makes a normal repo where Actions behave normally — and it starts a
clean history, which is also how the personal data stays out.

Task breakdown:

| # | Task | Effort |
|---|---|---|
| 1 | New repo, clean initial commit, strip `augury_profile.md`, reset all four JSON state files | 30 min |
| 2 | Move `scout.py`'s `PROFILE` + `SEARCH_QUERIES` out of code into `profile.md` + `queries.txt` | 1–2 h |
| 3 | Rewrite `company_profile.md` as a generic, non-personal example | 45 min |
| 4 | `--check-setup` flag: validate all 4 secrets, send one test Telegram message, make one cheap API call | 1–2 h |
| 5 | `SETUP.md` — BotFather walkthrough, getting `chat_id`, the 4 secrets, enabling Actions | 1–2 h |
| 6 | Config for timezone + schedule + score threshold (drop the hardcoded `Europe/Madrid` DST hack) | 1 h |
| 7 | Cost guardrails: Anthropic Console spend limit as a *required* setup step, keep `max_uses` | 30 min |
| 8 | MIT `LICENSE`, pinned `requirements.txt` | 15 min |

Item 4 is the highest-value one. A working `--check-setup` removes most of the
"it doesn't work and I don't know why" support traffic that otherwise lands back
on you.

### Option 2 — Public open source
Everything in Option 1, plus: queries that aren't PM-and-industrial-specific,
a second worked profile example, `CONTRIBUTING.md`, issue templates, graceful
failure when a service is down, and a support posture for strangers filing issues.
**Effort: +2–3 days on top of Option 1.** Only worth it if you want the repo as a
public portfolio piece — which, given it came out of a talk, is a plausible goal.

### Option 3 — Hosted product other people sign up for
Multi-tenant storage (the repo-as-database trick stops working the moment there
are two users), auth, billing — otherwise you pay everyone's Anthropic bill — and
GDPR obligations, because CV-shaped data becomes personal data you now process for
others. **Effort: weeks-to-months, and an ongoing operational commitment.** This is
a different product, not a packaging job. Not recommended off one conversation.

## What not to build

**A CLI (`pip install`) or a Docker image.** Both sound tidier and are worse here.
The whole reason this thing costs nothing to run is that GitHub Actions supplies
the scheduler *and* the repo supplies the database. Package it as a CLI or a
container and the user has to bring their own cron and their own storage — you'd
be handing them a harder problem than the one you solved. Ship the pattern that
already works.

## Recommendation

**Option 1, and it's reversible.** Everything in it is also step one of Option 2,
so if the reaction is good, going public later is an increment rather than a
rewrite. If the reaction is "neat, thanks" and nothing more, you've spent one
evening instead of three days.

Before starting, one thing genuinely can't be answered from here and shouldn't be
guessed: **whether he wants to run it, or wants to understand how it was built.**
Those are Option 1 and Option 0 respectively, and the difference is a full evening
of work. Worth one message to him first.

## Two things to be honest about in whatever ships

- **The bill is his.** ~$15–20/month, an Anthropic key and an Exa key required.
  Say it in the first paragraph of the README, not the appendix.
- **The results are only as good as the profile.** The scoring rubric is the
  product; the code is plumbing. A packaged version that ships without teaching
  someone how to write a good `profile.md` will look like it doesn't work.
