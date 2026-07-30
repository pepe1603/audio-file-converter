"""Tests de utilidades."""

from io import StringIO
from pathlib import Path

from rich.console import Console

from src.ui.console import print_entrance_banner, print_exit_banner
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


def test_print_exit_banner_renders():
    buf = StringIO()
    c = Console(file=buf, force_terminal=True, width=80, color_system=None)
    print_exit_banner(
        "Audio File Converter",
        "1.1.0",
        "Tester",
        12,
        env_name="Windows",
        target_console=c,
    )
    text = buf.getvalue()
    assert "Audio File Converter" in text
    assert "SESIÓN FINALIZADA" in text or "SESION FINALIZADA" in text
    assert "Tester" in text


def test_print_entrance_banner_renders():
    buf = StringIO()
    c = Console(file=buf, force_terminal=True, width=80, color_system=None)
    print_entrance_banner(
        "Audio File Converter",
        "1.1.0",
        "Tester",
        env_name="Windows",
        data_path="C:/data",
        ffmpeg_ok=True,
        ffmpeg_label="7.0",
        total_conversions=3,
        target_console=c,
    )
    text = buf.getvalue()
    assert "Audio File Converter" in text
    assert "SESIÓN INICIADA" in text or "SESION INICIADA" in text
    assert "Tester" in text
