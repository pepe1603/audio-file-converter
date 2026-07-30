# Audio File Converter (AFC)

CLI multiplataforma para convertir archivos de audio entre múltiples formatos usando FFmpeg.

**Versión estable:** `1.1.0`

## Características

- Conversión entre múltiples formatos de audio
- Conversión por lotes y de carpetas completas
- Conversión desde USB / dispositivos extraíbles
- Preservar y editar metadatos (Mutagen)
- Cambiar bitrate y frecuencia de muestreo
- Historial SQLite con exportación (TXT / Markdown)
- Reporte único acumulativo (`conversion_report.md` o `.txt`)
- Banners legendarios de entrada y salida (adaptativos al terminal)
- Interfaz CLI profesional con Rich
- Multiplataforma: Windows / Linux / macOS / Termux

## Formatos soportados

**Entrada y salida:** MP3, WAV, FLAC, AAC, M4A, OGG, OPUS, AIFF, WMA

## Requisitos

- Python 3.12+
- FFmpeg (instalado en el sistema)

## Instalación

### Windows / Linux / macOS

```bash
cd audio-file-converter
python -m venv venv
```

Activar entorno virtual:

- Windows (PowerShell): `.\venv\Scripts\Activate.ps1`
- Windows (Git Bash): `source venv/Scripts/activate`
- Linux/macOS: `source venv/bin/activate`

```bash
pip install -r requirements.txt
```

Instalar FFmpeg:

- Windows: `winget install FFmpeg`
- Linux: `sudo apt install ffmpeg`
- macOS: `brew install ffmpeg`

### Android (Termux)

```bash
pkg update && pkg upgrade
pkg install python ffmpeg git
termux-setup-storage
cd audio-file-converter
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Uso

```bash
python src/main.py
```

### Menú principal

```
1. Convertir un archivo
2. Convertir varios archivos
3. Convertir una carpeta completa
4. Convertir desde USB / extraíble
5. Editar metadatos
6. Ver información del archivo
7. Historial
8. Exportar historial
9. Configuración
10. Verificar dependencias
0. Salir
```

### Conversión desde USB

1. Detecta unidades extraíbles conectadas.
2. Permite navegar el árbol del dispositivo hasta un máximo de **5 niveles** desde la raíz.
3. Elige destino de las conversiones (en ambos casos **una sola carpeta**, sin subcarpetas por formato):
   - **1 — En el PC:** `converted/from_removable/<dispositivo>/<fecha>/`
     (historial y reporte único en el PC).
   - **2 — En el mismo USB (modo limpio):** `AFC_Converted_<fecha>/` junto al origen;
     **no** escribe historial ni exports en el PC. Solo convertidos + un reporte.
4. Convierte un archivo o un lote (carpeta actual o con subcarpetas dentro del límite).
5. Muestra resumen **antes** y **después** de la conversión.

### Reporte único

Todas las conversiones (archivo, lote, carpeta, USB) actualizan **un solo archivo**:

- `~/AudioConverter/exports/conversion_report.md` **o** `.txt`
- Formato elegido en **Configuración → Formato de reporte**
- USB modo limpio: el mismo formato, pero dentro de la carpeta del USB

## Estructura del proyecto

```
audio-file-converter/
├── docs/
├── exports/
├── tests/
├── src/
│   ├── main.py
│   ├── core/
│   │   ├── converter.py
│   │   ├── metadata.py
│   │   ├── ffmpeg_manager.py
│   │   ├── validator.py
│   │   ├── exporter.py
│   │   ├── history.py
│   │   ├── dependencies.py
│   │   ├── scanner.py
│   │   └── presets.py
│   ├── storage/
│   │   └── database.py
│   ├── models/
│   │   ├── audio_file.py
│   │   └── conversion.py
│   ├── ui/
│   │   ├── menus.py
│   │   ├── console.py
│   │   └── progress.py
│   └── utils/
│       ├── paths.py
│       ├── logger.py
│       └── helpers.py
├── README.md
├── LICENSE
└── requirements.txt
```

## Carpetas de datos

Por defecto en `~/AudioConverter/`:

```
AudioConverter/
├── converted/
│   ├── mp3/
│   ├── flac/
│   ├── wav/
│   └── ...
├── exports/
├── database/
│   └── afc.db
└── logs/
    └── afc.log
```

En Termux con permisos: `/storage/emulated/0/AudioConverter/`

## Tecnologías

- Python 3.12+
- FFmpeg / FFprobe
- Rich
- Typer
- Pydantic
- Mutagen
- SQLite
- platformdirs

## Roadmap

- [x] Fase 1: Estructura, menú, conversión simple, FFmpeg
- [x] Fase 2: Lotes, progreso, presets
- [x] Fase 3: Metadatos, información de archivo
- [x] Fase 4: SQLite, historial, exportación
- [x] Fase 5: Configuración persistente, multiplataforma, Termux
- [ ] Fase 6: API REST (FastAPI) e interfaz web

## Licencia

MIT © JOSE COLOMBIO GONZALEZ PEREZ
