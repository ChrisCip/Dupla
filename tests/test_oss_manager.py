from aps_integration.oss_manager import build_object_name


def test_build_object_name_supports_override_and_unique_suffix() -> None:
    object_name = build_object_name(
        r"C:\tmp\sample.dwg",
        object_name="custom_name.dwg",
        unique_suffix="20260323_101530",
    )

    assert object_name == "custom_name_20260323_101530.dwg"
