from main import collect_overlay


def test_collect_overlay_skips_gitkeep_at_every_level(tmp_path):
    # Real payload files plus .gitkeep placeholders at the root and in nested dirs.
    (tmp_path / ".gitkeep").write_text("")
    (tmp_path / "system" / "bin").mkdir(parents=True)
    (tmp_path / "system" / "bin" / "foo").write_text("x")
    (tmp_path / "system" / "bin" / ".gitkeep").write_text("")
    (tmp_path / "system" / "vendor" / "lib").mkdir(parents=True)
    (tmp_path / "system" / "vendor" / "lib" / ".gitkeep").write_text("")
    (tmp_path / "system" / "etc").mkdir(parents=True)
    (tmp_path / "system" / "etc" / "baz.txt").write_text("x")

    assert collect_overlay(tmp_path) == ["system/bin/foo", "system/etc/baz.txt"]
