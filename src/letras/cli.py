import asyncio
import os
from pathlib import Path

import click
from rich.console import Console

from letras.config.config import Config
from letras.infrastructure.database.connection import PostgresConnection
from letras.runners.full import FullRunner
from letras.runners.incremental import IncrementalRunner

console = Console()


def setup_output_dir(output_dir: str) -> Path:
    """Create and validate output directory"""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_async(coro):
    """Run async function in new event loop"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@click.group()
def cli():
    """Letras - Gospel lyrics scraper"""
    pass


@cli.command()
@click.option(
    "--verbose", "-v", is_flag=True, default=True, help="Show detailed output"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="data",
    help="Output directory for files",
)
def full(verbose: bool, output: str):
    """Run full scraping of all artists"""
    try:
        output_dir = setup_output_dir(output)
        settings = Config.get_settings()

        runner = FullRunner(
            db_config={
                "host": settings.db_host,
                "port": settings.db_port,
                "database": settings.db_name,
                "user": settings.db_user,
                "password": settings.db_password,
            },
            base_url=settings.base_url,
            verbose=verbose,
        )

        async def run():
            try:
                await runner.initialize()
                await runner.run(output_dir=str(output_dir))
            finally:
                await runner.close()

        run_async(run())

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()


@cli.command()
@click.option(
    "--verbose", "-v", is_flag=True, default=True, help="Show detailed output"
)
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="data",
    help="Output directory for files",
)
def incremental(verbose: bool, output: str):
    """Run incremental update using existing database"""
    try:
        output_dir = setup_output_dir(output)
        settings = Config.get_settings()

        runner = IncrementalRunner(
            db_config={
                "host": settings.db_host,
                "port": settings.db_port,
                "database": settings.db_name,
                "user": settings.db_user,
                "password": settings.db_password,
            },
            base_url=settings.base_url,
            verbose=verbose,
        )

        async def run():
            try:
                await runner.initialize()
                await runner.run(output_dir=str(output_dir))
            finally:
                await runner.close()

        run_async(run())

    except Exception as e:
        console.print(f"[red]Error:[/red] {str(e)}")
        raise click.Abort()


@cli.command()
def init():
    """Initialize database schema"""
    try:
        settings = Config.get_settings()
        db = PostgresConnection(
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
        )

        async def run():
            try:
                await db.initialize()
                console.print("[green]Database initialized successfully[/green]")
            finally:
                await db.close()

        run_async(run())

    except Exception as e:
        console.print(f"[red]Error initializing database:[/red] {str(e)}")
        raise click.Abort()


def main():
    """CLI entry point"""
    try:
        cli()
    except Exception as e:
        console.print(f"[red]Fatal error:[/red] {str(e)}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
