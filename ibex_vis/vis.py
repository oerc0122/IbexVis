"""Main run script."""

import ast
import importlib
import itertools
import json
import logging
import types
from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt

from ibex_vis import dummy_genie as dg
from ibex_vis.classes import CurrentState, Property

InputParamData = dict[str, float | Property] | Path


def reset_state() -> None:
    """Reset the runner state."""
    dg.CURRENT_STATE = CurrentState.empty()


def runner(script_file: Path, parameters: dict[str, Property]) -> CurrentState:
    """Run a given script.

    Parameters:
        script_file (Path): Script to run.
        parameters (dict[str, Property]): Properties to use.

    Returns:
        State (CurrentState): State after run.

    Raises:
        ValueError: No runscript function.
    """
    reset_state()
    dg.CURRENT_STATE.properties = parameters

    loader = importlib.machinery.SourceFileLoader("<user_script>", script_file)
    src = loader.get_data(script_file).decode()
    if "runscript" not in src:
        raise ValueError("Unable to find main runscript function.")
    src = src.replace("genie_python", "ibex_vis.dummy_genie")
    src = src.replace("inst", "ibex_vis.dummy_inst")
    code = loader.source_to_code(src, script_file)
    tmp_mod = types.ModuleType("UserScriptModule")
    tmp_mod.__file__ = str(script_file)
    env = {**globals()}
    env.update(tmp_mod.__dict__)
    exec(code, env)

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


def scan(script_file: Path) -> set[str]:
    """Scan script for ``cset`` (block) vars.

    Parameters:
        script_file (Path): File to scan.

    Returns:
        blocks (set[str]): Present block variables.

    Notes:
        Assumes block names are given as literals.
    """
    tree = ast.parse(script_file.read_text(encoding="utf-8"))
    CSET_KW = {"runcontrol", "lowlimit", "highlimit", "wait", "verbose"}

    blocks = set()

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "cset"
        ):
            blocks |= {arg.value for arg in node.args[::2] if isinstance(arg, ast.Constant)} | {
                kw.arg for kw in node.keywords
            } - CSET_KW

    return blocks


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
    logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)

    if isinstance(input_scripts, Path):
        input_scripts = (input_scripts,)

    if isinstance(parameters, (Path, dict)):
        parameters = itertools.repeat(parameters)

    parameters = map(properties_from_input, parameters)

    for script, params in zip(input_scripts, parameters, strict=False):
        if not script.is_file():
            raise FileNotFoundError(f"{script} is not a file.")

        run = runner(script, params)

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
            ax.axvspan(start, end, alpha=0.2, color="green")

        for start, end in run.records:
            if start is None or end is None:
                continue
            ax.axvspan(start, end, alpha=0.2, color="red")

        fig.legend()
        if out_plot is None:
            plt.show(block=True)
        else:
            fig.savefig(out_plot)
