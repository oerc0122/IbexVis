"""Ibex vis CLI interface."""

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .vis import main, scan

DEFAULT_PROPERTIES = {
    "time": {
        "rate": 1.0,
        "always_advance": True,
        "units": "min",
    },
    "beam": {
        "rate": 1.0,
        "always_advance": True,
        "units": "μA",
    },
    "events": {
        "rate": 1.0,
        "always_advance": True,
        "units": "Mevents",
    },
}


def dump(args: argparse.Namespace) -> None:
    """Dump config file.

    Parameters:
        args (argparse.Namespace): Args to use.
    """
    blocks = {block: {"rate": 1.0, "units": ""} for file in args.FILES for block in scan(file)}

    with args.config.open("w", encoding="utf-8") as out_file:
        json.dump(DEFAULT_PROPERTIES | blocks, out_file, indent=2)


def cli() -> None:
    parser = argparse.ArgumentParser(
        prog="Ibex Vis",
        description="Visualise the results of an IBEX control script.",
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s v{__version__}")
    parser.add_argument(
        "-L",
        "--log",
        help="output verbosity",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        default="WARNING",
    )
    parser.add_argument("FILES", nargs=argparse.REMAINDER, type=Path, help="Files to process")
    parser.add_argument(
        "-d",
        "--dump",
        action="store_true",
        help="dump default config file and exit.",
    )
    parser.add_argument(
        "-c",
        "--config",
        type=Path,
        help="file containing beam configuration.",
        required=True,
    )
    parser.add_argument(
        "-p",
        "--plot",
        action="append",
        help="properties to plot",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="file to write output, default: screen",
        default=None,
    )

    override_grp = parser.add_argument_group("override")
    override_grp.add_argument(
        "-G",
        "--genie",
        help="genie import to dummy in module import format, e.g. `my_module.my_package`",
        default="genie_python",
    )
    override_grp.add_argument(
        "-I",
        "--inst",
        help=(
            "instrument to dummy as `from:to`, e.g. `inst:my_module.my_package` "
            "or None if no dummying needed. "
            "Default: %(default)s"
        ),
        default=None,
    )
    override_grp.add_argument(
        "-P",
        "--paths",
        help="paths to add to sys path when importing modules",
        action="append",
        type=Path,
    )
    override_grp.add_argument(
        "--dummies-override",
        help=(
            "ADVANCED interface to override dummies as `from:to from:to`, "
            "e.g. `genie_python:ibex_vis.dummy_genie inst:ibex_vis.dummy_inst`"
        ),
        nargs="+",
        default=None,
    )

    args = parser.parse_args()

    if args.dump:
        dump(args)
        return

    # Add in paths
    for path in args.paths:
        sys.path.insert(0, path)

    dummies = {args.genie: "ibex_vis.dummy_genie"}
    if args.inst is not None:
        key, val = args.inst.split(":")
        dummies[key] = val

    if args.dummies_override is not None:
        dummies = dict(arg.split(":", maxsplit=1) for arg in args.dummies_override)

    main(
        input_scripts=args.FILES,
        parameters=args.config,
        plot=args.plot,
        out_plot=args.output,
        loglevel=args.log,
        dummies=dummies,
    )


if __name__ == "__main__":
    cli()
