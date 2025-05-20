"""Main run script."""

import argparse
import itertools
import json
from collections.abc import Sequence
from pathlib import Path
from runpy import run_path
from tempfile import NamedTemporaryFile

import matplotlib.pyplot as plt

from ibex_vis import __version__
from ibex_vis import dummy_genie as dg
from ibex_vis.classes import Property

InputParamData = dict[str, float | Property] | Path


def runner(script_file: Path, parameters: dict[str, Property]) -> dg.CurrentState:
    """Run a given script.

    Parameters:
        script_file (Path): Script to run.
        parameters (dict[str, Property]): Properties to use.

    Returns:
        State (dg.CurrentState): State after run.

    Raises:
        ValueError: No runscript function.
    """
    dg.CURRENT_STATE = dg.CurrentState(properties=parameters, counts=[], run_variables={})

    with NamedTemporaryFile("w+", encoding="utf-8") as out_file:
        with script_file.open(encoding="utf-8") as in_file:
            for line in in_file:
                new_line = line.replace("genie_python", "ibex_vis.dummy_genie")
                new_line = new_line.replace("inst", "ibex_vis.dummy_inst")
                out_file.write(new_line)

        out_file.seek(0)
        script = run_path(out_file.name, run_name="tmp")
        if "runscript" not in script:
            raise ValueError("Unable to find main runscript function.")

        script["runscript"]()

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


def main(
    input_scripts: Path | Sequence[Path],
    parameters: InputParamData | Sequence[InputParamData],
    plot: Sequence[str] = (),
    out_plot: Path | None = None,
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

        run = runner(script, params)

        to_plot = plot or (run.properties.keys() - {"time"})

        time = run.properties["time"].data

        fig, ax = plt.subplots()
        for name in to_plot:
            ax.plot(time, run.properties[name].data, label=name)

        for start, end in run.counts:
            if start is None or end is None:
                continue
            ax.axvspan(start, end, alpha=0.25, color="green")

        fig.legend()
        if out_plot is None:
            fig.show()
        else:
            fig.savefig(out_plot)


def cli() -> None:
    parser = argparse.ArgumentParser(
        prog="Ibex Vis",
        description="Visualise the results of an IBEX control script.",
    )
    parser.add_argument("FILES", nargs=argparse.REMAINDER, type=Path, help="Files to process")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s v{__version__}")
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="File containing beam configuration.",
        required=True,
    )
    parser.add_argument(
        "-p",
        "--plot",
        action="append",
        help="Properties to plot",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="File to write output, default: screen",
        default=None,
    )
    parser.add_argument(
        "-d",
        "--dump",
        action="store_true",
        help="Dump default config file and exit.",
    )

    args = parser.parse_args()

    if args.dump:
        with args.config.open("w", encoding="utf-8") as out_file:
            json.dump(
                {
                    "time": {
                        "rate": 1.0,
                        "always_advance": True,
                    },
                    "beam": {
                        "rate": 127.0,
                        "always_advance": True,
                    },
                    "events": {
                        "rate": 1.0,
                        "always_advance": True,
                    },
                },
                out_file,
            )
        return

    main(input_scripts=args.FILES, parameters=args.config, plot=args.plot, out_plot=args.output)


if __name__ == "__main__":
    cli()
