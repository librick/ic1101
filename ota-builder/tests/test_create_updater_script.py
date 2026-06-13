from main import PARTITIONS, create_updater_script


def test_create_updater_script_basic():
    # Vendor file deliberately listed before the system files to confirm the
    # script always emits system payload first, then vendor payload.
    files = [
        "system/bin/foo",
        "system/vendor/bin/bar",
        "system/etc/baz.txt",
    ]

    expected = (
        'assert(getprop("ro.product.device") == "vcm30t30" || getprop("ro.build.product") == "vcm30t30");\n'
        "show_progress(1.000000, 0);\n"
        "set_progress(0.000000);\n"
        'mount("ext4", "EMMC", "/dev/block/platform/sdhci-tegra.3/by-name/APP", "/system");\n'
        'mount("ext4", "EMMC", "/dev/block/platform/sdhci-tegra.3/by-name/CAP", "/system/vendor");\n'
        'package_extract_file("system/bin/foo", "/system/bin/foo");\n'
        'set_perm(0, 0, 0644, "/system/bin/foo");\n'
        'package_extract_file("system/etc/baz.txt", "/system/etc/baz.txt");\n'
        'set_perm(0, 0, 0644, "/system/etc/baz.txt");\n'
        'package_extract_file("system/vendor/bin/bar", "/system/vendor/bin/bar");\n'
        'set_perm(0, 0, 0644, "/system/vendor/bin/bar");\n'
        'unmount("/system/vendor");\n'
        'unmount("/system");\n'
        'package_extract_file("sleep", "/tmp/sleep");\n'
        'set_perm(0, 0, 0755, "/tmp/sleep");\n'
        "set_progress(1.000000);\n"
        'run_program("/tmp/sleep", "30");\n'
    )

    assert create_updater_script(files, {}, PARTITIONS) == expected


def test_create_updater_script_system_only():
    # With no vendor payload, the CAP mount/unmount lines must be absent.
    files = [
        "system/bin/foo",
        "system/etc/baz.txt",
    ]

    expected = (
        'assert(getprop("ro.product.device") == "vcm30t30" || getprop("ro.build.product") == "vcm30t30");\n'
        "show_progress(1.000000, 0);\n"
        "set_progress(0.000000);\n"
        'mount("ext4", "EMMC", "/dev/block/platform/sdhci-tegra.3/by-name/APP", "/system");\n'
        'package_extract_file("system/bin/foo", "/system/bin/foo");\n'
        'set_perm(0, 0, 0644, "/system/bin/foo");\n'
        'package_extract_file("system/etc/baz.txt", "/system/etc/baz.txt");\n'
        'set_perm(0, 0, 0644, "/system/etc/baz.txt");\n'
        'unmount("/system");\n'
        'package_extract_file("sleep", "/tmp/sleep");\n'
        'set_perm(0, 0, 0755, "/tmp/sleep");\n'
        "set_progress(1.000000);\n"
        'run_program("/tmp/sleep", "30");\n'
    )

    result = create_updater_script(files, {}, PARTITIONS)
    assert result == expected
    assert "CAP" not in result
    assert "/system/vendor" not in result


def test_create_updater_script_vendor_only():
    # Only vendor payload: /system (APP) must still be mounted first as the parent of CAP,
    # even though no file lands directly on it.
    files = ["system/vendor/lib/x.so"]

    expected = (
        'assert(getprop("ro.product.device") == "vcm30t30" || getprop("ro.build.product") == "vcm30t30");\n'
        "show_progress(1.000000, 0);\n"
        "set_progress(0.000000);\n"
        'mount("ext4", "EMMC", "/dev/block/platform/sdhci-tegra.3/by-name/APP", "/system");\n'
        'mount("ext4", "EMMC", "/dev/block/platform/sdhci-tegra.3/by-name/CAP", "/system/vendor");\n'
        'package_extract_file("system/vendor/lib/x.so", "/system/vendor/lib/x.so");\n'
        'set_perm(0, 0, 0644, "/system/vendor/lib/x.so");\n'
        'unmount("/system/vendor");\n'
        'unmount("/system");\n'
        'package_extract_file("sleep", "/tmp/sleep");\n'
        'set_perm(0, 0, 0755, "/tmp/sleep");\n'
        "set_progress(1.000000);\n"
        'run_program("/tmp/sleep", "30");\n'
    )

    assert create_updater_script(files, {}, PARTITIONS) == expected


def test_create_updater_script_empty_overlay():
    expected = (
        'assert(getprop("ro.product.device") == "vcm30t30" || getprop("ro.build.product") == "vcm30t30");\n'
        "show_progress(1.000000, 0);\n"
        "set_progress(0.000000);\n"
        'package_extract_file("sleep", "/tmp/sleep");\n'
        'set_perm(0, 0, 0755, "/tmp/sleep");\n'
        "set_progress(1.000000);\n"
        'run_program("/tmp/sleep", "30");\n'
    )

    result = create_updater_script([], {}, PARTITIONS)
    assert result == expected
    assert "mount(" not in result
