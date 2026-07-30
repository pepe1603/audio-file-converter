"""Utilidades de consola Rich."""

import random
import shutil
from datetime import datetime
from typing import Optional

from rich.align import Align
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()

_EXIT_QUOTES = (
    "El silencio también es un formato. Hasta la próxima pista.",
    "Tu onda queda en el aire. AFC se retira con clase.",
    "Conversión completa. El maestro del audio abandona el estudio.",
    "De bits a leyenda: la sesión cierra en fade-out.",
    "Los codecs descansan. Tú no dejas de sonar.",
    "FFmpeg apaga las luces. El show fue épico.",
    "Un último sample… y cortamos. Excelente sesión.",
    "No es un adiós: es un stop con estilo.",
    "Calidad legendaria no se improvisa. Se convierte.",
    "El espectro se desvanece. Vuelve cuando quieras masterizar.",
)

_ENTER_QUOTES = (
    "Los bits despiertan. La leyenda del audio entra en escena.",
    "FFmpeg en caliente. Hoy convertimos historia.",
    "Del silencio al master: la sesión acaba de empezar.",
    "Tu estudio portátil está listo. Que suene limpio.",
    "Una pista, mil formatos. Elige tu destino.",
    "El espectro se enciende. Bienvenido al convertidor.",
    "Calidad primero. Velocidad después. Estilo siempre.",
    "USB, carpeta o archivo: todo termina en oro sonoro.",
    "No solo conviertes archivos. Forjas leyenda.",
    "Press play on excellence. AFC online.",
)


def print_banner(app_name: str, version: str, username: str, device: str, total: int) -> None:
    """Banner compacto del menú principal."""
    banner = f"""
[bold cyan]{app_name}[/bold cyan]
[green]Versión {version}[/green]
[dim]Usuario: {username} | Dispositivo: {device}[/dim]
[dim]Total de conversiones: {total}[/dim]
"""
    console.print(Panel(banner.strip(), box=box.DOUBLE_EDGE, expand=False))


def print_entrance_banner(
    app_name: str,
    version: str,
    username: str,
    *,
    env_name: str = "",
    data_path: str = "",
    ffmpeg_ok: bool = True,
    ffmpeg_label: str = "",
    total_conversions: int = 0,
    target_console: Optional[Console] = None,
) -> None:
    """Banner de entrada flexible según ancho de terminal, tono legendario."""
    out = target_console or console
    width = _panel_width(out)
    now = datetime.now()
    hour = now.hour
    if 5 <= hour < 12:
        moment = "Buenos días"
        tone = "yellow"
        border = "yellow"
    elif 12 <= hour < 19:
        moment = "Buenas tardes"
        tone = "cyan"
        border = "bright_cyan"
    else:
        moment = "Buenas noches"
        tone = "magenta"
        border = "bright_magenta"

    quote = random.choice(_ENTER_QUOTES)
    art = _enter_art(width)
    title = Text(f"★  {app_name}  ★", style="bold bright_white")
    subtitle = Text(f"v{version}  ·  inicio de sesión", style="dim")

    status = (
        f"[green]✓ FFmpeg[/green] {ffmpeg_label}"
        if ffmpeg_ok
        else f"[red]✗ FFmpeg[/red] {ffmpeg_label or 'no disponible'}"
    )

    body_lines = [
        Text.from_markup(f"[{tone}]{moment}, [bold]{username}[/bold].[/{tone}]"),
        Text(""),
        Text.from_markup(art, justify="center"),
        Text(""),
        Text.from_markup(f"[italic bright_white]« {quote} »[/italic bright_white]"),
        Text(""),
        Text.from_markup(status),
        Text.from_markup(
            f"[green]Conversiones en historial:[/green] [bold]{total_conversions}[/bold]"
        ),
    ]
    if env_name:
        body_lines.append(Text.from_markup(f"[dim]Entorno: {env_name}[/dim]"))
    if data_path:
        body_lines.append(Text.from_markup(f"[dim]Datos: {data_path}[/dim]"))
    body_lines.append(
        Text.from_markup(f"[dim]{now.strftime('%Y-%m-%d %H:%M:%S')} · listo para convertir[/dim]")
    )

    content = Group(
        Align.center(title),
        Align.center(subtitle),
        Text(""),
        *body_lines,
    )
    out.print()
    out.print(
        Panel(
            content,
            box=box.DOUBLE_EDGE,
            border_style=border,
            padding=(1, 2),
            width=width,
        )
    )
    out.print(
        Align.center(Text.from_markup("[bold bright_cyan]✦  SESIÓN INICIADA  ✦[/bold bright_cyan]"))
    )
    out.print()


def print_exit_banner(
    app_name: str,
    version: str,
    username: str,
    total_conversions: int,
    *,
    env_name: str = "",
    target_console: Optional[Console] = None,
) -> None:
    """Banner de salida flexible según ancho de terminal, con tono legendario."""
    out = target_console or console
    width = _panel_width(out)
    now = datetime.now()
    hour = now.hour
    if 5 <= hour < 12:
        moment = "Buenos días"
        tone = "yellow"
    elif 12 <= hour < 19:
        moment = "Buenas tardes"
        tone = "cyan"
    else:
        moment = "Buenas noches"
        tone = "magenta"

    quote = random.choice(_EXIT_QUOTES)
    art = _exit_art(width)
    title = Text(f"★  {app_name}  ★", style="bold bright_white")
    subtitle = Text(f"v{version}  ·  cierre de sesión", style="dim")

    body_lines = [
        Text.from_markup(f"[{tone}]{moment}, [bold]{username}[/bold].[/{tone}]"),
        Text(""),
        Text.from_markup(art, justify="center"),
        Text(""),
        Text.from_markup(f"[italic bright_white]« {quote} »[/italic bright_white]"),
        Text(""),
        Text.from_markup(
            f"[green]Conversiones en historial:[/green] [bold]{total_conversions}[/bold]"
        ),
    ]
    if env_name:
        body_lines.append(Text.from_markup(f"[dim]Entorno: {env_name}[/dim]"))
    body_lines.append(
        Text.from_markup(
            f"[dim]{now.strftime('%Y-%m-%d %H:%M:%S')} · que el audio te acompañe[/dim]"
        )
    )

    content = Group(
        Align.center(title),
        Align.center(subtitle),
        Text(""),
        *body_lines,
    )
    out.print()
    out.print(
        Panel(
            content,
            box=box.DOUBLE_EDGE,
            border_style="bright_cyan",
            padding=(1, 2),
            width=width,
        )
    )
    out.print(
        Align.center(Text.from_markup("[bold green]✦  SESIÓN FINALIZADA  ✦[/bold green]"))
    )
    out.print()


def _panel_width(out: Console) -> int:
    width = out.width or shutil.get_terminal_size((80, 24)).columns
    return max(40, min(width, 100))


def _enter_art(width: int) -> str:
    if width >= 72:
        return (
            "[bright_yellow]     ♪   █████╗ ███████╗ ██████╗[/bright_yellow]\n"
            "[yellow]    ♫   ██╔══██╗██╔════╝██╔════╝[/yellow]\n"
            "[bright_cyan]   ♪    ███████║█████╗  ██║     [/bright_cyan]\n"
            "[cyan]  ♫     ██╔══██║██╔══╝  ██║     [/cyan]\n"
            "[bright_green] ♪      ██║  ██║██║     ╚██████╗[/bright_green]\n"
            "[green]        ╚═╝  ╚═╝╚═╝      ╚═════╝[/green]\n"
            "[dim]     ─── press start · convert · conquer ───[/dim]"
        )
    if width >= 52:
        return (
            "[bright_yellow]  ♪  ╔═╗╔═╗╔═╗[/bright_yellow]\n"
            "[cyan] ♫   ╠═╣╠╣ ║  [/cyan]\n"
            "[bright_green]♪    ╩ ╩╚  ╚═╝[/bright_green]\n"
            "[dim]  · legendary entrance ·[/dim]"
        )
    return (
        "[bright_yellow]♪ AFC ♫[/bright_yellow]\n"
        "[dim]in ·[/dim]"
    )


def _exit_art(width: int) -> str:
    if width >= 72:
        return (
            "[bright_cyan]     ♪   █████╗ ███████╗ ██████╗[/bright_cyan]\n"
            "[cyan]    ♫   ██╔══██╗██╔════╝██╔════╝[/cyan]\n"
            "[bright_blue]   ♪    ███████║█████╗  ██║     [/bright_blue]\n"
            "[blue]  ♫     ██╔══██║██╔══╝  ██║     [/blue]\n"
            "[bright_magenta] ♪      ██║  ██║██║     ╚██████╗[/bright_magenta]\n"
            "[magenta]        ╚═╝  ╚═╝╚═╝      ╚═════╝[/magenta]\n"
            "[dim]     ─── audio · forever · converted ───[/dim]"
        )
    if width >= 52:
        return (
            "[bright_cyan]  ♪  ╔═╗╔═╗╔═╗[/bright_cyan]\n"
            "[cyan] ♫   ╠═╣╠╣ ║  [/cyan]\n"
            "[bright_magenta]♪    ╩ ╩╚  ╚═╝[/bright_magenta]\n"
            "[dim]  · legendary exit ·[/dim]"
        )
    return (
        "[bright_cyan]♪ AFC ♫[/bright_cyan]\n"
        "[dim]out ·[/dim]"
    )


def print_success(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")


def print_error(message: str) -> None:
    console.print(f"[red]✗[/red] {message}")


def print_warning(message: str) -> None:
    console.print(f"[yellow]⚠[/yellow] {message}")


def print_info(message: str) -> None:
    console.print(f"[cyan]{message}[/cyan]")
