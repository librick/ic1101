import os
import re
from collections.abc import Callable

_VENDOR_CLASS_RE = re.compile(r"^\.class .*L(com/mitsubishielectric|com/honda)/")
_IMPLEMENTS_PARCELABLE_RE = re.compile(r"^\.implements Landroid/os/Parcelable;")


class FileFinder:
    """Finds vendor smali files under the three smali source directories.

    Searches vendor-app-smali, vendor-framework-smali, and system-framework-smali
    in that order. A file is selected when match_filename accepts its name and
    extract_descriptor returns a class descriptor. Deduplicates by descriptor,
    keeping the first occurrence found.
    """

    def __init__(
        self,
        vendor_app_smali_dir: str,
        vendor_framework_smali_dir: str,
        system_framework_smali_dir: str,
        match_filename: Callable[[str], bool],
        extract_descriptor: Callable[[str], str | None],
    ):
        self._dirs = [
            vendor_app_smali_dir,
            vendor_framework_smali_dir,
            system_framework_smali_dir,
        ]
        self._match_filename = match_filename
        self._extract_descriptor = extract_descriptor

    def find(self) -> list[str]:
        seen_descriptors: set[str] = set()
        results: list[str] = []
        for directory in self._dirs:
            for root, _, files in os.walk(directory):
                for filename in files:
                    if not self._match_filename(filename):
                        continue
                    path = os.path.join(root, filename)
                    descriptor = self._extract_descriptor(path)
                    if descriptor is None:
                        continue
                    if descriptor not in seen_descriptors:
                        seen_descriptors.add(descriptor)
                        results.append(path)
        return sorted(results)


def _extract_vendor_class_descriptor(path: str) -> str | None:
    """Returns the .class descriptor if the file declares a vendor class, else None."""
    try:
        with open(path) as f:
            for line in f:
                if _VENDOR_CLASS_RE.match(line):
                    return line.strip()
                if line.startswith(".method"):
                    break
    except OSError:
        return None
    return None


def _extract_vendor_parcelable_descriptor(path: str) -> str | None:
    """Returns the .class descriptor if the file is a vendor Parcelable, else None."""
    try:
        with open(path) as f:
            descriptor = None
            is_parcelable = False
            for line in f:
                stripped = line.strip()
                if descriptor is None and _VENDOR_CLASS_RE.match(stripped):
                    descriptor = stripped
                if _IMPLEMENTS_PARCELABLE_RE.match(stripped):
                    is_parcelable = True
                if stripped.startswith(".method"):
                    break
            if descriptor is not None and is_parcelable:
                return descriptor
    except OSError:
        return None
    return None


def file_finder_proxies(
    vendor_app_smali_dir: str,
    vendor_framework_smali_dir: str,
    system_framework_smali_dir: str,
) -> FileFinder:
    """Builds a finder for $Stub$Proxy.smali files in Honda or Mitsubishi Electric packages."""
    return FileFinder(
        vendor_app_smali_dir,
        vendor_framework_smali_dir,
        system_framework_smali_dir,
        match_filename=lambda name: name.endswith("$Stub$Proxy.smali"),
        extract_descriptor=_extract_vendor_class_descriptor,
    )


def file_finder_stubs(
    vendor_app_smali_dir: str,
    vendor_framework_smali_dir: str,
    system_framework_smali_dir: str,
) -> FileFinder:
    """Builds a finder for $Stub.smali files in Honda or Mitsubishi Electric packages."""
    return FileFinder(
        vendor_app_smali_dir,
        vendor_framework_smali_dir,
        system_framework_smali_dir,
        match_filename=lambda name: name.endswith("$Stub.smali"),
        extract_descriptor=_extract_vendor_class_descriptor,
    )


def file_finder_parcelables(
    vendor_app_smali_dir: str,
    vendor_framework_smali_dir: str,
    system_framework_smali_dir: str,
) -> FileFinder:
    """Builds a finder for Parcelable .smali files in Honda or Mitsubishi Electric packages.

    Skips inner classes ($) since Parcelable definitions are always top-level classes.
    """
    return FileFinder(
        vendor_app_smali_dir,
        vendor_framework_smali_dir,
        system_framework_smali_dir,
        match_filename=lambda name: name.endswith(".smali") and "$" not in name,
        extract_descriptor=_extract_vendor_parcelable_descriptor,
    )
