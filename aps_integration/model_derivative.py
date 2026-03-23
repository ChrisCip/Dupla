"""
Model Derivative API helpers for DWG extraction via REST.

Flow:
    Upload DWG -> Translate to SVF2 -> Read metadata -> Read properties

Everything stays REST-based. No COM or local Autodesk automation is used.
"""

from __future__ import annotations

import base64
import time
from collections.abc import Iterable

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://developer.api.autodesk.com"
MD_URL = f"{BASE_URL}/modelderivative/v2/designdata"

DEFAULT_VIEWS = ("2d",)
DEFAULT_TRANSLATION_TIMEOUT_SECONDS = 3600
DEFAULT_POLL_INTERVAL_SECONDS = 10
DEFAULT_MAX_PROPERTY_WAIT_SECONDS = 3600
REQUEST_TIMEOUT_SECONDS = 60


def _get_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _normalize_views(views: Iterable[str] | None) -> list[str]:
    normalized: list[str] = []
    for view in views or DEFAULT_VIEWS:
        lowered = str(view).strip().lower()
        if lowered not in {"2d", "3d"}:
            raise ValueError(f"Invalid view '{view}'. Expected '2d' and/or '3d'.")
        if lowered not in normalized:
            normalized.append(lowered)
    return normalized or list(DEFAULT_VIEWS)


def _short_urn(urn: str) -> str:
    return urn if len(urn) <= 24 else f"{urn[:24]}..."


def _manifest_status_and_progress(manifest: dict | None) -> tuple[str, str]:
    if not manifest:
        return "missing", "0%"
    return (
        str(manifest.get("status") or "unknown").lower(),
        str(manifest.get("progress") or "0%"),
    )


def _iter_manifest_nodes(node: dict | list | None):
    if isinstance(node, dict):
        yield node
        for child in node.get("children", []) or []:
            yield from _iter_manifest_nodes(child)
        for child in node.get("derivatives", []) or []:
            yield from _iter_manifest_nodes(child)
    elif isinstance(node, list):
        for item in node:
            yield from _iter_manifest_nodes(item)


def _manifest_roles(manifest: dict | None) -> set[str]:
    roles: set[str] = set()
    for node in _iter_manifest_nodes(manifest):
        role = node.get("role")
        if role:
            roles.add(str(role).lower())
    return roles


def _manifest_satisfies_views(manifest: dict | None, views: Iterable[str]) -> bool:
    requested = set(_normalize_views(views))
    if not requested:
        return False
    roles = _manifest_roles(manifest)
    return requested.issubset(roles)


def get_manifest(token: str, urn: str) -> dict | None:
    url = f"{MD_URL}/{urn}/manifest"
    response = requests.get(
        url,
        headers=_get_headers(token),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def urn_from_object_id(bucket_key: str, object_name: str) -> str:
    """
    Generate the base64 URN from bucket + object name.
    """
    object_id = f"urn:adsk.objects:os.object:{bucket_key}/{object_name}"
    return base64.urlsafe_b64encode(object_id.encode()).decode().rstrip("=")


def translate_to_svf2(
    token: str,
    urn: str,
    max_retries: int = 3,
    views: Iterable[str] = DEFAULT_VIEWS,
) -> dict:
    """
    Submit an SVF2 translation job for the requested views.

    By default the budgeting pipeline asks for 2D only because it is
    significantly cheaper than translating both 2D and 3D for large DWGs.
    """
    normalized_views = _normalize_views(views)
    print(
        f"\n[MODEL DERIVATIVE] Submitting translation job | "
        f"URN={_short_urn(urn)} | views={normalized_views}"
    )
    url = f"{MD_URL}/job"
    payload = {
        "input": {"urn": urn},
        "output": {
            "formats": [
                {
                    "type": "svf2",
                    "views": normalized_views,
                }
            ]
        },
    }

    last_response: requests.Response | None = None
    for attempt in range(1, max_retries + 1):
        response = requests.post(
            url,
            json=payload,
            headers=_get_headers(token),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        last_response = response

        if response.status_code == 200:
            print("[OK] Translation job accepted; manifest may already exist.")
            return response.json()
        if response.status_code in {201, 202}:
            print("[OK] Translation job started.")
            return response.json()
        if response.status_code in {429} or response.status_code >= 500:
            wait_seconds = 10 * attempt
            print(
                f"[WARN] Autodesk returned {response.status_code} on translation attempt "
                f"{attempt}/{max_retries}. Retrying in {wait_seconds}s..."
            )
            time.sleep(wait_seconds)
            continue

        print(f"[ERROR] Translation request failed: {response.status_code}: {response.text}")
        response.raise_for_status()

    if last_response is not None:
        print(
            f"[ERROR] Translation failed after {max_retries} retries: "
            f"{last_response.status_code}: {last_response.text}"
        )
        last_response.raise_for_status()
    raise RuntimeError(
        f"Translation failed after {max_retries} retries for URN {_short_urn(urn)}."
    )


def wait_for_translation(
    token: str,
    urn: str,
    timeout: int = DEFAULT_TRANSLATION_TIMEOUT_SECONDS,
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
) -> str:
    """
    Poll the manifest until translation succeeds, fails, or times out.

    Returns:
        'success', 'failed', or 'timeout'
    """
    print(
        f"[MODEL DERIVATIVE] Waiting for translation | "
        f"URN={_short_urn(urn)} | timeout={timeout}s | poll={poll_interval_seconds}s"
    )
    start = time.monotonic()
    sleep_seconds = max(int(poll_interval_seconds), 1)

    while True:
        elapsed = int(time.monotonic() - start)
        manifest = get_manifest(token, urn)
        status, progress = _manifest_status_and_progress(manifest)
        print(
            f"   URN={_short_urn(urn)} | status={status} | progress={progress} | elapsed={elapsed}s"
        )

        if status == "success":
            return "success"
        if status == "failed":
            print(f"[ERROR] Translation failed for URN={_short_urn(urn)}: {manifest}")
            return "failed"
        if elapsed >= timeout:
            print(
                f"[ERROR] Translation timeout reached for URN={_short_urn(urn)} "
                f"after {elapsed}s."
            )
            return "timeout"

        remaining = max(timeout - elapsed, 1)
        time.sleep(min(sleep_seconds, remaining))
        sleep_seconds = min(max(int(poll_interval_seconds), 1), sleep_seconds + 2, 30)


def get_model_views(token: str, urn: str) -> list[dict]:
    """
    Get model views (metadata). Each view includes the GUID needed to request
    properties.
    """
    print(f"\n[MODEL DERIVATIVE] Fetching model views | URN={_short_urn(urn)}")
    url = f"{MD_URL}/{urn}/metadata"
    response = requests.get(
        url,
        headers=_get_headers(token),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()

    views = data.get("data", {}).get("metadata", [])
    for view in views:
        print(
            f"   View: {view.get('name', '?')} | GUID: {view.get('guid', '?')} | "
            f"role: {view.get('role', '?')}"
        )
    return views


def get_model_tree(token: str, urn: str, guid: str) -> dict:
    """
    Get the hierarchical object tree for a model view.
    """
    print(
        f"\n[MODEL DERIVATIVE] Fetching object tree | URN={_short_urn(urn)} | guid={guid[:8]}..."
    )
    url = f"{MD_URL}/{urn}/metadata/{guid}"
    for _ in range(30):
        response = requests.get(
            url,
            headers=_get_headers(token),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 200:
            return response.json()
        if response.status_code == 202:
            print("   Object tree still processing, waiting...")
            time.sleep(3)
            continue
        response.raise_for_status()
    raise TimeoutError(
        f"Timeout fetching model tree for URN={_short_urn(urn)} guid={guid[:8]}..."
    )


def get_all_properties(
    token: str,
    urn: str,
    guid: str,
    max_wait_seconds: int = DEFAULT_MAX_PROPERTY_WAIT_SECONDS,
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
) -> dict:
    """
    Fetch all properties for a model view.

    Property indexing can take a long time on large DWGs, so this waits based
    on elapsed time rather than a fragile fixed-attempt loop.
    """
    print(
        f"\n[MODEL DERIVATIVE] Fetching all properties | "
        f"URN={_short_urn(urn)} | guid={guid[:8]}... | "
        f"timeout={max_wait_seconds}s | poll={poll_interval_seconds}s"
    )
    url = f"{MD_URL}/{urn}/metadata/{guid}/properties"
    start = time.monotonic()
    sleep_seconds = max(int(poll_interval_seconds), 1)

    while True:
        elapsed = int(time.monotonic() - start)
        response = requests.get(
            url,
            headers=_get_headers(token),
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        if response.status_code == 200:
            data = response.json()
            collection = data.get("data", {}).get("collection", [])
            print(
                f"[OK] Extracted properties for {len(collection)} objects | "
                f"URN={_short_urn(urn)} | guid={guid[:8]}..."
            )
            return data

        if response.status_code in {202, 404}:
            print(
                f"   Properties still processing | URN={_short_urn(urn)} | "
                f"guid={guid[:8]}... | status={response.status_code} | elapsed={elapsed}s"
            )
            if elapsed >= max_wait_seconds:
                raise TimeoutError(
                    f"Timed out waiting for properties for URN={urn} guid={guid}. "
                    "Property indexing may still be processing remotely in Autodesk."
                )
            remaining = max(max_wait_seconds - elapsed, 1)
            time.sleep(min(sleep_seconds, remaining))
            sleep_seconds = min(max(int(poll_interval_seconds), 1), sleep_seconds + 2, 30)
            continue

        print(
            f"[ERROR] Property request failed | URN={_short_urn(urn)} | "
            f"guid={guid[:8]}... | status={response.status_code}: {response.text}"
        )
        response.raise_for_status()


def query_specific_properties(token: str, urn: str, guid: str, object_ids: list[int]) -> dict:
    """
    Query properties for a specific object ID list.
    """
    print(
        f"\n[MODEL DERIVATIVE] Querying properties for {len(object_ids)} objects | "
        f"URN={_short_urn(urn)} | guid={guid[:8]}..."
    )
    url = f"{MD_URL}/{urn}/metadata/{guid}/properties:query"
    payload = {
        "pagination": {"limit": len(object_ids)},
        "query": {"$in": ["objectid"] + object_ids},
    }
    response = requests.post(
        url,
        json=payload,
        headers=_get_headers(token),
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def extract_dwg_data(
    token: str,
    bucket_key: str,
    object_name: str,
    *,
    views: Iterable[str] = DEFAULT_VIEWS,
    translation_timeout_seconds: int = DEFAULT_TRANSLATION_TIMEOUT_SECONDS,
    poll_interval_seconds: int = DEFAULT_POLL_INTERVAL_SECONDS,
    max_property_wait_seconds: int = DEFAULT_MAX_PROPERTY_WAIT_SECONDS,
) -> dict:
    """
    Full pipeline: translate a DWG and extract all available properties.

    The budgeting workflow defaults to 2D-only translation because large DWGs
    are much faster and cheaper to process that way.
    """
    normalized_views = _normalize_views(views)
    urn = urn_from_object_id(bucket_key, object_name)
    print(f"\n{'=' * 60}")
    print("MODEL DERIVATIVE EXTRACTION")
    print(f"Bucket: {bucket_key}")
    print(f"Object: {object_name}")
    print(f"URN: {_short_urn(urn)}")
    print(f"Views: {normalized_views}")
    print(f"Translation timeout: {translation_timeout_seconds}s")
    print(f"Property timeout: {max_property_wait_seconds}s")
    print(f"{'=' * 60}")

    manifest = get_manifest(token, urn)
    manifest_status, manifest_progress = _manifest_status_and_progress(manifest)
    manifest_reused = False
    should_submit_translation = True

    if manifest is None:
        print(f"[MODEL DERIVATIVE] No existing manifest found | URN={_short_urn(urn)}")
    else:
        roles = sorted(_manifest_roles(manifest))
        print(
            f"[MODEL DERIVATIVE] Existing manifest found | URN={_short_urn(urn)} | "
            f"status={manifest_status} | progress={manifest_progress} | roles={roles}"
        )
        if manifest_status == "success" and _manifest_satisfies_views(manifest, normalized_views):
            manifest_reused = True
            should_submit_translation = False
            print("[MODEL DERIVATIVE] Reusing successful manifest for requested views.")
        elif manifest_status in {"inprogress", "pending"}:
            manifest_reused = True
            should_submit_translation = False
            print("[MODEL DERIVATIVE] Reusing in-progress manifest and continuing to poll.")
        elif manifest_status == "success":
            print(
                "[MODEL DERIVATIVE] Existing manifest does not clearly cover the requested views. "
                "Submitting a new translation job."
            )
        elif manifest_status == "failed":
            print("[MODEL DERIVATIVE] Existing manifest failed previously. Resubmitting translation.")

    if should_submit_translation:
        translate_to_svf2(token, urn, views=normalized_views)

    if not (manifest_reused and manifest_status == "success" and _manifest_satisfies_views(manifest, normalized_views)):
        status = wait_for_translation(
            token,
            urn,
            timeout=translation_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )
        if status == "timeout":
            raise TimeoutError(
                f"Translation did not finish within {translation_timeout_seconds}s for URN={urn}. "
                "Autodesk may still be processing the file remotely. Re-run later to reuse the same manifest."
            )
        if status != "success":
            raise RuntimeError(f"Translation failed with status '{status}' for URN={urn}.")

    views_payload = get_model_views(token, urn)
    if not views_payload:
        raise RuntimeError(f"No views were found for translated model URN={urn}.")

    requested_view_set = set(normalized_views)
    filtered_views = [
        view
        for view in views_payload
        if str(view.get("role", "")).lower() in requested_view_set
    ]
    if filtered_views:
        print(
            f"[MODEL DERIVATIVE] Using {len(filtered_views)} filtered views "
            f"matching requested roles {normalized_views}."
        )
        views_payload = filtered_views
    else:
        print(
            "[WARN] No view role matched the requested set exactly. "
            "Proceeding with all available views."
        )

    all_results = {
        "urn": urn,
        "object_name": object_name,
        "views_requested": normalized_views,
        "manifest_reused": manifest_reused,
        "views": [],
    }

    for view in views_payload:
        guid = view.get("guid", "")
        view_name = view.get("name", "Unknown")
        role = view.get("role", "")
        print(f"\n--- Processing view: {view_name} ({role}) | guid={guid[:8]}... ---")
        try:
            properties = get_all_properties(
                token,
                urn,
                guid,
                max_wait_seconds=max_property_wait_seconds,
                poll_interval_seconds=poll_interval_seconds,
            )
            collection = properties.get("data", {}).get("collection", [])
            all_results["views"].append(
                {
                    "name": view_name,
                    "guid": guid,
                    "role": role,
                    "object_count": len(collection),
                    "objects": collection,
                }
            )
        except Exception as exc:
            print(f"[WARN] Failed extracting view {view_name}: {exc}")
            all_results["views"].append(
                {
                    "name": view_name,
                    "guid": guid,
                    "role": role,
                    "error": str(exc),
                }
            )

    total_objects = sum(view.get("object_count", 0) for view in all_results["views"])
    print(f"\n{'=' * 60}")
    print(
        f"MODEL DERIVATIVE EXTRACTION COMPLETE | "
        f"URN={_short_urn(urn)} | objects={total_objects} | views={len(all_results['views'])}"
    )
    print(f"{'=' * 60}")
    return all_results
