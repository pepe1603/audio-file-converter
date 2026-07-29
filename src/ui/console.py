"""Utilidades de consola Rich."""

from rich.console import Console
from rich.panel import Panel
from rich import box

console = Console()


def print_banner(app_name: str, version: str, username: str, device: str, total: int) -> None:
    banner = f"""
[bold cyan]{app_name}[/bold cyan]
[green]Versión {version}[/green]
[dim]Usuario: {username} | Dispositivo: {device}[/dim]
[dim]Total de conversiones: {total}[/dim]
"""
    console.print(Panel(banner.strip(), box=box.DOUBLE_EDGE, expand=False))


def print_success(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_info(message: str) -> None:
    console.print(f"[cyan]{message}[/cyan]")
