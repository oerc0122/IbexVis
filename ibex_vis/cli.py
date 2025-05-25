"""Ibex vis CLI interface."""
import argparse
import json
import logging
from pathlib import Path

from . import __version__
from .vis import main, scan


class LogAction(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
        super().__init__(option_strings, dest, **kwargs)
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, getattr(logging, values))


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
        help="Dump to config file and exit. NB: Will overwrite --config argument!",
    )
    parser.add_argument(
        "-L",
        "--log",
        action=LogAction,
        help="Verbose output",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        default=logging.WARNING,
    )

    args = parser.parse_args()

    if args.dump:
        props = scan(input_scripts=args.FILES, loglevel=args.log)
        out_props = {key: prop.to_dict() for key, prop in props.items()}

        with args.config.open("w", encoding="utf-8") as out_file:

            json.dump(
                out_props,
                out_file,
                indent=2,
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
