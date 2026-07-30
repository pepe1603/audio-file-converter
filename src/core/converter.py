"""Motor de conversión de audio con FFmpeg."""

from pathlib import Path
from typing import Callable, Optional

from rich.console import Console

from src.models.audio_file import AudioFormat, BitratePreset, SampleRatePreset
from src.models.conversion import (
    ConversionOptions,
    ConversionResult,
    ConversionStatus,
    BatchConversionResult,
)
from src.core.ffmpeg_manager import FFmpegManager
from src.core.metadata import MetadataHandler
from src.core.presets import CODEC_MAP, LOSSLESS_FORMATS, DEFAULT_BITRATE
from src.core.validator import Validator
from src.utils.helpers import unique_path
from src.utils.logger import setup_logger


class AudioConverter:
    """Conversor de archivos de audio."""

    def __init__(
        self,
        console: Optional[Console] = None,
        ffmpeg: Optional[FFmpegManager] = None,
        metadata_handler: Optional[MetadataHandler] = None,
        default_output_dir: Optional[Path] = None,
    ):
        self.console = console or Console()
        self.ffmpeg = ffmpeg or FFmpegManager()
        self.metadata = metadata_handler or MetadataHandler(self.console, self.ffmpeg)
        self.default_output_dir = default_output_dir
        self.logger = setup_logger()

    def convert(
        self,
        input_path: Path,
        options: ConversionOptions,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> ConversionResult:
        input_path = Path(input_path).expanduser()
        validation = Validator.validate_file(input_path)
        if not validation.valid:
            return ConversionResult(
                success=False,
                input_path=input_path,
                error_message=validation.message,
                status=ConversionStatus.FAILED,
            )

        if not self.ffmpeg.is_available:
            return ConversionResult(
                success=False,
                input_path=input_path,
                error_message="FFmpeg no está disponible",
                status=ConversionStatus.FAILED,
            )

        output_path = self._resolve_output_path(input_path, options)
        cmd = self._build_command(input_path, output_path, options)

        self.logger.info("Convirtiendo %s -> %s", input_path, output_path)
        if progress_callback:
            progress_callback(0.1)

        ok, error = self.ffmpeg.run(cmd)
        if progress_callback:
            progress_callback(0.85)

        if not ok or not output_path.exists():
            self.logger.error("Fallo conversión: %s", error)
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                input_format=input_path.suffix.lstrip(".").lower(),
                output_format=options.output_format.value,
                bitrate=options.bitrate.value,
                error_message=error or "No se generó el archivo de salida",
                status=ConversionStatus.FAILED,
            )

        if options.preserve_metadata:
            try:
                self.metadata.copy_metadata(input_path, output_path)
            except Exception as exc:
                self.logger.warning("No se pudieron copiar metadatos: %s", exc)

        if progress_callback:
            progress_callback(1.0)

        probe = self.ffmpeg.probe(output_path)
        return ConversionResult(
            success=True,
            input_path=input_path,
            output_path=output_path,
            input_format=input_path.suffix.lstrip(".").lower(),
            output_format=options.output_format.value,
            bitrate=options.bitrate.value,
            duration=probe.duration if probe.success else None,
            status=ConversionStatus.SUCCESS,
        )

    def convert_batch(
        self,
        files: list[Path],
        options: ConversionOptions,
        progress_callback: Optional[Callable[[int, int, Path], None]] = None,
    ) -> BatchConversionResult:
        batch = BatchConversionResult(total=len(files))

        for index, file_path in enumerate(files, 1):
            if progress_callback:
                progress_callback(index, len(files), file_path)

            result = self.convert(file_path, options)
            batch.results.append(result)

            if result.status == ConversionStatus.SUCCESS:
                batch.success += 1
            elif result.status == ConversionStatus.SKIPPED:
                batch.skipped += 1
            else:
                batch.failed += 1

        return batch

    def _resolve_output_path(self, input_path: Path, options: ConversionOptions) -> Path:
        fmt = options.output_format.value
        base_dir = options.output_dir or self.default_output_dir or input_path.parent
        if options.flat_output:
            output_dir = Path(base_dir)
        else:
            output_dir = Path(base_dir) / fmt
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{input_path.stem}.{fmt}"
        return unique_path(output_path)

    def _build_command(
        self,
        input_path: Path,
        output_path: Path,
        options: ConversionOptions,
    ) -> list[str]:
        fmt = options.output_format
        codec = CODEC_MAP[fmt]

        cmd = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel", "error",
            "-i", str(input_path),
            "-vn",
            "-c:a", codec,
        ]

        if fmt not in LOSSLESS_FORMATS:
            bitrate = self._resolve_bitrate(fmt, options.bitrate)
            if bitrate:
                cmd.extend(["-b:a", bitrate])

        if fmt == AudioFormat.FLAC:
            cmd.extend(["-compression_level", "8"])

        if fmt == AudioFormat.M4A:
            cmd.extend(["-movflags", "+faststart"])

        if options.sample_rate != SampleRatePreset.ORIGINAL:
            cmd.extend(["-ar", options.sample_rate.value])

        if options.preserve_metadata:
            cmd.extend(["-map_metadata", "0"])

        cmd.append(str(output_path))
        return cmd

    def _resolve_bitrate(self, fmt: AudioFormat, preset: BitratePreset) -> Optional[str]:
        if preset == BitratePreset.ORIGINAL:
            return DEFAULT_BITRATE.get(fmt)
        return preset.value
