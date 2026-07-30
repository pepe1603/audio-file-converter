"""Reportes de sesión de conversión (MD y TXT)."""

from datetime import datetime
from pathlib import Path
from typing import Optional

from src.models.conversion import BatchConversionResult, ConversionOptions, ConversionResult
from src.utils.helpers import format_duration, format_size


class SessionReportWriter:
    """Crea y actualiza resúmenes de conversión en Markdown y TXT."""

    MD_NAME = "usb_conversion_summary.md"
    TXT_NAME = "usb_conversion_summary.txt"

    def __init__(self, exports_dir: Path):
        self.exports_dir = Path(exports_dir)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.md_path = self.exports_dir / self.MD_NAME
        self.txt_path = self.exports_dir / self.TXT_NAME

    def write_session(
        self,
        *,
        device_label: str,
        device_path: Path,
        source_label: str,
        files: list[Path],
        options: ConversionOptions,
        batch: BatchConversionResult,
        username: str,
        started_at: datetime,
        finished_at: Optional[datetime] = None,
        destination_label: str = "",
    ) -> tuple[Path, Path]:
        finished_at = finished_at or datetime.now()
        stamp = finished_at.strftime("%Y-%m-%d %H:%M:%S")

        md_block = self._build_markdown(
            stamp=stamp,
            device_label=device_label,
            device_path=device_path,
            source_label=source_label,
            files=files,
            options=options,
            batch=batch,
            username=username,
            started_at=started_at,
            finished_at=finished_at,
            destination_label=destination_label,
        )
        txt_block = self._build_txt(
            stamp=stamp,
            device_label=device_label,
            device_path=device_path,
            source_label=source_label,
            files=files,
            options=options,
            batch=batch,
            username=username,
            started_at=started_at,
            finished_at=finished_at,
            destination_label=destination_label,
        )

        self._append_md(md_block)
        self._append_txt(txt_block)

        # Copia fechada de la sesión
        session_stamp = finished_at.strftime("%Y%m%d_%H%M%S")
        session_md = self.exports_dir / f"usb_session_{session_stamp}.md"
        session_txt = self.exports_dir / f"usb_session_{session_stamp}.txt"
        session_md.write_text(md_block, encoding="utf-8")
        session_txt.write_text(txt_block, encoding="utf-8")

        return self.md_path, self.txt_path

    def _append_md(self, block: str) -> None:
        if not self.md_path.exists():
            header = (
                "# Resumen de conversiones desde USB\n\n"
                "Archivo actualizado automáticamente por Audio File Converter.\n\n"
                "---\n\n"
            )
            self.md_path.write_text(header + block, encoding="utf-8")
        else:
            with open(self.md_path, "a", encoding="utf-8") as f:
                f.write("\n---\n\n")
                f.write(block)

    def _append_txt(self, block: str) -> None:
        if not self.txt_path.exists():
            header = (
                "RESUMEN DE CONVERSIONES DESDE USB\n"
                "Audio File Converter\n"
                f"{'=' * 60}\n\n"
            )
            self.txt_path.write_text(header + block, encoding="utf-8")
        else:
            with open(self.txt_path, "a", encoding="utf-8") as f:
                f.write("\n" + "=" * 60 + "\n\n")
                f.write(block)

    def _build_markdown(
        self,
        *,
        stamp: str,
        device_label: str,
        device_path: Path,
        source_label: str,
        files: list[Path],
        options: ConversionOptions,
        batch: BatchConversionResult,
        username: str,
        started_at: datetime,
        finished_at: datetime,
        destination_label: str = "",
    ) -> str:
        lines = [
            f"## Sesión {stamp}",
            "",
            f"- **Usuario:** {username}",
            f"- **Dispositivo:** {device_label}",
            f"- **Ruta dispositivo:** `{device_path}`",
            f"- **Origen:** {source_label}",
        ]
        if destination_label:
            lines.append(f"- **Destino:** {destination_label}")
        lines.extend(
            [
                f"- **Inicio:** {started_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"- **Fin:** {finished_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"- **Formato destino:** {options.output_format.value.upper()}",
                f"- **Bitrate:** {options.bitrate.description}",
                f"- **Sample rate:** {options.sample_rate.description}",
                f"- **Metadatos:** {'Sí' if options.preserve_metadata else 'No'}",
                f"- **Carpeta salida:** `{options.output_dir}`",
                f"- **Total archivos:** {batch.total}",
                f"- **Éxito:** {batch.success}",
                f"- **Fallos:** {batch.failed}",
                f"- **Omitidos:** {batch.skipped}",
                "",
                "### Archivos",
                "",
            ]
        )
        for result in batch.results:
            status = "OK" if result.success else "ERROR"
            out = result.output_path or "-"
            err = f" — {result.error_message}" if result.error_message else ""
            lines.append(
                f"- [{status}] `{result.input_path.name}` → `{out}`"
                f" ({format_duration(result.duration)}){err}"
            )
        lines.append("")
        return "\n".join(lines)

    def _build_txt(
        self,
        *,
        stamp: str,
        device_label: str,
        device_path: Path,
        source_label: str,
        files: list[Path],
        options: ConversionOptions,
        batch: BatchConversionResult,
        username: str,
        started_at: datetime,
        finished_at: datetime,
        destination_label: str = "",
    ) -> str:
        lines = [
            f"SESION {stamp}",
            f"Usuario: {username}",
            f"Dispositivo: {device_label}",
            f"Ruta dispositivo: {device_path}",
            f"Origen: {source_label}",
        ]
        if destination_label:
            lines.append(f"Destino: {destination_label}")
        lines.extend(
            [
                f"Inicio: {started_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Fin: {finished_at.strftime('%Y-%m-%d %H:%M:%S')}",
                f"Formato destino: {options.output_format.value.upper()}",
                f"Bitrate: {options.bitrate.description}",
                f"Sample rate: {options.sample_rate.description}",
                f"Metadatos: {'Si' if options.preserve_metadata else 'No'}",
                f"Carpeta salida: {options.output_dir}",
                f"Total: {batch.total} | Exito: {batch.success} | Fallos: {batch.failed} | Omitidos: {batch.skipped}",
                "",
                "Archivos:",
            ]
        )
        for result in batch.results:
            status = "OK" if result.success else "ERROR"
            out = result.output_path or "-"
            err = f" | {result.error_message}" if result.error_message else ""
            lines.append(
                f"  [{status}] {result.input_path.name} -> {out}"
                f" ({format_duration(result.duration)}){err}"
            )
        lines.append("")
        return "\n".join(lines)

    @staticmethod
    def format_pre_summary(
        *,
        device_label: str,
        device_path: Path,
        source_label: str,
        files: list[Path],
        options: ConversionOptions,
        destination_label: str = "",
    ) -> str:
        groups: dict[str, int] = {}
        total_size = 0
        for path in files:
            ext = path.suffix.lower().lstrip(".") or "?"
            groups[ext] = groups.get(ext, 0) + 1
            try:
                total_size += path.stat().st_size
            except OSError:
                pass

        lines = [
            f"Dispositivo: {device_label}",
            f"Ruta: {device_path}",
            f"Origen: {source_label}",
        ]
        if destination_label:
            lines.append(f"Destino: {destination_label}")
        lines.extend(
            [
                f"Archivos: {len(files)}",
                f"Tamaño total: {format_size(total_size)}",
                f"Formato destino: {options.output_format.value.upper()}",
                f"Bitrate: {options.bitrate.description}",
                f"Sample rate: {options.sample_rate.description}",
                f"Conservar metadatos: {'Sí' if options.preserve_metadata else 'No'}",
                f"Salida: {options.output_dir}",
                "Por formato origen:",
            ]
        )
        for ext, count in sorted(groups.items()):
            lines.append(f"  - {ext.upper()}: {count}")
        if len(files) <= 15:
            lines.append("Lista:")
            for path in files:
                lines.append(f"  - {path.name}")
        else:
            lines.append("Lista (primeros 15):")
            for path in files[:15]:
                lines.append(f"  - {path.name}")
            lines.append(f"  ... y {len(files) - 15} más")
        return "\n".join(lines)
