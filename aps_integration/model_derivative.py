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
DEFAULT_FAILED_MANIFEST_GRACE_POLLS = 3
DEFAULT_FAILED_MANIFEST_GRACE_SLEEP_SECONDS = 20
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


def _node_markers(node: dict | None) -> list[str]:
    if not isinstance(node, dict):
        return []
    markers: list[str] = []
    for key in ("role", "type", "mime", "name", "urn"):
        value = node.get(key)
        if value:
            markers.append(str(value).lower())
    return markers


def _is_property_database_node(node: dict | None) -> bool:
    markers = _node_markers(node)
    return any(
        "autodesk.cloudplatform.propertydatabase" in marker
        or "propertydatabase" in marker
        or "autodesk-db" in marker
        for marker in markers
    )


def inspect_manifest_derivatives(manifest: dict | None) -> dict[str, object]:
    status, progress = _manifest_status_and_progress(manifest)
    property_database_statuses: list[str] = []
    for node in _iter_manifest_nodes(manifest):
        if _is_property_database_node(node):
            property_database_statuses.append(
                str(node.get("status") or "unknown").lower()
            )

    return {
        "manifest_status": status,
        "manifest_progress": progress,
        "manifest_failed": status == "failed",
        "roles": sorted(_manifest_roles(manifest)),
        "property_database_exists": bool(property_database_statuses),
        "property_database_success": any(
            node_status == "success" for node_status in property_database_statuses
        ),
        "property_database_statuses": property_database_statuses,
    }


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
    failed_manifest_grace_polls: int = 0,
    failed_manifest_grace_sleep_seconds: int = DEFAULT_FAILED_MANIFEST_GRACE_SLEEP_SECONDS,
) -> str:
    """
    Poll the manifest until translation succeeds, fails, or times out.

    Returns:
        'success', 'failed', or 'timeout'
    """
    print(
        f"[MODEL DERIVATIVE] Waiting for translation | "
        f"URN={_short_urn(urn)} | timeout={timeout}s | poll={poll_interval_seconds}s | "
        f"failed_manifest_grace_polls={failed_manifest_grace_polls}"
    )
    start = time.monotonic()
    sleep_seconds = max(int(poll_interval_seconds), 1)
    grace_polls_remaining = max(int(failed_manifest_grace_polls), 0)
    grace_sleep_seconds = max(int(failed_manifest_grace_sleep_seconds), 1)

    while True:
        elapsed = int(time.monotonic() - start)
        manifest = get_manifest(token, urn)
        manifest_info = inspect_manifest_derivatives(manifest)
        status = str(manifest_info["manifest_status"])
        progress = str(manifest_info["manifest_progress"])
        print(
            f"   URN={_short_urn(urn)} | status={status} | progress={progress} | "
            f"property_database_success={manifest_info['property_database_success']} | "
            f"elapsed={elapsed}s"
        )

        if status == "success":
            return "success"
        if status == "failed":
            if grace_polls_remaining > 0:
                print(
                    f"[WARN] Failed manifest seen for URN={_short_urn(urn)} but grace is active. "
                    f"Assuming Autodesk may still be surfacing a stale failed manifest. "
                    f"Remaining grace polls: {grace_polls_remaining}."
                )
                grace_polls_remaining -= 1
                remaining = max(timeout - elapsed, 1)
                time.sleep(min(grace_sleep_seconds, remaining))
                continue
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


def _filter_requested_views(views_payload: list[dict], normalized_views: list[str]) -> list[dict]:
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
        return filtered_views

    print(
        "[WARN] No view role matched the requested set exactly. "
        "Proceeding with all available views."
    )
    return views_payload


def _extract_view_results(
    token: str,
    urn: str,
    views_payload: list[dict],
    normalized_views: list[str],
    *,
    max_property_wait_seconds: int,
    poll_interval_seconds: int,
) -> tuple[list[dict], int]:
    extracted_views: list[dict] = []
    successful_view_count = 0
    filtered_views = _filter_requested_views(views_payload, normalized_views)

    for view in filtered_views:
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
            extracted_views.append(
                {
                    "name": view_name,
                    "guid": guid,
                    "role": role,
                    "object_count": len(collection),
                    "objects": collection,
                }
            )
            successful_view_count += 1
        except Exception as exc:
            print(f"[WARN] Failed extracting view {view_name}: {exc}")
            extracted_views.append(
                {
                    "name": view_name,
                    "guid": guid,
                    "role": role,
                    "error": str(exc),
                }
            )

    return extracted_views, successful_view_count


def _build_failed_translation_message(
    *,
    urn: str,
    manifest_strategy: str,
    property_database_exists: bool,
    property_database_success: bool,
    salvage_attempted: bool,
) -> str:
    return (
        f"Translation failed for URN={urn}. "
        f"manifest_strategy={manifest_strategy}. "
        f"property_database_exists={property_database_exists}. "
        f"property_database_success={property_database_success}. "
        f"salvage_attempted={salvage_attempted}."
    )


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
    failed_manifest_grace_polls: int = DEFAULT_FAILED_MANIFEST_GRACE_POLLS,
    failed_manifest_grace_sleep_seconds: int = DEFAULT_FAILED_MANIFEST_GRACE_SLEEP_SECONDS,
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
    print(f"Failed-manifest grace polls: {failed_manifest_grace_polls}")
    print(f"Failed-manifest grace sleep: {failed_manifest_grace_sleep_seconds}s")
    print(f"{'=' * 60}")

    manifest = get_manifest(token, urn)
    manifest_info = inspect_manifest_derivatives(manifest)
    manifest_status = str(manifest_info["manifest_status"])
    manifest_progress = str(manifest_info["manifest_progress"])
    manifest_reused = False
    should_submit_translation = True
    translation_submitted = False
    resubmitted_after_failed_manifest = False
    manifest_strategy = "fresh_submission"

    if manifest is None:
        print(f"[MODEL DERIVATIVE] No existing manifest found | URN={_short_urn(urn)}")
    else:
        print(
            f"[MODEL DERIVATIVE] Existing manifest found | URN={_short_urn(urn)} | "
            f"status={manifest_status} | progress={manifest_progress} | "
            f"roles={manifest_info['roles']} | "
            f"property_database_exists={manifest_info['property_database_exists']} | "
            f"property_database_success={manifest_info['property_database_success']}"
        )
        if manifest_status == "success" and _manifest_satisfies_views(manifest, normalized_views):
            manifest_reused = True
            should_submit_translation = False
            manifest_strategy = "reused_success_manifest"
            print("[MODEL DERIVATIVE] Reusing successful manifest for requested views.")
        elif manifest_status in {"inprogress", "pending"}:
            manifest_reused = True
            should_submit_translation = False
            manifest_strategy = "reused_in_progress_manifest"
            print("[MODEL DERIVATIVE] Reusing in-progress manifest and continuing to poll.")
        elif manifest_status == "success":
            manifest_strategy = "resubmitted_for_view_mismatch"
            print(
                "[MODEL DERIVATIVE] Existing manifest does not clearly cover the requested views. "
                "Submitting a new translation job."
            )
        elif manifest_status == "failed":
            manifest_strategy = "resubmitted_after_failed_manifest"
            resubmitted_after_failed_manifest = True
            print("[MODEL DERIVATIVE] Existing manifest failed previously. Resubmitting translation.")

    if should_submit_translation:
        translate_to_svf2(token, urn, views=normalized_views)
        translation_submitted = True

    status = manifest_status
    if not (
        manifest_reused
        and manifest_status == "success"
        and _manifest_satisfies_views(manifest, normalized_views)
    ):
        status = wait_for_translation(
            token,
            urn,
            timeout=translation_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            failed_manifest_grace_polls=(
                failed_manifest_grace_polls if resubmitted_after_failed_manifest else 0
            ),
            failed_manifest_grace_sleep_seconds=failed_manifest_grace_sleep_seconds,
        )
        if status == "timeout":
            raise TimeoutError(
                f"Translation did not finish within {translation_timeout_seconds}s for URN={urn}. "
                f"manifest_strategy={manifest_strategy}. "
                "Autodesk may still be processing the file remotely. Re-run later to reuse the same manifest."
            )

    latest_manifest = get_manifest(token, urn)
    latest_manifest_info = inspect_manifest_derivatives(latest_manifest)
    print(
        f"[MODEL DERIVATIVE] Final manifest snapshot | URN={_short_urn(urn)} | "
        f"status={latest_manifest_info['manifest_status']} | "
        f"progress={latest_manifest_info['manifest_progress']} | "
        f"property_database_exists={latest_manifest_info['property_database_exists']} | "
        f"property_database_success={latest_manifest_info['property_database_success']}"
    )

    salvage_attempted = False
    salvage_succeeded = False
    views_results: list[dict] | None = None
    successful_view_count = 0

    if status != "success" and bool(latest_manifest_info["property_database_success"]):
        salvage_attempted = True
        print(
            f"[WARN] Manifest is not successful but PropertyDatabase is ready | "
            f"URN={_short_urn(urn)}. Attempting metadata/property salvage."
        )
        try:
            views_payload = get_model_views(token, urn)
            if views_payload:
                views_results, successful_view_count = _extract_view_results(
                    token,
                    urn,
                    views_payload,
                    normalized_views,
                    max_property_wait_seconds=max_property_wait_seconds,
                    poll_interval_seconds=poll_interval_seconds,
                )
                salvage_succeeded = successful_view_count > 0
        except Exception as exc:
            print(f"[WARN] Salvage attempt failed for URN={_short_urn(urn)}: {exc}")

    if status != "success" and not salvage_succeeded:
        raise RuntimeError(
            _build_failed_translation_message(
                urn=urn,
                manifest_strategy=manifest_strategy,
                property_database_exists=bool(
                    latest_manifest_info["property_database_exists"]
                ),
                property_database_success=bool(
                    latest_manifest_info["property_database_success"]
                ),
                salvage_attempted=salvage_attempted,
            )
        )

    if views_results is None:
        views_payload = get_model_views(token, urn)
        if not views_payload:
            raise RuntimeError(f"No views were found for translated model URN={urn}.")
        views_results, successful_view_count = _extract_view_results(
            token,
            urn,
            views_payload,
            normalized_views,
            max_property_wait_seconds=max_property_wait_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    all_results = {
        "urn": urn,
        "object_name": object_name,
        "views_requested": normalized_views,
        "manifest_reused": manifest_reused,
        "manifest_strategy": manifest_strategy,
        "translation_submitted": translation_submitted,
        "resubmitted_after_failed_manifest": resubmitted_after_failed_manifest,
        "manifest_status": str(latest_manifest_info["manifest_status"]),
        "manifest_progress": str(latest_manifest_info["manifest_progress"]),
        "property_database_exists": bool(latest_manifest_info["property_database_exists"]),
        "property_database_success": bool(
            latest_manifest_info["property_database_success"]
        ),
        "salvage_attempted": salvage_attempted,
        "salvage_succeeded": salvage_succeeded,
        "views": views_results,
    }

    total_objects = sum(view.get("object_count", 0) for view in all_results["views"])
    print(f"\n{'=' * 60}")
    print(
        f"MODEL DERIVATIVE EXTRACTION COMPLETE | "
        f"URN={_short_urn(urn)} | objects={total_objects} | views={len(all_results['views'])} | "
        f"successful_views={successful_view_count} | salvage_attempted={salvage_attempted}"
    )
    print(f"{'=' * 60}")
    return all_results
