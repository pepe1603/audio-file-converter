"""Modelos de conversión de audio."""

from pathlib import Path
from typing import Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

from src.models.audio_file import AudioFormat, BitratePreset, SampleRatePreset


class ConversionStatus(str, Enum):
    """Estado de una conversión."""

    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class ConversionOptions(BaseModel):
    """Opciones de conversión."""

    output_format: AudioFormat
    bitrate: BitratePreset = BitratePreset.B192
    sample_rate: SampleRatePreset = SampleRatePreset.ORIGINAL
    preserve_metadata: bool = True
    output_dir: Optional[Path] = None
    flat_output: bool = False

    @field_validator("output_dir", mode="before")
    @classmethod
    def coerce_path(cls, value):
        return Path(value) if value is not None else value


class ConversionResult(BaseModel):
    """Resultado de una conversión individual."""

    success: bool
    input_path: Path
    output_path: Optional[Path] = None
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    bitrate: Optional[str] = None
    duration: Optional[float] = None
    error_message: Optional[str] = None
    status: ConversionStatus = ConversionStatus.PENDING

    @field_validator("input_path", "output_path", mode="before")
    @classmethod
    def coerce_path(cls, value):
        return Path(value) if value is not None else value


class ConversionRecord(BaseModel):
    """Registro de historial de conversión."""

    id: Optional[int] = None
    date: str = Field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    source_file: str
    destination_file: str
    source_format: str
    destination_format: str
    bitrate: Optional[str] = None
    sample_rate: Optional[str] = None
    status: str = ConversionStatus.SUCCESS.value
    duration: Optional[float] = None
    username: str = "Usuario"
    error_message: Optional[str] = None


class BatchConversionResult(BaseModel):
    """Resultado de una conversión por lotes."""

    total: int = 0
    success: int = 0
    failed: int = 0
    skipped: int = 0
    results: list[ConversionResult] = Field(default_factory=list)

    @property
    def all_success(self) -> bool:
        return self.failed == 0 and self.success > 0
