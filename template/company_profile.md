# What kind of company is worth watching?

REPLACE THIS with your own rubric. Claude reads this file and scores every
newly discovered company 0–10 against it. **Edit this file to widen or narrow
what gets flagged — you never need to touch the code.** The score a company
must reach before you hear about it is `score_threshold` in `config.json`.

This half of the tool answers a different question from the job search: not
"who is hiring right now", but "who should already be on my radar for when
they do start hiring".

## What I'm looking for

Describe the shape of company you'd want to work at — industry, product type,
who they sell to, company stage, anything that matters to you. Write it in
your own words; there's no format.

## Hard filters (score these low no matter what else fits)

**1. Product company, not a services / consulting / staffing agency.**
If the company mainly sells people's time — custom development shops,
staffing, system integrators, "we build your MVP" agencies — it is not a fit.
Score it low and set `is_product_company` to false, however interesting the
domain sounds.

**2. Add your own.** For example: an industry you have no background in and
don't want to learn. Be explicit — this is a hard gate, not a preference.

## Soft signals (raise the score, none is a gate on its own)

- Company stage you prefer, e.g. seed to Series C rather than a large incumbent
- Technology you want to work on
- Who they sell to
- Remote-friendliness, or a region you'd like

Everything not listed as a hard filter is a soft signal only. If you're
starting out, keep the funnel wide — say "when unsure between two scores, pick
the higher one" — and narrow it later once you see what comes through.
