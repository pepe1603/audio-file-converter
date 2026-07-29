"""Servicio de historial de conversiones."""

from typing import Optional

from src.models.conversion import ConversionRecord, ConversionResult, ConversionStatus
from src.storage.database import Database


class HistoryService:
    """Capa de servicio sobre la base de datos de historial."""

    def __init__(self, database: Database):
        self.db = database

    def add_from_result(
        self,
        result: ConversionResult,
        username: str = "Usuario",
        sample_rate: Optional[str] = None,
    ) -> int:
        record = ConversionRecord(
            source_file=str(result.input_path),
            destination_file=str(result.output_path) if result.output_path else "",
            source_format=result.input_format or "",
            destination_format=result.output_format or "",
            bitrate=result.bitrate,
            sample_rate=sample_rate,
            status=result.status.value if isinstance(result.status, ConversionStatus) else str(result.status),
            duration=result.duration,
            username=username,
            error_message=result.error_message,
        )
        return self.db.add_conversion(record)

    def recent(self, limit: int = 20) -> list[ConversionRecord]:
        return self.db.get_recent(limit)

    def search(
        self,
        format_filter: Optional[str] = None,
        status: Optional[str] = None,
        text: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[ConversionRecord]:
        return self.db.search(
            format_filter=format_filter,
            status=status,
            text=text,
            date_from=date_from,
            date_to=date_to,
        )

    def total(self) -> int:
        return self.db.get_total()

    def stats_by_format(self) -> dict[str, int]:
        return self.db.get_stats_by_format()

    def stats_by_status(self) -> dict[str, int]:
        return self.db.get_stats_by_status()

    def clear_failed(self) -> int:
        return self.db.delete_failed()

    def all_records(self, limit: int = 10000) -> list[ConversionRecord]:
        return self.db.get_recent(limit)
