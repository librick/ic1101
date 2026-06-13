import pytest

from main import BuildError, FileMeta, load_meta


def test_load_meta_parses_entries(tmp_path):
    # Covers octal mode parsing, a full-line comment, a blank line, and a trailing comment.
    meta_path = tmp_path / "overlay-meta.txt"
    meta_path.write_text(
        "system/bin/foo 0 2000 0755\n"
        "# a comment\n"
        "\n"
        "system/etc/baz.txt 1000 1000 0644   # trailing comment\n"
    )

    assert load_meta(meta_path) == {
        "system/bin/foo": FileMeta(0, 2000, 0o755),
        "system/etc/baz.txt": FileMeta(1000, 1000, 0o644),
    }


def test_load_meta_missing_file_returns_empty(tmp_path):
    assert load_meta(tmp_path / "nope") == {}


def test_load_meta_directory_is_error(tmp_path):
    meta_path = tmp_path / "overlay-meta.txt"
    meta_path.mkdir()

    with pytest.raises(BuildError):
        load_meta(meta_path)


def test_load_meta_rejects_malformed_line(tmp_path):
    meta_path = tmp_path / "overlay-meta.txt"
    meta_path.write_text("system/bin/foo 0 2000\n")

    with pytest.raises(BuildError):
        load_meta(meta_path)
