"""Tests básicos del validador."""

from pathlib import Path

from src.core.validator import Validator
from src.models.audio_file import AudioFormat


def test_validate_missing_file(tmp_path: Path):
    result = Validator.validate_file(tmp_path / "no_existe.mp3")
    assert result.valid is False


def test_validate_unsupported_extension(tmp_path: Path):
    fake = tmp_path / "archivo.txt"
    fake.write_text("hola", encoding="utf-8")
    result = Validator.validate_file(fake)
    assert result.valid is False


def test_validate_supported_extension(tmp_path: Path):
    fake = tmp_path / "cancion.mp3"
    fake.write_bytes(b"ID3")
    result = Validator.validate_file(fake)
    assert result.valid is True
    assert result.format == AudioFormat.MP3


def test_validate_output_format():
    result = Validator.validate_output_format("flac")
    assert result.valid is True
    assert result.format == AudioFormat.FLAC
