"""Presets de conversión de audio."""

from src.models.audio_file import AudioFormat, BitratePreset, SampleRatePreset


# Codecs FFmpeg por formato de salida
CODEC_MAP: dict[AudioFormat, str] = {
    AudioFormat.MP3: "libmp3lame",
    AudioFormat.FLAC: "flac",
    AudioFormat.AAC: "aac",
    AudioFormat.OGG: "libvorbis",
    AudioFormat.M4A: "aac",
    AudioFormat.WAV: "pcm_s16le",
    AudioFormat.AIFF: "pcm_s16be",
    AudioFormat.OPUS: "libopus",
    AudioFormat.WMA: "wmav2",
}

# Extensiones de contenedor para formatos que difieren del codec
CONTAINER_EXTENSION: dict[AudioFormat, str] = {
    AudioFormat.MP3: "mp3",
    AudioFormat.FLAC: "flac",
    AudioFormat.AAC: "aac",
    AudioFormat.OGG: "ogg",
    AudioFormat.M4A: "m4a",
    AudioFormat.WAV: "wav",
    AudioFormat.AIFF: "aiff",
    AudioFormat.OPUS: "opus",
    AudioFormat.WMA: "wma",
}

# Bitrate por defecto por formato lossy
DEFAULT_BITRATE: dict[AudioFormat, str] = {
    AudioFormat.MP3: "192k",
    AudioFormat.AAC: "192k",
    AudioFormat.OGG: "192k",
    AudioFormat.M4A: "256k",
    AudioFormat.OPUS: "128k",
    AudioFormat.WMA: "192k",
}

LOSSLESS_FORMATS = {AudioFormat.FLAC, AudioFormat.WAV, AudioFormat.AIFF}

BITRATE_OPTIONS = list(BitratePreset)
SAMPLE_RATE_OPTIONS = list(SampleRatePreset)
OUTPUT_FORMATS = list(AudioFormat)
INPUT_EXTENSIONS = AudioFormat.supported_extensions()
