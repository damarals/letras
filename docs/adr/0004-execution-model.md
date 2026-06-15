# Execution model: a stateless app, the latest Release as state, CI-orchestrated

## Status

accepted

## Context

With no database server (ADR-0001), a scheduled run needs its prior state from
somewhere, must stay $0 and low-maintenance, and should be runnable locally for
debugging without secrets.

## Decision

- **State = the latest GitHub Release asset.** The newest Release's raw `.db` is
  the corpus state; there is no other persistent store.
- **The app is stateless and GitHub-agnostic.** It reads an input `.db` path and
  writes Release files (updated `.db`, `.txt` ZIP, `RELEASE_NOTES.md`) to an
  output directory. It makes no network calls to GitHub.
- **CI orchestrates Release I/O.** The workflow runs `gh release download`
  (fetch the prior `.db`) → `letras run` → `gh release create` (publish a dated
  Release).
- **Two modes, one pipeline.** `--incremental` (the weekly default) scrapes only
  slugs absent from the input `.db`; `--full` (manual) re-scrapes everything.
  Mode is a selection policy, not a class.

## Considered options

- Managed database / committed DB file / git LFS — see ADR-0001 and the
  state-location decision.
- **App performs its own GitHub I/O.** Couples the app to GitHub, needs a token
  to run locally, and is harder to test. Rejected to keep the app
  filesystem-in / filesystem-out.

## Consequences

- A run is reproducible locally: download any Release's `.db`, run the app,
  inspect outputs — no secrets, no services.
- The first-ever run (no prior Release) starts from an empty corpus.
- The entire GitHub coupling lives in CI YAML, not in the codebase.
