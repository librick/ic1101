from pathlib import Path

import pytest

from file_utils import (
    check_file_exists,
    find_file_by_name,
    find_paired_files,
    list_files_with_extension,
    resolve_empty_dir,
)


def _touch(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    return path


class TestFindFileByName:
    def test_finds_file_at_top_level(self, tmp_path: Path) -> None:
        target = _touch(tmp_path / "target.txt")

        assert find_file_by_name(tmp_path, "target.txt") == target

    def test_finds_file_in_nested_subdirectory(self, tmp_path: Path) -> None:
        target = _touch(tmp_path / "a" / "b" / "target.txt")

        assert find_file_by_name(tmp_path, "target.txt") == target

    def test_raises_filenotfounderror_when_no_match(self, tmp_path: Path) -> None:
        _touch(tmp_path / "other.txt")

        with pytest.raises(FileNotFoundError, match="not found under"):
            find_file_by_name(tmp_path, "target.txt")

    def test_raises_runtimeerror_when_multiple_matches(self, tmp_path: Path) -> None:
        _touch(tmp_path / "a" / "target.txt")
        _touch(tmp_path / "b" / "target.txt")

        with pytest.raises(RuntimeError, match="multiple files"):
            find_file_by_name(tmp_path, "target.txt")

    def test_directory_with_matching_name_ignored(self, tmp_path: Path) -> None:
        (tmp_path / "target.txt").mkdir()
        target = _touch(tmp_path / "sub" / "target.txt")

        assert find_file_by_name(tmp_path, "target.txt") == target

    def test_raises_filenotfounderror_for_nonexistent_parent_dir(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="directory not found"):
            find_file_by_name(tmp_path / "missing", "target.txt")

    def test_raises_notadirectoryerror_when_parent_is_file(self, tmp_path: Path) -> None:
        file_path = _touch(tmp_path / "a.txt")

        with pytest.raises(NotADirectoryError, match="expected directory, found file"):
            find_file_by_name(file_path, "target.txt")


class TestResolveEmptyDir:
    def test_creates_dir_when_absent(self, tmp_path: Path) -> None:
        target = tmp_path / "out"

        result = resolve_empty_dir(target)

        assert target.is_dir()
        assert list(target.iterdir()) == []
        assert result == target

    def test_accepts_existing_empty_dir(self, tmp_path: Path) -> None:
        target = tmp_path / "out"
        target.mkdir()

        result = resolve_empty_dir(target)

        assert target.is_dir()
        assert list(target.iterdir()) == []
        assert result == target

    def test_returns_resolved_absolute_path(self, tmp_path: Path) -> None:
        unresolved = tmp_path / "sub" / ".." / "out"

        result = resolve_empty_dir(unresolved)

        assert result == tmp_path / "out"
        assert result.is_absolute()

    def test_raises_notadirectoryerror_for_existing_file(self, tmp_path: Path) -> None:
        target = _touch(tmp_path / "a.txt")

        with pytest.raises(NotADirectoryError, match="is not a directory"):
            resolve_empty_dir(target)

    def test_raises_fileexistserror_for_non_empty_dir(self, tmp_path: Path) -> None:
        target = tmp_path / "out"
        sentinel = _touch(target / "sentinel.txt")

        with pytest.raises(FileExistsError, match="is not empty"):
            resolve_empty_dir(target)

        assert sentinel.is_file()

    def test_hidden_file_counts_as_non_empty(self, tmp_path: Path) -> None:
        target = tmp_path / "out"
        _touch(target / ".hidden")

        with pytest.raises(FileExistsError, match="is not empty"):
            resolve_empty_dir(target)

    def test_empty_subdirectory_counts_as_non_empty(self, tmp_path: Path) -> None:
        target = tmp_path / "out"
        (target / "sub").mkdir(parents=True)

        with pytest.raises(FileExistsError, match="is not empty"):
            resolve_empty_dir(target)

    def test_raises_filenotfounderror_when_parent_missing(self, tmp_path: Path) -> None:
        target = tmp_path / "missing" / "leaf"

        with pytest.raises(FileNotFoundError):
            resolve_empty_dir(target)


class TestCheckFileExists:
    def test_returns_none_for_existing_regular_file(self, tmp_path: Path) -> None:
        target = _touch(tmp_path / "a.txt")

        assert check_file_exists(target) is None

    def test_returns_none_for_symlink_to_regular_file(self, tmp_path: Path) -> None:
        target = _touch(tmp_path / "a.txt")
        link = tmp_path / "link.txt"
        link.symlink_to(target)

        assert check_file_exists(link) is None

    def test_raises_filenotfounderror_for_missing_path(self, tmp_path: Path) -> None:
        target = tmp_path / "missing.txt"

        with pytest.raises(FileNotFoundError, match="file not found:"):
            check_file_exists(target)

    def test_raises_isadirectoryerror_for_directory(self, tmp_path: Path) -> None:
        with pytest.raises(IsADirectoryError, match="expected file, found directory"):
            check_file_exists(tmp_path)

    def test_raises_filenotfounderror_for_broken_symlink(self, tmp_path: Path) -> None:
        link = tmp_path / "link.txt"
        link.symlink_to(tmp_path / "missing.txt")

        with pytest.raises(FileNotFoundError, match="file not found:"):
            check_file_exists(link)


class TestFindPairedFiles:
    def test_returns_paired_sources_sorted(self, tmp_path: Path) -> None:
        _touch(tmp_path / "b.odex")
        _touch(tmp_path / "b.jar")
        _touch(tmp_path / "a.odex")
        _touch(tmp_path / "a.jar")

        result = find_paired_files(tmp_path, ".odex", ".jar")

        assert result == [tmp_path / "a.odex", tmp_path / "b.odex"]

    def test_multi_dot_stem(self, tmp_path: Path) -> None:
        _touch(tmp_path / "a.foo.odex")
        _touch(tmp_path / "a.foo.jar")

        result = find_paired_files(tmp_path, ".odex", ".jar")

        assert result == [tmp_path / "a.foo.odex"]

    @pytest.mark.parametrize("bad_ext", ["", "odex", "o.dex", "odex."])
    def test_raises_valueerror_for_invalid_source_ext(self, tmp_path: Path, bad_ext: str) -> None:
        with pytest.raises(ValueError, match="source_ext"):
            find_paired_files(tmp_path, bad_ext, ".jar")

    @pytest.mark.parametrize("bad_ext", ["", "odex", "o.dex", "odex."])
    def test_raises_valueerror_for_invalid_companion_ext(self, tmp_path: Path, bad_ext: str) -> None:
        with pytest.raises(ValueError, match="companion_ext"):
            find_paired_files(tmp_path, ".odex", bad_ext)

    def test_raises_notadirectoryerror_for_file_path(self, tmp_path: Path) -> None:
        file_path = _touch(tmp_path / "a.txt")

        with pytest.raises(NotADirectoryError, match="expected directory, found file"):
            find_paired_files(file_path, ".odex", ".jar")

    def test_raises_filenotfounderror_for_nonexistent_path(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="directory not found"):
            find_paired_files(tmp_path / "missing", ".odex", ".jar")

    def test_orphan_source_excluded(self, tmp_path: Path) -> None:
        _touch(tmp_path / "a.odex")

        result = find_paired_files(tmp_path, ".odex", ".jar")

        assert result == []

    def test_orphan_companion_excluded(self, tmp_path: Path) -> None:
        _touch(tmp_path / "a.jar")

        result = find_paired_files(tmp_path, ".odex", ".jar")

        assert result == []

    def test_mixed_only_paired_returned(self, tmp_path: Path) -> None:
        _touch(tmp_path / "a.odex")
        _touch(tmp_path / "a.jar")
        _touch(tmp_path / "b.odex")
        _touch(tmp_path / "c.jar")

        result = find_paired_files(tmp_path, ".odex", ".jar")

        assert result == [tmp_path / "a.odex"]

    def test_companion_that_is_a_directory_excluded(self, tmp_path: Path) -> None:
        _touch(tmp_path / "a.odex")
        (tmp_path / "a.jar").mkdir()

        result = find_paired_files(tmp_path, ".odex", ".jar")

        assert result == []

    def test_subdirectories_not_recursed(self, tmp_path: Path) -> None:
        _touch(tmp_path / "a.odex")
        _touch(tmp_path / "a.jar")
        _touch(tmp_path / "sub" / "b.odex")
        _touch(tmp_path / "sub" / "b.jar")

        result = find_paired_files(tmp_path, ".odex", ".jar")

        assert result == [tmp_path / "a.odex"]

    def test_empty_dir_returns_empty_list(self, tmp_path: Path) -> None:
        result = find_paired_files(tmp_path, ".odex", ".jar")

        assert result == []


class TestListFilesWithExtension:
    def test_returns_sorted_matching_files(self, tmp_path: Path) -> None:
        _touch(tmp_path / "c.apk")
        _touch(tmp_path / "a.apk")
        _touch(tmp_path / "b.jar")

        result = list_files_with_extension(tmp_path, ".apk")

        assert result == [tmp_path / "a.apk", tmp_path / "c.apk"]

    def test_subdirectories_not_recursed(self, tmp_path: Path) -> None:
        _touch(tmp_path / "a.apk")
        _touch(tmp_path / "sub" / "b.apk")

        result = list_files_with_extension(tmp_path, ".apk")

        assert result == [tmp_path / "a.apk"]

    @pytest.mark.parametrize("bad_ext", ["", "apk", "a.pk", "apk."])
    def test_raises_valueerror_for_invalid_extension(self, tmp_path: Path, bad_ext: str) -> None:
        with pytest.raises(ValueError, match="alphanumerics"):
            list_files_with_extension(tmp_path, bad_ext)

    def test_raises_filenotfounderror_for_nonexistent_path(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="directory not found"):
            list_files_with_extension(tmp_path / "missing", ".apk")
