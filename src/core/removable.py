"""Detección y navegación de dispositivos extraíbles (USB)."""

import os
import platform
import string
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from src.core.presets import INPUT_EXTENSIONS


MAX_TREE_DEPTH = 5

HIDDEN_DIR_NAMES = {
    "system volume information",
    "$recycle.bin",
    "recycle.bin",
    "found.000",
    "found.001",
    ".trashes",
    ".spotlight-v100",
    ".fseventsd",
    "lost+found",
}


@dataclass
class RemovableDevice:
    """Dispositivo o volumen extraíble detectado."""

    label: str
    path: Path
    filesystem: Optional[str] = None
    total_gb: Optional[float] = None
    free_gb: Optional[float] = None

    @property
    def display(self) -> str:
        size = ""
        if self.total_gb is not None:
            free = f"{self.free_gb:.1f} GB libres / " if self.free_gb is not None else ""
            size = f" ({free}{self.total_gb:.1f} GB)"
        fs = f" [{self.filesystem}]" if self.filesystem else ""
        return f"{self.label} — {self.path}{fs}{size}"


@dataclass
class BrowseEntry:
    """Entrada del explorador de dispositivo."""

    name: str
    path: Path
    is_dir: bool
    is_audio: bool = False
    size_bytes: Optional[int] = None


class RemovableMediaManager:
    """Gestiona dispositivos extraíbles y navegación limitada en profundidad."""

    def __init__(self, max_depth: int = MAX_TREE_DEPTH):
        self.max_depth = max_depth

    def list_devices(self) -> list[RemovableDevice]:
        system = platform.system().lower()
        if system == "windows":
            devices = self._list_windows()
        elif system == "darwin":
            devices = self._list_macos()
        else:
            devices = self._list_linux_termux()

        unique: dict[str, RemovableDevice] = {}
        for device in devices:
            try:
                key = str(device.path.resolve())
            except OSError:
                key = str(device.path)
            if device.path.exists() and device.path.is_dir():
                unique[key] = device
        return sorted(unique.values(), key=lambda d: str(d.path).lower())

    def depth_from_root(self, root: Path, current: Path) -> int:
        try:
            root_resolved = root.resolve()
            current_resolved = current.resolve()
            relative = current_resolved.relative_to(root_resolved)
        except (OSError, ValueError):
            return -1
        parts = [p for p in relative.parts if p not in (".", "")]
        return len(parts)

    def can_enter(self, root: Path, directory: Path) -> bool:
        """Permite entrar a carpetas hasta el nivel max_depth (inclusive)."""
        depth = self.depth_from_root(root, directory)
        return 0 <= depth <= self.max_depth

    def list_directory(self, root: Path, directory: Path) -> list[BrowseEntry]:
        directory = Path(directory)
        if not directory.exists() or not directory.is_dir():
            return []

        depth = self.depth_from_root(root, directory)
        if depth < 0 or depth > self.max_depth:
            return []

        entries: list[BrowseEntry] = []
        try:
            children = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except OSError:
            return []

        for child in children:
            try:
                if child.name.startswith(".") or child.name.lower() in HIDDEN_DIR_NAMES:
                    continue
                if child.is_dir():
                    child_depth = self.depth_from_root(root, child)
                    if 0 <= child_depth <= self.max_depth:
                        entries.append(BrowseEntry(name=child.name, path=child, is_dir=True))
                elif child.is_file() and child.suffix.lower() in INPUT_EXTENSIONS:
                    size = None
                    try:
                        size = child.stat().st_size
                    except OSError:
                        pass
                    entries.append(
                        BrowseEntry(
                            name=child.name,
                            path=child,
                            is_dir=False,
                            is_audio=True,
                            size_bytes=size,
                        )
                    )
            except OSError:
                continue
        return entries

    def scan_audio(
        self,
        root: Path,
        directory: Path,
        recursive: bool = True,
    ) -> list[Path]:
        """Escanea audio sin superar max_depth desde la raíz del dispositivo."""
        directory = Path(directory)
        root = Path(root)
        start_depth = self.depth_from_root(root, directory)
        if start_depth < 0 or start_depth > self.max_depth:
            return []

        files: list[Path] = []

        def walk(current: Path, depth: int) -> None:
            if depth > self.max_depth:
                return
            try:
                items = list(current.iterdir())
            except OSError:
                return
            for item in items:
                try:
                    if item.name.startswith(".") or item.name.lower() in HIDDEN_DIR_NAMES:
                        continue
                    if item.is_file() and item.suffix.lower() in INPUT_EXTENSIONS:
                        files.append(item)
                    elif recursive and item.is_dir():
                        next_depth = depth + 1
                        if next_depth <= self.max_depth:
                            walk(item, next_depth)
                except OSError:
                    continue

        walk(directory, start_depth)
        return sorted(files, key=lambda p: str(p).lower())

    def _disk_usage(self, path: Path) -> tuple[Optional[float], Optional[float]]:
        try:
            usage = os.statvfs(path) if hasattr(os, "statvfs") else None
            if usage is not None:
                total = (usage.f_frsize * usage.f_blocks) / (1024 ** 3)
                free = (usage.f_frsize * usage.f_bavail) / (1024 ** 3)
                return total, free
        except (AttributeError, OSError):
            pass
        try:
            import shutil

            total, _, free = shutil.disk_usage(path)
            return total / (1024 ** 3), free / (1024 ** 3)
        except OSError:
            return None, None

    def _list_windows(self) -> list[RemovableDevice]:
        devices: list[RemovableDevice] = []
        try:
            import ctypes

            get_drive_type = ctypes.windll.kernel32.GetDriveTypeW
            get_volume_name = ctypes.windll.kernel32.GetVolumeInformationW
            DRIVE_REMOVABLE = 2
            DRIVE_CDROM = 5

            for letter in string.ascii_uppercase:
                root = f"{letter}:\\"
                drive_type = get_drive_type(root)
                if drive_type not in (DRIVE_REMOVABLE,):
                    # Incluir solo extraíbles; algunos USB aparecen como FIXED
                    # Se añaden además con PowerShell más abajo
                    if drive_type != 3:  # FIXED se evalúa aparte
                        continue
                    # Solo FIXED que no sea el sistema
                    system_drive = os.environ.get("SystemDrive", "C:").upper()
                    if root.upper().startswith(system_drive):
                        continue
                    # Heurística: omitir fijos del sistema; PowerShell filtrará mejor
                    continue

                path = Path(root)
                if not path.exists():
                    continue

                label_buf = ctypes.create_unicode_buffer(1024)
                fs_buf = ctypes.create_unicode_buffer(1024)
                serial = ctypes.c_uint()
                max_comp = ctypes.c_uint()
                flags = ctypes.c_uint()
                ok = get_volume_name(
                    root,
                    label_buf,
                    ctypes.sizeof(label_buf),
                    ctypes.byref(serial),
                    ctypes.byref(max_comp),
                    ctypes.byref(flags),
                    fs_buf,
                    ctypes.sizeof(fs_buf),
                )
                label = label_buf.value if ok and label_buf.value else f"Unidad {letter}"
                total, free = self._disk_usage(path)
                devices.append(
                    RemovableDevice(
                        label=label,
                        path=path,
                        filesystem=fs_buf.value if ok else None,
                        total_gb=total,
                        free_gb=free,
                    )
                )
        except Exception:
            pass

        # Complemento: Get-Volume / wmic para USB montados como Fixed
        devices.extend(self._list_windows_powershell())
        return devices

    def _list_windows_powershell(self) -> list[RemovableDevice]:
        """Solo unidades extraíbles (DriveType 2) o discos conectados por bus USB."""
        devices: list[RemovableDevice] = []
        ps = r"""
$ErrorActionPreference = 'SilentlyContinue'
$ids = New-Object 'System.Collections.Generic.HashSet[string]'

# USB flash / removable clásico
Get-CimInstance Win32_LogicalDisk | Where-Object { $_.DriveType -eq 2 } | ForEach-Object {
  [void]$ids.Add($_.DeviceID)
}

# Discos externos por interfaz USB (pueden montarse como Fixed)
Get-CimInstance Win32_DiskDrive | Where-Object { $_.InterfaceType -eq 'USB' } | ForEach-Object {
  $disk = $_
  Get-CimAssociatedInstance -InputObject $disk -ResultClassName Win32_DiskPartition | ForEach-Object {
    Get-CimAssociatedInstance -InputObject $_ -ResultClassName Win32_LogicalDisk | ForEach-Object {
      [void]$ids.Add($_.DeviceID)
    }
  }
}

$sys = $env:SystemDrive
$result = @()
foreach ($id in $ids) {
  if (-not $id) { continue }
  if ($id.TrimEnd('\').ToUpper() -eq $sys.ToUpper()) { continue }
  $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='$id'"
  if ($null -eq $disk) { continue }
  $result += [PSCustomObject]@{
    DeviceID   = $disk.DeviceID
    VolumeName = $disk.VolumeName
    FileSystem = $disk.FileSystem
    Size       = $disk.Size
    FreeSpace  = $disk.FreeSpace
  }
}
if ($result.Count -eq 0) { '' } else { $result | ConvertTo-Json -Compress }
"""
        try:
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=20,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return devices

            import json

            raw = result.stdout.strip()
            if not raw:
                return devices
            data = json.loads(raw)
            if isinstance(data, dict):
                data = [data]
            system_drive = os.environ.get("SystemDrive", "C:").upper()
            for item in data:
                device_id = (item.get("DeviceID") or "").upper()
                if not device_id:
                    continue
                if device_id.rstrip("\\") == system_drive:
                    continue
                path = Path(f"{device_id}\\")
                if not path.exists():
                    continue
                size = item.get("Size")
                free = item.get("FreeSpace")
                total_gb = float(size) / (1024 ** 3) if size else None
                free_gb = float(free) / (1024 ** 3) if free else None
                label = item.get("VolumeName") or f"Unidad {device_id.rstrip(':')}"
                devices.append(
                    RemovableDevice(
                        label=label,
                        path=path,
                        filesystem=item.get("FileSystem"),
                        total_gb=total_gb,
                        free_gb=free_gb,
                    )
                )
        except Exception:
            pass
        return devices

    def _list_macos(self) -> list[RemovableDevice]:
        devices: list[RemovableDevice] = []
        volumes = Path("/Volumes")
        if not volumes.exists():
            return devices
        system_names = {"macintosh hd", "macintosh hd - data"}
        try:
            for entry in volumes.iterdir():
                if not entry.is_dir():
                    continue
                if entry.name.lower() in system_names:
                    continue
                total, free = self._disk_usage(entry)
                devices.append(
                    RemovableDevice(
                        label=entry.name,
                        path=entry,
                        total_gb=total,
                        free_gb=free,
                    )
                )
        except OSError:
            pass
        return devices

    def _list_linux_termux(self) -> list[RemovableDevice]:
        devices: list[RemovableDevice] = []
        candidates: list[Path] = []

        user = os.environ.get("USER") or os.environ.get("USERNAME") or ""
        for base in (
            Path("/media") / user if user else None,
            Path("/run/media") / user if user else None,
            Path("/media"),
            Path("/mnt"),
            Path("/storage"),
        ):
            if base is None or not base.exists():
                continue
            try:
                for entry in base.iterdir():
                    name = entry.name.lower()
                    if name in {"emulated", "self", "tmp"}:
                        continue
                    if entry.is_dir():
                        candidates.append(entry)
            except OSError:
                continue

        # Montajes en /proc/mounts que parezcan extraíbles
        try:
            mounts = Path("/proc/mounts").read_text(encoding="utf-8", errors="ignore")
            for line in mounts.splitlines():
                parts = line.split()
                if len(parts) < 2:
                    continue
                src, dest = parts[0], parts[1]
                if any(x in src for x in ("/dev/sd", "/dev/mmc", "/dev/usb", "fuse")):
                    dest_path = Path(dest)
                    if dest_path.is_dir() and dest not in {"/", "/boot", "/home"}:
                        candidates.append(dest_path)
        except OSError:
            pass

        seen: set[str] = set()
        for path in candidates:
            try:
                key = str(path.resolve())
            except OSError:
                key = str(path)
            if key in seen:
                continue
            seen.add(key)
            if not path.exists() or not path.is_dir():
                continue
            # En Termux, /storage/XXXX-XXXX suele ser SD/OTG
            total, free = self._disk_usage(path)
            devices.append(
                RemovableDevice(
                    label=path.name or str(path),
                    path=path,
                    total_gb=total,
                    free_gb=free,
                )
            )
        return devices
