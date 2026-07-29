"""Exportación del historial de conversiones."""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console

from src.models.conversion import ConversionRecord
from src.utils.helpers import format_duration


class HistoryExporter:
    """Exporta el historial a TXT, Markdown y JSON."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def export_to_txt(self, records: list[ConversionRecord], output_path: Path) -> bool:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write("HISTORIAL DE CONVERSIONES - Audio File Converter\n")
                f.write("=" * 60 + "\n")
                f.write(f"Fecha de exportación: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Total de conversiones: {len(records)}\n")
                f.write("=" * 60 + "\n\n")

                for i, record in enumerate(records, 1):
                    f.write(f"[{i}] {Path(record.source_file).name}\n")
                    f.write(f"    Fecha: {record.date}\n")
                    f.write(f"    Origen: {record.source_format} -> {record.destination_format}\n")
                    f.write(f"    Bitrate: {record.bitrate or 'N/A'}\n")
                    f.write(f"    Estado: {record.status}\n")
                    f.write(f"    Duración: {format_duration(record.duration)}\n")
                    f.write(f"    Destino: {record.destination_file}\n")
                    f.write(f"    Usuario: {record.username}\n")
                    if record.error_message:
                        f.write(f"    Error: {record.error_message}\n")
                    f.write("\n")

                f.write("=" * 60 + "\n")
                f.write("Fin del reporte\n")
            return True
        except Exception as exc:
            self.console.print(f"[red]Error al exportar a TXT: {exc}[/red]")
            return False

    def export_to_markdown(self, records: list[ConversionRecord], output_path: Path) -> bool:
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("# Historial de Conversiones\n\n")
                f.write(f"**Fecha de exportación:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
                f.write(f"**Total de conversiones:** {len(records)}\n\n")
                f.write("---\n\n")

                for i, record in enumerate(records, 1):
                    name = Path(record.source_file).name
                    f.write(f"## {i}. {name}\n\n")
                    f.write(f"- **Fecha:** {record.date}\n")
                    f.write(f"- **Formato:** {record.source_format} → {record.destination_format}\n")
                    f.write(f"- **Bitrate:** {record.bitrate or 'N/A'}\n")
                    f.write(f"- **Estado:** {record.status}\n")
                    f.write(f"- **Duración:** {format_duration(record.duration)}\n")
                    f.write(f"- **Origen:** `{record.source_file}`\n")
                    f.write(f"- **Destino:** `{record.destination_file}`\n")
                    f.write(f"- **Usuario:** {record.username}\n\n")

                f.write("---\n\n")
                f.write("*Generado por Audio File Converter*\n")
            return True
        except Exception as exc:
            self.console.print(f"[red]Error al exportar a Markdown: {exc}[/red]")
            return False

    def export_to_json(self, records: list[ConversionRecord], output_path: Path) -> bool:
        try:
            data = {
                "export_date": datetime.now().isoformat(),
                "total_conversions": len(records),
                "conversions": [
                    {
                        "id": r.id,
                        "date": r.date,
                        "source_file": r.source_file,
                        "destination_file": r.destination_file,
                        "source_format": r.source_format,
                        "destination_format": r.destination_format,
                        "bitrate": r.bitrate,
                        "sample_rate": r.sample_rate,
                        "status": r.status,
                        "duration": r.duration,
                        "username": r.username,
                        "error_message": r.error_message,
                    }
                    for r in records
                ],
            }
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as exc:
            self.console.print(f"[red]Error al exportar a JSON: {exc}[/red]")
            return False
