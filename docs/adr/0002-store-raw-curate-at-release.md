# Store raw, curate at Release

## Status

accepted

## Context

The corpus admission policy (Portuguese language, 100–4000 char bounds, and
Catholic / Afro-Brazilian / non-protestant keyword exclusions) was specified in
`filters.yaml` but never enforced. We want it enforced without (a) re-scraping
whenever the policy changes, or (b) losing the ability to audit what was
excluded and why.

## Decision

Scraping stores every collected **Song** and its **Lyrics** in the SQLite store,
recording detected language and length. **Admission** is a *pure function*
applied at **Release** time, not at scrape time. A Release contains only
admitted Lyrics; the store retains everything.

## Considered options

- **Curate at ingest** — apply Admission during scraping and store only admitted
  Lyrics. The store would equal the product (smaller, simpler to reason about),
  but every policy change forces a full re-scrape, rejected data is
  unrecoverable, and Admission logic is welded into the scrape loop and hard to
  test in isolation.

## Consequences

- The store intentionally contains non-gospel rows (e.g. Catholic songs the
  Source filed under "gospel"). This is expected, not a bug.
- Admission is a single deep, pure module whose interface is its own test
  surface; re-curation is free and requires no network access.
- The schema must let admission be computed at export — store language and
  length alongside the raw content.
- A Release is a curated projection of the Corpus, so Release size < store size.
