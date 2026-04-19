import re
import shutil
from pathlib import Path
from typing import Final

_EXTENSION_RE: Final[re.Pattern[str]] = re.compile(r"\.[a-zA-Z0-9]+")


def _validate_extension(name: str, value: str) -> None:
    if not _EXTENSION_RE.fullmatch(value):
        raise ValueError(f"{name} must be a dot followed by alphanumerics, got {value!r}")


def delete_dir(path: Path) -> None:
    """Remove `path` if it exists."""
    if path.exists():
        shutil.rmtree(path)


def delete_and_recreate_dir(path: Path) -> None:
    """Remove `path` if it exists, then recreate it as an empty directory."""
    if path.exists():
        shutil.rmtree(path)
    path.mkdir()


def resolve_empty_dir(path: Path) -> Path:
    """Resolve `path` and ensure it is usable as a fresh output directory.

    If `path` does not exist, it is created (its parent must already exist).
    If `path` exists, it must be an empty directory.

    Returns the resolved path.
    """
    path = path.resolve(strict=False)
    if path.exists():
        if not path.is_dir():
            raise NotADirectoryError(f"{path} exists and is not a directory")
        if any(path.iterdir()):
            raise FileExistsError(f"{path} is not empty")
    path.mkdir(exist_ok=True)
    return path


def check_binary_exists(binary: str) -> None:
    """Raise if `binary` is not resolvable on PATH."""
    if shutil.which(binary) is None:
        raise FileNotFoundError(f"{binary} not found on PATH")


def check_file_exists(path: Path) -> None:
    """Raise if `path` is not an existing regular file."""
    if not path.exists():
        raise FileNotFoundError(f"file not found: {path}")
    if path.is_dir():
        raise IsADirectoryError(f"expected file, found directory: {path}")
    if not path.is_file():
        raise OSError(f"path exists but is not a regular file: {path}")


def check_dir_exists(path: Path) -> None:
    """Raise if `path` is not an existing directory."""
    if not path.exists():
        raise FileNotFoundError(f"directory not found: {path}")
    if path.is_file():
        raise NotADirectoryError(f"expected directory, found file: {path}")
    if not path.is_dir():
        raise OSError(f"path exists but is not a directory: {path}")


def find_paired_files(parent_dir: Path, source_ext: str, companion_ext: str) -> list[Path]:
    """Find files with `source_ext` that have a companion with `companion_ext`.

    Args:
        parent_dir: Directory to search.
        source_ext: Extension of files to return (e.g. ".odex").
        companion_ext: Extension the companion must have (e.g. ".jar").

    Returns:
        Sorted list of paths with `source_ext` whose same-stem
        companion with `companion_ext` exists.
    """
    _validate_extension("source_ext", source_ext)
    _validate_extension("companion_ext", companion_ext)
    check_dir_exists(parent_dir)

    matches = [
        source_path
        for source_path in parent_dir.glob(f"*{source_ext}")
        if source_path.with_suffix(companion_ext).is_file()
    ]
    return sorted(matches)


def resolve_files_in_dirs(*, names: list[str], search_dirs: list[Path]) -> list[Path]:
    """Resolve each filename against the search directories, in order.

    Duplicate names and duplicate search directories are silently ignored.

    Args:
        names: Ordered list of filenames to resolve. Duplicates are skipped.
        search_dirs: Directories to search. The first match wins.
    """
    unique_dirs = list(dict.fromkeys(search_dirs))
    resolved: list[Path] = []
    seen_names: set[str] = set()
    for name in names:
        if name in seen_names:
            continue
        seen_names.add(name)
        for d in unique_dirs:
            candidate = d / name
            if candidate.is_file():
                resolved.append(candidate)
                break
        else:
            searched = ", ".join(str(d) for d in unique_dirs)
            raise FileNotFoundError(f"{name!r} not found in: {searched}")
    return resolved


def list_files_with_extension(parent_dir: Path, ext: str) -> list[Path]:
    """Return sorted paths to all files directly in `parent_dir` whose name ends with `ext`.

    Args:
        ext: File extension with a leading period, e.g. ".apk".
            Matches the convention used by `pathlib.Path.suffix`.
    """
    _validate_extension("ext", ext)
    check_dir_exists(parent_dir)
    return sorted(parent_dir.glob(f"*{ext}"))
