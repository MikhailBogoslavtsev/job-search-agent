# Company Scout — matching profile

This file is the scoring rubric for Level C (Company Scout). The scoring script
reads it at runtime and hands it to Claude, which scores every newly discovered
company 0–10 against it. **Edit this file to widen or narrow what gets flagged —
you never need to touch the code.**

I'm in an exploration phase and want a WIDE funnel right now. I'd rather see a
company and dismiss it than never see it. Err toward including.

## What I'm looking for

I'm interested in companies building software products that apply AI, computer
vision, machine learning, imagery, sensor data or automation to real-world
physical operations — across construction, infrastructure, industry, energy,
agriculture, logistics, manufacturing, and adjacent domains. I care about
product companies (SaaS / platforms), not services or consulting agencies.
Startup-stage is more interesting than large corporates. I'm open to a wide
range — err toward including a company rather than excluding it.

## The one hard filter

**Product company, not a services / outsourcing / consulting agency.**
If the company mainly sells people's time (custom development shops, staffing,
system integrators, "we build your MVP" agencies), it is NOT a fit — score it
low and set `is_product_company` to false, regardless of how interesting the
domain sounds. A real product/SaaS/platform company that sells a repeatable
product is what I want.

## Soft signals (raise the score, but none is a gate on its own)

- Applies AI / computer vision / ML / imagery / sensor / automation to a
  physical, real-world operation.
- Sells B2B to field teams, operators, engineers, contractors, or industrial
  customers.
- Startup stage (seed to Series C) rather than a large incumbent.
- Product-led: a platform or SaaS product, ideally with some 0-to-1 surface.
- Remote-friendly or European is a mild plus — but do NOT filter by country.
- It can be consumer product also but less priority because most probably my domain will not fit

## Not a fit

- Services / consulting / agencies (the hard filter above).

Everything not listed as the hard filter is a soft signal only. When unsure
between two scores, pick the higher one — the funnel is meant to be wide.
