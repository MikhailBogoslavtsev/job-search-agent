# Company Scout — matching profile

This file is the scoring rubric for Level C (Company Scout). The scoring script
reads it at runtime and hands it to Claude, which scores every newly discovered
company 0–10 against it. **Edit this file to widen or narrow what gets flagged —
you never need to touch the code.**

I'm in an exploration phase and want a WIDE funnel right now. I'd rather see a
company and dismiss it than never see it. Err toward including.

## What I'm looking for

I'm interested in companies building B2B SaaS products in ANY industry —
not just construction, infrastructure, industry, energy, agriculture,
logistics and manufacturing (my own background), but also HR tech, martech,
devtools/infra, legal tech, cybersecurity, supply chain, climate/energy tech,
healthtech ops, real estate tech, and vertical AI tools generally. Applying
AI, computer vision, ML, imagery, sensor data or automation to real-world
physical operations is still a strong plus, not a requirement. I care about
product companies (SaaS / platforms), not services or consulting agencies.
Startup-stage is more interesting than large corporates. I'm open to a wide
range — err toward including a company rather than excluding it.

## The two hard filters

**1. Product company, not a services / outsourcing / consulting agency.**
If the company mainly sells people's time (custom development shops, staffing,
system integrators, "we build your MVP" agencies), it is NOT a fit — score it
low and set `is_product_company` to false, regardless of how interesting the
domain sounds. A real product/SaaS/platform company that sells a repeatable
product is what I want.

**2. Not fintech.** Fintech (banking, payments, lending, trading, insurance
infrastructure, etc.) requires domain-specific regulatory/financial knowledge
I don't have — score fintech companies low even if everything else about them
fits.

## Soft signals (raise the score, but none is a gate on its own)

- **Top-priority archetype: the "Augury cluster" — industrial AI with
  agents/copilots for plant & operations personas.** Companies building
  AI-native (ideally *agentic* — copilots, LLM agents, applied ML on
  operational data) products for manufacturing, plants, factories, field
  service or heavy-asset operations, sold to process engineers, reliability
  engineers, maintenance planners, operations leaders or plant managers.
  This is the strongest fit of all — score these highly and flag them
  clearly. Bonus when they unify fragmented industrial data sources
  (historians, CMMS, MES, ERP, sensors, CAD). Examples of the shape:
  Augury, Tractian, Cognite, Uptake, Sight Machine, Tulip Interfaces,
  MaintainX, Seeq, Samotics. See `augury_profile.md` for the full archetype
  and target cluster.
- **Specific area of strong interest: AI-driven supply chain planning and
  optimization platforms** (demand forecasting, inventory/network
  optimization, logistics planning, procurement optimization, etc.). Flag
  these clearly and score them highly.
- Any B2B SaaS vertical — industrial/physical-operations domains are a plus
  but not required.
- Applies AI / computer vision / ML / imagery / sensor / automation to a
  physical, real-world operation.
- Sells B2B to field teams, operators, engineers, contractors, or industrial
  customers.
- Startup stage (seed to Series C) rather than a large incumbent.
- Product-led: a platform or SaaS product, ideally with some 0-to-1 surface.
- Remote-friendly or European is a mild plus — but do NOT filter by country.
- It can be consumer product also but less priority because most probably my domain will not fit

## Not a fit

- Services / consulting / agencies (hard filter 1).
- Fintech (hard filter 2).

Everything not listed as a hard filter is a soft signal only. When unsure
between two scores, pick the higher one — the funnel is meant to be wide.
