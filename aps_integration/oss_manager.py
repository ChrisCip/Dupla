import os
import requests
from aps_integration.aps_auth import get_aps_token
from dotenv import load_dotenv

load_dotenv()

APS_BUCKET_NAME = os.getenv("APS_BUCKET_NAME", "dupla_dwg_bucket_test_01") 
# Los nombres de bucket deben ser unicos a nivel global en Autodesk y en minusculas.

BASE_URL = "https://developer.api.autodesk.com/oss/v2"

def create_bucket(token, bucket_name):
    """
    Crea un bucket (contenedor de archivos) en los servidores de Autodesk.
    """
    print(f"Verificando/Creando bucket '{bucket_name}'...")
    url = f"{BASE_URL}/buckets"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "bucketKey": bucket_name,
        "policyKey": "transient" # transient: los archivos se borran solitos a las 24 horas (ideal para esta API)
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        print("[OK] Bucket creado existosamente.")
    elif response.status_code == 409:
        print("[INFO] El bucket ya existe. Podemos usarlo.")
    else:
        print(f"[ERROR] Error al crear bucket: {response.status_code} - {response.text}")
        response.raise_for_status()

def upload_file_to_bucket(token, bucket_name, file_path, object_name=None):
    """
    Sube un archivo local al bucket de Autodesk usando Signed URLs 
    (El endpoint directo estandar está deprecado por Autodesk).
    """
    if not object_name:
        object_name = os.path.basename(file_path)
        
    print(f"Preparando subida para '{object_name}'...")
    
    # 1. Obtener URL firmada de escritura
    upload_url = generate_signed_url(token, bucket_name, object_name, access="write")
    
    # 2. Subir directamente el binario a S3 a traves de la URL firmada
    print(f"Subiendo '{object_name}' al bucket '{bucket_name}'...")
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
            
        response = requests.put(upload_url, data=file_data)
        response.raise_for_status()
            
        print("[OK] Archivo subido con éxito!")
        return object_name
            
    except FileNotFoundError:
        print(f"[ERROR] El archivo no existe en la ruta: {file_path}")
        return None

def generate_signed_url(token, bucket_name, object_name, access="read"):
    """
    Genera una URL temporal (Signed URL) para descargar un archivo.
    access='read'  -> Para que AutoCAD pueda descargar nuestro DWG
    access='write' -> Para que AutoCAD pueda subir 'resultados.json'
    """
    print(f"Generando URL firmada para '{object_name}' ({access})...")
    url = f"{BASE_URL}/buckets/{bucket_name}/objects/{object_name}/signed"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    # Si pedimos permisos de escritura (para subir un archivo nuevo),
    # OSS requiere obligatoriamente que singleUse sea True para esta operación
    payload = {
        "minutesExpiration": 60,
    }
    if access == "write":
        payload["singleUse"] = True
    elif access == "readWrite":
        payload["singleUse"] = False
        
    url_con_access = f"{url}?access={access}"
    response = requests.post(url_con_access, json=payload, headers=headers)
    
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print("Error en Signed URL:", response.text)
        raise
        
    signed_url = response.json().get("signedUrl")
    print("[OK] URL firmada generada con éxito.")
    return signed_url


if __name__ == "__main__":
    token = get_aps_token()
    create_bucket(token, APS_BUCKET_NAME)
    
    # Intenta subir un archivo de prueba (si tienes alguno a la mano)
    # Reemplaza la ruta por un DWG tuyo.
    test_file = r"C:\Users\chris\Downloads\8- ACAD-PLANOS GIUALCA I - RV7 - EXP.039-025.dwg SOLO IMPRESION.dwg"
    object_name = os.path.basename(test_file)
    if os.path.exists(test_file):
        upload_file_to_bucket(token, APS_BUCKET_NAME, test_file)
        url = generate_signed_url(token, APS_BUCKET_NAME, object_name)
        print(f"URL de Acceso Temporal: {url}")
