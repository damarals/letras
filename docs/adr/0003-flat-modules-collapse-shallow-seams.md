# Flat capability modules; collapse single-implementation seams

## Status

accepted

## Context

The original code used a hexagonal/DDD layout: a `LyricsRepository` ABC (with a
single adapter), a `LyricsService` layer, and separate `FullRunner` /
`IncrementalRunner` classes. At this project's size these are mostly *shallow*
seams — the interface is nearly as complex as its single implementation, so the
indirection adds reading cost without leverage.

## Decision

Organize the rebuild as flat capability modules (`domain`, `source`, `store`,
`release`, `pipeline`). Specifically:

- **One concrete `CorpusStore`** (SQLite, raw SQL) — no repository port/ABC.
  Tests use in-memory SQLite.
- **One `Pipeline`** parameterized by a selection policy — no Full/Incremental
  class split.
- **`Fetcher` (HTTP) split from `Parser` (pure HTML → domain).**
- **`Admission` as a first-class pure module**, applied at export.
- **No standalone service layer**; orchestration lives in the `Pipeline`.

## Considered options

- **Retain hexagonal/DDD layering (ports + adapters + services).** Familiar and
  adapter-swappable by contract, but with a single store and a single source the
  ports are *hypothetical* seams and the service layer is largely pass-through —
  indirection that fails the deletion test.
- **Vertical slices by use-case.** Scatters the shared domain (entities, store)
  or forces a `shared/` bucket for what is a small, linear pipeline.

## Consequences

- Reintroducing a repository interface or a service layer should be a
  deliberate, justified change — e.g. when a *second* store or source actually
  appears. One adapter = hypothetical seam; add the seam when the second adapter
  is real.
- The `Parser`↔`Fetcher` split is the one seam kept deliberately: it makes
  parsing pure and fixture-testable and isolates the volatile site selectors.
