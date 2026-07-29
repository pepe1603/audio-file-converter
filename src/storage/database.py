"""Base de datos SQLite para historial de conversiones."""

import sqlite3
from pathlib import Path
from typing import Optional

from src.models.conversion import ConversionRecord


class Database:
    """Gestor SQLite del historial AFC."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_database(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    source_file TEXT NOT NULL,
                    destination_file TEXT NOT NULL,
                    source_format TEXT NOT NULL,
                    destination_format TEXT NOT NULL,
                    bitrate TEXT,
                    sample_rate TEXT,
                    status TEXT NOT NULL,
                    duration REAL,
                    username TEXT,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.commit()

    def add_conversion(self, record: ConversionRecord) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversions (
                    date, source_file, destination_file, source_format,
                    destination_format, bitrate, sample_rate, status,
                    duration, username, error_message
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.date,
                    record.source_file,
                    record.destination_file,
                    record.source_format,
                    record.destination_format,
                    record.bitrate,
                    record.sample_rate,
                    record.status,
                    record.duration,
                    record.username,
                    record.error_message,
                ),
            )
            conn.commit()
            return int(cursor.lastrowid)

    def get_recent(self, limit: int = 20) -> list[ConversionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM conversions
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def search(
        self,
        format_filter: Optional[str] = None,
        status: Optional[str] = None,
        text: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
    ) -> list[ConversionRecord]:
        query = "SELECT * FROM conversions WHERE 1=1"
        params: list = []

        if format_filter:
            query += " AND destination_format = ?"
            params.append(format_filter.lower())
        if status:
            query += " AND status = ?"
            params.append(status)
        if text:
            query += " AND (source_file LIKE ? OR destination_file LIKE ?)"
            params.extend([f"%{text}%", f"%{text}%"])
        if date_from:
            query += " AND date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND date <= ?"
            params.append(date_to)

        query += " ORDER BY created_at DESC"

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get_total(self) -> int:
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS c FROM conversions").fetchone()
        return int(row["c"]) if row else 0

    def get_stats_by_format(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT destination_format, COUNT(*) AS c
                FROM conversions
                GROUP BY destination_format
                ORDER BY c DESC
                """
            ).fetchall()
        return {row["destination_format"]: row["c"] for row in rows}

    def get_stats_by_status(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT status, COUNT(*) AS c
                FROM conversions
                GROUP BY status
                """
            ).fetchall()
        return {row["status"]: row["c"] for row in rows}

    def delete_failed(self) -> int:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM conversions WHERE status = 'failed'")
            conn.commit()
            return cursor.rowcount

    def get_setting(self, key: str) -> Optional[str]:
        with self._connect() as conn:
            row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else None

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (key, value),
            )
            conn.commit()

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> ConversionRecord:
        return ConversionRecord(
            id=row["id"],
            date=row["date"],
            source_file=row["source_file"],
            destination_file=row["destination_file"],
            source_format=row["source_format"],
            destination_format=row["destination_format"],
            bitrate=row["bitrate"],
            sample_rate=row["sample_rate"],
            status=row["status"],
            duration=row["duration"],
            username=row["username"] or "Usuario",
            error_message=row["error_message"],
        )
