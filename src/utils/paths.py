"""Gestión de rutas de la aplicación."""

import json
import os
import platform
import shutil
from pathlib import Path
from typing import Optional
from enum import Enum

from platformdirs import user_data_dir, user_config_dir


APP_NAME = "AudioConverter"
APP_AUTHOR = "AFC"


class EnvironmentType(Enum):
    TERMUX = "termux"
    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"
    UNKNOWN = "unknown"


class PathManager:
    """Administra rutas de datos, configuración y salidas."""

    FORMAT_FOLDERS = ("mp3", "flac", "wav", "ogg", "opus", "m4a", "aac", "aiff", "wma")

    def __init__(self):
        self.env_type = self._detect_environment()
        self.base_path = self._resolve_base_path()
        self.config_path = self._resolve_config_path()
        self.config_file = self.config_path / "config.json"
        self._config: dict = {}
        self._load_config()
        self.ensure_directories()

    def _detect_environment(self) -> EnvironmentType:
        if "TERMUX_VERSION" in os.environ or Path("/data/data/com.termux").exists():
            return EnvironmentType.TERMUX
        system = platform.system().lower()
        if system == "windows":
            return EnvironmentType.WINDOWS
        if system == "darwin":
            return EnvironmentType.MACOS
        if system == "linux":
            return EnvironmentType.LINUX
        return EnvironmentType.UNKNOWN

    def _resolve_base_path(self) -> Path:
        if self.env_type == EnvironmentType.TERMUX:
            storage = Path("/storage/emulated/0")
            if storage.exists() and os.access(storage, os.W_OK):
                return storage / APP_NAME
            return Path.home() / APP_NAME
        return Path.home() / APP_NAME

    def _resolve_config_path(self) -> Path:
        if self.env_type == EnvironmentType.TERMUX:
            return Path.home() / ".config" / "audio-file-converter"
        return Path(user_config_dir(APP_NAME, APP_AUTHOR))

    @property
    def display_name(self) -> str:
        names = {
            EnvironmentType.TERMUX: "Móvil (Termux/Android)",
            EnvironmentType.WINDOWS: "Computadora (Windows)",
            EnvironmentType.LINUX: "Computadora (Linux)",
            EnvironmentType.MACOS: "Computadora (macOS)",
            EnvironmentType.UNKNOWN: "Sistema desconocido",
        }
        return names[self.env_type]

    @property
    def is_mobile(self) -> bool:
        return self.env_type == EnvironmentType.TERMUX

    @property
    def converted_dir(self) -> Path:
        custom = self._config.get("output_dir")
        if custom:
            return Path(custom)
        return self.base_path / "converted"

    @property
    def exports_dir(self) -> Path:
        return self.base_path / "exports"

    @property
    def database_dir(self) -> Path:
        return self.base_path / "database"

    @property
    def logs_dir(self) -> Path:
        return self.base_path / "logs"

    @property
    def database_path(self) -> Path:
        return self.database_dir / "afc.db"

    def format_dir(self, fmt: str) -> Path:
        return self.converted_dir / fmt.lower()

    def ensure_directories(self) -> None:
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.config_path.mkdir(parents=True, exist_ok=True)
        self.converted_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.database_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        for folder in self.FORMAT_FOLDERS:
            (self.converted_dir / folder).mkdir(parents=True, exist_ok=True)

    def _load_config(self) -> None:
        if self.config_file.exists():
            try:
                self._config = json.loads(self.config_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                self._config = {}
        else:
            self._config = {
                "output_dir": str(self.base_path / "converted"),
                "default_format": "mp3",
                "default_bitrate": "192k",
                "default_sample_rate": "original",
                "preserve_metadata": True,
                "username": "Usuario",
            }
            self._save_config()

    def _save_config(self) -> None:
        self.config_path.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(
            json.dumps(self._config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def get(self, key: str, default=None):
        return self._config.get(key, default)

    def set(self, key: str, value) -> None:
        self._config[key] = value
        self._save_config()

    def set_output_dir(self, path: Path) -> Path:
        resolved = Path(path).expanduser().resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        for folder in self.FORMAT_FOLDERS:
            (resolved / folder).mkdir(parents=True, exist_ok=True)
        self.set("output_dir", str(resolved))
        return resolved

    def reset_config(self) -> None:
        self._config = {
            "output_dir": str(self.base_path / "converted"),
            "default_format": "mp3",
            "default_bitrate": "192k",
            "default_sample_rate": "original",
            "preserve_metadata": True,
            "username": self._config.get("username", "Usuario"),
        }
        self._save_config()
        self.ensure_directories()

    @property
    def username(self) -> str:
        return self._config.get("username", "Usuario")

    @username.setter
    def username(self, value: str) -> None:
        self.set("username", value)
