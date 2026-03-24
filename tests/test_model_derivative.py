import aps_integration.model_derivative as md


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self) -> dict:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}: {self.text}")


def test_translate_to_svf2_defaults_to_2d_only() -> None:
    original_post = md.requests.post
    captured: dict = {}

    def fake_post(url, json, headers, timeout):  # type: ignore[no-untyped-def]
        captured["url"] = url
        captured["payload"] = json
        captured["timeout"] = timeout
        return _FakeResponse(201, {"result": "created"})

    md.requests.post = fake_post
    try:
        result = md.translate_to_svf2("token", "urn:demo")
    finally:
        md.requests.post = original_post

    assert result == {"result": "created"}
    assert captured["payload"]["output"]["formats"][0]["views"] == ["2d"]


def test_wait_for_translation_polls_manifest_until_success() -> None:
    original_get_manifest = md.get_manifest
    original_sleep = md.time.sleep

    manifests = iter(
        [
            {"status": "inprogress", "progress": "45%"},
            {"status": "success", "progress": "complete"},
        ]
    )

    md.get_manifest = lambda token, urn: next(manifests)  # type: ignore[assignment]
    md.time.sleep = lambda seconds: None  # type: ignore[assignment]
    try:
        status = md.wait_for_translation(
            "token",
            "urn:demo",
            timeout=120,
            poll_interval_seconds=1,
        )
    finally:
        md.get_manifest = original_get_manifest
        md.time.sleep = original_sleep

    assert status == "success"


def test_wait_for_translation_honors_failed_manifest_grace() -> None:
    original_get_manifest = md.get_manifest
    original_sleep = md.time.sleep

    manifests = iter(
        [
            {"status": "failed", "progress": "complete"},
            {"status": "failed", "progress": "complete"},
            {"status": "success", "progress": "complete"},
        ]
    )

    md.get_manifest = lambda token, urn: next(manifests)  # type: ignore[assignment]
    md.time.sleep = lambda seconds: None  # type: ignore[assignment]
    try:
        status = md.wait_for_translation(
            "token",
            "urn:demo",
            timeout=120,
            poll_interval_seconds=1,
            failed_manifest_grace_polls=2,
            failed_manifest_grace_sleep_seconds=1,
        )
    finally:
        md.get_manifest = original_get_manifest
        md.time.sleep = original_sleep

    assert status == "success"


def test_wait_for_translation_refreshes_token_on_401_and_reuses_it() -> None:
    original_get = md.requests.get
    original_get_aps_token = md.get_aps_token
    original_sleep = md.time.sleep

    calls: list[str] = []
    responses = iter(
        [
            _FakeResponse(401, text="Unauthorized"),
            _FakeResponse(200, {"status": "success", "progress": "complete"}),
        ]
    )

    def fake_get(url, headers, timeout):  # type: ignore[no-untyped-def]
        calls.append(headers["Authorization"])
        return next(responses)

    md.requests.get = fake_get
    md.get_aps_token = lambda: "fresh-token"  # type: ignore[assignment]
    md.time.sleep = lambda seconds: None  # type: ignore[assignment]
    token_state = {"access_token": "expired-token"}
    try:
        status = md.wait_for_translation(
            token_state,
            "urn:demo",
            timeout=120,
            poll_interval_seconds=1,
        )
    finally:
        md.requests.get = original_get
        md.get_aps_token = original_get_aps_token
        md.time.sleep = original_sleep

    assert status == "success"
    assert token_state["access_token"] == "fresh-token"
    assert token_state["refresh_count"] == 1
    assert calls == ["Bearer expired-token", "Bearer fresh-token"]


def test_inspect_manifest_derivatives_detects_property_database_success() -> None:
    manifest = {
        "status": "failed",
        "progress": "complete",
        "derivatives": [
            {"role": "2d", "status": "failed"},
            {
                "role": "Autodesk.CloudPlatform.PropertyDatabase",
                "status": "success",
            },
        ],
    }

    info = md.inspect_manifest_derivatives(manifest)

    assert info["manifest_failed"] is True
    assert info["property_database_exists"] is True
    assert info["property_database_success"] is True
    assert "success" in info["property_database_statuses"]


def test_get_all_properties_refreshes_token_on_401_then_succeeds() -> None:
    original_get = md.requests.get
    original_get_aps_token = md.get_aps_token

    calls: list[str] = []
    responses = iter(
        [
            _FakeResponse(401, text="Unauthorized"),
            _FakeResponse(
                200,
                {"data": {"collection": [{"objectid": 1}, {"objectid": 2}]}},
            ),
        ]
    )

    def fake_get(url, headers, timeout):  # type: ignore[no-untyped-def]
        calls.append(headers["Authorization"])
        return next(responses)

    md.requests.get = fake_get
    md.get_aps_token = lambda: "fresh-token"  # type: ignore[assignment]
    token_state = {"access_token": "expired-token"}
    try:
        data = md.get_all_properties(
            token_state,
            "urn:demo",
            "guid-demo",
            max_wait_seconds=10,
            poll_interval_seconds=1,
        )
    finally:
        md.requests.get = original_get
        md.get_aps_token = original_get_aps_token

    assert token_state["access_token"] == "fresh-token"
    assert token_state["refresh_count"] == 1
    assert len(data["data"]["collection"]) == 2
    assert calls == ["Bearer expired-token", "Bearer fresh-token"]


def test_get_all_properties_uses_elapsed_timeout() -> None:
    original_get = md.requests.get
    original_sleep = md.time.sleep
    original_monotonic = md.time.monotonic

    monotonic_values = iter([0.0, 2.0, 4.0, 6.0])

    def fake_get(url, headers, timeout):  # type: ignore[no-untyped-def]
        return _FakeResponse(202, text="Still processing")

    md.requests.get = fake_get
    md.time.sleep = lambda seconds: None  # type: ignore[assignment]
    md.time.monotonic = lambda: next(monotonic_values)  # type: ignore[assignment]
    try:
        try:
            md.get_all_properties(
                "token",
                "urn:demo",
                "guid-demo",
                max_wait_seconds=4,
                poll_interval_seconds=1,
            )
        except TimeoutError as exc:
            message = str(exc)
        else:  # pragma: no cover - defensive guard
            raise AssertionError("Expected get_all_properties to time out.")
    finally:
        md.requests.get = original_get
        md.time.sleep = original_sleep
        md.time.monotonic = original_monotonic

    assert "may still be processing remotely" in message
    assert "urn:demo" in message


def test_extract_dwg_data_reuses_existing_success_manifest() -> None:
    original_get_manifest = md.get_manifest
    original_translate = md.translate_to_svf2
    original_wait = md.wait_for_translation
    original_views = md.get_model_views
    original_properties = md.get_all_properties

    translate_called = {"value": False}

    md.get_manifest = lambda token, urn: {  # type: ignore[assignment]
        "status": "success",
        "progress": "complete",
        "derivatives": [{"role": "2d"}],
    }

    def fake_translate(*args, **kwargs):  # type: ignore[no-untyped-def]
        translate_called["value"] = True
        return {"result": "submitted"}

    md.translate_to_svf2 = fake_translate  # type: ignore[assignment]
    md.wait_for_translation = lambda *args, **kwargs: "success"  # type: ignore[assignment]
    md.get_model_views = lambda token, urn: [  # type: ignore[assignment]
        {"guid": "guid-2d", "name": "Plan", "role": "2d"}
    ]
    md.get_all_properties = lambda *args, **kwargs: {  # type: ignore[assignment]
        "data": {"collection": [{"objectid": 1}]}
    }

    try:
        result = md.extract_dwg_data(
            "token",
            "bucket",
            "sample.dwg",
            views=("2d",),
            translation_timeout_seconds=30,
            poll_interval_seconds=1,
            max_property_wait_seconds=30,
        )
    finally:
        md.get_manifest = original_get_manifest
        md.translate_to_svf2 = original_translate
        md.wait_for_translation = original_wait
        md.get_model_views = original_views
        md.get_all_properties = original_properties

    assert result["manifest_reused"] is True
    assert result["views_requested"] == ["2d"]
    assert translate_called["value"] is False
    assert result["views"][0]["object_count"] == 1


def test_extract_dwg_data_salvages_failed_manifest_with_property_database() -> None:
    original_get_manifest = md.get_manifest
    original_translate = md.translate_to_svf2
    original_wait = md.wait_for_translation
    original_views = md.get_model_views
    original_properties = md.get_all_properties

    manifests = iter(
        [
            {"status": "failed", "progress": "complete", "derivatives": []},
            {
                "status": "failed",
                "progress": "complete",
                "derivatives": [
                    {
                        "role": "Autodesk.CloudPlatform.PropertyDatabase",
                        "status": "success",
                    }
                ],
            },
        ]
    )
    captured_wait_kwargs: dict = {}

    md.get_manifest = lambda token, urn: next(manifests)  # type: ignore[assignment]
    md.translate_to_svf2 = lambda *args, **kwargs: {"result": "submitted"}  # type: ignore[assignment]

    def fake_wait(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured_wait_kwargs.update(kwargs)
        return "failed"

    md.wait_for_translation = fake_wait  # type: ignore[assignment]
    md.get_model_views = lambda token, urn: [  # type: ignore[assignment]
        {"guid": "guid-2d", "name": "Plan", "role": "2d"}
    ]
    md.get_all_properties = lambda *args, **kwargs: {  # type: ignore[assignment]
        "data": {"collection": [{"objectid": 1}, {"objectid": 2}]}
    }

    try:
        result = md.extract_dwg_data(
            "token",
            "bucket",
            "failed_but_salvageable.dwg",
            views=("2d",),
            translation_timeout_seconds=30,
            poll_interval_seconds=1,
            max_property_wait_seconds=30,
            failed_manifest_grace_polls=3,
            failed_manifest_grace_sleep_seconds=2,
        )
    finally:
        md.get_manifest = original_get_manifest
        md.translate_to_svf2 = original_translate
        md.wait_for_translation = original_wait
        md.get_model_views = original_views
        md.get_all_properties = original_properties

    assert captured_wait_kwargs["failed_manifest_grace_polls"] == 3
    assert captured_wait_kwargs["failed_manifest_grace_sleep_seconds"] == 2
    assert result["manifest_strategy"] == "resubmitted_after_failed_manifest"
    assert result["property_database_exists"] is True
    assert result["property_database_success"] is True
    assert result["salvage_attempted"] is True
    assert result["salvage_succeeded"] is True
    assert result["views"][0]["object_count"] == 2


def test_extract_dwg_data_failed_error_includes_manifest_and_salvage_flags() -> None:
    original_get_manifest = md.get_manifest
    original_translate = md.translate_to_svf2
    original_wait = md.wait_for_translation

    manifests = iter(
        [
            {"status": "failed", "progress": "complete", "derivatives": []},
            {"status": "failed", "progress": "complete", "derivatives": []},
        ]
    )

    md.get_manifest = lambda token, urn: next(manifests)  # type: ignore[assignment]
    md.translate_to_svf2 = lambda *args, **kwargs: {"result": "submitted"}  # type: ignore[assignment]
    md.wait_for_translation = lambda *args, **kwargs: "failed"  # type: ignore[assignment]

    try:
        try:
            md.extract_dwg_data(
                "token",
                "bucket",
                "failed_file.dwg",
                views=("2d",),
                translation_timeout_seconds=30,
                poll_interval_seconds=1,
                max_property_wait_seconds=30,
            )
        except RuntimeError as exc:
            message = str(exc)
        else:  # pragma: no cover - defensive guard
            raise AssertionError("Expected extract_dwg_data to raise RuntimeError.")
    finally:
        md.get_manifest = original_get_manifest
        md.translate_to_svf2 = original_translate
        md.wait_for_translation = original_wait

    assert "manifest_strategy=resubmitted_after_failed_manifest" in message
    assert "property_database_exists=False" in message
    assert "salvage_attempted=False" in message


def test_extract_dwg_data_timeout_message_is_clear() -> None:
    original_get_manifest = md.get_manifest
    original_translate = md.translate_to_svf2
    original_wait = md.wait_for_translation

    md.get_manifest = lambda token, urn: None  # type: ignore[assignment]
    md.translate_to_svf2 = lambda *args, **kwargs: {"result": "submitted"}  # type: ignore[assignment]
    md.wait_for_translation = lambda *args, **kwargs: "timeout"  # type: ignore[assignment]

    try:
        try:
            md.extract_dwg_data(
                "token",
                "bucket",
                "large_file.dwg",
                views=("2d",),
                translation_timeout_seconds=30,
                poll_interval_seconds=1,
                max_property_wait_seconds=30,
            )
        except TimeoutError as exc:
            message = str(exc)
        else:  # pragma: no cover - defensive guard
            raise AssertionError("Expected extract_dwg_data to raise TimeoutError.")
    finally:
        md.get_manifest = original_get_manifest
        md.translate_to_svf2 = original_translate
        md.wait_for_translation = original_wait

    assert "Autodesk may still be processing the file remotely" in message
    assert "for URN=" in message
