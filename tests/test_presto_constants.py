from budget.presto_constants import PRESTO_FIRST_DATA_ROW, assert_presto_header_row_matches_export


def test_presto_first_data_row() -> None:
    assert PRESTO_FIRST_DATA_ROW == 4


def test_headers_match_export() -> None:
    assert_presto_header_row_matches_export()
