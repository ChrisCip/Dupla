from app.domain.business_pliego import (
    BUSINESS_PLIEGO_KEY,
    BUSINESS_PLIEGO_SECTION_KEYS,
    MIN_SECTION_LEN,
    default_empty_sections,
    pliego_sections_incomplete_message,
    transition_blockers_for_business_pliego,
)


def _full_sections(text: str = "x" * MIN_SECTION_LEN) -> dict[str, str]:
    s = default_empty_sections()
    for k in BUSINESS_PLIEGO_SECTION_KEYS:
        s[k] = text
    return s


def test_transition_legacy_summary_only():
    spec = {"summary": "y" * MIN_SECTION_LEN}
    assert transition_blockers_for_business_pliego(spec) is None


def test_transition_legacy_summary_short():
    spec = {"summary": "short"}
    assert transition_blockers_for_business_pliego(spec) is not None


def test_transition_structured_incomplete_section():
    sec = _full_sections()
    sec["scope"] = "ab"
    spec = {
        BUSINESS_PLIEGO_KEY: {
            "schema_version": 1,
            "sections": sec,
            "approved": True,
        }
    }
    assert transition_blockers_for_business_pliego(spec) is not None


def test_transition_structured_not_approved():
    spec = {
        BUSINESS_PLIEGO_KEY: {
            "schema_version": 1,
            "sections": _full_sections(),
            "approved": False,
        }
    }
    msg = transition_blockers_for_business_pliego(spec)
    assert msg is not None
    assert "aprobado" in msg.lower()


def test_transition_structured_ok():
    spec = {
        BUSINESS_PLIEGO_KEY: {
            "schema_version": 1,
            "sections": _full_sections(),
            "approved": True,
        }
    }
    assert transition_blockers_for_business_pliego(spec) is None


def test_pliego_sections_incomplete_message():
    bad = default_empty_sections()
    for k in BUSINESS_PLIEGO_SECTION_KEYS:
        bad[k] = "ab"
    spec = {BUSINESS_PLIEGO_KEY: {"schema_version": 1, "sections": bad}}
    assert pliego_sections_incomplete_message(spec) is not None
