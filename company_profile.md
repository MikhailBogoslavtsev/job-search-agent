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

### Second lane — AI-native / agentic B2B SaaS (not physical-ops)

There's a real secondary lane that sits outside the physical-operations list
above and is just as interesting: AI-native / agentic B2B SaaS **product**
companies. Score these on the same footing as the physical-ops lane. It
includes:

- **Data infrastructure for AI** — the tooling and data layer that AI products
  are built on (e.g. Encord, Skild AI).
- **AI-native product-builder roles** — companies where the product itself is
  AI-native and the PM is expected to build with it (e.g. Smartcat, Hostaway's
  AI platform team).
- **"Prototype with AI tools yourself" as a stated requirement**, not just a
  nice-to-have — treat that as a strong positive signal.

This lane is evidenced by where a lot of my applications and best-fit
interviews actually landed (e.g. Smartcat, Fundraise Up) — often here rather
than in construction / industrial specifically. Do not down-score a company
just because it isn't in the physical-ops domains.

## The one hard filter

**Product company, not a services / outsourcing / consulting agency.**
If the company mainly sells people's time (custom development shops, staffing,
system integrators, "we build your MVP" agencies), it is NOT a fit — score it
low and set `is_product_company` to false, regardless of how interesting the
domain sounds. A real product/SaaS/platform company that sells a repeatable
product is what I want.

## Soft signals (raise the score, but none is a gate on its own)

- Applies AI / computer vision / ML / imagery / sensor / automation to a
  physical, real-world operation (not purely digital/online workflows).
- Sells B2B to field teams, operators, engineers, contractors, or industrial
  customers.
- **Stage:** prefer Seed–Series B. I'll stretch for a strong domain match —
  I've applied to later-stage / public companies (Autodesk, Trimble, Hostaway,
  Neura Robotics) when the *product itself* was a tight fit. Those are
  exceptions, not the target, so a later-stage company should only score well
  when the product match is genuinely strong.
- **Level / role fit** (useful when the page is a job posting): Head of Product
  and product-leadership titles are the target. Senior / Staff PM roles are
  acceptable as a deliberate stepping stone — but mainly when they carry real
  end-to-end ownership of a product area, not a narrow single-feature scope.
- Product-led: a platform or SaaS product, ideally with some 0-to-1 surface.
- Remote-friendly or European is a mild plus. Location is otherwise not a
  blanket filter — but see the Geography section below for a few regions that
  do pull the score down.

## Geography (a soft signal, but a real one)

Companies **headquartered in India, China, South Korea, or Turkey** are a low
fit for me — score them **low (roughly 2–4)** — **unless** the page clearly
shows they hire **remote worldwide** (or specifically across Europe / my
region). I'm not looking to relocate to those regions or take a local-only
role there.

- Still worth recording (that's why they go in the file), just not worth a
  Telegram alert when there's no worldwide-remote signal.
- If a company from one of these regions **clearly** offers remote-worldwide or
  global roles, don't apply this penalty — score it on its merits.
- Examples seen that should score low: Kesowa, YugmiAI, Aeroyantra, FieldNerve
  (India), Eyerod (Turkey) — all with no worldwide roles.

This applies only to the regions named above. Companies elsewhere (Europe, US,
etc.) are not penalized on location.

## Not a fit

- Services / consulting / agencies (the hard filter above).
- Pure consumer apps with no B2B/operational angle.
- Talent-network / recruiting intermediaries (e.g. Hire5) — these aren't a real
  company touch, so they shouldn't pass the filter. Only surface one if it's
  genuinely the only route to a target company; otherwise score it low.

Everything not listed as the hard filter is a soft signal only. When unsure
between two scores, pick the higher one — the funnel is meant to be wide.
