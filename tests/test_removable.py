"""Tests de dispositivos extraíbles y profundidad de árbol."""

from pathlib import Path

from src.core.removable import MAX_TREE_DEPTH, RemovableMediaManager
from src.core.session_report import SessionReportWriter
from src.models.audio_file import AudioFormat, BitratePreset, SampleRatePreset
from src.models.conversion import BatchConversionResult, ConversionOptions, ConversionResult


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
