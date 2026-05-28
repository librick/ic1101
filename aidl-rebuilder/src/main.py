import argparse
import logging
import os
import sys

from file_finder import (
    file_finder_parcelables,
    file_finder_proxies,
    file_finder_stubs,
)
from pipeline_interfaces import run_pipeline_interfaces
from pipeline_parcelables import run_pipeline_parcelables
from writers.aidl_interface_writer_yaml import AidlInterfaceWriterYaml
from writers.parcelable_writer_yaml import ParcelableWriterYaml

logger = logging.getLogger(__name__)


def parse_args_cli():
    parser = argparse.ArgumentParser(description="Generate YAML interface and parcelable definitions from smali files.")
    parser.add_argument(
        "--vendor-app-smali-dir",
        required=True,
        help="Directory containing vendor app smali files",
    )
    parser.add_argument(
        "--vendor-framework-smali-dir",
        required=True,
        help="Directory containing vendor framework smali files",
    )
    parser.add_argument(
        "--system-framework-smali-dir",
        required=True,
        help="Directory containing system framework smali files",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for interfaces.yaml and parcels.yaml",
    )
    return parser.parse_args()


def check_dir_exists(path: str) -> None:
    """Logs an error and exits if the directory does not exist."""
    if not os.path.isdir(path):
        logger.error("directory not found: %s", path)
        sys.exit(1)


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    args = parse_args_cli()

    vendor_app_smali_dir = os.path.abspath(args.vendor_app_smali_dir)
    vendor_framework_smali_dir = os.path.abspath(args.vendor_framework_smali_dir)
    system_framework_smali_dir = os.path.abspath(args.system_framework_smali_dir)
    output_dir = os.path.abspath(args.output_dir)
    check_dir_exists(vendor_app_smali_dir)
    check_dir_exists(vendor_framework_smali_dir)
    check_dir_exists(system_framework_smali_dir)
    check_dir_exists(output_dir)

    smali_dirs = dict(
        vendor_app_smali_dir=vendor_app_smali_dir,
        vendor_framework_smali_dir=vendor_framework_smali_dir,
        system_framework_smali_dir=system_framework_smali_dir,
    )

    output_path_interfaces = os.path.join(output_dir, "interfaces.yaml")
    output_path_parcelables = os.path.join(output_dir, "parcelables.yaml")

    logger.info("searching for proxy files")
    proxy_paths = file_finder_proxies(**smali_dirs).find()
    logger.info("searching for stub files")
    stub_paths = file_finder_stubs(**smali_dirs).find()

    logger.info("found %d proxy files", len(proxy_paths))
    logger.info("found %d stub files", len(stub_paths))

    if len(proxy_paths) != len(stub_paths):
        logger.error(
            "found %d proxy files but %d stub files; counts must match",
            len(proxy_paths),
            len(stub_paths),
        )
        sys.exit(1)

    interfaces = run_pipeline_interfaces(proxy_paths, stub_paths)
    logger.info("writing %d interfaces to %s", len(interfaces), output_path_interfaces)
    with open(output_path_interfaces, "w") as f:
        with AidlInterfaceWriterYaml(f) as writer:
            writer.write(interfaces, list(smali_dirs.values()))

    logger.info("searching for parcelable files")
    parcelable_paths = file_finder_parcelables(**smali_dirs).find()
    logger.info("found %d parcelable files", len(parcelable_paths))
    parcels = run_pipeline_parcelables(parcelable_paths)
    logger.info("writing %d parcelables to %s", len(parcels), output_path_parcelables)
    with open(output_path_parcelables, "w") as f:
        with ParcelableWriterYaml(f) as writer:
            writer.write(parcels, list(smali_dirs.values()))


if __name__ == "__main__":
    main()
