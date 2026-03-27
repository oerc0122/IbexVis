from pathlib import Path

import pytest

from ibex_vis.vis import scan

DATA_DIR = Path(__file__).parent / "data"

TRIAL_SCRIPT = DATA_DIR / "trial_script.py"
TRIAL_IMPORT = DATA_DIR / "trial_import.py"
TRIAL_CLASS = DATA_DIR / "trial_class.py"
TRIAL_CLASS_2 = DATA_DIR / "trial_class_2.py"

@pytest.mark.parametrize(
    ("inp", "expected"),
    [
        (TRIAL_SCRIPT, {"T_head"}),
        (TRIAL_IMPORT, {"T_head", "dilfridge", "golf"}),
        (TRIAL_CLASS, {"dilfridge"}),
        (TRIAL_CLASS_2, {"golf"})
    ]
)
def test_scanner(inp, expected):
    assert scan(inp) == expected
