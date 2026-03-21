import os
import requests
from aps_integration.aps_auth import get_aps_token
from aps_integration.oss_manager import APS_BUCKET_NAME, upload_file_to_bucket, generate_signed_url, create_bucket
from aps_integration.da_manager import run_workitem, check_workitem_status

def run_extraction_flow():
    token = get_aps_token()
    
    print("\n--- 1. PREPARANDO ARCHIVOS ---")
    create_bucket(token, APS_BUCKET_NAME)
    
    # Usaremos el archivo que probaste hace un momento
    test_file = r"C:\Users\chris\Downloads\8- ACAD-PLANOS GIUALCA I - RV7 - EXP.039-025.dwg SOLO IMPRESION.dwg"
    # Subiremos el archivo con un nombre seguro a la nube (sin espacios)
    import re
    object_name = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', os.path.basename(test_file))
    
    # Subir a la nube
    upload_file_to_bucket(token, APS_BUCKET_NAME, test_file, object_name)
    
    print("\n--- 2. CONFIGURANDO PERMISOS TEMPORALES ---")
    # URL para que la nube lea nuestro DWG
    input_url = generate_signed_url(token, APS_BUCKET_NAME, object_name, access="read")
    
    # URL para que la nube pueda GUARDAR el JSON de resultados
    output_filename = "resultados_extraccion.json"
    output_url = generate_signed_url(token, APS_BUCKET_NAME, output_filename, access="readWrite")
    
    print("\n--- 3. EJECUTANDO EXTRACCIÓN EN AUTODESK ---")
    workitem_id = run_workitem(token, input_url, output_url)
    
    # Esperamos a que el servidor de AutoCAD termine
    print("Esperando a que el motor de AutoCAD termine de procesar el dibujo...")
    status = check_workitem_status(token, workitem_id)
    
    print("\n--- 4. DESCARGANDO RESULTADOS ---")
    if status == "success":
        print("[OK] ¡El Servidor terminó con éxito!")
        # Generamos URL para descargar nosotros el JSON
        download_url = generate_signed_url(token, APS_BUCKET_NAME, output_filename, access="read")
        print("Descargando archivo JSON desde Autodesk OSS...")
        
        res = requests.get(download_url)
        res.raise_for_status()
        
        output_path = "resultados_nube.json"
        
        with open(output_path, "wb") as f:
            f.write(res.content)
            
        print(f"[OK] ¡Resultados guardados exitosamente en '{output_path}'!")
        print("¡Ya puedes abrir el archivo para ver qué extrajo!")
    else:
        print(f"\n[ERROR] La extracción falló con estado '{status}'.")
        # El manager imprime el reportUrl, pero vamos a descargarlo automaticamente aqui
        print("Descargando el reporte de errores de Autodesk...")
        res_wi = requests.get(f"https://developer.api.autodesk.com/da/us-east/v3/workitems/{workitem_id}", headers={"Authorization": f"Bearer {token}"})
        if res_wi.status_code == 200:
            report_url = res_wi.json().get('reportUrl')
            if report_url:
                try:
                    # El reportUrl de S3 falla (InvalidToken) si le mandamos el Bearer de Autodesk
                    report_text = requests.get(report_url).text
                    print("\n" + "="*50)
                    print("--- REPORTE DE AUTOCAD ---")
                    print(report_text)
                    print("="*50 + "\n")
                except Exception as e:
                    print("No se pudo descargar el reporte", e)
        print("Revisa el reporte arriba para ver por qué falló el WorkItem.")

if __name__ == "__main__":
    run_extraction_flow()
