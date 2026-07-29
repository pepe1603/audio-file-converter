"""Escáner de archivos de audio."""

from pathlib import Path
from typing import Optional

from src.core.presets import INPUT_EXTENSIONS


class AudioScanner:
    """Escanea carpetas en busca de archivos de audio soportados."""

    def __init__(self, recursive: bool = True, max_depth: Optional[int] = None):
        self.recursive = recursive
        self.max_depth = max_depth

    def scan(self, directory: Path, root: Optional[Path] = None) -> list[Path]:
        directory = Path(directory).expanduser()
        if not directory.exists() or not directory.is_dir():
            return []

        if self.max_depth is None and root is None:
            files: list[Path] = []
            pattern_iter = directory.rglob("*") if self.recursive else directory.glob("*")
            for path in pattern_iter:
                if path.is_file() and path.suffix.lower() in INPUT_EXTENSIONS:
                    files.append(path)
            return sorted(files, key=lambda p: str(p).lower())

        return self._scan_with_depth(directory, root or directory)

    def _scan_with_depth(self, directory: Path, root: Path) -> list[Path]:
        max_depth = self.max_depth if self.max_depth is not None else 10_000
        files: list[Path] = []

        def walk(current: Path, depth: int) -> None:
            if depth > max_depth:
                return
            try:
                items = list(current.iterdir())
            except OSError:
                return
            for item in items:
                try:
                    if item.is_file() and item.suffix.lower() in INPUT_EXTENSIONS:
                        files.append(item)
                    elif self.recursive and item.is_dir() and depth < max_depth:
                        walk(item, depth + 1)
                except OSError:
                    continue

        try:
            start_depth = len(directory.resolve().relative_to(root.resolve()).parts)
        except (OSError, ValueError):
            start_depth = 0

        walk(directory, start_depth)
        return sorted(files, key=lambda p: str(p).lower())

    def count(self, directory: Path) -> int:
        return len(self.scan(directory))

    def group_by_format(self, files: list[Path]) -> dict[str, list[Path]]:
        groups: dict[str, list[Path]] = {}
        for path in files:
            ext = path.suffix.lower().lstrip(".")
            groups.setdefault(ext, []).append(path)
        return groups
