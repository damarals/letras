from rich.console import Console

from core.runner import GospelLyricsRunner

console = Console()

try:
    runner = GospelLyricsRunner()
    runner.run()
    
except KeyboardInterrupt:
    console.print("[bold yellow]WARNING[/bold yellow]     [white]Proccess Interrupted by the user")
except Exception as e:
    console.print(f"[bold red]ERROR[/bold red]     [white]Error during the execution: {str(e)}")
    raise
finally:
    console.print("\n[bold blue]INFO[/bold blue]     [white]Finished Proccess!")
