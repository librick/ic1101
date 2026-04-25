import logging
import sys
from pathlib import Path
from typing import Final

import apk_resources
import deodex
import process
from baksmali_noise import BAKSMALI_DEODEX_NOISE_PATTERNS
from boot_img import carve_out_ramdisk, extract_ramdisk
from bootclasspath import get_bootclasspath_jar_names
from file_utils import (
    check_binary_exists,
    delete_and_recreate_dir,
    delete_dir,
    delete_file,
    find_file_by_name,
    list_files_with_extension,
    resolve_empty_dir,
    resolve_files_in_dirs,
)
from java.apktool import Apktool
from java.baksmali import Baksmali
from java.smali import Smali
from process.process_runner_asyncio import ProcessRunnerAsyncio
from unarchive import unzip_mdt_zip, unzip_outer_zip

logger = logging.getLogger(__name__)

_JAR_NAME_SMALI: Final[str] = "smali-2.5.2.jar"
_JAR_NAME_BAKSMALI: Final[str] = "baksmali-2.5.2.jar"
_JAR_NAME_APKTOOL: Final[str] = "apktool_2.12.1.jar"

_APKTOOL_FRAMEWORK_TAG: Final[str] = "ic1101-mitsubishi"
_UPDATE_ID: Final[str] = "2250"
_BAKSMALI_DEODEX_API_LEVEL: Final[int] = 17


class PipelineError(Exception):
    pass


async def run_pipeline(input_dir: Path, output_dir: Path, jvm_jobs: int) -> None:
    """Run the APK rebuilder pipeline.

    - Extracts input .zip archive to get the inner SwUpdate.mdt archive
    - Extracts the inner SwUpdate.mdt archive to get the Android filesystem tree
    - Deodexes, reassembles, and repacks framework jars first (apps depend on framework classes)
    - Deodexes, reassembles, and repacks app APKs against the repacked frameworks
    - Decodes APK resources with apktool
    """
    check_binary_exists("java")

    zip_files = sorted(input_dir.glob("*.zip"))
    if len(zip_files) != 1:
        raise PipelineError(f"expected exactly one .zip file in {input_dir}, found {len(zip_files)}")
    zip_path = zip_files[0]
    logger.info("Found input archive: %s", zip_path)

    output_dir_resolved = resolve_empty_dir(output_dir)
    logger.info("Output will be written to %s", output_dir_resolved)

    def to_stderr(line: bytes) -> None:
        sys.stderr.buffer.write(line)

    baksmali_stderr = process.filter_lines(to_stderr, BAKSMALI_DEODEX_NOISE_PATTERNS)

    baksmali_runner = ProcessRunnerAsyncio(
        default_stdout_handler=to_stderr,
        default_stderr_handler=baksmali_stderr,
    )
    default_runner = ProcessRunnerAsyncio(
        default_stdout_handler=to_stderr,
        default_stderr_handler=to_stderr,
    )

    baksmali = Baksmali.build(input_dir / _JAR_NAME_BAKSMALI, baksmali_runner)
    smali = Smali.build(input_dir / _JAR_NAME_SMALI, default_runner)
    apktool = Apktool.build(input_dir / _JAR_NAME_APKTOOL, default_runner)

    unzipped_zip_dir = output_dir_resolved / "unzipped-zip"
    unzipped_mdt_dir = output_dir_resolved / "unzipped-mdt"
    ramdisk_path = output_dir_resolved / "ramdisk"
    extracted_ramdisk_dir = output_dir_resolved / "extracted-ramdisk"
    system_framework_smali_dir = output_dir_resolved / "system-framework-smali"
    system_framework_classes_dir = output_dir_resolved / "system-framework-classes"
    system_framework_jars_repacked_dir = output_dir_resolved / "system-framework-jars-repacked"
    vendor_framework_smali_dir = output_dir_resolved / "vendor-framework-smali"
    vendor_framework_classes_dir = output_dir_resolved / "vendor-framework-classes"
    vendor_framework_jars_repacked_dir = output_dir_resolved / "vendor-framework-jars-repacked"
    system_app_smali_dir = output_dir_resolved / "system-app-smali"
    system_app_classes_dir = output_dir_resolved / "system-app-classes"
    system_apps_repacked_dir = output_dir_resolved / "system-app-apks-repacked"
    vendor_app_smali_dir = output_dir_resolved / "vendor-app-smali"
    vendor_app_classes_dir = output_dir_resolved / "vendor-app-classes"
    vendor_apps_repacked_dir = output_dir_resolved / "vendor-app-apks-repacked"
    apktool_system_apps_dir = output_dir_resolved / "apktool-system-apps"
    apktool_vendor_apps_dir = output_dir_resolved / "apktool-vendor-apps"
    apktool_vendor_framework_dir = output_dir_resolved / "apktool-vendor-framework"

    delete_and_recreate_dir(unzipped_zip_dir)
    delete_and_recreate_dir(unzipped_mdt_dir)
    delete_file(ramdisk_path)
    delete_and_recreate_dir(extracted_ramdisk_dir)
    delete_and_recreate_dir(apktool_system_apps_dir)
    delete_and_recreate_dir(apktool_vendor_apps_dir)
    delete_dir(apktool_vendor_framework_dir)

    logger.info("extracting zip archive %s to %s", zip_path, unzipped_zip_dir)
    mdt_file = unzip_outer_zip(zip_path, unzipped_zip_dir, _UPDATE_ID)

    logger.info("extracting mdt archive %s to %s", mdt_file, unzipped_mdt_dir)
    unzip_mdt_zip(mdt_file, unzipped_mdt_dir)

    system_apps_dir = unzipped_mdt_dir / "system" / "app"
    vendor_apps_dir = unzipped_mdt_dir / "system" / "vendor" / "app"
    system_framework_dir = unzipped_mdt_dir / "system" / "framework"
    vendor_framework_dir = unzipped_mdt_dir / "system" / "vendor" / "framework"
    vendor_framework_res_apk = vendor_framework_dir / "framework-res.apk"

    boot_img_path = find_file_by_name(unzipped_mdt_dir, "boot.img")
    logger.info("carving out ramdisk from boot.img at %s to %s", boot_img_path, ramdisk_path)
    carve_out_ramdisk(boot_img=boot_img_path, out_path=ramdisk_path)
    logger.info("extracting ramdisk from %s to %s", ramdisk_path, extracted_ramdisk_dir)
    await extract_ramdisk(ramdisk=ramdisk_path, out_dir=extracted_ramdisk_dir, runner=default_runner)

    bootclasspath_jars = resolve_files_in_dirs(
        names=get_bootclasspath_jar_names(),
        search_dirs=[system_framework_dir, vendor_framework_dir],
    )

    await deodex.deodex_assemble_and_repack(
        label="system framework",
        input_dir=system_framework_dir,
        original_file_dir=system_framework_dir,
        file_suffix=".jar",
        baksmali=baksmali,
        smali=smali,
        bootclasspath=bootclasspath_jars,
        classpath_dirs=[vendor_framework_dir],
        api_level=_BAKSMALI_DEODEX_API_LEVEL,
        concurrency=jvm_jobs,
        output_smali_dir=system_framework_smali_dir,
        output_classes_dir=system_framework_classes_dir,
        output_repacked_dir=system_framework_jars_repacked_dir,
    )

    await deodex.deodex_assemble_and_repack(
        label="vendor framework",
        input_dir=vendor_framework_dir,
        original_file_dir=vendor_framework_dir,
        file_suffix=".jar",
        baksmali=baksmali,
        smali=smali,
        bootclasspath=bootclasspath_jars,
        classpath_dirs=[vendor_framework_dir],
        api_level=_BAKSMALI_DEODEX_API_LEVEL,
        concurrency=jvm_jobs,
        output_smali_dir=vendor_framework_smali_dir,
        output_classes_dir=vendor_framework_classes_dir,
        output_repacked_dir=vendor_framework_jars_repacked_dir,
    )

    classpath_dirs = [
        d
        for d in (system_framework_jars_repacked_dir, vendor_framework_jars_repacked_dir)
        if d.is_dir() and any(d.glob("*.jar"))
    ]
    if not classpath_dirs:
        raise PipelineError(
            f"no repacked framework jars in {system_framework_jars_repacked_dir} "
            + f"or {vendor_framework_jars_repacked_dir}; preceding deodex steps produced no output"
        )

    await deodex.deodex_assemble_and_repack(
        label="system app",
        input_dir=system_apps_dir,
        original_file_dir=system_apps_dir,
        file_suffix=".apk",
        baksmali=baksmali,
        smali=smali,
        bootclasspath=bootclasspath_jars,
        classpath_dirs=classpath_dirs,
        api_level=_BAKSMALI_DEODEX_API_LEVEL,
        concurrency=jvm_jobs,
        output_smali_dir=system_app_smali_dir,
        output_classes_dir=system_app_classes_dir,
        output_repacked_dir=system_apps_repacked_dir,
    )

    await deodex.deodex_assemble_and_repack(
        label="vendor app",
        input_dir=vendor_apps_dir,
        original_file_dir=vendor_apps_dir,
        file_suffix=".apk",
        baksmali=baksmali,
        smali=smali,
        bootclasspath=bootclasspath_jars,
        classpath_dirs=classpath_dirs,
        api_level=_BAKSMALI_DEODEX_API_LEVEL,
        concurrency=jvm_jobs,
        output_smali_dir=vendor_app_smali_dir,
        output_classes_dir=vendor_app_classes_dir,
        output_repacked_dir=vendor_apps_repacked_dir,
    )

    await apk_resources.install_framework(
        apktool=apktool,
        framework_res_apk=vendor_framework_res_apk,
        framework_tag=_APKTOOL_FRAMEWORK_TAG,
    )
    await apk_resources.decode_apps(
        apktool=apktool,
        framework_tag=_APKTOOL_FRAMEWORK_TAG,
        apk_paths=list_files_with_extension(system_apps_dir, ".apk"),
        output_dir=apktool_system_apps_dir,
    )
    await apk_resources.decode_apps(
        apktool=apktool,
        framework_tag=_APKTOOL_FRAMEWORK_TAG,
        apk_paths=list_files_with_extension(vendor_apps_dir, ".apk"),
        output_dir=apktool_vendor_apps_dir,
    )
    await apk_resources.decode_framework(
        apktool=apktool,
        framework_res_apk=vendor_framework_res_apk,
        framework_tag=_APKTOOL_FRAMEWORK_TAG,
        output_dir=apktool_vendor_framework_dir,
    )
