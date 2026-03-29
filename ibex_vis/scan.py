"""Scan scripts for set variables."""

from __future__ import annotations

import ast
import importlib.util
import logging
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Iterator

LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)


class Scanner(ast.NodeVisitor):
    CSET_KW: Final[set[str]] = {"runcontrol", "lowlimit", "highlimit", "wait", "verbose"}
    EXCLUDE: str[str] = set(sys.modules) | {
        "__main__",
        "genie_python",
        "numpy",
        "scipy",
        "matplotlib",
        "pytest",
        "ase",
    }

    @contextmanager
    def _scanning(self, script_file: Path) -> Iterator[None]:
        self.currently_scanning = script_file
        yield
        del self.currently_scanning

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.blocks: set[str] = set()
        self.seen: set[str] = set()
        self.to_scan: set[Path] = set()
        self.scanned: set[Path] = set()

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
            for name, path in get_modules(alias.name, self.EXCLUDE):
                if name in self.seen:
                    continue
                self.to_scan.add(path)
                self.seen.add(name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        super().generic_visit(node)

        if not node.module:
            return

        for name, path in get_modules(node.module, self.EXCLUDE):
            if name in self.seen:
                continue
            self.to_scan.add(path)
            self.seen.add(name)

    def scan_single_file(self, script_file: Path) -> set[str]:
        with self._scanning(script_file):
            tree = ast.parse(script_file.read_text(encoding="utf-8"))
            LOG.info("Scanning %s...", script_file)

            self.visit(tree)
            self.scanned.add(script_file)
        return self.blocks

    def scan(self, script_file: Path) -> set[str]:
        self.to_scan.add(script_file)

        while self.to_scan:
            next_file = self.to_scan.pop()
            self.scan_single_file(next_file)
        return self.blocks


def get_modules(module: str, exclude: set[str]) -> Iterator[tuple[str, Path]]:
    """Find modules from an Import node.

    Parameters:
        module (str): Module identifier

    Raises:
        ValueError: Unable to determine module class.

    Yields:
        Paths to scan
    """
    path = module.split(".")

    # Find root
    spec = importlib.util.find_spec(path[0])

    if path[0] in exclude:
        return

    if spec is None or not spec.origin:
        LOG.warning("Missing import %s, perhaps not installed in PYTHONPATH", path)
        return

    if spec.origin == "frozen":
        return

    root = Path(spec.origin).parent.parent

    if root.joinpath(*path).is_dir():  # Endpoint is system module
        ntrial = len(path) + 1
    elif (
        trial := root.joinpath(*path).with_suffix(".py")
    ).is_file():  # Endpoint is system module file
        ntrial = len(path)
        yield ".".join(path), trial
    elif not (Path(spec.origin).parent / "__init__.py").is_file():  # Local/PYTHONPATH import
        yield ".".join(path), Path(spec.origin)
        return
    elif (
        trial := root.joinpath(*path[:-1]).with_suffix(".py")
    ).is_file():  # Endpoint is component of file
        ntrial = len(path)
        yield ".".join(path), trial
    else:
        raise ValueError("Unable to determine endpoint")

    for part_path in (path[:i] for i in range(1, ntrial)):
        yield ".".join(part_path), root.joinpath(*part_path) / "__init__.py"
