# Working conventions for this repo

- **No feature branches / PRs for routine changes.** This is a solo personal
  project — commit and push directly to `main`. Skip opening a PR unless the
  user explicitly asks for one.
- If a Claude Code on the web / Cowork session is auto-assigned its own
  session branch (that assignment is done by the platform, not this file, so
  it can't be turned off from here), merge that branch's commits into `main`
  and push `main` directly before ending the session, rather than leaving an
  unmerged branch/PR for the user to merge by hand.
- Ordinary commit + push to `main` is pre-authorized by this file — no need
  to ask before each one. Still confirm before anything destructive (force
  push, `git reset --hard`, rewriting published history) per the general
  safety rules.
