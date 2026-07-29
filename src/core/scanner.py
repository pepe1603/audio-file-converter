"""Escáner de archivos de audio."""

from pathlib import Path

from src.core.presets import INPUT_EXTENSIONS


class AudioScanner:
    """Escanea carpetas en busca de archivos de audio soportados."""

    def __init__(self, recursive: bool = True):
        self.recursive = recursive

    def scan(self, directory: Path) -> list[Path]:
        directory = Path(directory).expanduser()
        if not directory.exists() or not directory.is_dir():
            return []

        files: list[Path] = []
        pattern_iter = directory.rglob("*") if self.recursive else directory.glob("*")
        for path in pattern_iter:
            if path.is_file() and path.suffix.lower() in INPUT_EXTENSIONS:
                files.append(path)

        return sorted(files, key=lambda p: str(p).lower())

    def count(self, directory: Path) -> int:
        return len(self.scan(directory))

    def group_by_format(self, files: list[Path]) -> dict[str, list[Path]]:
        groups: dict[str, list[Path]] = {}
        for path in files:
            ext = path.suffix.lower().lstrip(".")
            groups.setdefault(ext, []).append(path)
        return groups
