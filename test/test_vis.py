import json
from pathlib import Path

import pytest

from ibex_vis.classes import Property
from ibex_vis.vis import properties_from_input, runner

DATA_DIR = Path(__file__).parent / "data"

TEST_SCRIPT = (DATA_DIR / "test-script.genie").read_text(encoding="utf-8")

@pytest.fixture
def properties():
    return {
        "time": Property("time", rate=1.0, always_advance=True, units="min"),
        "beam": Property("beam", rate=127.0, always_advance=True, units="μA"),
        "events": Property("events", rate=1.0, always_advance=True, units="Mevents"),
        "T_head": Property("T_head", initial=300.0, rate=10.0, units="K"),
    }


def test_properties_from_input(properties):
    param_file = DATA_DIR / "test-config.json"

    with param_file.open(encoding="utf-8") as file:
        raw_parameters = json.load(file)

    parameters = properties_from_input(raw_parameters)

    assert parameters == properties


def test_runner(tmp_path, properties):
    script_file = tmp_path / "test_script.py"
    script_file.write_text(TEST_SCRIPT, encoding="utf-8")

    run = runner(script_file, properties)
    print(run)

    assert run.properties["time"].current == 738.0
    assert run.counts == [(0.0, 369.0), (369.0, 738.0)]
    assert run.records == [(15.0, 369.0), (384.0, 738.0)]


def test_runner_bailout(tmp_path, properties):
    script_file = tmp_path / "test_script.py"

    # Never ends
    mod_script = TEST_SCRIPT.replace("lowlimit = tt-5", "lowlimit = tt+5")

    script_file.write_text(mod_script, encoding="utf-8")

    with pytest.raises(ValueError, match="Exceeded"):
        runner(script_file, properties)
