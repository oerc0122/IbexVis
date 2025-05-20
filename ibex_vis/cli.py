"""Ibex vis CLI interface."""

import argparse
from pathlib import Path

from . import __version__
from .vis import main


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
    parser.add_argument(
        "-L",
        "--log",
        help="Verbose output",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        default="WARNING",
    )

    args = parser.parse_args()

    if args.dump:
        with args.config.open("w", encoding="utf-8") as out_file:
            json.dump(
                {
                    "time": {
                        "rate": 1.0,
                        "always_advance": True,
                        "units": "min",
                    },
                    "beam": {
                        "rate": 1.0,
                        "always_advance": True,
                        "units": "µA/min",
                    },
                    "events": {
                        "rate": 1.0,
                        "always_advance": True,
                        "units": "Mevents/min",
                    },
                },
                out_file,
            )
        return

    main(
        input_scripts=args.FILES,
        parameters=args.config,
        plot=args.plot,
        out_plot=args.output,
        loglevel=args.log,
    )


if __name__ == "__main__":
    cli()
