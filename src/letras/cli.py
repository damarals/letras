"""Command-line surface. Thin adapter over the pipeline and exporter."""

from datetime import UTC, datetime
from pathlib import Path

import typer

from letras.config import Settings
from letras.domain.policy import load_policy
from letras.pipeline import run as scrape
from letras.release.exporter import export_release
from letras.source.fetcher import Fetcher
from letras.source.rate_limiter import RateLimiter
from letras.store.corpus_store import CorpusStore

app = typer.Typer(help="Letras — gospel lyrics corpus scraper", no_args_is_help=True)


def _build_fetcher(settings: Settings) -> Fetcher:
    """Construct a Fetcher wired with the shared, adaptive rate limiter."""
    limiter = RateLimiter(
        rate=settings.requests_per_second,
        min_rate=settings.min_requests_per_second,
        max_rate=settings.max_requests_per_second,
        increase_step=settings.rate_increase_step,
        backoff_factor=settings.backoff_factor,
        jitter=settings.jitter,
    )
    return Fetcher(
        settings.base_url,
        delay=settings.delay,
        max_attempts=settings.max_attempts,
        http2=settings.http2,
        max_connections=settings.max_connections,
        max_keepalive_connections=settings.max_keepalive_connections,
        keepalive_expiry=settings.keepalive_expiry,
        rate_limiter=limiter,
    )


@app.command()
def run(
    incremental: bool = typer.Option(
        False, help="Scrape only songs not already in the corpus"
    ),
    artist: str | None = typer.Option(None, help="Scrape only this artist slug"),
    corpus: Path = typer.Option(Path("corpus.db"), help="Corpus SQLite file"),
    max_songs: int | None = typer.Option(None, help="Cap songs per artist (debug)"),
) -> None:
    """Scrape the source into the corpus store."""
    settings = Settings()
    fetcher = _build_fetcher(settings)
    store = CorpusStore(corpus)
    try:
        scrape(
            fetcher,
            store,
            workers=settings.max_workers,
            incremental=incremental,
            only_slug=artist,
            max_songs=max_songs,
        )
    finally:
        fetcher.close()
        store.close()


@app.command()
def export(
    corpus: Path = typer.Option(Path("corpus.db"), help="Corpus SQLite file"),
    out: Path = typer.Option(Path("dist"), help="Output directory for the Release"),
) -> None:
    """Build a Release (corpus.db + .txt ZIP + notes) from the corpus."""
    store = CorpusStore(corpus)
    try:
        date = datetime.now(UTC).strftime("%Y%m%d")
        export_release(store, corpus, out, date=date, policy=load_policy())
    finally:
        store.close()
