"""Main run script."""

import importlib
import itertools
import json
import logging
import types
from collections.abc import Sequence
from pathlib import Path
from unittest.mock import patch

import matplotlib.pyplot as plt

from ibex_vis import dummy_genie as dg
from ibex_vis.classes import CurrentState, Property
from ibex_vis.log import get_logger

InputParamData = dict[str, float | Property] | Path

DEFAULT_PROPERTIES = {
    "time": Property(
        "time",
        rate=1.0,
        always_advance=True,
        units="min",
    ),
    "beam": Property(
        "beam",
        rate=1.0,
        always_advance=True,
        units="µA/min",
    ),
    "events": Property(
        "events",
        rate=1.0,
        always_advance=True,
        units="Mevents/min",
    ),
}


def get_runner(script_file: Path) -> tuple[types.CodeType, dict]:
    """Get a dummy runner for the given script.

    Parameters:
        script_file (Path): Script to run.

    Returns:
        code (code): Code with dummied functions.
        env (dict): Run environment.
    """
    loader = importlib.machinery.SourceFileLoader("<user_script>", script_file)
    src = loader.get_data(script_file).decode()
    src = src.replace("genie_python", "ibex_vis.dummy_genie")
    src = src.replace("inst", "ibex_vis.dummy_inst")
    code = loader.source_to_code(src, script_file)
    tmp_mod = types.ModuleType("UserScriptModule")
    tmp_mod.__file__ = str(script_file)
    env = {**globals()}
    env.update(tmp_mod.__dict__)
    return code, env


def runner(
    script_file: Path,
    parameters: dict[str, Property],
    *,
    loglevel: int = logging.WARNING,
) -> CurrentState:
    """Run a given script.

    Parameters:
        script_file (Path): Script to run.
        parameters (dict[str, Property]): Properties to use.

    Returns:
        State (CurrentState): State after run.

    Raises:
        ValueError: No runscript function.
    """
    dg.CURRENT_STATE = CurrentState(properties=parameters, counts=[], run_variables={})
    dg.LOGGER = get_logger(script_file, loglevel)

    code, env = get_runner(script_file)
    exec(code, env)

    if "runscript" not in env:
        raise ValueError("Unable to find main runscript function.")
    env["runscript"]()

    return dg.CURRENT_STATE


def properties_from_input(parameters: InputParamData) -> dict[str, Property]:
    """Get properties dict from any data structures.

    Parameters:
        parameters (InputParamData): Data to process.

    Returns:
        out_dict (dict[str, Property]): Processed files.

    Raises:
        ValueError: Invalid parameters block.
        FileNotFoundError: Invalid file provided.
    """
    input_val = "dict"
    if isinstance(parameters, Path):
        input_val = f"file ({parameters})"
        if not parameters.is_file():
            raise FileNotFoundError(f"{parameters} is not a file.")

        with parameters.open(encoding="utf-8") as config_file:
            parameters = json.load(config_file)

    out_dict = {}
    try:
        for key, val in parameters.items():
            if isinstance(val, Property):
                out_dict[key] = val
            else:
                out_dict[key] = Property(name=key, **val)
    except Exception as err:
        raise ValueError(
            f"Issue while processing a key ({key}) from provided {input_val}.",
        ) from err

    return out_dict


def scan(
    input_scripts: Path | Sequence[Path],
    *,
    loglevel: int = logging.DEBUG,
) -> dict[str, Property]:
    """Scans a source file for properties.

    Parameters:
        input_scripts (Path | Sequence[Path]): Scripts to process.
        loglevel (int): Logging level.

    Returns:
        properties (dict[str, Property]): Accumulated properties.
    """
    if isinstance(input_scripts, Path):
        input_scripts = (input_scripts,)

    properties = DEFAULT_PROPERTIES
    for script in input_scripts:
        if not script.is_file():
            raise FileNotFoundError(f"{script} is not a file.")

        with patch('ibex_vis.dummy_genie.genie', new=dg.EvenFakerGenie):
            run = runner(script, properties, loglevel=loglevel)
            properties |= run.properties

    return properties


def main(
    input_scripts: Path | Sequence[Path],
    parameters: InputParamData | Sequence[InputParamData],
    *,
    plot: Sequence[str] = (),
    out_plot: Path | None = None,
    loglevel: int = logging.WARNING,
) -> None:
    """Process input scripts into a property stream.

    Parameters:
        input_scripts (Path | Sequence[Path]): Scripts to process.
        parameters (InputParamData | Sequence[InputParamData]): Initial configuration parameters.
        plot (Sequence[str]): Variables to plot.
        out_plot (Path, optional): File to write plot to.

    Raises:
        FileNotFoundError: If script doesn't exist.
    """
    if isinstance(input_scripts, Path):
        input_scripts = (input_scripts,)

    if isinstance(parameters, (Path, dict)):
        parameters = itertools.repeat(parameters)

    parameters = map(properties_from_input, parameters)

    for script, params in zip(input_scripts, parameters, strict=False):
        if not script.is_file():
            raise FileNotFoundError(f"{script} is not a file.")

        run = runner(script, params, loglevel=loglevel)

        to_plot = plot or (run.properties.keys() - {"time"})

        time = run.properties["time"].data

        fig, ax = plt.subplots()
        for name in to_plot:
            ax.plot(time, run.properties[name].data, label=name)

        ax.set_xlabel(f"Time ({run.properties['time'].units})")
        if len(to_plot) == 1:
            prop = run.properties[to_plot[0]]
            ax.set_ylabel(prop.name + (f" ({prop.units})" if prop.units else ""))

        for start, end in run.counts:
            if start is None or end is None:
                continue
            ax.axvspan(start, end, alpha=0.25, color="green")

        fig.legend()
        if out_plot is None:
            plt.show(block=True)
        else:
            fig.savefig(out_plot)
