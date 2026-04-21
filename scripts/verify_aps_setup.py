"""
Verificación rápida de credenciales APS y (opcional) Design Automation.

Orden recomendado con cuenta nueva:
1) Este script — confirma token y recursos accesibles
2) python aps_integration/da_manager.py — registra AppBundle + Activity si usas DA
3) python dupla_run_full_analysis_local.py — pipeline completo (Model Derivative / OSS)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import requests
from requests import HTTPError

from aps_integration.aps_auth import get_aps_token


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Autodesk APS token and optional DA API reachability")
    parser.add_argument(
        "--check-da",
        action="store_true",
        help="GET appbundles en Design Automation (requiere scope code:all).",
    )
    args = parser.parse_args()

    try:
        token = get_aps_token()
    except HTTPError as exc:
        body = ""
        if exc.response is not None:
            body = (exc.response.text or "")[:400]
        print(
            "\nFallo de autenticación APS. Revisa en `.env` del repo:\n"
            "  - CLIENT_ID y CLIENT_SECRET (app Autodesk con Client credentials)\n"
            "  - Que el `.env` esté en la raíz del proyecto y que ejecutes el script desde ahí.\n"
            "Error HTTP:", exc.response.status_code if exc.response else "?", body, sep="\n", end="\n"
        )
        if exc.response is not None and exc.response.status_code == 401:
            print(
                "\n401 invalid_credentials: las credenciales no coinciden con ninguna app activa "
                "en developer.autodesk.com/myapps — genera un nuevo secret o crea otra app."
            )
        raise SystemExit(1) from exc

    print(f"[OK] Token APS ({len(token)} chars)")

    if args.check_da:
        url = "https://developer.api.autodesk.com/da/us-east/v3/appbundles"
        r = requests.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=60)
        if r.status_code != 200:
            print(f"[WARN] DA appbundles list: HTTP {r.status_code} — {r.text[:500]}")
            print("       Si el pipeline solo usa Model Derivative + OSS, puede ignorarse.")
        else:
            data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            items = data.get("data") or data.get("results") or []
            print(f"[OK] Design Automation reachable; appbundles payload keys: {list(data.keys())[:8]}")
            if isinstance(items, list):
                print(f"     Items count (if list): {len(items)}")

    zip_path = REPO_ROOT / "aps_integration" / "DuplaExtractor.zip"
    if zip_path.exists():
        print(f"[OK] DuplaExtractor.zip present ({zip_path.stat().st_size} bytes)")
    else:
        print(f"[INFO] No DuplaExtractor.zip at {zip_path} — run DA packaging before da_manager.py")


if __name__ == "__main__":
    main()
