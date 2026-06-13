#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from partition import Partition, owner, postorder, preorder

logger = logging.getLogger(__name__)


class BuildError(Exception):
    """A build step could not proceed."""


@dataclass(frozen=True)
class FileMeta:
    """Ownership and permissions for one deployed file."""

    uid: int
    gid: int
    mode: int  # e.g. 0o644


ROOT = Path(__file__).resolve().parent.parent

# Represent partitions as a forest.
# When we generate our updater-script, this allows us to automatically emit
# mount/unmount pairs in the right order.
# For example, /system must be mounted before /system/vendor,
# and /system/vendor must be unmounted before /system.
PARTITIONS = (
    Partition(
        block_dev="/dev/block/platform/sdhci-tegra.3/by-name/APP",
        mount_point="/system",
        fs_type="ext4",
        storage="EMMC",
        children=(
            Partition(
                block_dev="/dev/block/platform/sdhci-tegra.3/by-name/CAP",
                mount_point="/system/vendor",
                fs_type="ext4",
                storage="EMMC",
            ),
        ),
    ),
)

# /sbin/daupdater refers to /system/build.prop's `ro.build.id` property as the "DA version",
# where DA stands for DisplayAudio, Honda's term for the headunit.
# This is the primary vendor-specified version string for the headunit software.
# daupdater will only allow an update to proceed if (among other requirements):
# - The SwUpdate.mdt zip archive contains a system/build.prop file
# - The SwUpdate.mdt's system/build.prop file contains a `ro.build.id=<version>` line
# - The device's /system partition contains a /system/build.prop file
# - The device's /system/build.prop file contains a `ro.build.id=<version>` line
# - The version strings do NOT match (daupdater refuses to apply an update for the same version)
# There is also an app-based update flow (/sbin/daupdater is lower-level and less restrictive)
# that further requires that:
# - The version has the literal prefix `1.F1` and is of the format 1.F1<X><YYY><Z>,
#       where X, YYY, Z form some hierarchical version number
# - The new version (from SwUpdate.mdt) is strictly greater than the current version (from /system/build.prop)
#       where strictly greater involves checking X, YYY, and Z in hierarchical order
#
# We choose to target /sbin/daupdater because it's simpler than the app-based update path
# and runs on every reboot (its service is started by libsurfaceflinger.so).
# We deliberately use a new DA version that does NOT start with `1.F1`, so that the app-based update path
# is a no-op, which also means any UI-based update popups are automatically suppressed,
# and limits the potential for unwanted/unknown side effects.
# Because official updates rely on that prefix, this also makes it unlikely that
# our crafted DA version string will collide with an official current DA version string.
#
# Next, we use a trick to ensure that our new DA version string is never actually persisted on the target.
# daupdater performs its validation on SwUpdate.mdt's included system/build.prop file,
# but never validates that the packaged system/build.prop is actually *installed*.
# This is an orthogonal concern that is handled by the updater-script.
# We restrict our updater-script so that it *never installs* system/build.prop.
# This means that daupdater will always see our crafted new DA version,
# but we never actually have to change or clobber the installed current DA version.
# daupdater will always see a different version string, and dutifully stage the update.
NEW_DA_VERSION = "IC1101"

NEW_DA_BUILD_TAGS = "release-keys"

# There are two types of updates: SwUpdate.txt and SwUpdate2.txt
# The only difference is which path is used for the zip file, but it's always one of:
# - `/mnt/usbdrive1/SwUpdate.mdt` (v1)
# - `/mnt/usbdrive1/<rom_type>/SwUpdate.mdt` (v2)
# Where the latter path is templated with the current rom type
# (from /system/vendor/build.prop's `custom_rom.type=*` line)
# By using v2, we allow building multiple packages for different rom types.
# But to use v2, we need to ship a SwUpdate2.txt file.
# We also need to include a single line in the SwUpdate2.txt file that starts with "Ver:".
# daupdater only needs the line to exist (it feeds /cache/.copy_complete bookkeeping we don't use),
# so we can put whatever here.
NEW_COMMAND_VERSION = "nichtsistsowieesscheint"

# By default, prevent users from clobbering their own build.prop files.
# Non-exhaustive; should not be relied upon for safety.
BANNED_TARGETS = {
    "/system/build.prop",
    "/system/vendor/build.prop",
}

DEFAULT_META = FileMeta(0, 0, 0o644)

# In-package path of the static sleep helper
SLEEP_PKG_PATH = "sleep"


def write_lf(path: Path, text: str) -> None:
    """Write text as raw LF bytes (no platform newline translation). daupdater
    chops the trailing byte of version / rom-type lines assuming it is the
    newline, so a stray CRLF or a missing newline would corrupt the value."""
    path.write_bytes(text.encode())


def load_meta(meta_path: Path) -> dict[str, FileMeta]:
    """Parse overlay-meta.txt: '<path> <uid> <gid> <mode-octal>' per line."""
    meta: dict[str, FileMeta] = {}
    if not meta_path.exists():
        return meta
    if not meta_path.is_file():
        raise BuildError(f"overlay-meta path exists but is not a file: {meta_path}")
    for lineno, raw in enumerate(meta_path.read_text().splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 4:
            raise BuildError(f"overlay-meta.txt:{lineno}: expected '<path> <uid> <gid> <mode>'")
        path, uid, gid, mode = parts
        meta[path] = FileMeta(int(uid), int(gid), int(mode, 8))
    return meta


def collect_overlay(overlay_dir: Path) -> list[str]:
    """Return an overlay-relative POSIX path for every file under overlay_dir.

    These are the overlay paths (the meta-lookup key and the package member name);
    prepend "/" to get the on-device target.
    """
    if not overlay_dir.is_dir():
        raise BuildError(f"no overlay dir: {overlay_dir}")
    overlay_paths = []
    for p in sorted(overlay_dir.rglob("*")):
        if p.is_file() and p.name != ".gitkeep":
            overlay_paths.append(p.relative_to(overlay_dir).as_posix())
    return overlay_paths


def check_banned(overlay_paths: list[str]) -> None:
    hits = sorted("/" + overlay_path for overlay_path in overlay_paths if "/" + overlay_path in BANNED_TARGETS)
    if hits:
        raise BuildError("refusing to build, overlay contains banned path(s):\n  " + "\n  ".join(hits))


def check_partitions(overlay_paths: list[str], partitions: tuple[Partition, ...]) -> None:
    """Reject overlay paths whose target isn't on a known partition.

    A target is valid iff some partition's mount point is a path-prefix of it; anything else
    (e.g. /cache, /data) would extract to an unmounted path on-device.
    """
    off = sorted("/" + overlay_path for overlay_path in overlay_paths if owner("/" + overlay_path, partitions) is None)
    if off:
        supported = ", ".join(partition.mount_point for partition in preorder(partitions))
        raise BuildError(
            f"refusing to build, overlay contains path(s) not on a supported partition ({supported}):\n  "
            + "\n  ".join(off)
        )


def create_updater_script(
    overlay_paths: list[str], meta: dict[str, FileMeta], partitions: tuple[Partition, ...]
) -> str:
    # Bucket each overlay path under its owning partition, then mount the partitions that are needed
    # (own files, or have a needed descendant) in pre-order and unmount in post-order.
    files: dict[Partition, list[str]] = {}
    for overlay_path in overlay_paths:
        owning = owner("/" + overlay_path, partitions)
        assert owning is not None, f"unvalidated overlay path: {overlay_path}"  # check_partitions is the guard
        files.setdefault(owning, []).append(overlay_path)

    needed: set[Partition] = set()

    def mark(node: Partition) -> bool:
        children_needed = [mark(child) for child in node.children]  # list, not any(), so all descendants mark
        if files.get(node) or any(children_needed):
            needed.add(node)
            return True
        return False

    for root in partitions:
        mark(root)

    out = [
        # device guard: refuse to apply on anything but the vcm30t30 headunit (NVIDIA Tegra 3)
        'assert(getprop("ro.product.device") == "vcm30t30" || getprop("ro.build.product") == "vcm30t30");',
        "show_progress(1.000000, 0);",
        "set_progress(0.000000);",
    ]
    for node in preorder(partitions):
        if node in needed:
            out.append(f'mount("{node.fs_type}", "{node.storage}", "{node.block_dev}", "{node.mount_point}");')

    def emit(overlay_path: str) -> None:
        m = meta.get(overlay_path, DEFAULT_META)
        target = "/" + overlay_path
        out.append(f'package_extract_file("{overlay_path}", "{target}");')
        out.append(f'set_perm({m.uid}, {m.gid}, 0{m.mode:o}, "{target}");')

    for node in preorder(partitions):
        for overlay_path in files.get(node, []):
            emit(overlay_path)

    for node in postorder(partitions):
        if node in needed:
            out.append(f'unmount("{node.mount_point}");')

    # Stage the static sleep helper on tmpfs and give the user a window to pull
    # the USB drive before recovery finishes and reboots into the daupdater
    # loop. It has to land on tmpfs, not a now-unmounted partition, so the
    # binary stays resident if the drive is pulled mid-wait. The package volume
    # is still mounted here, so the extract succeeds after the unmounts.
    unplug_window_secs = 30
    out.append(f'package_extract_file("{SLEEP_PKG_PATH}", "/tmp/sleep");')
    out.append('set_perm(0, 0, 0755, "/tmp/sleep");')
    out.append("set_progress(1.000000);")
    out.append(f'run_program("/tmp/sleep", "{unplug_window_secs}");')
    return "\n".join(out) + "\n"


def stage_tree(
    staging: Path,
    overlay_paths: list[str],
    meta: dict[str, FileMeta],
    rom_type: str,
    overlay_dir: Path,
    update_binary: Path,
    sleep_binary: Path,
    partitions: tuple[Partition, ...],
) -> None:
    # overlay payload (deployed verbatim)
    for overlay_path in overlay_paths:
        dst = staging / overlay_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(overlay_dir / overlay_path, dst)

    # Add placeholder files to SwUpdate.mdt that satisfy daupdater's version checks
    # but that are NOT actually installed to the target
    # (we don't emit updater-script instructions to install them).
    (staging / "system" / "vendor").mkdir(parents=True, exist_ok=True)
    write_lf(
        staging / "system" / "build.prop",
        f"ro.build.id={NEW_DA_VERSION}\nro.build.tags={NEW_DA_BUILD_TAGS}\n",
    )
    write_lf(staging / "system" / "vendor" / "build.prop", f"custom_rom.type={rom_type}\n")

    # Bundle the static sleep helper at the package path the updater-script
    # extracts from (SLEEP_PKG_PATH). It is deliberately not an overlay file:
    # it is never installed to a partition, only extracted to /tmp at apply
    # time, so it is staged directly here and never goes through the
    # overlay/check_partitions path (which would reject a non-partition target).
    if not sleep_binary.is_file():
        raise BuildError(f"missing sleep binary: {sleep_binary}")
    sleep_dst = staging / SLEEP_PKG_PATH
    sleep_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(sleep_binary, sleep_dst)

    # META-INF: OEM edify interpreter + generated script
    meta_dir = staging / "META-INF" / "com" / "google" / "android"
    meta_dir.mkdir(parents=True, exist_ok=True)
    if not update_binary.is_file():
        raise BuildError(f"missing {update_binary}")
    shutil.copy2(update_binary, meta_dir / "update-binary")
    (meta_dir / "updater-script").write_text(create_updater_script(overlay_paths, meta, partitions))


def make_zip(staging: Path, out_zip: Path) -> None:
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(staging.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(staging).as_posix())


def sign(unsigned: Path, signed: Path, signapk_jar: Path, sign_cert: Path, sign_key: Path) -> None:
    if not signapk_jar.is_file():
        raise BuildError(f"missing signapk jar: {signapk_jar}")
    if not sign_cert.is_file():
        raise BuildError(f"missing signing cert: {sign_cert}")
    if not sign_key.is_file():
        raise BuildError(f"missing signing key: {sign_key}")

    # Only pass a minimal set of env vars through to limit unexpected behavior
    _jvm_passthrough = ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "JAVA_HOME", "LD_LIBRARY_PATH")
    env = {k: os.environ[k] for k in _jvm_passthrough if k in os.environ}

    subprocess.run(
        [
            "java",
            "-jar",
            str(signapk_jar),
            "-w",
            str(sign_cert),
            str(sign_key),
            str(unsigned),
            str(signed),
        ],
        check=True,
        env=env,
    )


def build_mdt(
    rom_type: str,
    overlay_paths: list[str],
    meta: dict[str, FileMeta],
    out_dir: Path,
    overlay_dir: Path,
    update_binary: Path,
    sleep_binary: Path,
    signapk_jar: Path,
    sign_cert: Path,
    sign_key: Path,
    partitions: tuple[Partition, ...],
) -> Path:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        staging = tmp_path / "pkg"
        staging.mkdir()
        stage_tree(staging, overlay_paths, meta, rom_type, overlay_dir, update_binary, sleep_binary, partitions)
        unsigned = tmp_path / "unsigned.zip"
        make_zip(staging, unsigned)
        dest = out_dir / rom_type
        dest.mkdir(parents=True, exist_ok=True)
        signed = dest / "SwUpdate.mdt"
        sign(unsigned, signed, signapk_jar, sign_cert, sign_key)
        return signed


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    input_dir = ROOT / "input"

    ap = argparse.ArgumentParser(description="Build & sign a SwUpdate2 OTA package.")
    ap.add_argument(
        "--rom-type",
        action="append",
        default=None,
        help="custom_rom.type to target (repeatable). Default: 1115",
    )
    ap.add_argument("--overlay-dir", type=Path, default=input_dir / "overlay", help="files to deploy")
    ap.add_argument("--overlay-meta", type=Path, default=input_dir / "overlay-meta.txt", help="per-file uid/gid/mode")
    ap.add_argument("--signapk-jar", type=Path, default=input_dir / "signapk.jar", help="signapk.jar to sign with")
    ap.add_argument("--update-binary", type=Path, default=input_dir / "update-binary", help="edify interpreter")
    ap.add_argument(
        "--sleep-binary",
        type=Path,
        default=input_dir / "sleep" / "output" / "sleep",
        help="static sleep helper bundled into the package",
    )
    ap.add_argument("--sign-cert", type=Path, default=input_dir / "keys" / "testkey.x509.pem", help="signing cert")
    ap.add_argument("--sign-key", type=Path, default=input_dir / "keys" / "testkey.pk8", help="signing key")
    ap.add_argument("--output-dir", type=Path, default=ROOT / "output", help="where the build tree is written")
    args = ap.parse_args()

    rom_types = args.rom_type or ["1115"]

    logger.info("overlay dir: %s", args.overlay_dir)
    logger.info("overlay meta: %s", args.overlay_meta)
    logger.info("signapk jar: %s", args.signapk_jar)
    logger.info("sign cert: %s", args.sign_cert)
    logger.info("sign key: %s", args.sign_key)
    logger.info("update binary: %s", args.update_binary)
    logger.info("sleep binary: %s", args.sleep_binary)
    logger.info("output dir: %s", args.output_dir)
    logger.info("rom types: %s", rom_types)

    try:
        overlay_paths = collect_overlay(args.overlay_dir)
        check_banned(overlay_paths)
        check_partitions(overlay_paths, PARTITIONS)
        if not overlay_paths:
            logger.warning("overlay is empty; building an updater-script that deploys no files")
        meta = load_meta(args.overlay_meta)

        build_dir = args.output_dir / datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        if build_dir.exists():
            raise BuildError(f"build dir already exists: {build_dir}")
        build_dir.mkdir(parents=True)

        # Create a minimal SwUpdate2.txt file with a single `Ver:...` line.
        # When daupdater parses this file, it naively chops off the last byte of the line
        # and assumes it's a newline byte,
        # so we're careful to explicitly write a \n byte.
        write_lf(build_dir / "SwUpdate2.txt", f"Ver:{NEW_COMMAND_VERSION}\n")

        for overlay_path in overlay_paths:
            m = meta.get(overlay_path, DEFAULT_META)
            logger.info(
                "updater-script will deploy file: %s, owner: %d:%d, mode: 0%o", "/" + overlay_path, m.uid, m.gid, m.mode
            )
        for rt in rom_types:
            out = build_mdt(
                rt,
                overlay_paths,
                meta,
                build_dir,
                overlay_dir=args.overlay_dir,
                update_binary=args.update_binary,
                sleep_binary=args.sleep_binary,
                signapk_jar=args.signapk_jar,
                sign_cert=args.sign_cert,
                sign_key=args.sign_key,
                partitions=PARTITIONS,
            )
            logger.info("signed file: %s, custom_rom.type: %s", out, rt)

        logger.info("output tree ready: %s", build_dir)
        logger.info("build finished, copy the contents of the output tree to the root of a clean FAT32 USB drive")
    except (BuildError, OSError, subprocess.CalledProcessError):
        logger.exception("build failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
