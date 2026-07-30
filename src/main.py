#!/usr/bin/env python3
"""
Audio File Converter (AFC)
CLI multiplataforma para convertir archivos de audio con FFmpeg.
"""

import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from rich.console import Console
from rich.prompt import Prompt
import typer

from src.core.converter import AudioConverter
from src.core.dependencies import DependencyChecker
from src.core.exporter import HistoryExporter
from src.core.ffmpeg_manager import FFmpegManager
from src.core.history import HistoryService
from src.core.metadata import MetadataHandler
from src.core.scanner import AudioScanner
from src.storage.database import Database
from src.ui.console import print_banner, print_entrance_banner, print_exit_banner
from src.ui.menus import Menus
from src.utils.logger import setup_logger
from src.utils.paths import PathManager

app = typer.Typer(help="Audio File Converter - Convierte archivos de audio entre múltiples formatos")
console = Console()

APP_NAME = "Audio File Converter"
VERSION = "1.1.0"


class AudioFileConverterApp:
    """Aplicación principal AFC."""

    def __init__(self):
        self.console = Console()
        self.paths = PathManager()
        self.logger = setup_logger(log_dir=self.paths.logs_dir)
        self.database = Database(self.paths.database_path)
        self.ffmpeg = FFmpegManager()
        self.metadata = MetadataHandler(self.console, self.ffmpeg)
        self.converter = AudioConverter(
            console=self.console,
            ffmpeg=self.ffmpeg,
            metadata_handler=self.metadata,
            default_output_dir=self.paths.converted_dir,
        )
        self.history = HistoryService(self.database)
        self.exporter = HistoryExporter(self.console)
        self.scanner = AudioScanner(recursive=True)
        self.menus = Menus(
            console=self.console,
            paths=self.paths,
            converter=self.converter,
            metadata=self.metadata,
            history=self.history,
            exporter=self.exporter,
            scanner=self.scanner,
        )
        self.running = True

    def bootstrap(self) -> None:
        ffmpeg_info = self.ffmpeg.check()
        print_entrance_banner(
            APP_NAME,
            VERSION,
            self.paths.username,
            env_name=self.paths.display_name,
            data_path=str(self.paths.base_path),
            ffmpeg_ok=ffmpeg_info.available,
            ffmpeg_label=ffmpeg_info.version if ffmpeg_info.available else ffmpeg_info.message,
            total_conversions=self.history.total(),
            target_console=self.console,
        )
        if not ffmpeg_info.available:
            self.console.print(
                "[yellow]La conversión no funcionará hasta instalar FFmpeg[/yellow]"
            )
        if self.paths.is_mobile and not self.paths.base_path.exists():
            self.console.print(
                "[yellow]⚠ Ejecuta termux-setup-storage si necesitas almacenamiento compartido[/yellow]"
            )
        self.logger.info("AFC iniciado en %s", self.paths.display_name)

    def run(self) -> None:
        self.bootstrap()

        while self.running:
            print_banner(
                APP_NAME,
                VERSION,
                self.paths.username,
                self.paths.display_name,
                self.history.total(),
            )
            self.menus.show_main_menu()

            choice = Prompt.ask(
                "\nSeleccione una opción",
                choices=["0", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10"],
                default="0",
            )

            actions = {
                "1": self.menus.convert_single,
                "2": self.menus.convert_multiple,
                "3": self.menus.convert_folder,
                "4": self.menus.convert_from_usb,
                "5": self.menus.edit_metadata,
                "6": self.menus.show_file_info,
                "7": self.menus.history_menu,
                "8": self.menus.export_history,
                "9": self.menus.settings_menu,
                "10": self.menus.check_dependencies,
            }

            if choice == "0":
                print_exit_banner(
                    APP_NAME,
                    VERSION,
                    self.paths.username,
                    self.history.total(),
                    env_name=self.paths.display_name,
                    target_console=self.console,
                )
                self.running = False
            else:
                try:
                    actions[choice]()
                except KeyboardInterrupt:
                    self.console.print("\n[yellow]Operación cancelada[/yellow]")
                except Exception as exc:
                    self.logger.exception("Error en menú %s", choice)
                    self.console.print(f"\n[red]Error: {exc}[/red]")

            if self.running:
                Prompt.ask("\nPresione [bold]Enter[/bold] para continuar", default="")


def main() -> None:
    try:
        application = AudioFileConverterApp()
        application.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Aplicación interrumpida por el usuario[/yellow]")
        sys.exit(0)
    except Exception as exc:
        console.print(f"\n[red]Error fatal: {exc}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
