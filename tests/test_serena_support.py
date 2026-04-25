from core.coordination.nasas_paths import discipline_from_nasas_relative_path
from core.coordination.models_25d import Discipline


def test_automation_paths_map_to_electrical():
    rel = "planos recibidos/tecnicos/automatizacion/05. mayo 2024/15.04.2024/s18- data y cctv zona 1 n1-15-04-24.pdf"
    assert discipline_from_nasas_relative_path(rel) == Discipline.MEP_ELEC
