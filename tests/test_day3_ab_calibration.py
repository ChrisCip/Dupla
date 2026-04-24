import importlib.util
from pathlib import Path


def _load_day3_module():
    module_path = Path(__file__).resolve().parent.parent / "scripts" / "run_day3_ab_calibration.py"
    spec = importlib.util.spec_from_file_location("run_day3_ab_calibration", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_parse_thresholds_sorts_and_deduplicates() -> None:
    mod = _load_day3_module()
    values = mod._parse_thresholds("0.90,0.60,0.90,0.75")
    assert values == [0.6, 0.75, 0.9]


def test_extract_output_dir_from_runner_stdout() -> None:
    mod = _load_day3_module()
    stdout = "line a\nOutput: C:/tmp/dupla/run_001\nline b"
    assert mod._extract_output_dir(stdout) == "C:/tmp/dupla/run_001"
