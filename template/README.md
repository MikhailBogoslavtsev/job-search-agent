# Job Scout

A job-search agent that runs itself. A few times a week it searches the web for
roles and companies that match a profile you write in plain English, checks that
what it found is real, and sends you a Telegram message — only when there's
something worth seeing.

It runs on GitHub's free servers. There is nothing to install and no server to
keep alive.

**👉 [Open the setup page](SETUP_URL) — it walks you through the whole thing in
about 20 minutes and writes your profile for you.**

You do not need to know how to code. You do need to be willing to copy and
paste a few things carefully.

---

## Before you start: what this costs

The searching is done by Claude, and **you pay for that on your own account** —
roughly **$15–20 a month** at the default schedule. It is not free and it is not
a subscription anyone bills you for; it comes off an Anthropic API balance you
top up yourself.

Two ways to keep that predictable, both worth doing:

1. **Set a spend limit** in the Anthropic Console under Billing. Do this before
   your first run, not after.
2. **Run less often.** The schedule lives in `.github/workflows/scout.yml`. Three
   days a week instead of five is roughly 40% cheaper.

There is a real story behind that warning: one un-capped run of an earlier
version burned $5.53 in a single day by searching in circles. The cap that
prevents it is `max_web_searches` in `config.json`. Don't raise it casually.

## What you'll need

| | What | Free? |
|---|---|---|
| 1 | A GitHub account | Yes |
| 2 | A Telegram account | Yes |
| 3 | An Anthropic API key | Pay as you go, ~$15–20/mo |
| 4 | An Exa API key | Optional, free tier available |

The setup page gets you all four in order.

## The two halves

**Role Scout** answers *"who is hiring right now?"* — Claude searches the web,
returns candidate roles, and every link it gives you is fetched and checked
before you see it. Links that don't resolve are dropped; roles whose page says
"no longer accepting applications" are flagged rather than presented as live.

**Company Scout** answers a different question: *"who should be on my radar for
when they do start hiring?"* — it finds companies semantically, scores each new
one 0–10 against your rubric, and only tells you about the ones that clear your
threshold. This half needs the Exa key and is entirely optional.

## The files you actually edit

Everything personal lives in these. You never touch the Python.

| File | What it does |
|---|---|
| `profile.md` | Who you are and what you want. The single most important file. |
| `queries.txt` | The web searches Role Scout runs, one per line. |
| `company_profile.md` | The rubric Company Scout scores companies against. |
| `company_queries.json` | The semantic searches Company Scout runs. |
| `config.json` | How picky, which model, how many searches per run. |

To edit any of them on GitHub: click the file, click the pencil icon, type,
click **Commit changes**. That's it — the next run picks it up.

**If the results feel wrong, the fix is almost always `profile.md`, not the
code.** A vague profile produces vague matches.

## Something's broken

Go to the **Actions** tab → **Test my setup** → **Run workflow**. It checks
every key and every file one at a time and tells you in plain language what's
wrong and where to fix it. It costs about a cent to run.

## Where your data lives

Your API keys go into GitHub's encrypted secrets, which only your own workflows
can read. Everything the scout learns is written back into your own repository —
that's the whole database. No third-party service holds anything about you.

## How it works, if you're curious

The design point worth stealing: **decide what actually needs a model, then put
a budget and a check on it.**

- Searches are **rotated, not repeated** — a few from your list each run, cycling
  through, so a long list costs no more per run than a short one.
- Output tokens are **capped**, and the model is mid-tier. Discovery needs decent
  judgment over search results, not the largest model available.
- The schedule is **fixed and sparse**, not continuous.
- Every URL is **checked live** before it reaches you. Language models return
  confident links to pages that don't exist, and it's better to see nothing than
  a dead link.
- Companies are deduplicated **by domain and by normalized name**, because the
  same company shows up as its own site, its ATS subdomain, and three
  aggregators in a single run — and as "Wingtra" one week and "Wingtra AG" the
  next.

## Licence

MIT — see [LICENSE](LICENSE). Use it, change it, no warranty.
