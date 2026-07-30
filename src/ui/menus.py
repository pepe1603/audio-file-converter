"""Menús interactivos de Audio File Converter."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.table import Table
from rich import box

from src.models.audio_file import (
    AudioFormat,
    AudioMetadata,
    BitratePreset,
    SampleRatePreset,
)
from src.models.conversion import BatchConversionResult, ConversionOptions, ConversionRecord
from src.core.converter import AudioConverter
from src.core.dependencies import DependencyChecker
from src.core.exporter import HistoryExporter
from src.core.history import HistoryService
from src.core.metadata import MetadataHandler
from src.core.removable import MAX_TREE_DEPTH, RemovableDevice, RemovableMediaManager
from src.core.scanner import AudioScanner
from src.core.session_report import SessionReportWriter
from src.core.validator import Validator
from src.ui.progress import batch_progress, conversion_progress
from src.utils.helpers import format_duration, format_size
from src.utils.paths import PathManager


class Menus:
    """Controlador de menús de la aplicación."""

    def __init__(
        self,
        console: Console,
        paths: PathManager,
        converter: AudioConverter,
        metadata: MetadataHandler,
        history: HistoryService,
        exporter: HistoryExporter,
        scanner: AudioScanner,
    ):
        self.console = console
        self.paths = paths
        self.converter = converter
        self.metadata = metadata
        self.history = history
        self.exporter = exporter
        self.scanner = scanner
        self.removable = RemovableMediaManager(max_depth=MAX_TREE_DEPTH)
        self.session_reports = SessionReportWriter(self.paths.exports_dir)

    def show_main_menu(self) -> None:
        self.console.print("\n[bold]═══ MENÚ PRINCIPAL ═══[/bold]\n")
        table = Table(box=box.ROUNDED, show_header=False)
        table.add_column("Opción", style="cyan", justify="center", width=8)
        table.add_column("Acción", style="white")
        table.add_row("1", "Convertir un archivo")
        table.add_row("2", "Convertir varios archivos")
        table.add_row("3", "Convertir una carpeta completa")
        table.add_row("4", "Convertir desde USB / extraíble")
        table.add_row("5", "Editar metadatos")
        table.add_row("6", "Ver información del archivo")
        table.add_row("7", "Historial")
        table.add_row("8", "Exportar historial")
        table.add_row("9", "Configuración")
        table.add_row("10", "Verificar dependencias")
        table.add_row("0", "Salir")
        self.console.print(table)

    def convert_single(self) -> None:
        self.console.print("\n[bold cyan]═══ CONVERTIR UN ARCHIVO ═══[/bold cyan]\n")
        path_str = Prompt.ask("Ruta del archivo de audio")
        if not path_str:
            return

        path = Path(path_str.strip().strip('"'))
        validation = Validator.validate_file(path)
        if not validation.valid:
            self.console.print(f"[red]✗ {validation.message}[/red]")
            return

        options = self._ask_conversion_options()
        if options is None:
            return

        self.console.print("\n[cyan]Conversión iniciada...[/cyan]")
        with conversion_progress(self.console) as progress:
            task = progress.add_task("Convirtiendo", total=1.0)

            def on_progress(value: float) -> None:
                progress.update(task, completed=value)

            result = self.converter.convert(path, options, progress_callback=on_progress)

        self.history.add_from_result(
            result,
            username=self.paths.username,
            sample_rate=options.sample_rate.value,
        )

        if result.success:
            self.console.print("\n[green]✓ Conversión completada[/green]")
            self.console.print(f"[dim]Archivo generado: {result.output_path}[/dim]")
        else:
            self.console.print(f"\n[red]✗ Error: {result.error_message}[/red]")

    def convert_multiple(self) -> None:
        self.console.print("\n[bold cyan]═══ CONVERTIR VARIOS ARCHIVOS ═══[/bold cyan]\n")
        self.console.print("[dim]Ingrese rutas separadas por ; o una por línea (línea vacía para terminar)[/dim]\n")

        files: list[Path] = []
        while True:
            path_str = Prompt.ask("Archivo", default="")
            if not path_str:
                break
            if ";" in path_str:
                candidates = [p.strip().strip('"') for p in path_str.split(";") if p.strip()]
            else:
                candidates = [path_str.strip().strip('"')]

            for candidate in candidates:
                path = Path(candidate)
                validation = Validator.validate_file(path)
                if validation.valid:
                    files.append(path)
                    self.console.print(f"  [green]✓[/green] {path.name}")
                else:
                    self.console.print(f"  [red]✗[/red] {validation.message}")

        if not files:
            self.console.print("[yellow]No se agregaron archivos válidos[/yellow]")
            return

        self._run_batch(files)

    def convert_folder(self) -> None:
        self.console.print("\n[bold cyan]═══ CONVERTIR CARPETA ═══[/bold cyan]\n")
        folder_str = Prompt.ask("Ruta de la carpeta")
        if not folder_str:
            return

        folder = Path(folder_str.strip().strip('"'))
        validation = Validator.validate_directory(folder)
        if not validation.valid:
            self.console.print(f"[red]✗ {validation.message}[/red]")
            return

        recursive = Confirm.ask("¿Incluir subcarpetas?", default=True)
        self.scanner.recursive = recursive
        files = self.scanner.scan(folder)

        if not files:
            self.console.print("[yellow]No se encontraron archivos de audio soportados[/yellow]")
            return

        self.console.print(f"\n[green]Se encontraron {len(files)} archivos[/green]")
        groups = self.scanner.group_by_format(files)
        for fmt, items in sorted(groups.items()):
            self.console.print(f"  [dim]{fmt.upper()}: {len(items)}[/dim]")

        if not Confirm.ask("\n¿Iniciar conversión?", default=True):
            return

        self._run_batch(files)

    def convert_from_usb(self) -> None:
        self.console.print("\n[bold cyan]═══ CONVERTIR DESDE USB / EXTRAÍBLE ═══[/bold cyan]\n")
        self.console.print(
            f"[dim]Navegación limitada a {MAX_TREE_DEPTH} niveles desde la raíz del dispositivo[/dim]\n"
        )

        device = self._select_removable_device()
        if device is None:
            return

        selection = self._browse_removable_device(device)
        if selection is None:
            return

        files, source_label = selection
        if not files:
            self.console.print("[yellow]No hay archivos de audio para convertir[/yellow]")
            return

        destination = self._ask_usb_destination()
        if destination is None:
            return

        options = self._ask_conversion_options()
        if options is None:
            return

        started_at = datetime.now()
        save_on_pc = destination == "pc"
        if save_on_pc:
            output_dir = self.paths.removable_pc_session_dir(
                device.label, when=started_at, create=False
            )
            dest_label = f"PC → {output_dir}"
        else:
            output_dir = self.paths.removable_usb_session_dir(
                files, device.path, when=started_at, create=False
            )
            dest_label = f"USB (modo limpio) → {output_dir}"

        options = options.model_copy(update={"output_dir": output_dir})

        pre = SessionReportWriter.format_pre_summary(
            device_label=device.label,
            device_path=device.path,
            source_label=source_label,
            files=files,
            options=options,
            destination_label=dest_label,
        )
        self.console.print("\n[bold]Resumen previo a la conversión[/bold]")
        self.console.print(Panel(pre, box=box.ROUNDED, title="Antes", border_style="cyan"))

        if not Confirm.ask("\n¿Confirmar e iniciar conversión?", default=True):
            self.console.print("[yellow]Conversión cancelada[/yellow]")
            return

        output_dir.mkdir(parents=True, exist_ok=True)

        batch = self._execute_conversion_batch(
            files,
            options,
            record_history=save_on_pc,
            progress_label="USB",
        )
        finished_at = datetime.now()

        self._print_post_summary(batch, options)

        report_dir = self.paths.exports_dir if save_on_pc else output_dir
        reporter = SessionReportWriter(report_dir)
        md_path, txt_path = reporter.write_session(
            device_label=device.label,
            device_path=device.path,
            source_label=source_label,
            files=files,
            options=options,
            batch=batch,
            username=self.paths.username,
            started_at=started_at,
            finished_at=finished_at,
            destination_label=dest_label,
        )
        if save_on_pc:
            self.console.print("\n[green]✓ Reportes actualizados en PC[/green]")
        else:
            self.console.print(
                "\n[green]✓ Modo limpio: solo archivos convertidos y reporte en el USB[/green]"
            )
            self.console.print("[dim]Sin historial ni residuos en el PC[/dim]")
        self.console.print(f"[dim]MD:  {md_path}[/dim]")
        self.console.print(f"[dim]TXT: {txt_path}[/dim]")
        self.console.print(f"[dim]Salida: {output_dir}[/dim]")

    def _ask_usb_destination(self) -> Optional[str]:
        """Submenú: dónde guardar las conversiones desde extraíble."""
        self.console.print("\n[bold]¿Dónde guardar las conversiones?[/bold]\n")
        table = Table(box=box.ROUNDED, show_header=False)
        table.add_column("Opción", style="cyan", justify="center", width=8)
        table.add_column("Destino", style="white")
        table.add_row(
            "1",
            "En el PC — carpeta from_removable/<dispositivo>/<fecha>/<formato>/",
        )
        table.add_row(
            "2",
            "En el mismo USB — carpeta AFC_Converted_<fecha> junto al origen (modo limpio)",
        )
        table.add_row("0", "Cancelar")
        self.console.print(table)
        self.console.print(
            "[dim]Modo limpio (2): no escribe historial, exports ni basura en el PC; "
            "solo convierte y guarda en el USB.[/dim]\n"
        )

        choice = Prompt.ask("Seleccione", choices=["0", "1", "2"], default="1")
        if choice == "0":
            return None
        if choice == "1":
            return "pc"
        return "usb"

    def _select_removable_device(self) -> Optional[RemovableDevice]:
        while True:
            self.console.print("[cyan]Buscando dispositivos extraíbles...[/cyan]")
            devices = self.removable.list_devices()

            if not devices:
                self.console.print("[yellow]No se detectaron dispositivos extraíbles[/yellow]")
                self.console.print("[dim]Conecte un USB y use la opción Actualizar[/dim]\n")
            else:
                table = Table(box=box.ROUNDED, title="Dispositivos detectados")
                table.add_column("#", style="cyan", justify="center")
                table.add_column("Etiqueta", style="white")
                table.add_column("Ruta", style="green")
                table.add_column("Espacio", style="dim")
                for i, device in enumerate(devices, 1):
                    space = "-"
                    if device.free_gb is not None and device.total_gb is not None:
                        space = f"{device.free_gb:.1f}/{device.total_gb:.1f} GB"
                    table.add_row(str(i), device.label, str(device.path), space)
                self.console.print(table)

            table = Table(box=box.SIMPLE, show_header=False)
            table.add_column("Opción", style="cyan", justify="center")
            table.add_column("Acción")
            if devices:
                table.add_row("1-" + str(len(devices)), "Seleccionar dispositivo")
            table.add_row("R", "Actualizar lista")
            table.add_row("0", "Cancelar")
            self.console.print(table)

            choice = Prompt.ask("Seleccione", default="0").strip().lower()
            if choice in {"0", ""}:
                return None
            if choice == "r":
                continue
            if devices and choice.isdigit():
                idx = int(choice)
                if 1 <= idx <= len(devices):
                    selected = devices[idx - 1]
                    self.console.print(f"[green]✓ Dispositivo: {selected.display}[/green]")
                    return selected
            self.console.print("[red]Opción no válida[/red]")

    def _browse_removable_device(
        self,
        device: RemovableDevice,
    ) -> Optional[tuple[list[Path], str]]:
        current = device.path
        root = device.path
        page_size = 40
        audio_offset = 0

        while True:
            depth = self.removable.depth_from_root(root, current)
            if depth < 0:
                self.console.print("[red]Ruta fuera del dispositivo[/red]")
                current = root
                depth = 0
                audio_offset = 0

            entries = self.removable.list_directory(root, current)
            folders = [e for e in entries if e.is_dir]
            audios = [e for e in entries if e.is_audio]
            page = audios[audio_offset: audio_offset + page_size]
            has_more = audio_offset + page_size < len(audios)
            has_prev = audio_offset > 0

            self.console.print(
                f"\n[bold]Explorando:[/bold] {current}  "
                f"[dim](nivel {depth}/{MAX_TREE_DEPTH}) | "
                f"{len(folders)} carpetas | {len(audios)} audios[/dim]"
            )

            table = Table(box=box.ROUNDED)
            table.add_column("#", style="cyan", justify="center", width=6)
            table.add_column("Tipo", width=10)
            table.add_column("Nombre", style="white", max_width=60)
            table.add_column("Info", style="dim")

            row_map: dict[int, object] = {}
            n = 1
            for folder in folders:
                can_open = self.removable.can_enter(root, folder.path)
                info = "entrar" if can_open else f"máx. {MAX_TREE_DEPTH} niveles"
                name = folder.name if len(folder.name) <= 60 else folder.name[:57] + "..."
                table.add_row(str(n), "Carpeta", name, info)
                row_map[n] = ("dir", folder)
                n += 1
            for audio in page:
                size = format_size(audio.size_bytes) if audio.size_bytes is not None else "-"
                name = audio.name if len(audio.name) <= 60 else audio.name[:57] + "..."
                table.add_row(str(n), "Audio", name, size)
                row_map[n] = ("file", audio)
                n += 1

            if not row_map and not audios:
                self.console.print("[yellow]Carpeta vacía (sin subcarpetas ni audio visible)[/yellow]")
            else:
                self.console.print(table)
                if len(audios) > page_size:
                    end = min(audio_offset + page_size, len(audios))
                    self.console.print(
                        f"[dim]Audios {audio_offset + 1}-{end} de {len(audios)} "
                        f"(use N/P para paginar; A/B convierte todos)[/dim]"
                    )

            actions = Table(box=box.SIMPLE, show_header=False)
            actions.add_column("Opción", style="cyan", justify="center")
            actions.add_column("Acción")
            if row_map:
                actions.add_row("1-" + str(max(row_map)), "Abrir carpeta o seleccionar archivo")
            actions.add_row("A", "Convertir todo el audio de esta carpeta (solo nivel actual)")
            actions.add_row("B", f"Convertir carpeta + subcarpetas (máx. nivel {MAX_TREE_DEPTH})")
            if has_more:
                actions.add_row("N", "Siguiente página de audios")
            if has_prev:
                actions.add_row("P", "Página anterior de audios")
            if depth > 0:
                actions.add_row("U", "Subir un nivel")
            actions.add_row("0", "Cancelar")
            self.console.print(actions)

            choice = Prompt.ask("Seleccione", default="0").strip().lower()
            if choice in {"0", ""}:
                return None
            if choice == "u" and depth > 0:
                current = current.parent
                audio_offset = 0
                continue
            if choice == "n" and has_more:
                audio_offset += page_size
                continue
            if choice == "p" and has_prev:
                audio_offset = max(0, audio_offset - page_size)
                continue
            if choice == "a":
                files = self.removable.scan_audio(root, current, recursive=False)
                if not files:
                    self.console.print("[yellow]No hay audio en este nivel[/yellow]")
                    continue
                return files, f"Carpeta (nivel actual): {current}"
            if choice == "b":
                files = self.removable.scan_audio(root, current, recursive=True)
                if not files:
                    self.console.print("[yellow]No hay audio en el alcance permitido[/yellow]")
                    continue
                return files, f"Carpeta + subcarpetas (≤{MAX_TREE_DEPTH}): {current}"
            if choice.isdigit():
                idx = int(choice)
                if idx in row_map:
                    kind, entry = row_map[idx]
                    if kind == "dir":
                        if self.removable.can_enter(root, entry.path):
                            current = entry.path
                            audio_offset = 0
                        else:
                            self.console.print(
                                f"[yellow]No se puede entrar: límite de {MAX_TREE_DEPTH} niveles[/yellow]"
                            )
                        continue
                    return [entry.path], f"Archivo: {entry.path}"
            self.console.print("[red]Opción no válida[/red]")

    def _execute_conversion_batch(
        self,
        files: list[Path],
        options: ConversionOptions,
        *,
        record_history: bool = True,
        progress_label: str = "Lote",
    ) -> BatchConversionResult:
        self.console.print(f"\n[cyan]Convirtiendo {len(files)} archivo(s)...[/cyan]")
        with batch_progress(self.console) as progress:
            task = progress.add_task(progress_label, total=len(files))

            def on_item(index: int, total: int, path: Path) -> None:
                progress.update(task, completed=index - 1, description=path.name)

            batch = self.converter.convert_batch(files, options, progress_callback=on_item)
            progress.update(task, completed=len(files), description="Completado")

        if record_history:
            for result in batch.results:
                self.history.add_from_result(
                    result,
                    username=self.paths.username,
                    sample_rate=options.sample_rate.value,
                )
        return batch

    def _print_post_summary(
        self,
        batch: BatchConversionResult,
        options: ConversionOptions,
    ) -> None:
        lines = [
            f"Total: {batch.total}",
            f"Éxito: {batch.success}",
            f"Fallos: {batch.failed}",
            f"Omitidos: {batch.skipped}",
            f"Formato: {options.output_format.value.upper()}",
            f"Salida: {options.output_dir or self.paths.converted_dir}",
            "",
            "Detalle:",
        ]
        for result in batch.results:
            mark = "OK" if result.success else "ERROR"
            target = result.output_path.name if result.output_path else "-"
            extra = f" | {result.error_message}" if result.error_message else ""
            lines.append(f"  [{mark}] {result.input_path.name} -> {target}{extra}")

        self.console.print("\n[bold]Resumen posterior a la conversión[/bold]")
        self.console.print(Panel("\n".join(lines), box=box.ROUNDED, title="Después", border_style="green"))

    def edit_metadata(self) -> None:
        self.console.print("\n[bold cyan]═══ EDITAR METADATOS ═══[/bold cyan]\n")
        path_str = Prompt.ask("Ruta del archivo")
        if not path_str:
            return

        path = Path(path_str.strip().strip('"'))
        validation = Validator.validate_file(path)
        if not validation.valid:
            self.console.print(f"[red]✗ {validation.message}[/red]")
            return

        current = self.metadata.read_metadata(path)
        self.console.print("\n[bold]Metadatos actuales:[/bold]")
        self._print_metadata(current)

        self.console.print("\n[dim]Deje vacío para mantener el valor actual[/dim]\n")
        title = Prompt.ask("Título", default=current.title or "")
        artist = Prompt.ask("Artista", default=current.artist or "")
        album = Prompt.ask("Álbum", default=current.album or "")
        year = Prompt.ask("Año", default=current.year or "")
        genre = Prompt.ask("Género", default=current.genre or "")
        track = Prompt.ask("Track", default=current.track or "")
        comment = Prompt.ask("Comentarios", default=current.comment or "")
        cover = Prompt.ask("Ruta de portada (opcional)", default="")

        new_meta = AudioMetadata(
            title=title or None,
            artist=artist or None,
            album=album or None,
            year=year or None,
            genre=genre or None,
            track=track or None,
            comment=comment or None,
            cover_path=Path(cover) if cover else None,
        )

        if self.metadata.write_metadata(path, new_meta):
            self.console.print("\n[green]✓ Metadatos actualizados[/green]")
        else:
            self.console.print("\n[red]✗ No se pudieron actualizar los metadatos[/red]")

    def show_file_info(self) -> None:
        self.console.print("\n[bold cyan]═══ INFORMACIÓN DEL ARCHIVO ═══[/bold cyan]\n")
        path_str = Prompt.ask("Ruta del archivo")
        if not path_str:
            return

        path = Path(path_str.strip().strip('"'))
        validation = Validator.validate_file(path)
        if not validation.valid:
            self.console.print(f"[red]✗ {validation.message}[/red]")
            return

        info = self.metadata.get_info(path)
        if info is None:
            self.console.print("[red]✗ No se pudo leer el archivo[/red]")
            return

        table = Table(box=box.ROUNDED, show_header=False, title=info.name)
        table.add_column("Campo", style="cyan")
        table.add_column("Valor", style="white")
        table.add_row("Nombre", info.name)
        table.add_row("Ruta", str(info.path))
        table.add_row("Formato", info.format.value.upper() if info.format else "N/A")
        table.add_row("Duración", info.duration_str)
        table.add_row("Bitrate", info.bitrate_str)
        table.add_row("Canales", info.channels_str)
        table.add_row("Frecuencia", f"{info.sample_rate} Hz" if info.sample_rate else "N/A")
        table.add_row("Codec", info.codec or "N/A")
        table.add_row("Tamaño", info.size_str)
        table.add_row("Título", info.metadata.title or "-")
        table.add_row("Artista", info.metadata.artist or "-")
        table.add_row("Álbum", info.metadata.album or "-")
        table.add_row("Año", info.metadata.year or "-")
        table.add_row("Género", info.metadata.genre or "-")
        table.add_row("Track", info.metadata.track or "-")
        self.console.print(table)

    def history_menu(self) -> None:
        while True:
            self.console.print("\n[bold cyan]═══ HISTORIAL ═══[/bold cyan]\n")
            table = Table(box=box.SIMPLE, show_header=False)
            table.add_column("Opción", style="cyan", justify="center")
            table.add_column("Acción")
            table.add_row("1", "Ver últimas 20 conversiones")
            table.add_row("2", "Buscar por formato")
            table.add_row("3", "Buscar por nombre")
            table.add_row("4", "Estadísticas")
            table.add_row("5", "Limpiar fallidas")
            table.add_row("0", "Regresar")
            self.console.print(table)

            choice = Prompt.ask("Seleccione", choices=["0", "1", "2", "3", "4", "5"], default="1")
            if choice == "0":
                return
            if choice == "1":
                self._display_history(self.history.recent(20))
            elif choice == "2":
                fmt = Prompt.ask("Formato destino (mp3, flac, ...)")
                self._display_history(self.history.search(format_filter=fmt))
            elif choice == "3":
                text = Prompt.ask("Texto a buscar")
                self._display_history(self.history.search(text=text))
            elif choice == "4":
                self._show_stats()
            elif choice == "5":
                if Confirm.ask("¿Eliminar conversiones fallidas?", default=False):
                    deleted = self.history.clear_failed()
                    self.console.print(f"[green]✓ {deleted} registros eliminados[/green]")

    def export_history(self) -> None:
        self.console.print("\n[bold cyan]═══ EXPORTAR HISTORIAL ═══[/bold cyan]\n")
        records = self.history.all_records()
        if not records:
            self.console.print("[yellow]No hay conversiones para exportar[/yellow]")
            return

        self.console.print(f"[dim]Total: {len(records)}[/dim]\n")
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Opción", style="cyan", justify="center")
        table.add_column("Formato")
        table.add_row("1", "TXT")
        table.add_row("2", "Markdown")
        table.add_row("3", "JSON")
        table.add_row("0", "Regresar")
        self.console.print(table)

        choice = Prompt.ask("Seleccione", choices=["0", "1", "2", "3"], default="1")
        if choice == "0":
            return

        self.paths.exports_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if choice == "1":
            output = self.paths.exports_dir / f"historial_{stamp}.txt"
            ok = self.exporter.export_to_txt(records, output)
        elif choice == "2":
            output = self.paths.exports_dir / f"historial_{stamp}.md"
            ok = self.exporter.export_to_markdown(records, output)
        else:
            output = self.paths.exports_dir / f"historial_{stamp}.json"
            ok = self.exporter.export_to_json(records, output)

        if ok:
            self.console.print(f"\n[green]✓ Historial exportado[/green]")
            self.console.print(f"[dim]{output}[/dim]")
        else:
            self.console.print("\n[red]✗ Error al exportar[/red]")

    def settings_menu(self) -> None:
        while True:
            self.console.print("\n[bold cyan]═══ CONFIGURACIÓN ═══[/bold cyan]\n")
            self.console.print(f"[bold]Entorno:[/bold] {self.paths.display_name}")
            self.console.print(f"[bold]Usuario:[/bold] {self.paths.username}")
            self.console.print(f"[bold]Carpeta de salida:[/bold] {self.paths.converted_dir}")
            self.console.print(f"[bold]Base de datos:[/bold] {self.paths.database_path}")
            self.console.print(f"[bold]Config:[/bold] {self.paths.config_file}")

            table = Table(box=box.SIMPLE, show_header=False)
            table.add_column("Opción", style="cyan", justify="center")
            table.add_column("Acción")
            table.add_row("1", "Ver carpeta de salida")
            table.add_row("2", "Cambiar carpeta de salida")
            table.add_row("3", "Cambiar usuario")
            table.add_row("4", "Verificar FFmpeg")
            table.add_row("5", "Verificar base de datos")
            table.add_row("6", "Restablecer configuración")
            table.add_row("0", "Regresar")
            self.console.print(table)

            choice = Prompt.ask(
                "Seleccione",
                choices=["0", "1", "2", "3", "4", "5", "6"],
                default="0",
            )
            if choice == "0":
                return
            if choice == "1":
                self.console.print(f"\n[cyan]{self.paths.converted_dir}[/cyan]")
            elif choice == "2":
                new_path = Prompt.ask("Nueva carpeta de salida")
                if new_path:
                    resolved = self.paths.set_output_dir(Path(new_path.strip().strip('"')))
                    self.converter.default_output_dir = resolved
                    self.console.print(f"[green]✓ Carpeta actualizada: {resolved}[/green]")
            elif choice == "3":
                name = Prompt.ask("Nombre de usuario", default=self.paths.username)
                if name:
                    self.paths.username = name
                    self.console.print(f"[green]✓ Usuario: {name}[/green]")
            elif choice == "4":
                DependencyChecker.show_status(self.console)
            elif choice == "5":
                exists = self.paths.database_path.exists()
                total = self.history.total()
                icon = "[green]✓[/green]" if exists else "[red]✗[/red]"
                self.console.print(f"{icon} DB: {self.paths.database_path}")
                self.console.print(f"[dim]Registros: {total}[/dim]")
            elif choice == "6":
                if Confirm.ask("¿Restablecer configuración?", default=False):
                    self.paths.reset_config()
                    self.converter.default_output_dir = self.paths.converted_dir
                    self.console.print("[green]✓ Configuración restablecida[/green]")

    def check_dependencies(self) -> None:
        self.console.print("\n[bold cyan]═══ VERIFICAR DEPENDENCIAS ═══[/bold cyan]\n")
        DependencyChecker.show_status(self.console)

    def _run_batch(self, files: list[Path]) -> None:
        options = self._ask_conversion_options()
        if options is None:
            return

        self.console.print(f"\n[cyan]Convirtiendo {len(files)} archivos...[/cyan]")
        with batch_progress(self.console) as progress:
            task = progress.add_task("Lote", total=len(files))

            def on_item(index: int, total: int, path: Path) -> None:
                progress.update(task, completed=index - 1, description=path.name)

            batch = self.converter.convert_batch(files, options, progress_callback=on_item)
            progress.update(task, completed=len(files), description="Completado")

        for result in batch.results:
            self.history.add_from_result(
                result,
                username=self.paths.username,
                sample_rate=options.sample_rate.value,
            )

        self.console.print(
            f"\n[green]✓ Éxito: {batch.success}[/green] | "
            f"[red]Fallos: {batch.failed}[/red] | "
            f"[yellow]Omitidos: {batch.skipped}[/yellow]"
        )
        self.console.print(f"[dim]Salida: {self.paths.converted_dir}[/dim]")

    def _ask_conversion_options(self) -> Optional[ConversionOptions]:
        fmt = self._select_format()
        if fmt is None:
            return None

        bitrate = self._select_bitrate(fmt)
        if bitrate is None:
            return None

        sample_rate = self._select_sample_rate()
        if sample_rate is None:
            return None

        preserve = Confirm.ask("¿Conservar metadatos?", default=True)

        return ConversionOptions(
            output_format=fmt,
            bitrate=bitrate,
            sample_rate=sample_rate,
            preserve_metadata=preserve,
            output_dir=self.paths.converted_dir,
        )

    def _select_format(self) -> Optional[AudioFormat]:
        self.console.print("\n[bold]Formato destino:[/bold]")
        formats = list(AudioFormat)
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Opción", style="cyan", justify="center")
        table.add_column("Formato")
        for i, fmt in enumerate(formats, 1):
            table.add_row(str(i), fmt.description)
        table.add_row("0", "Cancelar")
        self.console.print(table)

        choices = ["0"] + [str(i) for i in range(1, len(formats) + 1)]
        choice = IntPrompt.ask("Seleccione", choices=choices, default=1)
        if choice == 0:
            return None
        return formats[choice - 1]

    def _select_bitrate(self, fmt: AudioFormat) -> Optional[BitratePreset]:
        if fmt in (AudioFormat.FLAC, AudioFormat.WAV, AudioFormat.AIFF):
            return BitratePreset.ORIGINAL

        self.console.print("\n[bold]Bitrate:[/bold]")
        presets = list(BitratePreset)
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Opción", style="cyan", justify="center")
        table.add_column("Bitrate")
        for i, preset in enumerate(presets, 1):
            table.add_row(str(i), preset.description)
        table.add_row("0", "Cancelar")
        self.console.print(table)

        choices = ["0"] + [str(i) for i in range(1, len(presets) + 1)]
        choice = IntPrompt.ask("Seleccione", choices=choices, default=2)
        if choice == 0:
            return None
        return presets[choice - 1]

    def _select_sample_rate(self) -> Optional[SampleRatePreset]:
        self.console.print("\n[bold]Frecuencia de muestreo:[/bold]")
        presets = list(SampleRatePreset)
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Opción", style="cyan", justify="center")
        table.add_column("Frecuencia")
        for i, preset in enumerate(presets, 1):
            table.add_row(str(i), preset.description)
        table.add_row("0", "Cancelar")
        self.console.print(table)

        choices = ["0"] + [str(i) for i in range(1, len(presets) + 1)]
        choice = IntPrompt.ask("Seleccione", choices=choices, default=3)
        if choice == 0:
            return None
        return presets[choice - 1]

    def _display_history(self, records: list[ConversionRecord]) -> None:
        if not records:
            self.console.print("[yellow]No hay registros[/yellow]")
            return

        table = Table(box=box.ROUNDED)
        table.add_column("ID", style="cyan", justify="center")
        table.add_column("Fecha", style="green")
        table.add_column("Origen", style="white", max_width=28)
        table.add_column("Fmt", style="magenta")
        table.add_column("Bitrate", style="yellow")
        table.add_column("Estado", style="blue")
        table.add_column("Duración", justify="right")

        for record in records:
            name = Path(record.source_file).name
            if len(name) > 28:
                name = name[:25] + "..."
            status_style = "green" if record.status == "success" else "red"
            table.add_row(
                str(record.id or "-"),
                record.date,
                name,
                f"{record.source_format}->{record.destination_format}",
                record.bitrate or "-",
                f"[{status_style}]{record.status}[/{status_style}]",
                format_duration(record.duration),
            )

        self.console.print(f"\n[bold]Resultados ({len(records)}):[/bold]\n")
        self.console.print(table)

    def _show_stats(self) -> None:
        total = self.history.total()
        by_format = self.history.stats_by_format()
        by_status = self.history.stats_by_status()

        self.console.print(f"\n[bold]Total de conversiones:[/bold] {total}\n")

        if by_format:
            table = Table(box=box.SIMPLE, title="Por formato destino")
            table.add_column("Formato", style="cyan")
            table.add_column("Cantidad", justify="right", style="green")
            for fmt, count in by_format.items():
                table.add_row(fmt.upper(), str(count))
            self.console.print(table)

        if by_status:
            table = Table(box=box.SIMPLE, title="Por estado")
            table.add_column("Estado", style="cyan")
            table.add_column("Cantidad", justify="right")
            for status, count in by_status.items():
                table.add_row(status, str(count))
            self.console.print(table)

    def _print_metadata(self, metadata: AudioMetadata) -> None:
        table = Table(box=box.SIMPLE, show_header=False)
        table.add_column("Campo", style="cyan")
        table.add_column("Valor")
        table.add_row("Título", metadata.title or "-")
        table.add_row("Artista", metadata.artist or "-")
        table.add_row("Álbum", metadata.album or "-")
        table.add_row("Año", metadata.year or "-")
        table.add_row("Género", metadata.genre or "-")
        table.add_row("Track", metadata.track or "-")
        table.add_row("Comentarios", metadata.comment or "-")
        self.console.print(table)
