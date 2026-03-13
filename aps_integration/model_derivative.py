"""
Model Derivative API — Extrae propiedades de archivos DWG via REST.

Flujo: Upload DWG → Traducir a SVF2 → Consultar Metadata → Consultar Properties
Todo via REST, sin compilar plugins.
"""

import os
import time
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://developer.api.autodesk.com"
MD_URL = f"{BASE_URL}/modelderivative/v2/designdata"


def _get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def urn_from_object_id(bucket_key: str, object_name: str) -> str:
    """
    Genera el URN en base64 a partir de bucket + object name.
    El URN es el identificador que usa Model Derivative para referirse al archivo.
    """
    object_id = f"urn:adsk.objects:os.object:{bucket_key}/{object_name}"
    urn_b64 = base64.urlsafe_b64encode(object_id.encode()).decode().rstrip("=")
    return urn_b64


def translate_to_svf2(token: str, urn: str) -> dict:
    """
    Envía un job de traducción para convertir el DWG a formato SVF2.
    SVF2 permite que Autodesk indexe todas las propiedades del archivo.
    """
    print(f"\n[MODEL DERIVATIVE] Enviando job de traducción...")
    url = f"{MD_URL}/job"

    payload = {
        "input": {
            "urn": urn,
        },
        "output": {
            "formats": [
                {
                    "type": "svf2",
                    "views": ["2d", "3d"],
                }
            ],
        },
    }

    response = requests.post(url, json=payload, headers=_get_headers(token))

    if response.status_code == 200:
        print("[OK] Job de traducción aceptado (ya estaba traducido).")
    elif response.status_code == 201:
        print("[OK] Job de traducción iniciado.")
    else:
        print(f"[ERROR] {response.status_code}: {response.text}")
        response.raise_for_status()

    return response.json()


def wait_for_translation(token: str, urn: str, timeout: int = 300) -> str:
    """
    Espera a que la traducción del modelo termine.
    Devuelve el estado final: 'success', 'failed', 'timeout'.
    """
    print("[MODEL DERIVATIVE] Esperando traducción...")
    url = f"{MD_URL}/{urn}/manifest"
    start = time.time()

    while time.time() - start < timeout:
        response = requests.get(url, headers=_get_headers(token))
        response.raise_for_status()
        data = response.json()

        status = data.get("status", "")
        progress = data.get("progress", "0%")
        print(f"   Estado: {status} ({progress})")

        if status == "success":
            return "success"
        elif status == "failed":
            print(f"[ERROR] Traducción falló: {data}")
            return "failed"
        elif status == "timeout":
            return "timeout"

        time.sleep(5)

    print("[ERROR] Timeout esperando traducción.")
    return "timeout"


def get_model_views(token: str, urn: str) -> list[dict]:
    """
    Obtiene las vistas del modelo (metadata).
    Cada vista tiene un GUID que necesitamos para consultar propiedades.
    """
    print("\n[MODEL DERIVATIVE] Obteniendo vistas del modelo...")
    url = f"{MD_URL}/{urn}/metadata"

    response = requests.get(url, headers=_get_headers(token))
    response.raise_for_status()
    data = response.json()

    views = data.get("data", {}).get("metadata", [])
    for v in views:
        print(f"   Vista: {v.get('name', '?')} | GUID: {v.get('guid', '?')} | Rol: {v.get('role', '?')}")

    return views


def get_model_tree(token: str, urn: str, guid: str) -> dict:
    """
    Obtiene el árbol jerárquico de objetos del modelo.
    """
    print(f"\n[MODEL DERIVATIVE] Obteniendo árbol de objetos (guid={guid[:8]}...)...")
    url = f"{MD_URL}/{urn}/metadata/{guid}"

    # Este endpoint puede devolver 202 si aún se está procesando
    for _ in range(30):
        response = requests.get(url, headers=_get_headers(token))
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 202:
            print("   Procesando árbol, esperando...")
            time.sleep(3)
        else:
            response.raise_for_status()

    raise TimeoutError("Timeout obteniendo árbol del modelo")


def get_all_properties(token: str, urn: str, guid: str) -> dict:
    """
    Obtiene TODAS las propiedades de todos los objetos del modelo.
    Esto incluye: capas, áreas, longitudes, bloques, atributos, etc.
    """
    print(f"\n[MODEL DERIVATIVE] Extrayendo todas las propiedades...")
    url = f"{MD_URL}/{urn}/metadata/{guid}/properties"

    # Este endpoint puede devolver 202 si aún se está procesando
    for attempt in range(60):
        response = requests.get(url, headers=_get_headers(token))
        if response.status_code == 200:
            data = response.json()
            collection = data.get("data", {}).get("collection", [])
            print(f"[OK] {len(collection)} objetos con propiedades extraídos.")
            return data
        elif response.status_code == 202:
            print(f"   Procesando propiedades (intento {attempt + 1})...")
            time.sleep(5)
        else:
            print(f"[ERROR] {response.status_code}: {response.text}")
            response.raise_for_status()

    raise TimeoutError("Timeout obteniendo propiedades del modelo")


def query_specific_properties(token: str, urn: str, guid: str, object_ids: list[int]) -> dict:
    """
    Consulta propiedades de objetos específicos (por ID).
    Usa el endpoint POST :query como en el código de referencia del repositorio de Autodesk.
    """
    print(f"\n[MODEL DERIVATIVE] Consultando propiedades de {len(object_ids)} objetos...")
    url = f"{MD_URL}/{urn}/metadata/{guid}/properties:query"

    payload = {
        "pagination": {
            "limit": len(object_ids),
        },
        "query": {
            "$in": ["objectid"] + object_ids,
        },
    }

    response = requests.post(url, json=payload, headers=_get_headers(token))
    response.raise_for_status()
    return response.json()


def extract_dwg_data(token: str, bucket_key: str, object_name: str) -> dict:
    """
    Pipeline completo: traduce un DWG y extrae todas sus propiedades.

    Args:
        token: Token de autenticación APS
        bucket_key: Nombre del bucket OSS
        object_name: Nombre del objeto en el bucket

    Returns:
        dict con toda la data extraída del DWG
    """
    # 1. Generar URN
    urn = urn_from_object_id(bucket_key, object_name)
    print(f"\n{'='*60}")
    print(f"EXTRACCIÓN MODEL DERIVATIVE")
    print(f"Bucket: {bucket_key}")
    print(f"Objeto: {object_name}")
    print(f"URN: {urn[:30]}...")
    print(f"{'='*60}")

    # 2. Traducir a SVF2
    translate_to_svf2(token, urn)

    # 3. Esperar traducción
    status = wait_for_translation(token, urn)
    if status != "success":
        raise RuntimeError(f"Traducción falló con estado: {status}")

    # 4. Obtener vistas
    views = get_model_views(token, urn)
    if not views:
        raise RuntimeError("No se encontraron vistas en el modelo traducido")

    # 5. Extraer propiedades de cada vista
    all_results = {
        "urn": urn,
        "object_name": object_name,
        "views": [],
    }

    for view in views:
        guid = view.get("guid", "")
        view_name = view.get("name", "Unknown")
        role = view.get("role", "")

        print(f"\n--- Procesando vista: {view_name} ({role}) ---")

        try:
            properties = get_all_properties(token, urn, guid)
            collection = properties.get("data", {}).get("collection", [])

            all_results["views"].append({
                "name": view_name,
                "guid": guid,
                "role": role,
                "object_count": len(collection),
                "objects": collection,
            })
        except Exception as e:
            print(f"[WARN] Error extrayendo vista {view_name}: {e}")
            all_results["views"].append({
                "name": view_name,
                "guid": guid,
                "role": role,
                "error": str(e),
            })

    total_objects = sum(v.get("object_count", 0) for v in all_results["views"])
    print(f"\n{'='*60}")
    print(f"EXTRACCIÓN COMPLETA: {total_objects} objetos en {len(views)} vistas")
    print(f"{'='*60}")

    return all_results
