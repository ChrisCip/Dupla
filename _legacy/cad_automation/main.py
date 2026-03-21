"""
CLI principal del sistema de automatización CAD.
Coordina todos los módulos y genera reportes en TXT.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

from .discovery import discover_files, generate_discovery_report
from .parser import parse_dxf, generate_parse_report
from .disciplines import (
    separate_by_discipline, analyze_disciplines,
    generate_discipline_report,
)
from .units import normalize_units, detect_units, generate_units_report
from .splitter import split_layouts, list_layouts, generate_split_report
from .analysis import (
    calculate_areas, detect_clashes, generate_analysis_report,
)
from .config import get_output_dir, REPORT_SEPARATOR


def main():
    """Entry point principal."""
    parser = argparse.ArgumentParser(
        prog="cad_automation",
        description="Automatización de archivos CAD - Dupla Engineering",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")
    
    # ── scan ──
    scan_parser = subparsers.add_parser(
        "scan", help="Descubrir y clasificar archivos CAD en un directorio"
    )
    scan_parser.add_argument("directory", help="Directorio a escanear")
    scan_parser.add_argument("-r", "--recursive", action="store_true",
                            default=True, help="Buscar recursivamente")
    
    # ── parse ──
    parse_parser = subparsers.add_parser(
        "parse", help="Analizar un archivo DXF (capas, entidades, layouts)"
    )
    parse_parser.add_argument("file", help="Archivo DXF a analizar")
    
    # ── separate ──
    sep_parser = subparsers.add_parser(
        "separate", help="Separar un archivo DXF por disciplinas"
    )
    sep_parser.add_argument("file", help="Archivo DXF a separar")
    sep_parser.add_argument("-o", "--output", help="Directorio de salida")
    
    # ── normalize ──
    norm_parser = subparsers.add_parser(
        "normalize", help="Normalizar unidades de un archivo DXF"
    )
    norm_parser.add_argument("file", help="Archivo DXF a normalizar")
    norm_parser.add_argument("-o", "--output", help="Directorio de salida")
    norm_parser.add_argument("-u", "--unit", default="mm",
                            choices=["mm", "cm", "m", "in", "ft"],
                            help="Unidad objetivo (default: mm)")
    
    # ── split ──
    split_parser = subparsers.add_parser(
        "split", help="Separar layouts de un archivo DXF en archivos individuales"
    )
    split_parser.add_argument("file", help="Archivo DXF a separar")
    split_parser.add_argument("-o", "--output", help="Directorio de salida")
    split_parser.add_argument("--no-model", action="store_true",
                             help="No incluir Model Space")
    
    # ── analyze ──
    analyze_parser = subparsers.add_parser(
        "analyze", help="Calcular áreas y detectar clashes"
    )
    analyze_parser.add_argument("file", help="Archivo DXF a analizar")
    analyze_parser.add_argument("-o", "--output", help="Directorio de salida")
    analyze_parser.add_argument("--tolerance", type=float, default=0.0,
                               help="Tolerancia para clash detection")
    
    # ── process (pipeline completo) ──
    proc_parser = subparsers.add_parser(
        "process", help="Pipeline completo: scan + parse + separate + normalize + analyze"
    )
    proc_parser.add_argument("path", help="Archivo DXF o directorio")
    proc_parser.add_argument("-o", "--output", help="Directorio de salida")
    
    # ── demo ──
    demo_parser = subparsers.add_parser(
        "demo", help="Generar archivos DXF de demostración para testing"
    )
    demo_parser.add_argument("-o", "--output", default=".", help="Directorio de salida")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    try:
        if args.command == "scan":
            cmd_scan(args)
        elif args.command == "parse":
            cmd_parse(args)
        elif args.command == "separate":
            cmd_separate(args)
        elif args.command == "normalize":
            cmd_normalize(args)
        elif args.command == "split":
            cmd_split(args)
        elif args.command == "analyze":
            cmd_analyze(args)
        elif args.command == "process":
            cmd_process(args)
        elif args.command == "demo":
            cmd_demo(args)
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


# ============================================================================
# IMPLEMENTACIÓN DE COMANDOS
# ============================================================================

def cmd_scan(args):
    """Comando: escanear directorio."""
    directory = Path(args.directory).resolve()
    print(f"\n{'='*80}")
    print(f"ESCANEANDO: {directory}")
    print(f"{'='*80}\n")
    
    files = discover_files(directory, recursive=args.recursive)
    report = generate_discovery_report(files)
    
    # Guardar reporte
    output = _save_report(directory, "scan_report.txt", report)
    print(report)
    print(f"\nReporte guardado: {output}")


def cmd_parse(args):
    """Comando: analizar archivo DXF."""
    file_path = Path(args.file).resolve()
    _check_file(file_path)
    
    cad_file = parse_dxf(file_path)
    report = generate_parse_report(cad_file)
    
    output = _save_report(file_path.parent, f"parse_{file_path.stem}.txt", report)
    print(report)
    print(f"\nReporte guardado: {output}")


def cmd_separate(args):
    """Comando: separar por disciplinas."""
    file_path = Path(args.file).resolve()
    _check_file(file_path)
    
    output_dir = Path(args.output) if args.output else None
    
    # Primero parsear para generar reporte
    cad_file = parse_dxf(file_path)
    groups = analyze_disciplines(cad_file)
    disc_report = generate_discipline_report(cad_file, groups)
    
    # Separar
    generated = separate_by_discipline(file_path, output_dir)
    
    # Reporte completo
    report = disc_report + "\n\nArchivos generados:\n"
    for f in generated:
        report += f"  -> {f}\n"
    
    output = _save_report(file_path.parent, f"disciplines_{file_path.stem}.txt", report)
    print(report)
    print(f"\nReporte guardado: {output}")


def cmd_normalize(args):
    """Comando: normalizar unidades."""
    from .models import UnitSystem
    
    file_path = Path(args.file).resolve()
    _check_file(file_path)
    
    unit_map = {
        "mm": UnitSystem.MILLIMETERS,
        "cm": UnitSystem.CENTIMETERS,
        "m": UnitSystem.METERS,
        "in": UnitSystem.INCHES,
        "ft": UnitSystem.FEET,
    }
    target = unit_map[args.unit]
    output_dir = Path(args.output) if args.output else None
    
    # Detectar unidades actuales
    current, measurement = detect_units(file_path)
    
    # Normalizar
    result = normalize_units(file_path, target, output_dir)
    
    if result:
        from .config import get_conversion_factor
        factor = get_conversion_factor(current, target)
        report = generate_units_report(file_path, current, target, factor, 0)
        output = _save_report(file_path.parent, f"units_{file_path.stem}.txt", report)
        print(report)
        print(f"\nReporte guardado: {output}")
    else:
        print("El archivo ya está en la unidad correcta.")


def cmd_split(args):
    """Comando: separar layouts."""
    file_path = Path(args.file).resolve()
    _check_file(file_path)
    
    output_dir = Path(args.output) if args.output else None
    
    layouts = list_layouts(file_path)
    generated = split_layouts(
        file_path, output_dir,
        include_model_space=not args.no_model,
    )
    
    report = generate_split_report(file_path, layouts, generated)
    output = _save_report(file_path.parent, f"split_{file_path.stem}.txt", report)
    print(report)
    print(f"\nReporte guardado: {output}")


def cmd_analyze(args):
    """Comando: análisis (áreas + clashes)."""
    file_path = Path(args.file).resolve()
    _check_file(file_path)
    
    areas = calculate_areas(file_path)
    clashes = detect_clashes(file_path, tolerance=args.tolerance)
    
    report = generate_analysis_report(file_path, areas, clashes)
    
    output_dir = Path(args.output) if args.output else None
    if output_dir is None:
        output_dir = get_output_dir(file_path, "reports")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output = output_dir / f"analysis_{file_path.stem}.txt"
    output.write_text(report, encoding="utf-8")
    
    print(report)
    print(f"\nReporte guardado: {output}")


def cmd_process(args):
    """
    Comando: pipeline completo.
    
    Detecta automaticamente si debe usar AutoCAD COM (para DWG)
    o ezdxf (para DXF). Si hay DWG + AutoCAD instalado, todo 
    se procesa nativamente sin conversion intermedia.
    """
    path = Path(args.path).resolve()
    output_base = Path(args.output) if args.output else get_output_dir(path, "reports")
    output_base.mkdir(parents=True, exist_ok=True)
    
    all_reports: list[str] = []
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    all_reports.append(f"{'='*80}")
    all_reports.append(f"PIPELINE COMPLETO DE PROCESAMIENTO CAD")
    all_reports.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    all_reports.append(f"Fuente: {path}")
    all_reports.append(f"{'='*80}\n")
    
    # Determinar archivos a procesar
    if path.is_file():
        files_to_process = [path]
    else:
        from .discovery import discover_files
        cad_files = discover_files(path)
        files_to_process = [f.path for f in cad_files]
        disc_report = generate_discovery_report(cad_files)
        all_reports.append(disc_report)
    
    if not files_to_process:
        all_reports.append("No se encontraron archivos CAD para procesar.")
        _save_full_report(output_base, timestamp, all_reports)
        return
    
    dwg_files = [f for f in files_to_process if f.suffix.lower() == ".dwg"]
    dxf_files = [f for f in files_to_process if f.suffix.lower() == ".dxf"]
    
    # --- MODO AUTOCAD (DWG nativo) ---
    if dwg_files:
        _process_dwg_native(dwg_files, output_base, all_reports)
    
    # --- MODO EZDXF (DXF) ---
    if dxf_files:
        _process_dxf(dxf_files, output_base, all_reports)
    
    _save_full_report(output_base, timestamp, all_reports)


def _process_dwg_native(dwg_files: list[Path], output_base: Path,
                         all_reports: list[str]) -> None:
    """Procesa archivos DWG usando AutoCAD COM nativo."""
    from .autocad_engine import AutoCADEngine, check_autocad_available
    
    if not check_autocad_available():
        all_reports.append(
            f"\n[AVISO] {len(dwg_files)} archivos DWG encontrados pero "
            f"AutoCAD/Civil 3D no esta disponible.\n"
            f"  Opciones:\n"
            f"  1. Abre AutoCAD o Civil 3D y ejecuta de nuevo\n"
            f"  2. Convierte los DWG a DXF manualmente\n"
            f"  3. Instala ODA File Converter como alternativa"
        )
        return
    
    all_reports.append(f"\n{'='*80}")
    all_reports.append(f"MODO: AUTOCAD COM (DWG NATIVO)")
    all_reports.append(f"Archivos DWG: {len(dwg_files)}")
    all_reports.append(f"{'='*80}\n")
    
    engine = AutoCADEngine(visible=False)
    if not engine.connect():
        all_reports.append("[ERROR] No se pudo conectar a AutoCAD/Civil 3D")
        return
    
    try:
        for file_path in dwg_files:
            all_reports.append(f"\n{'#'*80}")
            all_reports.append(f"# PROCESANDO (DWG): {file_path.name}")
            all_reports.append(f"{'#'*80}\n")
            
            try:
                # 1. Leer DWG nativo
                cad_file = engine.read_file(file_path)
                all_reports.append(generate_parse_report(cad_file))
                
                # 2. Analizar disciplinas
                groups = analyze_disciplines(cad_file)
                all_reports.append(generate_discipline_report(cad_file, groups))
                
                # 3. Separar por disciplinas -> DWG nativo
                out_disc = output_base / "por_disciplina"
                generated_disc = engine.separate_by_discipline(file_path, out_disc)
                all_reports.append(f"\nArchivos DWG por disciplina: {len(generated_disc)}")
                for f in generated_disc:
                    all_reports.append(f"  -> {f.name}")
                
                # 4. Normalizar unidades -> DWG nativo
                from .config import TARGET_UNIT
                out_norm = output_base / "normalizados"
                result = engine.normalize_units(file_path, TARGET_UNIT, out_norm)
                if result:
                    all_reports.append(f"\nArchivo normalizado (DWG): {result.name}")
                else:
                    all_reports.append("\nUnidades: ya esta en unidad correcta.")
                
                # 5. Separar layouts -> DWG nativo
                out_split = output_base / "planos_separados"
                generated_split = engine.split_layouts(file_path, out_split)
                all_reports.append(f"\nLayouts separados (DWG): {len(generated_split)}")
                for f in generated_split:
                    all_reports.append(f"  -> {f.name}")
                
                # 6. Analisis (usar datos ya leidos del COM)
                from .analysis import (
                    _calculate_areas_from_entities, _detect_clashes_from_entities,
                    generate_analysis_report_from_data,
                )
                areas = _calculate_areas_from_entities(cad_file)
                clashes = _detect_clashes_from_entities(cad_file)
                all_reports.append(generate_analysis_report_from_data(
                    file_path, areas, clashes))
                
            except Exception as e:
                all_reports.append(f"\n[ERROR] {file_path.name}: {e}")
                import traceback
                all_reports.append(traceback.format_exc())
    finally:
        engine.disconnect()


def _process_dxf(dxf_files: list[Path], output_base: Path,
                  all_reports: list[str]) -> None:
    """Procesa archivos DXF usando ezdxf (modo sin AutoCAD)."""
    all_reports.append(f"\n{'='*80}")
    all_reports.append(f"MODO: EZDXF (DXF)")
    all_reports.append(f"Archivos DXF: {len(dxf_files)}")
    all_reports.append(f"{'='*80}\n")
    
    for file_path in dxf_files:
        all_reports.append(f"\n{'#'*80}")
        all_reports.append(f"# PROCESANDO (DXF): {file_path.name}")
        all_reports.append(f"{'#'*80}\n")
        
        try:
            # 1. Parsear
            cad_file = parse_dxf(file_path)
            all_reports.append(generate_parse_report(cad_file))
            
            # 2. Analizar disciplinas
            groups = analyze_disciplines(cad_file)
            all_reports.append(generate_discipline_report(cad_file, groups))
            
            # 3. Separar por disciplinas
            out_disc = output_base / "por_disciplina"
            generated_disc = separate_by_discipline(file_path, out_disc)
            all_reports.append(f"\nArchivos por disciplina generados: {len(generated_disc)}")
            for f in generated_disc:
                all_reports.append(f"  -> {f.name}")
            
            # 4. Normalizar unidades
            out_norm = output_base / "normalizados"
            result = normalize_units(file_path, output_dir=out_norm)
            if result:
                all_reports.append(f"\nArchivo normalizado: {result.name}")
            else:
                all_reports.append("\nUnidades: ya esta en unidad correcta.")
            
            # 5. Separar layouts
            out_split = output_base / "planos_separados"
            generated_split = split_layouts(file_path, out_split)
            all_reports.append(f"\nLayouts separados: {len(generated_split)}")
            for f in generated_split:
                all_reports.append(f"  -> {f.name}")
            
            # 6. Analisis (areas + clashes)
            areas = calculate_areas(file_path)
            clashes = detect_clashes(file_path)
            all_reports.append(generate_analysis_report(file_path, areas, clashes))
            
        except Exception as e:
            all_reports.append(f"\n[ERROR] {e}")
            import traceback
            all_reports.append(traceback.format_exc())


def cmd_demo(args):
    """Comando: generar archivos DXF de demostración."""
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    
    from .tests.conftest import create_multi_discipline_dxf, create_multi_layout_dxf
    
    # Demo: archivo multi-disciplina
    demo1 = output_dir / "demo_multidisciplina.dxf"
    doc1 = create_multi_discipline_dxf()
    doc1.saveas(str(demo1))
    print(f"  [OK] {demo1.name}")
    
    # Demo: archivo multi-layout
    demo2 = output_dir / "demo_multilayout.dxf"
    doc2 = create_multi_layout_dxf()
    doc2.saveas(str(demo2))
    print(f"  [OK] {demo2.name}")
    
    print(f"\nArchivos de demostración generados en: {output_dir}")
    print("\nPrueba con:")
    print(f"  python -m cad_automation process {output_dir}")


# ============================================================================
# UTILIDADES
# ============================================================================

def _check_file(file_path: Path) -> None:
    """Verifica que el archivo existe y es DXF o DWG."""
    if not file_path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {file_path}")
    if file_path.suffix.lower() not in (".dxf", ".dwg"):
        raise ValueError(f"Formato no soportado: {file_path.suffix} "
                        f"(se requiere .dxf o .dwg)")


def _save_report(directory: Path, filename: str, content: str) -> Path:
    """Guarda un reporte en un archivo TXT."""
    report_dir = get_output_dir(directory if directory.is_dir() else directory.parent,
                                "reports")
    report_dir.mkdir(parents=True, exist_ok=True)
    output = report_dir / filename
    output.write_text(content, encoding="utf-8")
    return output


def _save_full_report(output_base: Path, timestamp: str, reports: list[str]) -> None:
    """Guarda el reporte completo del pipeline."""
    full_report = "\n".join(reports)
    
    # Consola (safe encoding for Windows)
    try:
        print(full_report)
    except UnicodeEncodeError:
        print(full_report.encode('ascii', errors='replace').decode('ascii'))
    
    # Archivo (UTF-8)
    report_path = output_base / f"full_report_{timestamp}.txt"
    report_path.write_text(full_report, encoding="utf-8")
    print(f"\n{'='*80}")
    print(f"REPORTE COMPLETO GUARDADO: {report_path}")
    print(f"{'='*80}")


if __name__ == "__main__":
    main()
