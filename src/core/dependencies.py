"""Verificación de dependencias del sistema."""

import shutil
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich import box


@dataclass
class DependencyStatus:
    name: str
    installed: bool
    version: Optional[str] = None
    path: Optional[str] = None
    message: str = ""


class DependencyChecker:
    """Verificador de dependencias de AFC."""

    @staticmethod
    def check_python() -> DependencyStatus:
        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        ok = sys.version_info >= (3, 12)
        return DependencyStatus(
            name="Python",
            installed=ok,
            version=version,
            path=sys.executable,
            message="Python 3.12+ requerido" if not ok else "OK",
        )

    @staticmethod
    def check_ffmpeg() -> DependencyStatus:
        path = shutil.which("ffmpeg")
        if not path:
            return DependencyStatus(
                name="FFmpeg",
                installed=False,
                message="No instalado. Windows: winget install FFmpeg | Linux: sudo apt install ffmpeg | macOS: brew install ffmpeg | Termux: pkg install ffmpeg",
            )
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=5,
            )
            version = "desconocida"
            if result.returncode == 0 and result.stdout:
                first = result.stdout.split("\n")[0]
                if "version" in first:
                    version = first.split("version")[1].split()[0]
            return DependencyStatus(
                name="FFmpeg",
                installed=True,
                version=version,
                path=path,
                message="OK",
            )
        except Exception as exc:
            return DependencyStatus(
                name="FFmpeg",
                installed=False,
                message=str(exc),
            )

    @staticmethod
    def check_ffprobe() -> DependencyStatus:
        path = shutil.which("ffprobe")
        if not path:
            return DependencyStatus(
                name="FFprobe",
                installed=False,
                message="Normalmente se instala junto con FFmpeg",
            )
        return DependencyStatus(
            name="FFprobe",
            installed=True,
            path=path,
            message="OK",
        )

    @staticmethod
    def check_mutagen() -> DependencyStatus:
        try:
            import mutagen

            return DependencyStatus(
                name="Mutagen",
                installed=True,
                version=getattr(mutagen, "version_string", "instalado"),
                message="OK",
            )
        except ImportError:
            return DependencyStatus(
                name="Mutagen",
                installed=False,
                message="Ejecuta: pip install mutagen",
            )

    @staticmethod
    def check_rich() -> DependencyStatus:
        try:
            import rich

            return DependencyStatus(
                name="Rich",
                installed=True,
                version=getattr(rich, "__version__", "instalado"),
                message="OK",
            )
        except ImportError:
            return DependencyStatus(
                name="Rich",
                installed=False,
                message="Ejecuta: pip install rich",
            )

    @staticmethod
    def check_sqlite() -> DependencyStatus:
        try:
            import sqlite3

            return DependencyStatus(
                name="SQLite",
                installed=True,
                version=sqlite3.sqlite_version,
                message="OK",
            )
        except ImportError:
            return DependencyStatus(
                name="SQLite",
                installed=False,
                message="SQLite no disponible en esta instalación de Python",
            )

    @classmethod
    def check_all(cls) -> list[DependencyStatus]:
        return [
            cls.check_python(),
            cls.check_ffmpeg(),
            cls.check_ffprobe(),
            cls.check_mutagen(),
            cls.check_rich(),
            cls.check_sqlite(),
        ]

    @classmethod
    def all_required_ok(cls) -> bool:
        required = {"Python", "FFmpeg", "FFprobe"}
        return all(
            status.installed
            for status in cls.check_all()
            if status.name in required
        )

    @classmethod
    def show_status(cls, console: Optional[Console] = None) -> None:
        console = console or Console()
        statuses = cls.check_all()

        table = Table(box=box.ROUNDED, title="Dependencias")
        table.add_column("Estado", justify="center")
        table.add_column("Nombre", style="bold")
        table.add_column("Versión")
        table.add_column("Detalle", style="dim")

        for status in statuses:
            icon = "[green]✓[/green]" if status.installed else "[red]✗[/red]"
            table.add_row(
                icon,
                status.name,
                status.version or "-",
                status.path or status.message,
            )

        console.print(table)
