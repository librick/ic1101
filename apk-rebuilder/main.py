import argparse
from pathlib import Path
import shutil
import subprocess
import sys
from typing import List
from urllib.request import urlretrieve
from urllib.parse import urlparse
import zipfile
from dataclasses import dataclass

DIR_NAME_UTILS = "utils"
DIR_NAME_UNZIPPED_ZIP = "unzipped-zip"
DIR_NAME_UNZIPPED_MDT = "unzipped-mdt"
DIR_NAME_SMALI = "vendor-app-smali"
DIR_NAME_VENDOR_APP_CLASSES = "vendor-app-classes"
DIR_NAME_OUTPUT_VENDOR_APPS = "output-vendor-apps"

URL_SMALI = "https://bitbucket.org/JesusFreke/smali/downloads/smali-2.5.2.jar"
URL_BAKSMALI = "https://bitbucket.org/JesusFreke/smali/downloads/baksmali-2.5.2.jar"


def get_jar_name_smali() -> str:
    parsed = urlparse(URL_SMALI)
    return parsed.path.rstrip("/").split("/")[-1]


def get_jar_name_baksmali() -> str:
    parsed = urlparse(URL_BAKSMALI)
    return parsed.path.rstrip("/").split("/")[-1]


def get_build_dir() -> Path:
    script_file = Path(__file__).resolve()
    script_dir = script_file.parent
    return script_dir / "build"


def download_file(url: str, output: Path) -> None:
    try:
        urlretrieve(url, filename=str(output))
    except Exception as e:
        sys.exit(f"Error downloading {url}: {e}")
    print(f"Downloaded file to {output}")


def delete_file_if_exists(file_path: str | Path):
    p = Path(file_path)
    try:
        p.unlink(missing_ok=True)
        return True if p.exists() is False else False
    except Exception as e:
        print(f"Error deleting {p}: {e}")


def reset_dir(path: Path):
    # Remove the directory if it exists
    if path.exists():
        shutil.rmtree(path)
    # Create the directory
    path.mkdir()


@dataclass
class JarPaths:
    smali_jar: Path
    baksmali_jar: Path


def download_jars(utils_dir: str | Path) -> JarPaths:
    """
    Downloads smali and baksmali jars into utils_dir,
    and return both paths in a struct.
    """
    jar_path_smali = Path(utils_dir) / get_jar_name_smali()
    jar_path_baksmali = Path(utils_dir) / get_jar_name_baksmali()

    delete_file_if_exists(jar_path_smali)
    delete_file_if_exists(jar_path_baksmali)

    download_file(URL_SMALI, jar_path_smali)
    download_file(URL_BAKSMALI, jar_path_baksmali)

    return JarPaths(smali_jar=jar_path_smali, baksmali_jar=jar_path_baksmali)


def zip_path_type(path_str: str) -> Path:
    p = Path(path_str)
    if not p.is_file():
        raise argparse.ArgumentTypeError(f"'{p}' does not exist or is not a file.")
    if p.suffix.lower() != ".zip":
        raise argparse.ArgumentTypeError(f"'{p}' is not a .zip file.")
    return p


def extract_flat(zip_path: Path, dest_dir: Path):
    """
    Extracts a zip file, ignoring a top-level directory and putting contents directly into dest_dir.
    """
    with zipfile.ZipFile(zip_path, "r") as zf:
        # List all the file paths in the archive
        all_names = [info.filename for info in zf.infolist() if info.filename.strip()]
        # Find their top-level directory names
        tops = {name.split("/", 1)[0] for name in all_names if "/" in name}
        # If there's exactly one, we'll treat it as the root
        root = tops.pop() if len(tops) == 1 else None

        for info in zf.infolist():
            orig = info.filename
            # Skip any “empty” entries
            if not orig or orig.endswith("/"):
                continue

            # Compute the “stripped” path
            rel_path = Path(orig)
            if root and rel_path.parts[0] == root:
                rel_path = Path(*rel_path.parts[1:])  # drop the root folder

            target = dest_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)

            # Extract file
            with zf.open(info) as src, open(target, "wb") as dst:
                shutil.copyfileobj(src, dst)


def verify_file(file_path: Path) -> None:
    if not file_path.exists():
        message = (
            "⚠️🐛 File doesn't match our expected format. Please open a bug report!"
        )
        print(message)
        sys.exit(f"Error: path does not exist: {file_path}")
    if not file_path.is_file():
        message = (
            "⚠️🐛 File doesn't match our expected format. Please open a bug report!"
        )
        print(message)
        sys.exit(f"Error: path exists but is not a file: '{file_path}'")


def verify_dir(dir_path: Path) -> None:
    if not dir_path.exists():
        message = (
            "⚠️🐛 File doesn't match our expected format. Please open a bug report!"
        )
        print(message)
        sys.exit(f"Error: path does not exist: {dir_path}")
    if not dir_path.is_dir():
        message = (
            "⚠️🐛 File file doesn't match our expected format. Please open a bug report!"
        )
        print(message)
        sys.exit(f"Error: path exists but is not a directory: {dir_path}")


def unzip_outer_zip(zip_path: Path, dest_dir) -> Path:
    """
    Extracts the user-provided .zip file and checks that it's a valid MELCO Running Change (MRC) update file.
    Returns the path to the SwUpdate.mdt file contained inside the .zip archive.
    """

    # Extract the .zip file.
    try:
        extract_flat(zip_path, dest_dir=dest_dir)
    except zipfile.BadZipFile as e:
        sys.exit(f"Bad ZIP file: {e}")
    except Exception as e:
        sys.exit(f"Extraction error: {e}")

    # Check that unzipped archive looks reasonable.
    path_sw_update = dest_dir / "SwUpdate2.txt"
    path_update_id = dest_dir / "2250"
    path_sw_update_mdt = dest_dir / "2250" / "SwUpdate.mdt"

    verify_file(path_sw_update)
    verify_dir(path_update_id)
    verify_file(path_sw_update_mdt)

    return path_sw_update_mdt


def unzip_mdt_zip(zip_path: Path, dest_dir):
    # Extract the .mdt file.
    try:
        extract_flat(zip_path, dest_dir=dest_dir)
    except zipfile.BadZipFile as e:
        sys.exit(f"Bad ZIP file: {e}")
    except Exception as e:
        sys.exit(f"Extraction error: {e}")

    # Check that Android system directory looks reasonable.
    verify_dir(dest_dir / "system")
    verify_dir(dest_dir / "system" / "app")
    verify_dir(dest_dir / "system" / "framework")
    verify_dir(dest_dir / "system" / "lib")
    verify_dir(dest_dir / "system" / "vendor")

    # Check that Android system/vendor directory looks reasonable.
    verify_dir(dest_dir / "system" / "vendor" / "app")
    verify_dir(dest_dir / "system" / "vendor" / "framework")
    verify_dir(dest_dir / "system" / "vendor" / "lib")


def check_java_exists() -> None:
    java_path = shutil.which("java")
    if java_path is None:
        print("Error: 'java' not found in your PATH.", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"Found Java at: {java_path}")


def get_odex_paths(parent_dir: str | Path) -> list[Path]:
    print(f"Getting paths to .odex files inside {parent_dir}")
    dir = Path(parent_dir)
    if not dir.is_dir():
        raise ValueError(f"{dir!r} is not a directory")

    matches: List[Path] = []
    for odex_path in dir.glob("*.odex"):
        apk_path = odex_path.with_suffix(".apk")
        if apk_path.exists() and apk_path.is_file():
            matches.append(odex_path)

    return matches


def disassemble_odex(
    baksmali_jar: Path,
    unzipped_mdt_dir: Path,
    output_smali_dir: Path,
    input_odex: Path,
    api_level: int = 17,
) -> None:
    """
    Runs baksmali on a single .odex, pointing at the correct framework jars
    and dumping output to output_smali_dir/<odex-stem>.

    :param baksmali_jar: Path to the baksmali jar file
    :param unzipped_mdt_dir: Path to the root of your unzipped .mdt image (contains the Android filesystem)
    :param output_smali_dir: Path where per-APK smali folders will be created
    :param input_odex: Path to the .odex file to disassemble
    :param api_level: Android API level (default: 17 for Android 4.2.2)
    """
    # Ensure that baksmali jar exists.
    if not baksmali_jar.is_file():
        raise FileNotFoundError(f"Cannot find baksmali JAR at {baksmali_jar}")

    # Standard API-17 framework jars.
    framework_dir = unzipped_mdt_dir / "system/framework"
    core_jar = framework_dir / "core.jar"
    ext_jar = framework_dir / "ext.jar"
    framework_jar = framework_dir / "framework.jar"
    services_jar = framework_dir / "services.jar"
    for jar in (core_jar, ext_jar, framework_jar, services_jar):
        if not jar.is_file():
            raise FileNotFoundError(f"Missing framework jar: {jar}")

    # Build bootclasspath string
    bootclasspath = ":".join(map(str, [core_jar, ext_jar, framework_jar, services_jar]))

    # Vendor framework directory
    vendor_fw_dir = unzipped_mdt_dir / "system/vendor/framework"
    if not vendor_fw_dir.is_dir():
        raise FileNotFoundError(f"Vendor framework dir not found: {vendor_fw_dir}")

    # Output directory named after the odex stem
    out_dir = output_smali_dir / input_odex.stem
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build the command
    cmd = [
        "java",
        "-jar",
        str(baksmali_jar),
        "disassemble",
        "--api",
        str(api_level),
        "--bootclasspath",
        bootclasspath,
        "-d",
        str(vendor_fw_dir),
        "-o",
        str(out_dir),
        str(input_odex),
    ]

    # Execute
    print("Running:", " ".join(cmd))
    subprocess.run(
        cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )


def assemble_smali_to_dex(
    smali_jar: Path, smali_dir: Path, classes_dir: Path, apk_name: str
) -> Path:
    """
    Assembles a directory of smali files into a classes.dex file.

    :param smali_jar: Path to the smali jar file
    :param smali_dir: Path to the root of your smali output (contains subdirs named by odex stem)
    :param classes_dir: Path where per-APK classes.dex files should be written
    :param odex_path:   Path to the original .odex file (used only for its stem)
    :return: Path to the newly created classes.dex
    """
    # Ensure that smali_jar exists.
    if not smali_jar.is_file():
        raise FileNotFoundError(f"Cannot find smali JAR at {smali_jar}")

    # Determine the smali input directory.
    smali_input = smali_dir / apk_name
    if not smali_input.is_dir():
        raise FileNotFoundError(f"Smali directory not found: {smali_input}")

    # Prepare the output directory and path.
    out_dir = classes_dir / apk_name
    out_dir.mkdir(parents=True, exist_ok=True)
    dex_path = out_dir / "classes.dex"

    # Build and run the command
    cmd = [
        "java",
        "-jar",
        str(smali_jar),
        "assemble",
        str(smali_input),
        "-o",
        str(dex_path),
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    return dex_path


def rebuild_apk_with_dex(
    unzipped_mdt_dir: Path, classes_dir: Path, output_apps_dir: Path, odex_path: Path
) -> Path:
    """
    Rebuild an APK by injecting a freshly assembled classes.dex.

    :param unzipped_mdt: Path to the root of your unzipped image (contains the Android filesystem)
    :param classes_dir: Path to the directory containing per-APK classes.dex subdirs
    :param output_apps_dir: Path where rebuilt APKs should be written
    :param odex_path: Path to the original .odex file (stem used to find matching APK & dex)
    :return: Path to the newly created APK
    """
    stem = odex_path.stem

    # Locate the generated classes.dex
    dex_path = classes_dir / stem / "classes.dex"
    if not dex_path.is_file():
        raise FileNotFoundError(f"Missing classes.dex at {dex_path}")

    # Locate the original APK under unzipped_mdt
    original_apk = unzipped_mdt_dir / "system" / "vendor" / "app" / f"{stem}.apk"
    if not original_apk.is_file():
        raise FileNotFoundError(f"Original APK not found at {original_apk}")

    # Prepare output directory & path
    output_apps_dir.mkdir(parents=True, exist_ok=True)
    rebuilt_apk = output_apps_dir / f"{stem}.apk"

    # Rebuild: copy original entries + inject classes.dex at root
    with zipfile.ZipFile(original_apk, "r") as src_zip:
        with zipfile.ZipFile(
            rebuilt_apk, "w", compression=zipfile.ZIP_DEFLATED
        ) as out_zip:
            # Copy all original entries
            for item in src_zip.infolist():
                data = src_zip.read(item.filename)
                out_zip.writestr(item, data)
            # Now inject the new classes.dex
            out_zip.write(dex_path, arcname="classes.dex")

    return rebuilt_apk


def process_apps(
    unzipped_mdt_dir: Path,
    input_apps_dir: Path,
    jars: JarPaths,
    output_smali_dir: Path,
    output_classes_dir: Path,
    output_apps_dir: Path,
):
    """
    Process apps in a given input_apps_dir directory.

    :param unzipped_mdt: Path to the root of your unzipped image (contains the Android filesystem)
    :param input_apps_dir: Path to the directory containing the *.apk and *.odex files
    :param jars: Class containing paths to baksmali and smali .jar files
    :param output_smali_dir: Where smali files will be written (under <output_smali_dir>/<apk-name>)
    :param output_classes_dir: Where classes.dex files will be written (under <output_classes_dir>/<apk-name>)
    :param output_apps_dir: Where rebuilt APKs (APKs with injected classes.dex files) will be written
    """
    # Clean up the directories.
    reset_dir(output_smali_dir)
    reset_dir(output_classes_dir)
    reset_dir(output_apps_dir)

    # Get paths to all of the .odex files in input_apps_dir.
    odex_paths = get_odex_paths(input_apps_dir)
    # Deodex the .odex files to produce .smali files.
    print(f"Attempting to deodex .odex files from {input_apps_dir}")
    for odex_path in odex_paths:
        disassemble_odex(
            baksmali_jar=jars.baksmali_jar,
            unzipped_mdt_dir=unzipped_mdt_dir,
            output_smali_dir=output_smali_dir,
            input_odex=odex_path,
        )

    # Use the .smali files to generate classes.dex files.
    print(f"Attempting to build classes.dex from smali files")
    for odex_path in odex_paths:
        assemble_smali_to_dex(
            smali_jar=jars.smali_jar,
            smali_dir=output_smali_dir,
            classes_dir=output_classes_dir,
            apk_name=odex_path.stem,
        )

    # Inject the classes.dex files into copies of the APKs.
    for odex_path in odex_paths:
        rebuild_apk_with_dex(
            unzipped_mdt_dir=unzipped_mdt_dir,
            classes_dir=output_classes_dir,
            output_apps_dir=output_apps_dir,
            odex_path=odex_path,
        )


def main():
    parser = argparse.ArgumentParser(
        description="Process a .zip file specified by its path."
    )
    parser.add_argument(
        "zip_path", type=zip_path_type, help="Path to an existing .zip file"
    )
    args = parser.parse_args()

    # Get the top-level build directory and ensure it's in a clean state.
    build_dir = get_build_dir()
    reset_dir(build_dir)
    print(f"Output will be written to {build_dir}")

    print("Checking if you have java installed. Needed to run smali and baksmali.")
    check_java_exists()

    # Will contain the unzipped MRC_<...>.zip .zip file.
    unzipped_zip_dir = build_dir / DIR_NAME_UNZIPPED_ZIP
    # Will contain the unzipped SwUpdate.mdt file.
    unzipped_mdt_dir = build_dir / DIR_NAME_UNZIPPED_MDT
    # Will contain the smali<...>.jar and baksmali<...>.jar.
    utils_dir = build_dir / DIR_NAME_UTILS
    # Will contain .smali files from deodexing system/vendor/app/*.odex files.
    vendor_app_smali_dir = build_dir / DIR_NAME_SMALI
    # Will contain classes.dex files from reassembling .smali files.
    vendor_app_classes_dir = build_dir / DIR_NAME_VENDOR_APP_CLASSES
    # Will contain reconstructed system/vendor/app/*.apk files with classes.dex files.
    output_vendor_apps_dir = build_dir / DIR_NAME_OUTPUT_VENDOR_APPS

    # Extract contents of MRC_<...>.zip file.
    reset_dir(unzipped_zip_dir)
    print(f"Extracting .zip archive to {unzipped_zip_dir}")
    mdt_file = unzip_outer_zip(args.zip_path, unzipped_zip_dir)

    # Extract contents of SwUpdate.mdt file.
    reset_dir(unzipped_mdt_dir)
    print(f"Extracting .mdt archive to {unzipped_mdt_dir}")
    unzip_mdt_zip(mdt_file, unzipped_mdt_dir)

    print(f"The Android file system has been extracted to '{unzipped_mdt_dir}'.")

    print(f"Attempting to download smali and baksmali jars.")
    reset_dir(utils_dir)

    jars = download_jars(utils_dir)

    vendor_apps_dir = unzipped_mdt_dir / "system" / "vendor" / "app"
    process_apps(
        unzipped_mdt_dir=unzipped_mdt_dir,
        input_apps_dir=vendor_apps_dir,
        jars=jars,
        output_smali_dir=vendor_app_smali_dir,
        output_classes_dir=vendor_app_classes_dir,
        output_apps_dir=output_vendor_apps_dir,
    )


if __name__ == "__main__":
    main()
