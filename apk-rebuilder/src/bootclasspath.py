"""Bootclasspath resolution for baksmali deodexing.

baksmali needs the target device's BOOTCLASSPATH in the same order the
device loads it at boot. On pre-ART Android (API < 21), .odex files
encode virtual method calls as vtable indices that depend on the order
of classes loaded from the bootclasspath. If baksmali sees the jars
in a different order, it will resolve some calls to the wrong methods.

The canonical way to recover this order is to unpack boot.img, extract
the ramdisk, and read the `export BOOTCLASSPATH ...` line from init.rc.
"""

from typing import Final

# BOOTCLASSPATH for MRC_EU_SW_v12_4.zip
# (sha256: 8ff66ea276e941b4428230a2cecbd2f824af334b1116fb4a5d981ab7e172969b)
# Recovered from boot.img -> ramdisk -> init.rc.
# Android 4.2.2 / API 17.
_MRC_EU_SW_V12_4_BOOTCLASSPATH: Final[list[str]] = [
    "core.jar",
    "core-junit.jar",
    "bouncycastle.jar",
    "ext.jar",
    "framework.jar",
    "telephony-common.jar",
    "mms-common.jar",
    "android.policy.jar",
    "services.jar",
    "apache-xml.jar",
    "UiLib.jar",
    "HondaNavigationLib.jar",
    "HondaTelematicsLib.jar",
    "WhitelistLib.jar",
    "honda-framework.jar",
    "HeaderService.jar",
]


def get_bootclasspath_jar_names() -> list[str]:
    """Return bootclasspath jar names in device load order.

    Currently hardcoded for MRC_EU_SW_v12_4.zip. Will be replaced by
    dynamic resolution from the update image's boot.img once that's
    wired up.
    """
    return list(_MRC_EU_SW_V12_4_BOOTCLASSPATH)
