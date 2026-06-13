from main import PARTITIONS
from partition import owner, postorder, preorder


def test_preorder_yields_parent_before_children():
    # Mount order: /system must come before its child /system/vendor.
    assert [p.mount_point for p in preorder(PARTITIONS)] == ["/system", "/system/vendor"]


def test_postorder_yields_children_before_parent():
    # Unmount order: /system/vendor must come before its parent /system.
    assert [p.mount_point for p in postorder(PARTITIONS)] == ["/system/vendor", "/system"]


def test_owner_returns_deepest_matching_partition():
    # A path under /system/vendor is owned by the deeper child, not /system.
    assert owner("/system/vendor/lib/bar.so", PARTITIONS).mount_point == "/system/vendor"
    # A path under /system but not /system/vendor is owned by /system.
    assert owner("/system/bin/foo", PARTITIONS).mount_point == "/system"
    # The mount point itself is owned by its partition.
    assert owner("/system/vendor", PARTITIONS).mount_point == "/system/vendor"


def test_owner_returns_none_off_tree():
    assert owner("/cache/important-file", PARTITIONS) is None
