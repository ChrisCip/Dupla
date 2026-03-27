import os
import re
from pathlib import Path

import requests

from aps_integration.aps_auth import get_aps_token
from aps_integration.oss_manager import (
    APS_BUCKET_NAME,
    create_bucket,
    generate_signed_url,
    upload_file_to_bucket,
)
from aps_integration.da_manager import run_workitem, check_workitem_status


def run_extraction_flow():
    token = get_aps_token()

    print("\n--- 1. PREPARANDO ARCHIVOS ---")
    create_bucket(token, APS_BUCKET_NAME)

    project_root = Path(__file__).resolve().parents[1]
    dwg_candidates = sorted(project_root.glob("*.dwg"))
    test_file = os.getenv("DUPLA_TEST_DWG", str(dwg_candidates[0] if dwg_candidates else ""))
    if not test_file or not os.path.exists(test_file):
        print("[ERROR] No se encontro DWG de prueba. Define DUPLA_TEST_DWG o coloca un .dwg en la raiz del proyecto.")
        return

    object_name = re.sub(r"[^a-zA-Z0-9_\\-.]", "_", os.path.basename(test_file))
    upload_file_to_bucket(token, APS_BUCKET_NAME, test_file, object_name)

    print("\n--- 2. CONFIGURANDO PERMISOS TEMPORALES ---")
    input_url = generate_signed_url(token, APS_BUCKET_NAME, object_name, access="read")

    output_filename = "resultados_extraccion.json"
    output_url = generate_signed_url(token, APS_BUCKET_NAME, output_filename, access="readWrite")

    output_areas_filename = "resultados_extraccion_areas.json"
    output_areas_url = generate_signed_url(token, APS_BUCKET_NAME, output_areas_filename, access="readWrite")

    print("\n--- 3. EJECUTANDO EXTRACCION EN AUTODESK ---")
    workitem_id = run_workitem(token, input_url, output_url, output_areas_url)

    print("Esperando a que el motor de AutoCAD termine de procesar el dibujo...")
    status = check_workitem_status(token, workitem_id)

    print("\n--- 4. DESCARGANDO RESULTADOS ---")
    if status == "success":
        print("[OK] El servidor termino con exito.")

        download_url = generate_signed_url(token, APS_BUCKET_NAME, output_filename, access="read")
        print("Descargando archivo JSON completo desde Autodesk OSS...")
        res = requests.get(download_url)
        res.raise_for_status()

        output_path = "resultados_nube.json"
        with open(output_path, "wb") as f:
            f.write(res.content)

        areas_download_url = generate_signed_url(token, APS_BUCKET_NAME, output_areas_filename, access="read")
        print("Descargando JSON enfocado en areas desde Autodesk OSS...")
        areas_res = requests.get(areas_download_url)
        areas_res.raise_for_status()

        areas_output_path = "resultados_areas_nube.json"
        with open(areas_output_path, "wb") as f:
            f.write(areas_res.content)

        print(f"[OK] Resultados guardados exitosamente en '{output_path}'.")
        print(f"[OK] JSON de areas guardado exitosamente en '{areas_output_path}'.")
    else:
        print(f"\n[ERROR] La extraccion fallo con estado '{status}'.")
        print("Descargando el reporte de errores de Autodesk...")
        res_wi = requests.get(
            f"https://developer.api.autodesk.com/da/us-east/v3/workitems/{workitem_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        if res_wi.status_code == 200:
            report_url = res_wi.json().get("reportUrl")
            if report_url:
                try:
                    report_text = requests.get(report_url).text
                    print("\n" + "=" * 50)
                    print("--- REPORTE DE AUTOCAD ---")
                    print(report_text)
                    print("=" * 50 + "\n")
                except Exception as e:
                    print("No se pudo descargar el reporte", e)


if __name__ == "__main__":
    run_extraction_flow()
