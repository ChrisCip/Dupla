import os
import requests
from dotenv import load_dotenv
from pathlib import Path

AUTH_URL = "https://developer.api.autodesk.com/authentication/v2/token"


def _load_project_env() -> Path:
    """Carga el .env desde la raiz del proyecto y devuelve su ruta esperada."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(dotenv_path=env_path)
    return env_path

def get_aps_token():
    """
    Obtiene un token de acceso (2-Legged OAuth) de Autodesk Platform Services.
    """
    env_path = _load_project_env()
    client_id = os.getenv("CLIENT_ID") or os.getenv("APS_CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET") or os.getenv("APS_CLIENT_SECRET")

    if not client_id or not client_secret:
        raise ValueError(
            "Faltan credenciales APS. Configura CLIENT_ID y CLIENT_SECRET "
            f"(o APS_CLIENT_ID y APS_CLIENT_SECRET) en {env_path}"
        )

    # Los scopes definen los permisos. Para Design Automation y OSS necesitamos estos:
    payload = {
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'client_credentials',
        'scope': 'data:read data:write data:create bucket:create bucket:read code:all viewables:read'
    }

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded'
    }

    print("Obteniendo token de autenticación de Autodesk APS...")
    response = requests.post(AUTH_URL, data=payload, headers=headers)
    
    if response.status_code == 200:
        access_token = response.json().get("access_token")
        print("[OK] Token obtenido con éxito!")
        return access_token
    else:
        print(f"[ERROR] Error al obtener token: {response.status_code} - {response.text}")
        response.raise_for_status()

if __name__ == "__main__":
    # Prueba rápida de autenticación
    token = get_aps_token()
    print(f"Token (primeros 20 caracteres): {token[:20]}...")
