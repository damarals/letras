"""Command-line surface. Thin adapter over the pipeline and exporter."""

from datetime import UTC, datetime
from pathlib import Path

import typer

from letras.domain.policy import load_policy
from letras.pipeline import run as scrape
from letras.release.exporter import export_release
from letras.source.fetcher import Fetcher
from letras.store.corpus_store import CorpusStore

app = typer.Typer(
    help="Letras — gospel lyrics corpus scraper", no_args_is_help=True
)


@app.command()
def run(
    artist: str | None = typer.Option(None, help="Scrape only this artist slug"),
    corpus: Path = typer.Option(Path("corpus.db"), help="Corpus SQLite file"),
    max_songs: int | None = typer.Option(None, help="Cap songs per artist (debug)"),
) -> None:
    """Scrape the source into the corpus store."""
    fetcher = Fetcher()
    store = CorpusStore(corpus)
    try:
        scrape(fetcher, store, only_slug=artist, max_songs=max_songs)
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
