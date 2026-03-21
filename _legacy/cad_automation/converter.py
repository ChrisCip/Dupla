"""
Módulo de conversión DWG <-> DXF.
Usa ODA File Converter (gratuito) para convertir entre formatos.

Descarga ODA File Converter:
  https://www.opendesign.com/guestfiles/oda_file_converter

En Windows se instala típicamente en:
  C:\\Program Files\\ODA\\ODAFileConverter\\ODAFileConverter.exe
"""

import subprocess
import shutil
from pathlib import Path
from typing import Optional


# Rutas típicas de ODA File Converter en Windows
ODA_DEFAULT_PATHS = [
    Path(r"C:\Program Files\ODA\ODAFileConverter\ODAFileConverter.exe"),
    Path(r"C:\Program Files (x86)\ODA\ODAFileConverter\ODAFileConverter.exe"),
    Path(r"C:\Program Files\ODA\ODAFileConverter_title 25.4.0\ODAFileConverter.exe"),
]


def find_oda_converter() -> Optional[Path]:
    """
    Busca el ejecutable de ODA File Converter en rutas conocidas.
    
    Returns:
        Ruta al ejecutable, o None si no se encuentra.
    """
    # Buscar en PATH del sistema
    oda_in_path = shutil.which("ODAFileConverter")
    if oda_in_path:
        return Path(oda_in_path)
    
    # Buscar en rutas por defecto
    for path in ODA_DEFAULT_PATHS:
        if path.exists():
            return path
    
    # Buscar dinámicamente en Program Files
    for program_dir in [Path(r"C:\Program Files"), Path(r"C:\Program Files (x86)")]:
        if program_dir.exists():
            for oda_dir in program_dir.glob("ODA*"):
                exe = oda_dir / "ODAFileConverter.exe"
                if exe.exists():
                    return exe
    
    return None


def dwg_to_dxf(
    input_path: Path,
    output_dir: Optional[Path] = None,
    oda_path: Optional[Path] = None,
    dxf_version: str = "ACAD2018",
) -> Path:
    """
    Convierte un archivo DWG a DXF usando ODA File Converter.
    
    Args:
        input_path: Archivo .dwg a convertir
        output_dir: Directorio de salida (por defecto: junto al original)
        oda_path: Ruta al ejecutable de ODA (auto-detectada si None)
        dxf_version: Versión DXF de salida
    
    Returns:
        Ruta al archivo DXF generado
    
    Raises:
        FileNotFoundError: Si ODA File Converter no está instalado
        RuntimeError: Si la conversión falla
    """
    input_path = Path(input_path).resolve()
    
    if not input_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {input_path}")
    
    if input_path.suffix.lower() != ".dwg":
        raise ValueError(f"Se esperaba archivo .dwg, recibido: {input_path.suffix}")
    
    # Encontrar ODA
    if oda_path is None:
        oda_path = find_oda_converter()
    
    if oda_path is None or not oda_path.exists():
        raise FileNotFoundError(
            "ODA File Converter no encontrado.\n"
            "Descargalo gratis de: https://www.opendesign.com/guestfiles/oda_file_converter\n"
            "Instalalo y luego ejecuta este comando de nuevo."
        )
    
    # Preparar directorios 
    input_dir = input_path.parent
    if output_dir is None:
        output_dir = input_dir / "_dxf_temp"
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # ODA File Converter CLI:
    # ODAFileConverter "input_dir" "output_dir" version type recurse audit [filter]
    # type: "DXF" para salida DXF, "DWG" para salida DWG
    # version: ACAD2018, ACAD2013, ACAD2010, etc.
    cmd = [
        str(oda_path),
        str(input_dir),      # Directorio fuente
        str(output_dir),     # Directorio destino
        dxf_version,         # Versión de salida
        "DXF",               # Formato de salida
        "0",                 # 0 = no recursivo
        "1",                 # 1 = audit & repair
        f"*.dwg",            # Filtro - SOLO el tipo dwg
    ]
    
    print(f"[DWG->DXF] Convirtiendo: {input_path.name}")
    print(f"[DWG->DXF] Usando ODA: {oda_path}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if result.returncode != 0:
            raise RuntimeError(
                f"ODA File Converter falló (código {result.returncode}):\n"
                f"STDOUT: {result.stdout}\n"
                f"STDERR: {result.stderr}"
            )
    except subprocess.TimeoutExpired:
        raise RuntimeError("ODA File Converter tardó demasiado (timeout 120s)")
    
    # Buscar el DXF generado
    expected_dxf = output_dir / input_path.with_suffix(".dxf").name
    
    if not expected_dxf.exists():
        # Buscar cualquier DXF que haya sido generado
        dxf_files = list(output_dir.glob("*.dxf"))
        if dxf_files:
            expected_dxf = dxf_files[0]
        else:
            raise RuntimeError(
                f"No se generó archivo DXF. Verifica que ODA File Converter "
                f"funcione correctamente.\nDirectorio de salida: {output_dir}"
            )
    
    print(f"[DWG->DXF] Generado: {expected_dxf.name}")
    return expected_dxf


def dxf_to_dwg(
    input_path: Path,
    output_dir: Optional[Path] = None,
    oda_path: Optional[Path] = None,
    dwg_version: str = "ACAD2018",
) -> Path:
    """
    Convierte un archivo DXF de vuelta a DWG usando ODA File Converter.
    
    Args:
        input_path: Archivo .dxf a convertir
        output_dir: Directorio de salida
        oda_path: Ruta al ejecutable de ODA
        dwg_version: Versión DWG de salida
    
    Returns:
        Ruta al archivo DWG generado
    """
    input_path = Path(input_path).resolve()
    
    if not input_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {input_path}")
    
    if oda_path is None:
        oda_path = find_oda_converter()
    
    if oda_path is None or not oda_path.exists():
        raise FileNotFoundError(
            "ODA File Converter no encontrado.\n"
            "Descargalo gratis de: https://www.opendesign.com/guestfiles/oda_file_converter"
        )
    
    input_dir = input_path.parent
    if output_dir is None:
        output_dir = input_dir
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    cmd = [
        str(oda_path),
        str(input_dir),
        str(output_dir),
        dwg_version,
        "DWG",        # Formato de salida
        "0",
        "1",
        f"*.dxf",
    ]
    
    print(f"[DXF->DWG] Convirtiendo: {input_path.name}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise RuntimeError(f"ODA falló: {result.stderr}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("ODA File Converter timeout")
    
    expected_dwg = output_dir / input_path.with_suffix(".dwg").name
    
    if not expected_dwg.exists():
        dwg_files = list(output_dir.glob("*.dwg"))
        if dwg_files:
            expected_dwg = dwg_files[0]
        else:
            raise RuntimeError(f"No se generó archivo DWG.")
    
    print(f"[DXF->DWG] Generado: {expected_dwg.name}")
    return expected_dwg


def convert_directory_dwg_to_dxf(
    directory: Path,
    output_dir: Optional[Path] = None,
    oda_path: Optional[Path] = None,
) -> list[Path]:
    """
    Convierte todos los archivos DWG de un directorio a DXF.
    
    Returns:
        Lista de archivos DXF generados
    """
    directory = Path(directory).resolve()
    dwg_files = list(directory.glob("*.dwg")) + list(directory.rglob("*.dwg"))
    # Eliminar duplicados
    dwg_files = list(set(dwg_files))
    
    if not dwg_files:
        print("[DWG->DXF] No se encontraron archivos .dwg")
        return []
    
    if oda_path is None:
        oda_path = find_oda_converter()
    
    print(f"[DWG->DXF] {len(dwg_files)} archivos DWG encontrados")
    
    results = []
    for dwg_file in dwg_files:
        try:
            dxf_path = dwg_to_dxf(dwg_file, output_dir, oda_path)
            results.append(dxf_path)
        except Exception as e:
            print(f"  [ERROR] {dwg_file.name}: {e}")
    
    return results


def convert_results_to_dwg(
    dxf_files: list[Path],
    output_dir: Optional[Path] = None,
    oda_path: Optional[Path] = None,
) -> list[Path]:
    """
    Convierte una lista de archivos DXF resultado a DWG.
    
    Returns:
        Lista de archivos DWG generados
    """
    if oda_path is None:
        oda_path = find_oda_converter()
    
    results = []
    for dxf_file in dxf_files:
        try:
            dwg_path = dxf_to_dwg(dxf_file, output_dir, oda_path)
            results.append(dwg_path)
        except Exception as e:
            print(f"  [ERROR] {dxf_file.name}: {e}")
    
    return results


def check_oda_available() -> bool:
    """Verifica si ODA File Converter está disponible."""
    return find_oda_converter() is not None


def get_oda_status() -> str:
    """Devuelve información sobre el estado de ODA File Converter."""
    oda = find_oda_converter()
    if oda:
        return f"ODA File Converter encontrado: {oda}"
    else:
        return (
            "ODA File Converter NO encontrado.\n"
            "Para procesar archivos DWG, instala ODA File Converter:\n"
            "  https://www.opendesign.com/guestfiles/oda_file_converter\n"
            "Sin ODA, solo se pueden procesar archivos DXF directamente."
        )
