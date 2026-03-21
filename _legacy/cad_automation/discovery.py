"""
Módulo de descubrimiento de archivos CAD.
Escanea directorios buscando archivos DXF/DWG y los clasifica.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from .models import CADFile, FileFormat
from .config import SUPPORTED_EXTENSIONS


def discover_files(
    directory: Path,
    recursive: bool = True,
    extensions: Optional[set[str]] = None
) -> list[CADFile]:
    """
    Escanea un directorio buscando archivos CAD.
    
    Args:
        directory: Directorio raíz para buscar
        recursive: Si True, busca en subdirectorios
        extensions: Extensiones a buscar (por defecto: .dxf, .dwg)
    
    Returns:
        Lista de CADFile con metadatos básicos
    """
    if extensions is None:
        extensions = SUPPORTED_EXTENSIONS
    
    cad_files: list[CADFile] = []
    
    if not directory.exists():
        print(f"[ERROR] El directorio no existe: {directory}")
        return cad_files
    
    # Resolver patrón de búsqueda
    if recursive:
        file_iterator = directory.rglob("*")
    else:
        file_iterator = directory.glob("*")
    
    for file_path in file_iterator:
        if not file_path.is_file():
            continue
        
        ext = file_path.suffix.lower()
        if ext not in extensions:
            continue
        
        # Determinar formato
        try:
            file_format = FileFormat(ext.lstrip("."))
        except ValueError:
            continue
        
        # Obtener metadatos del sistema de archivos
        stat = file_path.stat()
        
        cad_file = CADFile(
            path=file_path,
            format=file_format,
            file_size=stat.st_size,
            modified_date=datetime.fromtimestamp(stat.st_mtime),
        )
        
        cad_files.append(cad_file)
    
    # Ordenar por nombre
    cad_files.sort(key=lambda f: f.path.name.lower())
    
    return cad_files


def classify_file_by_name(cad_file: CADFile) -> Optional[str]:
    """
    Intenta clasificar un archivo por su nombre usando convenciones comunes.
    
    Patrones comunes:
        PRJ-A-001.dxf  → 'A' (Arquitectura)
        E-Planta-01.dxf → 'E' (Eléctrico)
        Estructural_Losa.dxf → 'S' (Estructural)
    
    Returns:
        Código de disciplina inferido del nombre, o None
    """
    from .config import classify_layer
    
    stem = cad_file.path.stem.upper()
    
    # Intentar clasificar el nombre del archivo como si fuera un nombre de capa
    discipline = classify_layer(stem)
    
    return discipline.name if discipline.name != "UNKNOWN" else None


def generate_discovery_report(cad_files: list[CADFile]) -> str:
    """
    Genera un reporte en texto del descubrimiento de archivos.
    
    Returns:
        Reporte formateado como string
    """
    lines = []
    lines.append("=" * 80)
    lines.append("REPORTE DE DESCUBRIMIENTO DE ARCHIVOS CAD")
    lines.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 80)
    lines.append("")
    
    if not cad_files:
        lines.append("No se encontraron archivos CAD.")
        return "\n".join(lines)
    
    lines.append(f"Total de archivos encontrados: {len(cad_files)}")
    lines.append("")
    
    # Agrupar por formato
    by_format: dict[str, list[CADFile]] = {}
    for f in cad_files:
        key = f.format.value.upper()
        by_format.setdefault(key, []).append(f)
    
    lines.append("Por formato:")
    for fmt, files in by_format.items():
        lines.append(f"  .{fmt}: {len(files)} archivos")
    lines.append("")
    
    # Listado detallado
    lines.append("-" * 60)
    lines.append(f"{'Archivo':<40} {'Formato':<8} {'Tamaño':>10}")
    lines.append("-" * 60)
    
    for f in cad_files:
        size_str = _format_size(f.file_size)
        lines.append(f"{f.filename:<40} {f.format.value.upper():<8} {size_str:>10}")
    
    lines.append("-" * 60)
    lines.append("")
    
    return "\n".join(lines)


def _format_size(size_bytes: int) -> str:
    """Formatea bytes a unidad legible."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
