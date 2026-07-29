"""Validación de archivos y opciones de conversión."""

from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from src.models.audio_file import AudioFormat
from src.core.presets import INPUT_EXTENSIONS


@dataclass
class ValidationResult:
    valid: bool
    message: str = ""
    format: Optional[AudioFormat] = None


class Validator:
    """Validador de entradas de audio."""

    @staticmethod
    def validate_file(path: Path) -> ValidationResult:
        if not path:
            return ValidationResult(valid=False, message="Ruta vacía")

        resolved = Path(path).expanduser()
        if not resolved.exists():
            return ValidationResult(valid=False, message=f"El archivo no existe: {resolved}")

        if not resolved.is_file():
            return ValidationResult(valid=False, message=f"No es un archivo: {resolved}")

        ext = resolved.suffix.lower()
        if ext not in INPUT_EXTENSIONS:
            supported = ", ".join(sorted(INPUT_EXTENSIONS))
            return ValidationResult(
                valid=False,
                message=f"Formato no soportado: {ext}. Soportados: {supported}",
            )

        fmt = AudioFormat.from_extension(ext)
        return ValidationResult(valid=True, message="Archivo válido", format=fmt)

    @staticmethod
    def validate_directory(path: Path) -> ValidationResult:
        if not path:
            return ValidationResult(valid=False, message="Ruta vacía")

        resolved = Path(path).expanduser()
        if not resolved.exists():
            return ValidationResult(valid=False, message=f"La carpeta no existe: {resolved}")

        if not resolved.is_dir():
            return ValidationResult(valid=False, message=f"No es una carpeta: {resolved}")

        return ValidationResult(valid=True, message="Carpeta válida")

    @staticmethod
    def validate_output_format(fmt: str) -> ValidationResult:
        audio_fmt = AudioFormat.from_extension(fmt)
        if audio_fmt is None:
            return ValidationResult(valid=False, message=f"Formato de salida no soportado: {fmt}")
        return ValidationResult(valid=True, message="Formato válido", format=audio_fmt)
