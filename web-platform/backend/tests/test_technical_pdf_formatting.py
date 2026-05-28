"""Tests for technical PDF table formatting helpers."""

from __future__ import annotations

from app.services.clash_reports.formatting import format_center_index, format_zoom_index


def test_format_center_index_two_lines() -> None:
    text = format_center_index("X: 153.000 mm · Y: -158.500 mm")
    assert "X:153.000" in text
    assert "<br/>" in text
    assert "Y:-158.500" in text


def test_format_zoom_index_truncates_long_command() -> None:
    long_cmd = "Z W " + "1234567890," * 8
    short = format_zoom_index(long_cmd, max_chars=40)
    assert len(short) <= 40
    assert short.endswith("…")


def test_format_zoom_index_missing() -> None:
    assert format_zoom_index(None) == "no"
