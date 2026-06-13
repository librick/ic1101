import pytest

from main import BuildError, check_banned


def test_check_banned_allows_clean_overlay():
    check_banned(["system/bin/foo", "system/vendor/lib/bar.so"])


def test_check_banned_rejects_banned_path():
    # overlay paths are relative; check_banned prepends "/" before matching BANNED_TARGETS.
    with pytest.raises(BuildError):
        check_banned(["system/build.prop"])
    with pytest.raises(BuildError):
        check_banned(["system/vendor/build.prop"])
