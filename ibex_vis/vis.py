"""Main run script."""

from __future__ import annotations

import ast
import importlib
import importlib.util
import itertools
import json
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias
from unittest.mock import patch

import matplotlib.pyplot as plt

from ibex_vis import dummy_genie as dg
from ibex_vis.classes import CurrentState, Property

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    InputParamData: TypeAlias = dict[str, dict[str, float] | Property] | Path


def reset_state() -> None:
    """Reset the runner state."""
    dg.CURRENT_STATE = CurrentState.empty()


def runner(
    script_file: Path,
    parameters: dict[str, Property],
    *,
    dummies: dict[str, str],
) -> CurrentState:
    """Run a given script.

    Parameters:
        script_file (Path): Script to run.
        parameters (dict[str, Property]): Properties to use.
        dummies (dict[str, str]): Modules to replace.

    Returns:
        State (CurrentState): State after run.

    Raises:
        ValueError: No runscript function.
        ImportError: Import failure.
    """
    reset_state()
    dg.CURRENT_STATE.properties = parameters

    # Ensure dummy modules are available
    try:
        replace = {key: importlib.import_module(dummy) for key, dummy in dummies.items()}
    except ImportError as err:
        raise ImportError("Unable to import dummy modules") from err

    spec = importlib.util.spec_from_file_location("__user_script__", script_file)
    if spec is None:
        raise ImportError(f"{script_file} is not valid for import.")

    module = importlib.util.module_from_spec(spec)

    with patch.dict(sys.modules, **replace, __user_script__=module):
        spec.loader.exec_module(module)

        if not hasattr(module, "runscript"):
            raise ValueError(f"{script_file} does not contain `runscript`")

        module.runscript()

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
    input_scripts: Path | Iterable[Path],
    parameters: InputParamData | Iterable[InputParamData],
    *,
    plot: Sequence[str] = (),
    out_plot: Path | None = None,
    loglevel: int = logging.WARNING,
    dummies: dict[str, str] | None = None,
) -> None:
    """Process input scripts into a property stream.

    Parameters:
        input_scripts (Path or Iterable[Path]): Scripts to process.
        parameters (InputParamData or Iterable[InputParamData]): Initial configuration parameters.
        plot (Sequence[str]): Variables to plot.
        out_plot (Path, optional): File to write plot to.
        dummies (dict[str, str], optional): Modules to replace.

    Raises:
        FileNotFoundError: If script doesn't exist.
    """
    logging.basicConfig(format="%(levelname)s: %(message)s", level=loglevel)

    if dummies is None:
        dummies = {"genie_python": "ibex_vis.dummy_genie"}

    if isinstance(input_scripts, Path):
        input_scripts = (input_scripts,)

    if isinstance(parameters, (Path, dict)):
        parameters = itertools.repeat(parameters)

    parameters = map(properties_from_input, parameters)

    for script, params in zip(input_scripts, parameters, strict=False):
        if not script.is_file():
            raise FileNotFoundError(f"{script} is not a file.")

        run = runner(script, params, dummies=dummies)

        to_plot = plot or (run.properties.keys() - {"time"})

        time = run.properties["time"].data

        fig, ax = plt.subplots()
        for name in to_plot:
            ax.plot(time, run.properties[name].data, label=name)

        ax.set_xlabel(f"Time ({run.properties['time'].units})")
        if len(to_plot) == 1:
            prop = run.properties[next(iter(to_plot))]
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
