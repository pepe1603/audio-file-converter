"""Tests de utilidades."""

from pathlib import Path

from src.utils.helpers import format_duration, format_size, sanitize_filename, unique_path


def test_format_duration():
    assert format_duration(None) == "N/A"
    assert format_duration(65) == "01:05"
    assert format_duration(3661) == "01:01:01"


def test_format_size():
    assert format_size(None) == "N/A"
    assert format_size(512) == "512.00 B"
    assert "KB" in format_size(2048)


def test_sanitize_filename():
    assert sanitize_filename('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"


def test_unique_path(tmp_path: Path):
    path = tmp_path / "audio.mp3"
    path.write_text("x", encoding="utf-8")
    alt = unique_path(path)
    assert alt != path
    assert alt.name == "audio_1.mp3"
