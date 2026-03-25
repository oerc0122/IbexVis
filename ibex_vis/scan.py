"""Scan scripts for set variables."""

from __future__ import annotations

import ast
import importlib.util
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Iterator

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class Scanner(ast.NodeVisitor):
    CSET_KW: Final[set[str]] = {"runcontrol", "lowlimit", "highlimit", "wait", "verbose"}

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.blocks: set[str] = set()
        self.seen: set[str] = set(sys.modules) | {"genie_python"} | {"inst"} | {"numpy"}
        self.to_scan: set[Path] = set()

    def visit_Call(self, node: ast.Call) -> None:
        super().generic_visit(node)

        if isinstance(node.func, ast.Attribute) and node.func.attr == "cset":
            self.blocks |= {
                arg.value
                for arg in node.args[::2]
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
            } | {kw.arg for kw in node.keywords if kw.arg} - self.CSET_KW

    def visit_Import(self, node: ast.Import) -> None:
        super().generic_visit(node)

        for alias in node.names:
            if alias.name not in self.seen:
                for name, path in get_modules(alias.name):
                    print(name, path)
                    self.to_scan.add(path)
                    self.seen.add(name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        super().generic_visit(node)

        if not node.module:
            return

        for name, path in get_modules(node.module):
            self.to_scan.add(path)
            self.seen.add(name)

    def scan_single_file(self, script_file: Path) -> set[str]:
        tree = ast.parse(script_file.read_text(encoding="utf-8"))
        LOG.info("Scanning %s...", script_file.stem)

        self.visit(tree)
        return self.blocks

    def scan(self, script_file: Path) -> set[str]:
        self.to_scan.add(script_file)

        while self.to_scan:
            next_file = self.to_scan.pop()
            self.scan_single_file(next_file)

        return self.blocks


def get_modules(module: str) -> Iterator[tuple[str, Path]]:
    """Find modules from an Import node.

    Parameters:
        module (str): Module identifier

    Yields:
        Paths to scan
    """
    path = module.split(".")

    # Find root
    spec = importlib.util.find_spec(path[0])
    print(spec, path)
    if spec is None or not spec.origin:
        return

    root = Path(spec.origin)
    yield path[0], root

    for i, _ in enumerate(path[1:], 1):
        yield ".".join(path[: i + 1]), root.joinpath(*path[1:i])


def scan(script_file: Path, seen: set[str] | None = None) -> set[str]:
    """Scan script for ``cset`` (block) vars.

    Parameters:
        script_file (Path): File to scan.
        seen (set[str], optional): Cache of already seen files.

    Returns:
        blocks (set[str]): Present block variables.

    Notes:
        Assumes block names are given as literals.
    """
    scanner = Scanner()

    scanner.scan(script_file)

    return scanner.blocks
