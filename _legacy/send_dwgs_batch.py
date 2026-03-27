"""
Envía múltiples archivos DWG a la API de Autodesk Model Derivative
y guarda cada resultado como un JSON separado.

Uso: python send_dwgs_batch.py
"""
import os
import re
import json
from pathlib import Path
from aps_integration.aps_auth import get_aps_token
from aps_integration.oss_manager import APS_BUCKET_NAME, upload_file_to_bucket, create_bucket
from aps_integration.model_derivative import extract_dwg_data


# ============================================================
# CONFIGURACIÓN
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DWG_FOLDER = Path(os.getenv("DUPLA_DWG_FOLDER", str(PROJECT_ROOT)))
OUTPUT_FOLDER = Path(os.getenv("DUPLA_OUTPUT_FOLDER", str(PROJECT_ROOT / "api_results")))


def safe_name(filename: str) -> str:
    """Convierte un nombre de archivo a un nombre seguro para la API."""
    return re.sub(r'[^a-zA-Z0-9_\-\.]', '_', filename)


def process_dwg(token: str, dwg_path: str, output_dir: Path) -> None:
    """Procesa un archivo DWG: sube, traduce y guarda resultado."""
    basename = os.path.basename(dwg_path)
    stem = Path(basename).stem  # nombre sin extensión
    object_name = safe_name(basename)

    print(f"\n{'='*70}")
    print(f"PROCESANDO: {basename}")
    print(f"{'='*70}")

    # 1. Subir archivo
    print(f"  [1/3] Subiendo archivo ({os.path.getsize(dwg_path) / 1024 / 1024:.1f} MB)...")
    upload_file_to_bucket(token, APS_BUCKET_NAME, dwg_path, object_name)

    # 2. Extraer datos via Model Derivative
    print(f"  [2/3] Extrayendo datos via Model Derivative API...")
    results = extract_dwg_data(token, APS_BUCKET_NAME, object_name)

    # 3. Guardar JSON con nombre único
    json_name = f"resultado_{safe_name(stem)}.json"
    json_path = output_dir / json_name
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"  [3/3] Resultado guardado: {json_path}")

    # Resumen
    for view in results.get("views", []):
        name = view.get("name", "?")
        count = view.get("object_count", 0)
        print(f"        Vista '{name}': {count} objetos")


def main():
    # Crear carpeta de salida
    output_dir = OUTPUT_FOLDER
    output_dir.mkdir(parents=True, exist_ok=True)

    # Buscar todos los DWG en la carpeta
    dwg_folder = DWG_FOLDER
    if not dwg_folder.exists():
        print(f"[ERROR] La carpeta DWG no existe: {dwg_folder}")
        return
    dwg_files = sorted(dwg_folder.glob("*.dwg"))

    if not dwg_files:
        print(f"[ERROR] No se encontraron archivos .dwg en: {dwg_folder}")
        return

    print(f"Encontrados {len(dwg_files)} archivos DWG:")
    for f in dwg_files:
        print(f"  - {f.name} ({f.stat().st_size / 1024 / 1024:.1f} MB)")

    # Autenticarse una sola vez
    print("\n--- AUTENTICANDO CON AUTODESK APS ---")
    token = get_aps_token()
    if not token:
        print("[ERROR] No se pudo obtener token de Autodesk APS.")
        return
    print("[OK] Token obtenido")

    # Crear bucket (si no existe)
    create_bucket(token, APS_BUCKET_NAME)

    # Procesar cada archivo
    for dwg_file in dwg_files:
        try:
            process_dwg(token, str(dwg_file), output_dir)
        except Exception as e:
            print(f"\n[ERROR] Falló {dwg_file.name}: {e}")
            continue

    print(f"\n{'='*70}")
    print(f"COMPLETADO - Resultados en: {output_dir}")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
