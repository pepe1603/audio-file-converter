"""Tests de dispositivos extraíbles y profundidad de árbol."""

from datetime import datetime
from pathlib import Path

from src.core.removable import MAX_TREE_DEPTH, RemovableMediaManager
from src.core.session_report import SessionReportWriter
from src.models.audio_file import AudioFormat, BitratePreset, SampleRatePreset
from src.models.conversion import BatchConversionResult, ConversionOptions, ConversionResult
from src.utils.paths import USB_CONVERTED_PREFIX, PathManager


def _make_tree(root: Path) -> None:
    # root/a/b/c/d/e/f
    deep = root
    for name in ["a", "b", "c", "d", "e", "f"]:
        deep = deep / name
        deep.mkdir(parents=True, exist_ok=True)
    (root / "song.mp3").write_bytes(b"ID3")
    (root / "a" / "track.wav").write_bytes(b"RIFF")
    (root / "a" / "b" / "c" / "d" / "e" / "deep.flac").write_bytes(b"fLaC")
    (root / "a" / "b" / "c" / "d" / "e" / "f" / "too_deep.mp3").write_bytes(b"ID3")


def test_depth_from_root(tmp_path: Path):
    mgr = RemovableMediaManager(max_depth=5)
    _make_tree(tmp_path)
    assert mgr.depth_from_root(tmp_path, tmp_path) == 0
    assert mgr.depth_from_root(tmp_path, tmp_path / "a" / "b") == 2
    assert mgr.depth_from_root(tmp_path, tmp_path / "a" / "b" / "c" / "d" / "e") == 5


def test_can_enter_respects_max_depth(tmp_path: Path):
    mgr = RemovableMediaManager(max_depth=5)
    _make_tree(tmp_path)
    assert mgr.can_enter(tmp_path, tmp_path / "a" / "b" / "c" / "d" / "e") is True
    assert mgr.can_enter(tmp_path, tmp_path / "a" / "b" / "c" / "d" / "e" / "f") is False


def test_scan_audio_max_depth(tmp_path: Path):
    mgr = RemovableMediaManager(max_depth=5)
    _make_tree(tmp_path)
    files = mgr.scan_audio(tmp_path, tmp_path, recursive=True)
    names = {p.name for p in files}
    assert "song.mp3" in names
    assert "track.wav" in names
    assert "deep.flac" in names
    assert "too_deep.mp3" not in names


def test_list_directory_filters_audio(tmp_path: Path):
    mgr = RemovableMediaManager(max_depth=5)
    (tmp_path / "ok.mp3").write_bytes(b"ID3")
    (tmp_path / "no.txt").write_text("x", encoding="utf-8")
    (tmp_path / "folder").mkdir()
    entries = mgr.list_directory(tmp_path, tmp_path)
    names = {e.name for e in entries}
    assert "ok.mp3" in names
    assert "folder" in names
    assert "no.txt" not in names


def test_session_report_create_and_update(tmp_path: Path):
    writer = SessionReportWriter(tmp_path / "exports")
    options = ConversionOptions(
        output_format=AudioFormat.MP3,
        bitrate=BitratePreset.B192,
        sample_rate=SampleRatePreset.ORIGINAL,
        preserve_metadata=True,
        output_dir=tmp_path / "out",
    )
    src = tmp_path / "a.wav"
    src.write_bytes(b"RIFF")
    result = ConversionResult(
        success=True,
        input_path=src,
        output_path=tmp_path / "out" / "mp3" / "a.mp3",
        input_format="wav",
        output_format="mp3",
        bitrate="192k",
        duration=1.0,
        status="success",
    )
    batch = BatchConversionResult(total=1, success=1, failed=0, skipped=0, results=[result])
    from datetime import datetime

    md1, txt1 = writer.write_session(
        device_label="USB TEST",
        device_path=tmp_path,
        source_label="Archivo: a.wav",
        files=[src],
        options=options,
        batch=batch,
        username="Tester",
        started_at=datetime.now(),
    )
    assert md1.exists() and txt1.exists()
    content1 = md1.read_text(encoding="utf-8")
    assert "USB TEST" in content1
    assert "a.wav" in content1

    writer.write_session(
        device_label="USB TEST",
        device_path=tmp_path,
        source_label="Archivo: a.wav",
        files=[src],
        options=options,
        batch=batch,
        username="Tester",
        started_at=datetime.now(),
    )
    content2 = md1.read_text(encoding="utf-8")
    assert content2.count("## Sesión") == 2
    assert MAX_TREE_DEPTH == 5


def test_removable_pc_session_dir(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(PathManager, "_detect_environment", lambda self: __import__(
        "src.utils.paths", fromlist=["EnvironmentType"]
    ).EnvironmentType.WINDOWS)
    monkeypatch.setattr(PathManager, "_resolve_base_path", lambda self: tmp_path / "AudioConverter")
    monkeypatch.setattr(
        PathManager,
        "_resolve_config_path",
        lambda self: tmp_path / "config",
    )
    paths = PathManager()
    when = datetime(2026, 7, 30, 14, 30, 0)
    session = paths.removable_pc_session_dir("USB TEST", when=when, create=True)
    assert session == paths.converted_dir / "from_removable" / "USB_TEST" / "2026-07-30_143000"
    assert session.is_dir()


def test_removable_usb_session_dir_single_file(tmp_path: Path):
    music = tmp_path / "Music"
    music.mkdir()
    src = music / "song.wav"
    src.write_bytes(b"RIFF")
    when = datetime(2026, 7, 30, 14, 30, 0)
    session = PathManager.removable_usb_session_dir(
        [src], tmp_path, when=when, create=True
    )
    assert session == music / f"{USB_CONVERTED_PREFIX}_20260730_143000"
    assert session.is_dir()


def test_removable_usb_session_dir_common_parent(tmp_path: Path):
    album = tmp_path / "Album"
    (album / "a").mkdir(parents=True)
    (album / "b").mkdir(parents=True)
    f1 = album / "a" / "1.mp3"
    f2 = album / "b" / "2.mp3"
    f1.write_bytes(b"ID3")
    f2.write_bytes(b"ID3")
    when = datetime(2026, 1, 2, 3, 4, 5)
    session = PathManager.removable_usb_session_dir(
        [f1, f2], tmp_path, when=when, create=False
    )
    assert session == album / f"{USB_CONVERTED_PREFIX}_20260102_030405"
    assert not session.exists()
