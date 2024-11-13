import argparse
from rich.console import Console

from core.runner import GospelLyricsRunner

console = Console()

parser = argparse.ArgumentParser(description='Gospel Lyrics Scraper')
parser.add_argument('--verbose', '-v', type=int, choices=[0, 1], default=1,
                    help='Verbosity level (0: minimal, 1: detailed)')

try:
    args = parser.parse_args()
    runner = GospelLyricsRunner(verbose=args.verbose)
    runner.run()
    
except KeyboardInterrupt:
    console.print("[bold yellow]WARNING[/bold yellow]     [white]Proccess Interrupted by the user")
except Exception as e:
    console.print(f"[bold red]ERROR[/bold red]     [white]Error during the execution: {str(e)}")
    raise
finally:
    console.print("\n[bold blue]INFO[/bold blue]     [white]Finished Proccess!")
