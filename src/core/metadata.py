"""Lectura y edición de metadatos de audio con Mutagen."""

from pathlib import Path
from typing import Optional

from rich.console import Console

from src.models.audio_file import AudioMetadata, AudioInfo, AudioFormat
from src.core.ffmpeg_manager import FFmpegManager


class MetadataHandler:
    """Manejador de metadatos de audio."""

    def __init__(self, console: Optional[Console] = None, ffmpeg: Optional[FFmpegManager] = None):
        self.console = console or Console()
        self.ffmpeg = ffmpeg or FFmpegManager()

    def get_info(self, file_path: Path) -> Optional[AudioInfo]:
        path = Path(file_path).expanduser()
        if not path.exists():
            return None

        probe = self.ffmpeg.probe(path)
        fmt = AudioFormat.from_extension(path.suffix)
        metadata = self.read_metadata(path)

        return AudioInfo(
            path=path,
            name=path.name,
            format=fmt,
            duration=probe.duration if probe.success else None,
            bitrate=probe.bitrate if probe.success else None,
            sample_rate=probe.sample_rate if probe.success else None,
            channels=probe.channels if probe.success else None,
            codec=probe.codec if probe.success else None,
            size_bytes=path.stat().st_size if path.exists() else None,
            metadata=metadata,
        )

    def read_metadata(self, file_path: Path) -> AudioMetadata:
        path = Path(file_path)
        ext = path.suffix.lower()
        try:
            if ext == ".mp3":
                return self._read_mp3(path)
            if ext in (".m4a", ".aac", ".mp4"):
                return self._read_mp4(path)
            if ext == ".flac":
                return self._read_flac(path)
            if ext in (".ogg", ".opus"):
                return self._read_ogg(path)
            if ext == ".wav":
                return self._read_wave(path)
            return AudioMetadata()
        except Exception:
            return AudioMetadata()

    def write_metadata(self, file_path: Path, metadata: AudioMetadata) -> bool:
        path = Path(file_path)
        if not path.exists():
            return False

        ext = path.suffix.lower()
        try:
            if ext == ".mp3":
                return self._write_mp3(path, metadata)
            if ext in (".m4a", ".aac"):
                return self._write_mp4(path, metadata)
            if ext == ".flac":
                return self._write_flac(path, metadata)
            if ext in (".ogg", ".opus"):
                return self._write_ogg(path, metadata)
            self.console.print(f"[yellow]⚠ Metadatos no editables para {ext}[/yellow]")
            return False
        except Exception as exc:
            self.console.print(f"[red]Error al escribir metadatos: {exc}[/red]")
            return False

    def copy_metadata(self, source: Path, destination: Path) -> bool:
        metadata = self.read_metadata(source)
        return self.write_metadata(destination, metadata)

    def _read_mp3(self, path: Path) -> AudioMetadata:
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3

        audio = MP3(path, ID3=ID3)
        tags = audio.tags
        if tags is None:
            return AudioMetadata()

        def get_text(frame_id: str) -> Optional[str]:
            frame = tags.get(frame_id)
            if frame is None:
                return None
            return str(frame.text[0]) if frame.text else None

        return AudioMetadata(
            title=get_text("TIT2"),
            artist=get_text("TPE1"),
            album=get_text("TALB"),
            year=get_text("TDRC") or get_text("TYER"),
            genre=get_text("TCON"),
            track=get_text("TRCK"),
            comment=str(tags.get("COMM::eng").text[0]) if tags.get("COMM::eng") else None,
        )

    def _write_mp3(self, path: Path, metadata: AudioMetadata) -> bool:
        from mutagen.mp3 import MP3
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, TDRC, TCON, TRCK, COMM, APIC

        audio = MP3(path, ID3=ID3)
        if audio.tags is None:
            audio.add_tags()
        tags = audio.tags

        if metadata.title is not None:
            tags.add(TIT2(encoding=3, text=metadata.title))
        if metadata.artist is not None:
            tags.add(TPE1(encoding=3, text=metadata.artist))
        if metadata.album is not None:
            tags.add(TALB(encoding=3, text=metadata.album))
        if metadata.year is not None:
            tags.add(TDRC(encoding=3, text=metadata.year))
        if metadata.genre is not None:
            tags.add(TCON(encoding=3, text=metadata.genre))
        if metadata.track is not None:
            tags.add(TRCK(encoding=3, text=metadata.track))
        if metadata.comment is not None:
            tags.add(COMM(encoding=3, lang="eng", desc="", text=metadata.comment))

        if metadata.cover_path and Path(metadata.cover_path).exists():
            cover = Path(metadata.cover_path)
            mime = "image/png" if cover.suffix.lower() == ".png" else "image/jpeg"
            tags.add(
                APIC(
                    encoding=0,
                    mime=mime,
                    type=3,
                    desc="Cover",
                    data=cover.read_bytes(),
                )
            )

        audio.save()
        return True

    def _read_mp4(self, path: Path) -> AudioMetadata:
        from mutagen.mp4 import MP4

        audio = MP4(path)

        def get_tag(key: str) -> Optional[str]:
            value = audio.tags.get(key) if audio.tags else None
            if not value:
                return None
            return str(value[0])

        track = None
        if audio.tags and "trkn" in audio.tags and audio.tags["trkn"]:
            track = str(audio.tags["trkn"][0][0])

        return AudioMetadata(
            title=get_tag("\xa9nam"),
            artist=get_tag("\xa9ART"),
            album=get_tag("\xa9alb"),
            year=get_tag("\xa9day"),
            genre=get_tag("\xa9gen"),
            track=track,
            comment=get_tag("\xa9cmt"),
        )

    def _write_mp4(self, path: Path, metadata: AudioMetadata) -> bool:
        from mutagen.mp4 import MP4, MP4Cover

        audio = MP4(path)
        if audio.tags is None:
            audio.add_tags()

        if metadata.title is not None:
            audio["\xa9nam"] = metadata.title
        if metadata.artist is not None:
            audio["\xa9ART"] = metadata.artist
        if metadata.album is not None:
            audio["\xa9alb"] = metadata.album
        if metadata.year is not None:
            audio["\xa9day"] = metadata.year
        if metadata.genre is not None:
            audio["\xa9gen"] = metadata.genre
        if metadata.comment is not None:
            audio["\xa9cmt"] = metadata.comment
        if metadata.track is not None:
            try:
                audio["trkn"] = [(int(metadata.track), 0)]
            except ValueError:
                pass

        if metadata.cover_path and Path(metadata.cover_path).exists():
            cover = Path(metadata.cover_path)
            img_format = MP4Cover.FORMAT_PNG if cover.suffix.lower() == ".png" else MP4Cover.FORMAT_JPEG
            audio["covr"] = [MP4Cover(cover.read_bytes(), imageformat=img_format)]

        audio.save()
        return True

    def _read_flac(self, path: Path) -> AudioMetadata:
        from mutagen.flac import FLAC

        audio = FLAC(path)

        def get_tag(key: str) -> Optional[str]:
            value = audio.get(key)
            return value[0] if value else None

        return AudioMetadata(
            title=get_tag("title"),
            artist=get_tag("artist"),
            album=get_tag("album"),
            year=get_tag("date"),
            genre=get_tag("genre"),
            track=get_tag("tracknumber"),
            comment=get_tag("comment"),
        )

    def _write_flac(self, path: Path, metadata: AudioMetadata) -> bool:
        from mutagen.flac import FLAC, Picture

        audio = FLAC(path)
        if metadata.title is not None:
            audio["title"] = metadata.title
        if metadata.artist is not None:
            audio["artist"] = metadata.artist
        if metadata.album is not None:
            audio["album"] = metadata.album
        if metadata.year is not None:
            audio["date"] = metadata.year
        if metadata.genre is not None:
            audio["genre"] = metadata.genre
        if metadata.track is not None:
            audio["tracknumber"] = metadata.track
        if metadata.comment is not None:
            audio["comment"] = metadata.comment

        if metadata.cover_path and Path(metadata.cover_path).exists():
            cover = Path(metadata.cover_path)
            picture = Picture()
            picture.type = 3
            picture.mime = "image/png" if cover.suffix.lower() == ".png" else "image/jpeg"
            picture.desc = "Cover"
            picture.data = cover.read_bytes()
            audio.clear_pictures()
            audio.add_picture(picture)

        audio.save()
        return True

    def _read_ogg(self, path: Path) -> AudioMetadata:
        from mutagen.oggvorbis import OggVorbis
        from mutagen.oggopus import OggOpus

        try:
            audio = OggOpus(path) if path.suffix.lower() == ".opus" else OggVorbis(path)
        except Exception:
            audio = OggVorbis(path)

        def get_tag(key: str) -> Optional[str]:
            value = audio.get(key)
            return value[0] if value else None

        return AudioMetadata(
            title=get_tag("title"),
            artist=get_tag("artist"),
            album=get_tag("album"),
            year=get_tag("date"),
            genre=get_tag("genre"),
            track=get_tag("tracknumber"),
            comment=get_tag("comment"),
        )

    def _write_ogg(self, path: Path, metadata: AudioMetadata) -> bool:
        from mutagen.oggvorbis import OggVorbis
        from mutagen.oggopus import OggOpus

        try:
            audio = OggOpus(path) if path.suffix.lower() == ".opus" else OggVorbis(path)
        except Exception:
            audio = OggVorbis(path)

        if metadata.title is not None:
            audio["title"] = metadata.title
        if metadata.artist is not None:
            audio["artist"] = metadata.artist
        if metadata.album is not None:
            audio["album"] = metadata.album
        if metadata.year is not None:
            audio["date"] = metadata.year
        if metadata.genre is not None:
            audio["genre"] = metadata.genre
        if metadata.track is not None:
            audio["tracknumber"] = metadata.track
        if metadata.comment is not None:
            audio["comment"] = metadata.comment

        audio.save()
        return True

    def _read_wave(self, path: Path) -> AudioMetadata:
        try:
            from mutagen.wave import WAVE

            audio = WAVE(path)
            if audio.tags is None:
                return AudioMetadata()
            tags = audio.tags

            def get_text(frame_id: str) -> Optional[str]:
                frame = tags.get(frame_id)
                if frame is None:
                    return None
                return str(frame.text[0]) if getattr(frame, "text", None) else None

            return AudioMetadata(
                title=get_text("TIT2"),
                artist=get_text("TPE1"),
                album=get_text("TALB"),
                year=get_text("TDRC"),
                genre=get_text("TCON"),
                track=get_text("TRCK"),
            )
        except Exception:
            return AudioMetadata()
