# Letras — Target Architecture

The rebuild design. Domain language is in [CONTEXT.md](../CONTEXT.md); the
hard-to-reverse decisions are in [docs/adr](./adr). This document is the
synthesis and the implementation plan.

## North-star

Same product — a curated Brazilian gospel-lyrics **Corpus** shipped as periodic
**Release**s — rebuilt for reliability, testability, and AI-navigability. No new
product surface (no live API/app); the design keeps that door open but does not
build it.

## Key decisions (see ADRs)

- **ADR-0001** — serverless; one **SQLite** file is the system of record; no DB server.
- **ADR-0002** — store raw, apply **Admission** at Release time.
- **ADR-0003** — flat capability modules; collapse single-implementation seams.
- **ADR-0004** — stateless app; latest Release asset is state; CI does release I/O.

## Module map

```
src/letras/
  domain/
    entities.py      Artist, Song, Lyrics  (frozen dataclasses; no views)
    policy.py        AdmissionPolicy  (typed, loaded from filters.yaml)
    admission.py     pure: admit(lyrics, song, artist, policy) -> Verdict
  source/
    fetcher.py       HTTP side effects: httpx, retries, rate-limit, thread pool
    parser.py        pure: HTML -> domain objects (the volatile seam)
  store/
    corpus_store.py  CorpusStore: sqlite3 + raw SQL (concrete, no ABC)
  release/
    exporter.py      stamp `admitted`, copy .db, write .txt ZIP + notes
    notes.py         render RELEASE_NOTES.md
  pipeline.py        run(mode): discover -> select -> scrape -> store
  config.py          pydantic-settings + policy loader
  cli.py             typer: run / export / stats
```

### Deep modules and their seams

- **`parser.py` (pure).** Interface: `parse_artist_index(html) -> list[Artist]`,
  `parse_artist_songs(html, artist) -> list[Song]`, `parse_song(html) ->
  ParsedSong`. All site-specific selectors live here; it is the test surface
  (HTML fixtures in → entities out, no network). The deliberate seam against
  `fetcher.py`.
- **`fetcher.py` (effects).** Interface: `artist_index()`, `artist_page(slug)`,
  `song_page(artist_slug, song_slug)` returning HTML. Owns httpx, `tenacity`
  retries, a politeness delay, and a bounded `ThreadPoolExecutor` for the `full`
  reconcile. Tested with `httpx.MockTransport`.
- **`admission.py` (pure).** Interface: `admit(...) -> Verdict(admitted: bool,
  reason: str | None)`. The domain's center; table-driven unit tests.
  Accent-normalized, word-boundary keyword matching (not naive substring).
- **`corpus_store.py` (effects, deep).** Interface: `known_artist_slugs()`,
  `known_song_slugs(artist_id)`, `upsert_artist/song/lyrics`,
  `iter_for_admission()`, `set_admitted(song_id, bool)`, `iter_admitted()`.
  Raw SQL hidden inside; tests run on `:memory:`.
- **`pipeline.py`.** Interface: `run(mode, fetcher, store, policy)`. The only
  full-vs-incremental difference is the selection predicate.

## Data model (SQLite)

```sql
CREATE TABLE artists (
  id         INTEGER PRIMARY KEY,
  name       TEXT NOT NULL,
  slug       TEXT NOT NULL UNIQUE,
  first_seen TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE songs (
  id         INTEGER PRIMARY KEY,
  artist_id  INTEGER NOT NULL REFERENCES artists(id),
  name       TEXT NOT NULL,
  slug       TEXT NOT NULL,
  first_seen TEXT NOT NULL DEFAULT (datetime('now')),
  UNIQUE (artist_id, slug)
);

CREATE TABLE lyrics (
  song_id    INTEGER PRIMARY KEY REFERENCES songs(id),   -- 1:1
  content    TEXT NOT NULL,
  language   TEXT,                                        -- detected, e.g. 'pt'
  char_count INTEGER NOT NULL,
  admitted   INTEGER NOT NULL DEFAULT 0,                  -- stamped at release
  scraped_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_songs_artist ON songs(artist_id);
```

Changes vs today: `views` dropped; `added_date` → `first_seen`; `language`,
`char_count`, `admitted` added so Admission is computable at export. The curated
**Corpus** is `lyrics WHERE admitted = 1`.

## Data flow

**Incremental (weekly):**
1. CI: `gh release download` → `in.db` (or empty on first run).
2. `letras run --incremental --corpus in.db --out dist/`
3. Pipeline: fetch+parse artist index → for each artist, fetch songs, select
   those whose `slug` is unknown → fetch+parse lyrics → detect language, count
   chars → upsert **raw** into the store.
4. `letras export --corpus in.db --out dist/`: run Admission over all lyrics →
   `set_admitted` → copy `.db` to `dist/corpus.db` → write
   `dist/lyrics-<date>.zip` (admitted `.txt` only) → write
   `dist/RELEASE_NOTES.md`.
5. CI: `gh release create v<date> dist/*`.

**Full (manual):** identical, but the selection predicate is "all songs," so
existing entries are re-scraped and their content refreshed.

## Stack

Python 3.12+, `uv` (packaging), `httpx`, `lxml` (or `selectolax`), `lingua`
(language detection), `tenacity` (retries), `pydantic` + `pydantic-settings`,
`PyYAML` (load the now load-bearing `filters.yaml`), `typer` (CLI), `rich`
(progress), `pytest`, `ruff` (lint+format), `mypy`. Dropped: `asyncpg`,
`aiohttp`, `beautifulsoup4`, `poetry`, `black`, `isort`, `pytest-asyncio`,
`responses`.

## CI/CD

- **`test.yaml`** (push/PR): `uv sync` → `ruff check` → `ruff format --check` →
  `mypy` → `pytest --cov`. No Docker, no Postgres, no secrets; seconds, not
  minutes.
- **`incremental.yaml`** (weekly cron + dispatch): download latest `.db` → run
  incremental → export → publish dated Release.
- **`full.yaml`** (dispatch only): full reconcile.
- **`smoke.yaml`** (optional, scheduled, non-gating): fetch one known song and
  report site drift.

Deleted: `docker-compose.yaml`, `Dockerfile`, `.docker/`, and the DB parts of
`.devcontainer/`.

## Testing

- **Pure unit:** `admission` (table-driven), `parser` (committed HTML fixtures),
  `policy` loading.
- **Store:** `:memory:` SQLite round-trips, upsert idempotency, unseen-slug
  queries.
- **Pipeline:** fake fetcher + in-memory store — incremental selects only new
  songs; full re-scrapes.
- **Exporter:** temp dir; assert `.db` + ZIP + notes and `admitted` stamping.
- **Drift guards (runtime):** raise if the artist index yields 0 artists or a
  song page has no lyrics element — silent breakage becomes impossible.

## Implementation plan

Each phase ends green (lint + types + tests) before the next. Pure cores first
(TDD-friendly), effects after, wiring last.

- **Phase 0 — Tooling.** New `pyproject` on `uv`, Python 3.12, ruff/mypy config,
  dependency swap, `test.yaml`. *Verify:* `uv sync`, `ruff`, empty `pytest` green.
- **Phase 1 — Domain core.** `entities`, `policy` (+ load `filters.yaml`),
  `admission`. *Verify:* admission unit tests cover language/length/keyword
  (incl. accent + word-boundary) cases.
- **Phase 2 — Store.** `corpus_store` + schema. *Verify:* `:memory:` round-trips,
  upsert idempotency, unseen-slug queries.
- **Phase 3 — Source.** `parser` (capture real HTML fixtures once), `fetcher`
  (httpx, retries, rate-limit, thread pool), drift guards. *Verify:* parser vs
  fixtures; fetcher vs `MockTransport`.
- **Phase 4 — Pipeline + exporter.** `pipeline` (selection policy), `exporter`,
  `notes`. *Verify:* fake-fetcher pipeline tests for both modes; exporter file +
  stamping tests.
- **Phase 5 — CLI.** `typer` commands. *Verify:* `CliRunner` smoke; a real
  `--full` run into `dist/` produces the artifacts.
- **Phase 6 — CI/CD.** `incremental.yaml`, `full.yaml`, optional `smoke.yaml`;
  delete Docker/compose/devcontainer-DB. *Verify:* a manual `full` dispatch
  yields a Release with `corpus.db` + ZIP + notes.
- **Phase 7 — Cutover.** Seed the corpus with one `full` run; rewrite the README
  (fix the DuckDB drift, document `admitted = 1`, the exports, and the new
  commands); delete the old `src/`.

**Seeding the corpus:** simplest is a one-time `full` scrape to build a fresh
`.db`. Optionally, import the most recent `pg_dump` from an existing Release to
preserve `first_seen` history (one-off script) — decide at Phase 7.
