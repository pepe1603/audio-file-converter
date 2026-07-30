# Guía completa — Audio File Converter v1.1.0

CLI multiplataforma para convertir audio con FFmpeg. Esta guía describe **cómo funciona cada opción** y **qué resultados deja**, con ejemplos reales (rutas de Windows; en Linux/macOS/Termux la idea es la misma bajo la carpeta de datos del usuario).

Al arrancar verás el **banner de entrada legendario** (saludo según la hora, arte AFC, estado de FFmpeg, total de conversiones). Luego el menú principal. Al salir (opción **0**), el **banner de cierre legendario**.

---

## Tabla de rutas típicas (Windows)

Usuario de ejemplo: `Jose`.

| Qué | Dónde |
|-----|--------|
| Convertidos normales | `C:\Users\Jose\AudioConverter\converted\<formato>\` |
| Desde USB → PC | `C:\Users\Jose\AudioConverter\converted\from_removable\<disp>\<fecha>\` |
| Reportes / exports | `C:\Users\Jose\AudioConverter\exports\` |
| Historial SQLite | `C:\Users\Jose\AudioConverter\database\afc.db` |
| Logs | `C:\Users\Jose\AudioConverter\logs\` |
| Config | carpeta de configuración del usuario (`config.json`, vía `platformdirs`) |

En Termux con almacenamiento compartido suele usarse algo como `/storage/emulated/0/AudioConverter/`.

---

## Formatos y opciones comunes de conversión

**Entrada y salida:** MP3, WAV, FLAC, AAC, M4A, OGG, OPUS, AIFF, WMA.

En cada conversión el programa pregunta, en este orden:

1. **Formato destino**
2. **Bitrate** (en formatos con pérdida; en lossless suele ir “original”)
3. **Frecuencia de muestreo** (sample rate)
4. **¿Conservar metadatos?** (sí/no)

Si el archivo de salida ya existe, se genera un nombre único: `demo.mp3` → `demo_1.mp3`, `demo_2.mp3`, etc.

---

## Menú principal

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

---

## 1 — Convertir un archivo

### Qué hace

Convierte **un solo** archivo de audio desde cualquier ruta válida del sistema.

### Flujo

1. Pegas la ruta del archivo.
2. Se valida (existe, extensión soportada).
3. Eliges formato, bitrate, sample rate y metadatos.
4. FFmpeg convierte.
5. Se registra en el **historial** y se actualiza el **reporte único**.

### Ejemplo

```
Entrada:  D:\Musica\demo.wav
Opciones: MP3, 192k, original, metadatos sí
```

### Resultado

```
C:\Users\Jose\AudioConverter\converted\mp3\demo.mp3
```

| Efecto | Detalle |
|--------|---------|
| Archivo generado | Sí, en `converted/<formato>/` |
| Historial SQLite | 1 registro |
| Reporte | Sesión añadida en `exports/conversion_report.md` o `.txt` |
| Consola | `✓ Conversión completada` + ruta |

---

## 2 — Convertir varios archivos

### Qué hace

Convierte varios archivos sueltos. Puedes ir uno por línea o varios en la misma línea separados por `;`. Línea vacía termina la lista.

### Ejemplo

```
Archivo: D:\Musica\a.flac
Archivo: D:\Musica\b.wav; D:\Musica\c.m4a
Archivo: <Enter vacío>
→ Formato: FLAC, sample rate original, metadatos sí
```

### Resultado

```
...\converted\flac\a.flac
...\converted\flac\b.flac
...\converted\flac\c.flac
```

| Efecto | Detalle |
|--------|---------|
| Archivos | Uno por entrada válida, en `converted/<formato>/` |
| Resumen | Éxito / fallos / omitidos |
| Historial | Un registro por archivo |
| Reporte | Una sesión “Varios archivos” |

Los candidatos inválidos se marcan con error y no se agregan al lote.

---

## 3 — Convertir una carpeta completa

### Qué hace

Escanea una carpeta (con o sin subcarpetas), cuenta archivos de audio soportados, muestra un resumen por formato origen y convierte el lote.

### Ejemplo

```
Carpeta: D:\Musica\Album2024
¿Incluir subcarpetas? Sí
Encontrados: 12 (MP3: 5, WAV: 7)
→ OGG, 192k
```

### Resultado

```
...\converted\ogg\tema1.ogg
...\converted\ogg\tema2.ogg
...
```

| Efecto | Detalle |
|--------|---------|
| Archivos no audio | Se ignoran |
| Historial | Un registro por conversión |
| Reporte | Sesión “Carpeta” |

---

## 4 — Convertir desde USB / extraíble

### Qué hace

1. Detecta unidades extraíbles conectadas.
2. Permite **navegar** el dispositivo hasta un máximo de **5 niveles** desde la raíz.
3. Eliges un archivo, todo el audio de la carpeta actual, o carpeta + subcarpetas (dentro del límite).
4. Eliges **dónde guardar** (PC o mismo USB).
5. Configuras la conversión.
6. Ves resumen **antes** y **después**.
7. Se escriben los archivos y el reporte según el destino.

### Navegación en el USB

Ejemplo unidad `E:\` con etiqueta `KINGSTON`:

```
E:\                  nivel 0
E:\Musica\           nivel 1
E:\Musica\Rock\      nivel 2
...
```

| Tecla / opción | Acción |
|----------------|--------|
| Número de fila | Abrir carpeta o seleccionar un audio |
| **A** | Convertir todo el audio **solo de esta carpeta** (nivel actual) |
| **B** | Carpeta + subcarpetas (máx. nivel 5 desde la raíz del USB) |
| **N** / **P** | Siguiente / anterior página de audios |
| **U** | Subir un nivel |
| **R** (lista de dispositivos) | Actualizar dispositivos |
| **0** | Cancelar |

### Submenú: ¿Dónde guardar?

En **ambos** destinos se crea **una sola carpeta** y los archivos van **directos dentro** (sin subcarpetas `mp3/`, `flac/`, etc.).

#### 4.1 — En el PC

Ruta de sesión:

```
C:\Users\Jose\AudioConverter\converted\from_removable\KINGSTON\2026-07-30_153045\
  cancion1.mp3
  cancion2.mp3
```

| Efecto | Detalle |
|--------|---------|
| Archivos | En esa carpeta plana |
| Historial SQLite | **Sí** |
| Reporte | **Sí**, en `exports/conversion_report.*` del PC |
| Residuos extra en PC | No (solo convertidos + historial/reporte normales de la app) |

**Ejemplo**

```
USB: E:\Musica\vivo.wav
Destino: 1 (PC)
Formato: MP3 320k
```

```
...\from_removable\KINGSTON\2026-07-30_153045\vivo.mp3
```

#### 4.2 — En el mismo USB (modo limpio)

Se crea una carpeta **junto al origen** (o en el padre común si hay varios archivos):

```
E:\Musica\AFC_Converted_20260730_153045\
  vivo.mp3
  conversion_report.md    (o .txt, según configuración)
```

Si conviertes archivos de `E:\Musica\Rock\` y `E:\Musica\Pop\`, la carpeta suele crearse en el padre común `E:\Musica\`.

| Efecto | Detalle |
|--------|---------|
| Archivos | Solo en el USB, carpeta plana |
| Historial SQLite en el PC | **No** |
| `exports/` del PC | **No** se toca |
| Reporte | **Solo** dentro de la carpeta del USB |
| Uso ideal | Convertir “de paso” sin dejar basura en C: |

### Resúmenes en pantalla

- **Antes:** dispositivo, origen, cantidad, tamaños, formato destino, ruta de salida.
- **Después:** totales éxito/fallo/omitidos y detalle por archivo.

---

## 5 — Editar metadatos

### Qué hace

Lee y reescribe etiquetas del archivo: título, artista, álbum, año, género, track, comentarios y ruta de portada opcional. Dejar un campo vacío mantiene el valor actual.

### Ejemplo

```
Archivo: D:\Musica\tema.mp3
Título: Noche
Artista: Pepe
Álbum: Demo 2026
```

### Resultado

- Se modifica **el mismo** archivo (no crea copia de conversión).
- **No** escribe en el historial de conversiones.
- **No** actualiza `conversion_report.*`.

---

## 6 — Ver información del archivo

### Qué hace

Solo lectura: nombre, ruta, formato, duración, bitrate, canales, frecuencia, codec, tamaño y metadatos principales.

### Ejemplo

```
D:\Musica\tema.mp3
→ MP3 | 03:42 | 320 kbps | Estéreo | 44100 Hz | ...
```

### Resultado

No modifica archivos ni bases de datos.

---

## 7 — Historial

Datos desde `afc.db`.

| Subopción | Qué hace |
|-----------|----------|
| 1 | Ver últimas 20 conversiones |
| 2 | Buscar / filtrar por formato destino (`mp3`, `flac`, …) |
| 3 | Buscar por texto en el nombre |
| 4 | Estadísticas (por formato y por estado) |
| 5 | Eliminar solo registros fallidos |
| 0 | Regresar |

**Nota:** las conversiones hechas con USB **modo limpio (4.2)** **no** aparecen en el historial del PC.

---

## 8 — Exportar historial

Exporta **todo** el historial a un archivo fechado en `exports/`.

| Opción | Formato |
|--------|---------|
| 1 | Usar el formato preferido de configuración (MD o TXT) |
| 2 | TXT |
| 3 | Markdown |
| 0 | Cancelar |

### Ejemplo de resultado

```
C:\Users\Jose\AudioConverter\exports\historial_20260730_154012.md
```

Es un **snapshot** del historial. No es el mismo archivo que `conversion_report.*` (ese se actualiza solo después de cada conversión).

---

## 9 — Configuración

| Opción | Efecto |
|--------|--------|
| 1 | Ver carpeta de salida actual |
| 2 | Cambiar carpeta de salida (crea subcarpetas por formato para el uso normal 1–3) |
| 3 | Cambiar nombre de usuario (banners, historial, reportes) |
| 4 | **Formato del reporte único:** Markdown (`.md`) o TXT (`.txt`) |
| 5 | Verificar FFmpeg |
| 6 | Verificar base de datos y número de registros |
| 7 | Restablecer configuración |
| 0 | Regresar |

### Reporte único (opción 4 de configuración)

Todas las conversiones del programa (1, 2, 3 y 4→PC) actualizan **un solo archivo acumulativo**:

- `~/AudioConverter/exports/conversion_report.md` **o**
- `~/AudioConverter/exports/conversion_report.txt`

En USB modo limpio se escribe el mismo tipo de reporte, pero **dentro de la carpeta del USB**.

Las nuevas sesiones se **añaden al final** (no se borra el historial del reporte).

---

## 10 — Verificar dependencias

Muestra si FFmpeg está disponible y usable. Sin FFmpeg, las conversiones fallarán.

---

## 0 — Salir

Muestra el banner de salida legendario (frase aleatoria, stats, arte adaptable al ancho del terminal) y cierra la aplicación.

**No** borra convertidos, historial ni reportes.

---

## Qué se escribe en cada caso (tabla resumen)

| Acción | Archivos convertidos | Historial DB | `conversion_report` | Otros |
|--------|----------------------|--------------|---------------------|--------|
| 1 Archivo | `converted/<fmt>/` | Sí | PC `exports/` | — |
| 2 Varios | `converted/<fmt>/` | Sí | PC `exports/` | — |
| 3 Carpeta | `converted/<fmt>/` | Sí | PC `exports/` | — |
| 4 → PC | `from_removable/.../` **plano** | Sí | PC `exports/` | — |
| 4 → USB limpio | `AFC_Converted_.../` **plano** en USB | **No** | **Solo en el USB** | Sin basura en el PC |
| 5 Metadatos | Mismo archivo editado | No | No | — |
| 6 Info | Nada | No | No | — |
| 8 Export historial | Nada de audio | No | No | `historial_*.md` o `.txt` |
| 0 Salir | Nada | No | No | — |

---

## Ejemplo de sesión completa

1. Arrancas el programa → **banner de entrada**.
2. Opción **1**: `C:\Users\Jose\Music\prueba.wav` → MP3 192k  
   → `...\converted\mp3\prueba.mp3` + historial + línea en el reporte.
3. Opción **4**: USB `E:\Podcasts\ep01.m4a` → destino **2 (USB)** → MP3  
   → `E:\Podcasts\AFC_Converted_20260730_160000\ep01.mp3`  
   → + `conversion_report.md` (o `.txt`) en esa misma carpeta  
   → el PC **no** recibe historial ni exports de esa conversión.
4. Opción **7** → ves la conversión del paso 2 (no la del USB limpio).
5. Opción **0** → **banner de salida** y fin.

---

## Requisitos y arranque

- Python 3.12+
- FFmpeg instalado en el sistema
- Dependencias: `pip install -r requirements.txt`

```bash
python src/main.py
```

Más detalles de instalación: ver el [README](../README.md) del proyecto.

---

*Audio File Converter v1.1.0 — guía de uso completa.*
