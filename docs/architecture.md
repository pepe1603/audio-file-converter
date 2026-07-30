# Arquitectura - Audio File Converter

## Flujo principal

```
main.py
  └── Menus (ui/menus.py)
        ├── AudioConverter (core/converter.py)
        │     ├── FFmpegManager
        │     ├── MetadataHandler
        │     └── Validator
        ├── HistoryService → Database (SQLite)
        ├── HistoryExporter
        └── PathManager (config + rutas)
```

## Principios

- **Separación de responsabilidades**: UI, conversión, metadatos, almacenamiento y utilidades viven en módulos distintos.
- **pathlib**: todas las rutas usan `Path`.
- **Configuración centralizada**: `PathManager` gestiona JSON de preferencias y carpetas de datos.
- **Validación previa**: existencia de archivo, extensión soportada y disponibilidad de FFmpeg.
- **Logging**: eventos en `~/AudioConverter/logs/afc.log`.

## Datos de usuario

| Recurso | Ubicación por defecto |
|---------|------------------------|
| Convertidos | `~/AudioConverter/converted/<formato>/` |
| Desde USB → PC | `~/AudioConverter/converted/from_removable/<disp>/<fecha>/<formato>/` |
| Desde USB → USB | `<origen>/AFC_Converted_<fecha>/<formato>/` (modo limpio, sin historial PC) |
| Historial | `~/AudioConverter/database/afc.db` |
| Exportaciones | `~/AudioConverter/exports/` |
| Config | config de usuario (`platformdirs`) |

En Termux con almacenamiento: `/storage/emulated/0/AudioConverter/`.
