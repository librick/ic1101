import pytest

from main import PARTITIONS, BuildError, check_partitions


def test_check_partitions_allows_system_and_vendor():
    # Both /system (APP) and /system/vendor (CAP) targets are supported.
    check_partitions(["system/bin/foo", "system/vendor/lib/bar.so"], PARTITIONS)


def test_check_partitions_rejects_off_partition():
    with pytest.raises(BuildError):
        check_partitions(["cache/my-important-file"], PARTITIONS)
    # a root-level path (target /foo) is not on a partition either
    with pytest.raises(BuildError):
        check_partitions(["foo"], PARTITIONS)
