import logging
from pathlib import Path

from java.apktool import Apktool

logger = logging.getLogger(__name__)


async def install_framework(
    *,
    apktool: Apktool,
    framework_res_apk: Path,
    framework_tag: str,
) -> None:
    """Register framework-res.apk in apktool's cache so it can decode APKs that reference framework resources."""
    if not framework_res_apk.is_file():
        raise FileNotFoundError(f"Framework APK not found at {framework_res_apk}")

    logger.info("installing framework into apktool: %s (tag=%s)", framework_res_apk, framework_tag)
    await apktool.install_framework(framework_apk=framework_res_apk, framework_tag=framework_tag)


async def decode_apps(
    *,
    apktool: Apktool,
    framework_tag: str,
    apk_paths: list[Path],
    output_dir: Path,
) -> None:
    """Decode APKs with apktool into per-APK subdirs of output_dir.

    A framework must already be installed under framework_tag via install_framework.
    """
    logger.info("decoding %d apks into %s", len(apk_paths), output_dir)
    for apk_path in apk_paths:
        apk_output_dir = output_dir / apk_path.stem
        logger.info("decoding apk: %s", apk_path)
        await apktool.decode(
            input_apk=apk_path,
            output_dir=apk_output_dir,
            framework_tag=framework_tag,
        )
        logger.info("decoded apk %s into %s", apk_path, apk_output_dir)


async def decode_framework(
    *,
    apktool: Apktool,
    framework_res_apk: Path,
    framework_tag: str,
    output_dir: Path,
) -> None:
    """Decode framework_res_apk's own resources into output_dir.

    Typically framework_res_apk is the same file that was passed to
    install_framework under framework_tag; this call extracts the
    framework's resources to disk.
    """
    if not framework_res_apk.is_file():
        raise FileNotFoundError(f"Framework APK not found at {framework_res_apk}")

    logger.info("decoding framework apk: %s", framework_res_apk)
    await apktool.decode(
        input_apk=framework_res_apk,
        output_dir=output_dir,
        framework_tag=framework_tag,
    )
    logger.info("decoded framework apk %s into %s", framework_res_apk, output_dir)
