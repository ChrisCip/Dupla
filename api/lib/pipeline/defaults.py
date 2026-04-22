"""GEBSA IV reference project — discipline order and display names."""

DISCIPLINE_ORDER: list[str] = ["arquitectura", "estructura", "sanitario", "electrico"]
ALLOWED_DISCIPLINES: frozenset[str] = frozenset(DISCIPLINE_ORDER)

DEFAULT_PROJECT_NAME = "Residencial GEBSA IV"
DEFAULT_PROJECT_ID = "gebsa_iv"
