"""Gestión de FFmpeg y FFprobe."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


@dataclass
class FFmpegInfo:
    available: bool
    version: Optional[str] = None
    path: Optional[str] = None
    ffprobe_path: Optional[str] = None
    message: str = ""


@dataclass
class ProbeResult:
    success: bool
    duration: Optional[float] = None
    bitrate: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    codec: Optional[str] = None
    format_name: Optional[str] = None
    size_bytes: Optional[int] = None
    tags: Optional[dict] = None
    error_message: Optional[str] = None


class FFmpegManager:
    """Wrapper para operaciones con FFmpeg/FFprobe."""

    def __init__(self):
        self._info: Optional[FFmpegInfo] = None

    def check(self) -> FFmpegInfo:
        ffmpeg_path = shutil.which("ffmpeg")
        ffprobe_path = shutil.which("ffprobe")

        if not ffmpeg_path:
            self._info = FFmpegInfo(
                available=False,
                message="FFmpeg no está instalado o no está en el PATH",
            )
            return self._info

        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            version = "desconocida"
            if result.returncode == 0 and result.stdout:
                first = result.stdout.split("\n")[0]
                if "version" in first:
                    version = first.split("version")[1].split()[0]

            self._info = FFmpegInfo(
                available=True,
                version=version,
                path=ffmpeg_path,
                ffprobe_path=ffprobe_path,
                message="FFmpeg disponible",
            )
        except Exception as exc:
            self._info = FFmpegInfo(
                available=False,
                message=f"Error al verificar FFmpeg: {exc}",
            )
        return self._info

    @property
    def is_available(self) -> bool:
        if self._info is None:
            self.check()
        return bool(self._info and self._info.available)

    def probe(self, file_path: Path) -> ProbeResult:
        if not shutil.which("ffprobe"):
            return ProbeResult(success=False, error_message="ffprobe no está disponible")

        if not file_path.exists():
            return ProbeResult(success=False, error_message=f"Archivo no encontrado: {file_path}")

        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                str(file_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                return ProbeResult(
                    success=False,
                    error_message=result.stderr[:300] if result.stderr else "Error en ffprobe",
                )

            data = json.loads(result.stdout)
            fmt = data.get("format", {})
            streams = data.get("streams", [])
            audio_stream = next(
                (s for s in streams if s.get("codec_type") == "audio"),
                {},
            )

            bitrate = None
            raw_br = audio_stream.get("bit_rate") or fmt.get("bit_rate")
            if raw_br:
                try:
                    bitrate = int(int(raw_br) / 1000)
                except (TypeError, ValueError):
                    bitrate = None

            sample_rate = None
            if audio_stream.get("sample_rate"):
                try:
                    sample_rate = int(audio_stream["sample_rate"])
                except (TypeError, ValueError):
                    sample_rate = None

            channels = audio_stream.get("channels")
            duration = None
            if fmt.get("duration"):
                try:
                    duration = float(fmt["duration"])
                except (TypeError, ValueError):
                    duration = None

            size_bytes = None
            if fmt.get("size"):
                try:
                    size_bytes = int(fmt["size"])
                except (TypeError, ValueError):
                    size_bytes = None

            return ProbeResult(
                success=True,
                duration=duration,
                bitrate=bitrate,
                sample_rate=sample_rate,
                channels=channels,
                codec=audio_stream.get("codec_name"),
                format_name=fmt.get("format_name"),
                size_bytes=size_bytes,
                tags=fmt.get("tags") or {},
            )
        except subprocess.TimeoutExpired:
            return ProbeResult(success=False, error_message="Tiempo de análisis excedido")
        except json.JSONDecodeError:
            return ProbeResult(success=False, error_message="Respuesta inválida de ffprobe")
        except Exception as exc:
            return ProbeResult(success=False, error_message=str(exc))

    def run(
        self,
        cmd: list[str],
        timeout: int = 600,
    ) -> tuple[bool, str]:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode == 0:
                return True, ""
            err = (result.stderr or result.stdout or "Error desconocido de FFmpeg")[:500]
            return False, err
        except subprocess.TimeoutExpired:
            return False, "Tiempo de conversión excedido"
        except Exception as exc:
            return False, str(exc)

    def get_duration(self, file_path: Path) -> Optional[float]:
        probe = self.probe(file_path)
        return probe.duration if probe.success else None
