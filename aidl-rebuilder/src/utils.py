import os
import re


class PathNotUnderAnyRootError(Exception):
    pass


def path_relative_to_root(path: str, roots: list[str]) -> str:
    """Return path as <basename(root)>/<relpath> for the first root it lives under.

    Raises PathNotUnderAnyRootError if path is not under any of the roots.
    """
    for root in roots:
        rel = os.path.relpath(path, root)
        if not rel.startswith(".."):
            return os.path.join(os.path.basename(root), rel)
    raise PathNotUnderAnyRootError(f"path not under any root: {path}; roots: {roots}")


def read_file_lines(path: str) -> list[str]:
    """Read a file into a list of lines.

    Raises OSError if the file cannot be opened.
    """
    with open(path) as f:
        return [line.rstrip("\n") for line in f]


def find_line(lines: list[str], pattern: re.Pattern) -> int | None:
    """Find the index of the first line matching the pattern.

    Returns the line index, or None if not found.
    """
    for i, line in enumerate(lines):
        if pattern.match(line.strip()):
            return i
    return None
