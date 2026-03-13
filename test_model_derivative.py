"""
Test del pipeline Model Derivative API.
Sube un DWG, lo traduce a SVF2, y extrae todas las propiedades.
"""
import os
import re
import json
from aps_integration.aps_auth import get_aps_token
from aps_integration.oss_manager import APS_BUCKET_NAME, upload_file_to_bucket, create_bucket
from aps_integration.model_derivative import extract_dwg_data


def main():
    token = get_aps_token()

    # 1. Preparar bucket y subir archivo
    print("\n--- 1. PREPARANDO ARCHIVOS ---")
    create_bucket(token, APS_BUCKET_NAME)

    test_file = r"C:\Users\chris\Downloads\8- ACAD-PLANOS GIUALCA I - RV7 - EXP.039-025.dwg SOLO IMPRESION.dwg"
    if not os.path.exists(test_file):
        print(f"[ERROR] No se encontró el archivo: {test_file}")
        return

    # Nombre seguro sin espacios
    object_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', os.path.basename(test_file))
    upload_file_to_bucket(token, APS_BUCKET_NAME, test_file, object_name)

    # 2. Extraer datos via Model Derivative API
    print("\n--- 2. EXTRAYENDO DATOS VIA MODEL DERIVATIVE ---")
    results = extract_dwg_data(token, APS_BUCKET_NAME, object_name)

    # 3. Guardar resultados
    output_path = "resultados_model_derivative.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n[OK] Resultados guardados en '{output_path}'")

    # Resumen rápido
    for view in results.get("views", []):
        name = view.get("name", "?")
        count = view.get("object_count", 0)
        print(f"   Vista '{name}': {count} objetos")


if __name__ == "__main__":
    main()
