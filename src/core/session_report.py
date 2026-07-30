"""Reporte único de conversiones (TXT o Markdown, según preferencia)."""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from src.models.conversion import BatchConversionResult, ConversionOptions, ConversionResult
from src.utils.helpers import format_duration, format_size


class ReportFormat(str, Enum):
    MD = "md"
    TXT = "txt"

    @property
    def extension(self) -> str:
        return self.value

    @property
    def label(self) -> str:
        return "Markdown" if self is ReportFormat.MD else "TXT"

    @classmethod
    def from_config(cls, value: Optional[str]) -> "ReportFormat":
        raw = (value or "md").strip().lower()
        if raw in {"txt", "text", "plain"}:
            return cls.TXT
        return cls.MD


class SessionReportWriter:
    """Mantiene un único archivo de reporte acumulativo en el formato elegido."""

    SUMMARY_STEM = "conversion_report"

    def __init__(self, exports_dir: Path, report_format: ReportFormat = ReportFormat.MD):
        self.exports_dir = Path(exports_dir)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.report_format = report_format
        self.report_path = self.exports_dir / f"{self.SUMMARY_STEM}.{report_format.extension}"

    def write_session(
        self,
        *,
        mode: str,
        source_label: str,
        files: list[Path],
        options: ConversionOptions,
        batch: BatchConversionResult,
        username: str,
        started_at: datetime,
        finished_at: Optional[datetime] = None,
        device_label: str = "",
        device_path: Optional[Path] = None,
        destination_label: str = "",
        write_session_copy: bool = False,
    ) -> Path:
        finished_at = finished_at or datetime.now()
        stamp = finished_at.strftime("%Y-%m-%d %H:%M:%S")

        if self.report_format is ReportFormat.MD:
            block = self._build_markdown(
                stamp=stamp,
                mode=mode,
                source_label=source_label,
                options=options,
                batch=batch,
                username=username,
                started_at=started_at,
                finished_at=finished_at,
                device_label=device_label,
                device_path=device_path,
                destination_label=destination_label,
            )
            self._append_md(block)
        else:
            block = self._build_txt(
                stamp=stamp,
                mode=mode,
                source_label=source_label,
                options=options,
                batch=batch,
                username=username,
                started_at=started_at,
                finished_at=finished_at,
                device_label=device_label,
                device_path=device_path,
                destination_label=destination_label,
            )
            self._append_txt(block)

        if write_session_copy:
            session_stamp = finished_at.strftime("%Y%m%d_%H%M%S")
            session_path = (
                self.exports_dir
                / f"session_{session_stamp}.{self.report_format.extension}"
            )
            session_path.write_text(block, encoding="utf-8")

        return self.report_path

    def _append_md(self, block: str) -> None:
        if not self.report_path.exists():
            header = (
                "# Reporte de conversiones — Audio File Converter\n\n"
                "Archivo único actualizado automáticamente.\n\n"
                "---\n\n"
            )
            self.report_path.write_text(header + block, encoding="utf-8")
        else:
            with open(self.report_path, "a", encoding="utf-8") as f:
                f.write("\n---\n\n")
                f.write(block)

    def _append_txt(self, block: str) -> None:
        if not self.report_path.exists():
            header = (
                "REPORTE DE CONVERSIONES — Audio File Converter\n"
                "Archivo unico actualizado automaticamente.\n"
                f"{'=' * 60}\n\n"
            )
            self.report_path.write_text(header + block, encoding="utf-8")
        else:
            with open(self.report_path, "a", encoding="utf-8") as f:
                f.write("\n" + "=" * 60 + "\n\n")
                f.write(block)

    def _build_markdown(
        self,
        *,
        stamp: str,
        mode: str,
        source_label: str,
        options: ConversionOptions,
        batch: BatchConversionResult,
        username: str,
        started_at: datetime,
        finished_at: datetime,
        device_label: str = "",
        device_path: Optional[Path] = None,
        destination_label: str = "",
    ) -> str:
        lines = [
            f"## Sesión {stamp}",
            "",
            f"- **Modo:** {mode}",
            f"- **Usuario:** {username}",
            f"- **Origen:** {source_label}",
        ]
        if device_label:
            lines.append(f"- **Dispositivo:** {device_label}")
        if device_path is not None:
            lines.append(f"- **Ruta dispositivo:** `{device_path}`")
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
        mode: str,
        source_label: str,
        options: ConversionOptions,
        batch: BatchConversionResult,
        username: str,
        started_at: datetime,
        finished_at: datetime,
        device_label: str = "",
        device_path: Optional[Path] = None,
        destination_label: str = "",
    ) -> str:
        lines = [
            f"SESION {stamp}",
            f"Modo: {mode}",
            f"Usuario: {username}",
            f"Origen: {source_label}",
        ]
        if device_label:
            lines.append(f"Dispositivo: {device_label}")
        if device_path is not None:
            lines.append(f"Ruta dispositivo: {device_path}")
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
                (
                    f"Total: {batch.total} | Exito: {batch.success} | "
                    f"Fallos: {batch.failed} | Omitidos: {batch.skipped}"
                ),
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
    def batch_from_result(result: ConversionResult) -> BatchConversionResult:
        batch = BatchConversionResult(total=1, results=[result])
        if result.success:
            batch.success = 1
        else:
            batch.failed = 1
        return batch

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
