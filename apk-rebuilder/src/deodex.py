import asyncio
import logging
import zipfile
from collections.abc import Awaitable
from pathlib import Path

from file_utils import check_dir_exists, check_file_exists, delete_and_recreate_dir, find_paired_files
from java.baksmali import Baksmali
from java.smali import Smali
from process.process_runner import ProcessFailed

logger = logging.getLogger(__name__)


async def _deodex_single_odex(
    baksmali: Baksmali,
    input_odex: Path,
    bootclasspath: list[Path],
    classpath_dirs: list[Path],
    api_level: int,
    output_smali_dir: Path,
) -> None:
    """Disassemble input_odex into smali text under output_smali_dir/<odex_stem>/.

    On partial success (exit code non-zero but some smali was produced),
    logs a warning and returns normally; on total failure, raises.
    """
    out_dir = output_smali_dir / input_odex.stem
    out_dir.mkdir(exist_ok=True)

    try:
        await baksmali.deodex(
            input_odex=input_odex,
            output_dir=out_dir,
            api_level=api_level,
            bootclasspath=bootclasspath,
            classpath_dirs=classpath_dirs,
        )
    except ProcessFailed as e:
        # baksmali still writes output for classes it can resolve,
        # so check if it produced anything useful.
        out_dir_files = list(out_dir.rglob("*.smali"))
        if not out_dir_files:
            raise
        logger.warning(
            "baksmali deodex returned exit code %d for %s; %d classes were "
            + "still deodexed successfully, some may have unresolved opcodes",
            e.result.return_code,
            input_odex,
            len(out_dir_files),
        )


async def _assemble_smali_to_dex(smali: Smali, smali_dir: Path, classes_dir: Path, archive_name: str) -> Path:
    """Assemble smali_dir/<archive_name>/ into classes_dir/<archive_name>/classes.dex."""
    smali_input = smali_dir / archive_name
    check_dir_exists(smali_input)
    out_dir = classes_dir / archive_name
    out_dir.mkdir(exist_ok=True)
    dex_path = out_dir / "classes.dex"
    await smali.assemble(input_smali_dir=smali_input, output_dex=dex_path)
    return dex_path


def _rebuild_archive_with_dex(
    original: Path,
    classes_dir: Path,
    output_dir: Path,
    stem: str,
    suffix: str,
) -> Path:
    """Copy original to output_dir/<stem><suffix>, replacing its classes.dex with classes_dir/<stem>/classes.dex."""
    dex_path = classes_dir / stem / "classes.dex"
    check_file_exists(dex_path)
    check_file_exists(original)

    rebuilt = output_dir / f"{stem}{suffix}"

    with (
        zipfile.ZipFile(original, "r") as src_zip,
        zipfile.ZipFile(rebuilt, "w", compression=zipfile.ZIP_DEFLATED) as out_zip,
    ):
        for item in src_zip.infolist():
            out_zip.writestr(item, src_zip.read(item.filename))
        out_zip.write(dex_path, arcname="classes.dex")

    return rebuilt


async def deodex_assemble_and_repack(
    *,
    label: str,
    input_dir: Path,
    original_file_dir: Path,
    file_suffix: str,
    baksmali: Baksmali,
    smali: Smali,
    bootclasspath: list[Path],
    classpath_dirs: list[Path],
    api_level: int,
    concurrency: int,
    output_smali_dir: Path,
    output_classes_dir: Path,
    output_repacked_dir: Path,
) -> None:
    """Deodex, reassemble, and repack a directory of archives with their sibling .odex files.

    Args:
        label: Human-readable name for log messages (e.g. "system framework", "vendor app").
        file_suffix: ".jar" or ".apk"; determines which archives are discovered and rebuilt.
        bootclasspath: Ordered jar paths for the device's BOOTCLASSPATH; passed to baksmali for vtable resolution.
        classpath_dirs: Directories passed as baksmali -d flags for additional class resolution.
        api_level: Android API level the .odex files were built for.
        concurrency: Maximum subprocesses to run in parallel within each phase.
        output_smali_dir: Wiped before use.
        output_classes_dir: Wiped before use.
        output_repacked_dir: Wiped before use.
    """
    sem = asyncio.Semaphore(concurrency)

    async def _limited[T](coro: Awaitable[T]) -> T:
        async with sem:
            return await coro

    delete_and_recreate_dir(output_smali_dir)
    delete_and_recreate_dir(output_classes_dir)
    delete_and_recreate_dir(output_repacked_dir)

    odex_paths = find_paired_files(input_dir, ".odex", file_suffix)

    logger.info("deodexing %s .odex files from %s (%d concurrent)", label, input_dir, concurrency)
    await asyncio.gather(
        *[
            _limited(
                _deodex_single_odex(
                    baksmali=baksmali,
                    input_odex=odex_path,
                    bootclasspath=bootclasspath,
                    classpath_dirs=classpath_dirs,
                    api_level=api_level,
                    output_smali_dir=output_smali_dir,
                )
            )
            for odex_path in odex_paths
        ]
    )

    logger.info("assembling classes.dex from %s smali files (%d concurrent)", label, concurrency)
    await asyncio.gather(
        *[
            _limited(
                _assemble_smali_to_dex(
                    smali=smali,
                    smali_dir=output_smali_dir,
                    classes_dir=output_classes_dir,
                    archive_name=odex_path.stem,
                )
            )
            for odex_path in odex_paths
        ]
    )

    # Sequential; per-archive zip I/O isn't worth parallelizing
    for odex_path in odex_paths:
        original = original_file_dir / f"{odex_path.stem}{file_suffix}"
        _rebuild_archive_with_dex(
            original=original,
            classes_dir=output_classes_dir,
            output_dir=output_repacked_dir,
            stem=odex_path.stem,
            suffix=file_suffix,
        )
