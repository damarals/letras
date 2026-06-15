# Serverless persistence: a versioned SQLite file, no database server

## Status

accepted

## Context

`letras` is a personal, scheduled scraper that ships a curated Brazilian
gospel-lyrics corpus as periodic dataset releases. The original design ran an
ephemeral PostgreSQL instance inside CI and recovered prior state by restoring
the previous release's `pg_dump` on every run — a large, fragile mechanism (it
left the incremental path broken) standing in for what is really just "load the
corpus and ask what we have already seen."

## Decision

Remove the database server entirely. The corpus is a single **SQLite** file that
is the system of record. Scraping reads and upserts into it directly; releases
are *exports* derived from it (a `.sql` dump, plus Parquet/CSV for downstream
consumers). There is no always-on database, no backup/restore step, and no
environment-specific DB host or credentials.

## Considered options

- **Managed Postgres (Neon/Supabase).** Cleaner path to a future live API, but
  adds a service to maintain, secrets, free-tier expiry risk, and cost —
  rejected against the "low-maintenance, $0" goal.
- **Keep ephemeral Postgres restored from the release dump.** The status quo;
  the source of fragility we are removing.
- **DuckDB / Parquet as system of record.** Optimizes the analytical/ML read
  path, but is weaker for the transactional upsert + `slug` point-lookups the
  scrape loop needs. We get those formats anyway as exports from SQLite, which
  keeps the deferred ML/dataset north-star open.

## Consequences

- The entire ephemeral-DB + `pg_dump`/restore + `IncrementalRunner` restore
  machinery is deleted.
- The repository becomes a SQLite adapter; the relational schema, unique
  constraints, and `ON CONFLICT` upserts carry over almost unchanged.
- "Where the SQLite file lives between runs" is a separate decision.
- A future API would read this file (or a copy), not a live DB — an accepted
  constraint, since the north-star deferred that.
