"""Modelos de archivo de audio."""

from pathlib import Path
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class AudioFormat(str, Enum):
    """Formatos de audio soportados."""

    MP3 = "mp3"
    FLAC = "flac"
    AAC = "aac"
    OGG = "ogg"
    M4A = "m4a"
    WAV = "wav"
    AIFF = "aiff"
    OPUS = "opus"
    WMA = "wma"

    @property
    def description(self) -> str:
        descriptions = {
            AudioFormat.MP3: "MP3 (Compatible)",
            AudioFormat.FLAC: "FLAC (Sin pérdida)",
            AudioFormat.AAC: "AAC (Alta eficiencia)",
            AudioFormat.OGG: "OGG Vorbis (Código abierto)",
            AudioFormat.M4A: "M4A (Apple/iOS)",
            AudioFormat.WAV: "WAV (Sin comprimir)",
            AudioFormat.AIFF: "AIFF (Apple sin comprimir)",
            AudioFormat.OPUS: "OPUS (Baja latencia)",
            AudioFormat.WMA: "WMA (Windows Media)",
        }
        return descriptions[self]

    @property
    def extension(self) -> str:
        return f".{self.value}"

    @property
    def is_lossy(self) -> bool:
        return self not in (AudioFormat.FLAC, AudioFormat.WAV, AudioFormat.AIFF)

    @classmethod
    def from_extension(cls, ext: str) -> Optional["AudioFormat"]:
        clean = ext.lower().lstrip(".")
        try:
            return cls(clean)
        except ValueError:
            return None

    @classmethod
    def supported_extensions(cls) -> set[str]:
        return {f".{fmt.value}" for fmt in cls}


class BitratePreset(str, Enum):
    """Presets de bitrate."""

    B128 = "128k"
    B192 = "192k"
    B256 = "256k"
    B320 = "320k"
    ORIGINAL = "original"

    @property
    def description(self) -> str:
        descriptions = {
            BitratePreset.B128: "128 kbps",
            BitratePreset.B192: "192 kbps",
            BitratePreset.B256: "256 kbps",
            BitratePreset.B320: "320 kbps",
            BitratePreset.ORIGINAL: "Mantener original",
        }
        return descriptions[self]


class SampleRatePreset(str, Enum):
    """Presets de frecuencia de muestreo."""

    R44100 = "44100"
    R48000 = "48000"
    ORIGINAL = "original"

    @property
    def description(self) -> str:
        descriptions = {
            SampleRatePreset.R44100: "44100 Hz",
            SampleRatePreset.R48000: "48000 Hz",
            SampleRatePreset.ORIGINAL: "Mantener original",
        }
        return descriptions[self]


class AudioMetadata(BaseModel):
    """Metadatos de un archivo de audio."""

    title: Optional[str] = None
    artist: Optional[str] = None
    album: Optional[str] = None
    year: Optional[str] = None
    genre: Optional[str] = None
    track: Optional[str] = None
    comment: Optional[str] = None
    cover_path: Optional[Path] = None


class AudioInfo(BaseModel):
    """Información técnica de un archivo de audio."""

    path: Path
    name: str
    format: Optional[AudioFormat] = None
    duration: Optional[float] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    codec: Optional[str] = None
    size_bytes: Optional[int] = None
    metadata: AudioMetadata = Field(default_factory=AudioMetadata)

    @field_validator("path", mode="before")
    @classmethod
    def coerce_path(cls, value):
        return Path(value) if value is not None else value

    @property
    def duration_str(self) -> str:
        if self.duration is None:
            return "N/A"
        total = int(self.duration)
        minutes, seconds = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    @property
    def bitrate_str(self) -> str:
        if self.bitrate is None:
            return "N/A"
        return f"{self.bitrate} kbps"

    @property
    def channels_str(self) -> str:
        if self.channels is None:
            return "N/A"
        if self.channels == 1:
            return "Mono"
        if self.channels == 2:
            return "Stereo"
        return f"{self.channels} canales"

    @property
    def size_str(self) -> str:
        if self.size_bytes is None:
            return "N/A"
        size = float(self.size_bytes)
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"
