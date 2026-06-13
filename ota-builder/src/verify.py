#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import logging
import re
import ssl
import stat
import subprocess
import sys
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

MBR_SIGNATURE = b"\x55\xaa"
GPT_PROTECTIVE_TYPE = 0xEE
BLOCK_DEVICE_PATTERN = re.compile(r"/dev/sd[a-z]+")
VER_PATTERN = re.compile(rb"^Ver:[A-Za-z0-9]+\n", re.MULTILINE)
BUILD_ID_PATTERN = re.compile(rb"^ro\.build\.id=[A-Za-z0-9]+\n", re.MULTILINE)
DIR_NAME_PATTERN = re.compile(r"[0-9]{4}")
UI_PRINT_PATTERN = re.compile(rb"\bui_print\s*\(")

BINARY_ELF_MAGIC = b"\x7fELF"
BINARY_EI_CLASS = 4
BINARY_EI_DATA = 5
BINARY_ELFCLASS32 = 1
BINARY_ELFDATA2LSB = 1
BINARY_EM_ARM = 40
BINARY_SHT_ARM_ATTRIBUTES = 0x70000003
BINARY_ARM_ATTRS_FORMAT_VERSION = ord("A")
BINARY_TAG_FILE = 1
BINARY_TAG_CPU_ARCH = 6
BINARY_CPU_ARCH_ARMV7 = 10
# Per the ARM ABI, these attribute tags carry NUL-terminated string values;
# everything else before Tag_CPU_arch is ULEB128.
BINARY_ARM_ATTR_STRING_TAGS = frozenset({4, 5, 67})

REQUIRED_ZIP_ENTRIES = (
    "META-INF/CERT.RSA",
    "META-INF/CERT.SF",
    "META-INF/MANIFEST.MF",
    "META-INF/com/android/otacert",
    "META-INF/com/google/android/update-binary",
    "META-INF/com/google/android/updater-script",
    "sleep",
    "system/build.prop",
    "system/vendor/build.prop",
)


class ValidationError(Exception):
    pass


@dataclass(frozen=True)
class MbrPartition:
    index: int
    type_byte: int
    start_lba: int
    sector_count: int


@dataclass(frozen=True)
class SigningKey:
    cert_path: Path
    spki_sha256: str


@dataclass(frozen=True)
class Elf32Header:
    machine: int
    section_header_offset: int
    section_header_entry_size: int
    section_header_count: int


def partition_device_path(block_device: Path, number: int = 1) -> Path:
    return block_device.with_name(f"{block_device.name}{number}")


def read_leading_bytes(path: Path, count: int) -> bytes:
    with path.open("rb") as handle:
        return handle.read(count)


def read_file_bytes(path: Path) -> bytes:
    with path.open("rb") as handle:
        return handle.read()


def read_archive_file(archive: zipfile.ZipFile, name: str, source: str) -> bytes:
    if archive.getinfo(name).is_dir():
        raise ValidationError(f"{source} is a directory entry; expected a file")
    return archive.read(name)


def is_regular_file(path: Path) -> bool:
    return stat.S_ISREG(path.lstat().st_mode)


def is_directory(path: Path) -> bool:
    return stat.S_ISDIR(path.lstat().st_mode)


def count_literal_lines(data: bytes, line: bytes) -> int:
    if not line.endswith(b"\n"):
        line = line + b"\n"
    count = 0
    start = 0
    while True:
        index = data.find(line, start)
        if index == -1:
            return count
        if index == 0 or data[index - 1] == 0x0A:
            count += 1
        start = index + 1


def count_matching_lines(data: bytes, pattern: re.Pattern[bytes]) -> int:
    return sum(1 for _ in pattern.finditer(data))


def parse_mbr_partitions(sector: bytes) -> list[MbrPartition]:
    partitions = []
    for index in range(4):
        offset = 446 + index * 16
        entry = sector[offset : offset + 16]
        type_byte = entry[4]
        start_lba = int.from_bytes(entry[8:12], "little")
        sector_count = int.from_bytes(entry[12:16], "little")
        if type_byte != 0:
            partitions.append(MbrPartition(index, type_byte, start_lba, sector_count))
    return partitions


def read_uleb128(data: bytes, offset: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        if offset >= len(data):
            raise ValidationError("truncated uleb128 in arm attributes")
        byte = data[offset]
        offset += 1
        result |= (byte & 0x7F) << shift
        if byte & 0x80 == 0:
            return result, offset
        shift += 7


def skip_ntbs(data: bytes, offset: int) -> int:
    end = data.find(b"\x00", offset)
    if end == -1:
        raise ValidationError("unterminated string in arm attributes")
    return end + 1


def parse_elf32_header(data: bytes, source: str) -> Elf32Header:
    if len(data) < 52:
        raise ValidationError(f"{source} is too small to be an elf object")
    if data[:4] != BINARY_ELF_MAGIC:
        raise ValidationError(f"{source} is not an elf object (bad magic)")
    if data[BINARY_EI_CLASS] != BINARY_ELFCLASS32:
        raise ValidationError(f"{source} is not a 32-bit elf object")
    if data[BINARY_EI_DATA] != BINARY_ELFDATA2LSB:
        raise ValidationError(f"{source} is not a little-endian elf object")
    machine = int.from_bytes(data[18:20], "little")
    shoff = int.from_bytes(data[32:36], "little")
    shentsize = int.from_bytes(data[46:48], "little")
    shnum = int.from_bytes(data[48:50], "little")
    return Elf32Header(machine, shoff, shentsize, shnum)


def find_arm_attributes_section(data: bytes, header: Elf32Header, source: str) -> bytes:
    if header.section_header_offset == 0 or header.section_header_count == 0:
        raise ValidationError(f"{source} has no section headers; cannot read arm attributes")
    for index in range(header.section_header_count):
        base = header.section_header_offset + index * header.section_header_entry_size
        entry = data[base : base + 40]
        if len(entry) < 40:
            raise ValidationError(f"{source} has a truncated section header")
        if int.from_bytes(entry[4:8], "little") == BINARY_SHT_ARM_ATTRIBUTES:
            sh_offset = int.from_bytes(entry[16:20], "little")
            sh_size = int.from_bytes(entry[20:24], "little")
            section = data[sh_offset : sh_offset + sh_size]
            if len(section) != sh_size:
                raise ValidationError(f"{source} arm attributes section is truncated")
            return section
    raise ValidationError(f"{source} has no .ARM.attributes section; cannot confirm armv7")


def read_file_attribute_arch(section: bytes, cursor: int, end: int) -> int | None:
    while cursor < end:
        tag, cursor = read_uleb128(section, cursor)
        if tag == BINARY_TAG_CPU_ARCH:
            arch, _ = read_uleb128(section, cursor)
            return arch
        if tag in BINARY_ARM_ATTR_STRING_TAGS:
            cursor = skip_ntbs(section, cursor)
        elif tag == 32:  # Tag_compatibility: ULEB128 flag followed by an NTBS
            _, cursor = read_uleb128(section, cursor)
            cursor = skip_ntbs(section, cursor)
        else:
            _, cursor = read_uleb128(section, cursor)
    return None


def scan_aeabi_file_tags(section: bytes, cursor: int, vendor_end: int, source: str) -> int | None:
    while cursor < vendor_end:
        scope_tag = section[cursor]
        block_start = cursor
        cursor += 1
        if cursor + 4 > vendor_end:
            raise ValidationError(f"{source} arm attributes sub-subsection is truncated")
        sub_size = int.from_bytes(section[cursor : cursor + 4], "little")
        block_end = block_start + sub_size
        if sub_size < 5 or block_end > vendor_end:
            raise ValidationError(f"{source} arm attributes sub-subsection length is invalid")
        if scope_tag == BINARY_TAG_FILE:
            arch = read_file_attribute_arch(section, cursor + 4, block_end)
            if arch is not None:
                return arch
        cursor = block_end
    return None


def arm_attributes_cpu_arch(section: bytes, source: str) -> int:
    if not section or section[0] != BINARY_ARM_ATTRS_FORMAT_VERSION:
        raise ValidationError(f"{source} arm attributes use an unsupported format version")
    offset = 1
    while offset < len(section):
        if offset + 4 > len(section):
            raise ValidationError(f"{source} arm attributes vendor section is truncated")
        sub_len = int.from_bytes(section[offset : offset + 4], "little")
        if sub_len < 4 or offset + sub_len > len(section):
            raise ValidationError(f"{source} arm attributes vendor length is invalid")
        vendor_end = offset + sub_len
        name_end = section.find(b"\x00", offset + 4)
        if name_end == -1 or name_end >= vendor_end:
            raise ValidationError(f"{source} arm attributes vendor name is unterminated")
        if section[offset + 4 : name_end] == b"aeabi":
            arch = scan_aeabi_file_tags(section, name_end + 1, vendor_end, source)
            if arch is not None:
                return arch
        offset = vendor_end
    raise ValidationError(f"{source} arm attributes do not specify Tag_CPU_arch")


def check_block_device_name(path: Path) -> None:
    if BLOCK_DEVICE_PATTERN.fullmatch(str(path)) is None:
        raise ValidationError(f"{path} is not of the form /dev/sdX")


def check_block_device(path: Path) -> None:
    if not path.exists():
        raise ValidationError(f"{path} does not exist")
    if not stat.S_ISBLK(path.stat().st_mode):
        raise ValidationError(f"{path} is not a block device")


def check_msdos_partition_table(sector: bytes, partitions: list[MbrPartition], source: str) -> None:
    if sector[510:512] != MBR_SIGNATURE:
        raise ValidationError(f"{source} has no mbr boot signature; not an msdos partition table")
    if any(p.type_byte == GPT_PROTECTIVE_TYPE for p in partitions):
        raise ValidationError(f"{source} has a gpt protective partition; not an msdos partition table")


def check_single_first_partition(partitions: list[MbrPartition], source: str) -> None:
    if len(partitions) != 1:
        raise ValidationError(f"{source} has {len(partitions)} partitions; expected exactly 1")
    only = partitions[0]
    if only.index != 0:
        raise ValidationError(f"{source} single partition is in slot {only.index + 1}; expected slot 1")


def check_fat32(boot_sector: bytes, source: str) -> None:
    if boot_sector[510:512] != MBR_SIGNATURE:
        raise ValidationError(f"{source} has no boot-sector signature; not a fat32 filesystem")
    fs_type = boot_sector[82:90].rstrip(b" \x00")
    if fs_type != b"FAT32":
        raise ValidationError(f"{source} filesystem type field is {fs_type!r}; expected FAT32")


def check_regular_file(path: Path) -> None:
    try:
        path.lstat()
    except OSError as exc:
        raise ValidationError(f"{path} does not exist") from exc
    if not is_regular_file(path):
        raise ValidationError(f"{path} is not a regular file")


def check_non_empty(data: bytes, source: str) -> None:
    if len(data) == 0:
        raise ValidationError(f"{source} is empty")


def check_unix_line_endings(data: bytes, source: str) -> None:
    if b"\r" in data:
        raise ValidationError(f"{source} contains carriage returns; expected unix line endings")


def check_first_line_crlf(data: bytes, line: bytes, source: str) -> None:
    # `line` is the bare line content, without a terminator.
    expected = line + b"\r\n"
    if not data.startswith(expected):
        raise ValidationError(f"{source} does not start with CRLF-terminated line {line!r}")


def check_unique_matching_line(data: bytes, pattern: re.Pattern[bytes], source: str) -> None:
    count = count_matching_lines(data, pattern)
    if count == 0:
        raise ValidationError(f"{source} has no line matching {pattern.pattern!r}")
    if count > 1:
        raise ValidationError(f"{source} has {count} lines matching {pattern.pattern!r}; expected exactly 1")


def check_unique_literal_line(data: bytes, line: bytes, source: str) -> None:
    count = count_literal_lines(data, line)
    if count == 0:
        raise ValidationError(f"{source} has no line {line!r}")
    if count > 1:
        raise ValidationError(f"{source} has {count} occurrences of line {line!r}; expected exactly 1")


def check_ascii_armored_certificate(data: bytes, source: str) -> None:
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValidationError(f"{source} is not ascii; expected an ascii-armored certificate") from exc
    try:
        der = ssl.PEM_cert_to_DER_cert(text)
    except ValueError as exc:
        raise ValidationError(f"{source} is not a valid ascii-armored certificate: {exc}") from exc
    if not der.startswith(b"\x30"):
        raise ValidationError(f"{source} pem body does not decode to an asn.1 certificate")


def check_armv7_elf(data: bytes, source: str) -> None:
    header = parse_elf32_header(data, source)
    if header.machine != BINARY_EM_ARM:
        raise ValidationError(f"{source} machine type is 0x{header.machine:x}; expected ARM (0x28)")
    section = find_arm_attributes_section(data, header, source)
    arch = arm_attributes_cpu_arch(section, source)
    if arch != BINARY_CPU_ARCH_ARMV7:
        raise ValidationError(f"{source} Tag_CPU_arch is {arch}; expected {BINARY_CPU_ARCH_ARMV7} (ARMv7)")


def mount_filesystem(device: Path, mount_point: Path) -> None:
    result = subprocess.run(
        ["mount", "--read-only", "--types", "vfat", device, mount_point],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise ValidationError(f"mount of {device} at {mount_point} failed: {result.stderr.strip()}")


def unmount_filesystem(mount_point: Path) -> None:
    result = subprocess.run(["umount", mount_point], capture_output=True, text=True, check=False)
    if result.returncode != 0:
        logger.warning("umount of %s failed: %s", mount_point, result.stderr.strip())


def verify_file_swupdate2_txt(path: Path) -> None:
    check_regular_file(path)
    data = read_file_bytes(path)
    source = str(path)
    check_non_empty(data, source)
    check_unix_line_endings(data, source)
    check_unique_matching_line(data, VER_PATTERN, source)


def verify_file_cert_rsa(archive: zipfile.ZipFile, mdt: Path) -> None:
    name = "META-INF/CERT.RSA"
    source = f"{mdt}:{name}"
    data = read_archive_file(archive, name, source)
    check_non_empty(data, source)


def verify_file_cert_sf(archive: zipfile.ZipFile, mdt: Path) -> None:
    name = "META-INF/CERT.SF"
    source = f"{mdt}:{name}"
    data = read_archive_file(archive, name, source)
    check_non_empty(data, source)
    # CERT.SF is a JAR signature file: signapk emits CRLF and CERT.RSA signs these
    # exact bytes, so CRLF is expected, not a defect.
    check_first_line_crlf(data, b"Signature-Version: 1.0", source)


def verify_file_manifest_mf(archive: zipfile.ZipFile, mdt: Path) -> None:
    name = "META-INF/MANIFEST.MF"
    source = f"{mdt}:{name}"
    data = read_archive_file(archive, name, source)
    check_non_empty(data, source)
    check_first_line_crlf(data, b"Manifest-Version: 1.0", source)


def verify_file_otacert(archive: zipfile.ZipFile, mdt: Path) -> None:
    name = "META-INF/com/android/otacert"
    source = f"{mdt}:{name}"
    data = read_archive_file(archive, name, source)
    check_non_empty(data, source)
    check_unix_line_endings(data, source)
    check_ascii_armored_certificate(data, source)


def verify_file_update_binary(archive: zipfile.ZipFile, mdt: Path) -> None:
    name = "META-INF/com/google/android/update-binary"
    source = f"{mdt}:{name}"
    data = read_archive_file(archive, name, source)
    check_non_empty(data, source)


def warn_on_ui_print(data: bytes, source: str) -> None:
    count = count_matching_lines(data, UI_PRINT_PATTERN)
    if count > 0:
        logger.warning(
            "%s has %d ui_print call(s); ui_print is not rendered to the UI in this recovery",
            source,
            count,
        )


def verify_file_updater_script(archive: zipfile.ZipFile, mdt: Path) -> None:
    name = "META-INF/com/google/android/updater-script"
    source = f"{mdt}:{name}"
    data = read_archive_file(archive, name, source)
    check_non_empty(data, source)
    check_unix_line_endings(data, source)
    warn_on_ui_print(data, source)


def verify_file_build_prop(archive: zipfile.ZipFile, mdt: Path) -> None:
    name = "system/build.prop"
    source = f"{mdt}:{name}"
    data = read_archive_file(archive, name, source)
    check_non_empty(data, source)
    check_unix_line_endings(data, source)
    check_unique_matching_line(data, BUILD_ID_PATTERN, source)
    check_unique_literal_line(data, b"ro.build.tags=release-keys", source)


def verify_file_vendor_build_prop(archive: zipfile.ZipFile, mdt: Path, dir_name: str) -> None:
    name = "system/vendor/build.prop"
    source = f"{mdt}:{name}"
    data = read_archive_file(archive, name, source)
    check_non_empty(data, source)
    check_unix_line_endings(data, source)
    check_unique_literal_line(data, b"custom_rom.type=" + dir_name.encode("ascii"), source)


def verify_file_sleep(archive: zipfile.ZipFile, mdt: Path) -> None:
    name = "sleep"
    source = f"{mdt}:{name}"
    data = read_archive_file(archive, name, source)
    check_non_empty(data, source)
    check_armv7_elf(data, source)


def run_openssl(args: list[str], stdin: bytes | None = None) -> subprocess.CompletedProcess[bytes]:
    try:
        return subprocess.run(["openssl", *args], input=stdin, capture_output=True, check=False)
    except FileNotFoundError as exc:
        raise ValidationError("openssl not found on path; required for signature checks") from exc


def cert_spki_sha256(cert_pem: bytes) -> str:
    pub = run_openssl(["x509", "-pubkey", "-noout"], cert_pem)
    if pub.returncode != 0:
        raise ValidationError(f"could not read certificate: {pub.stderr.decode(errors='replace').strip()}")
    der = run_openssl(["pkey", "-pubin", "-outform", "DER"], pub.stdout)
    if der.returncode != 0:
        raise ValidationError(f"could not read public key: {der.stderr.decode(errors='replace').strip()}")
    return hashlib.sha256(der.stdout).hexdigest()


def pkcs7_signer_cert_pem(pkcs7_der: bytes) -> bytes:
    result = run_openssl(["pkcs7", "-inform", "DER", "-print_certs"], pkcs7_der)
    if result.returncode != 0:
        raise ValidationError(f"could not parse pkcs7 block: {result.stderr.decode(errors='replace').strip()}")
    return result.stdout


def wholefile_signature_der(comment: bytes) -> bytes:
    if len(comment) < 6 or comment[-4:-2] != b"\xff\xff":
        raise ValidationError("archive comment has no signapk whole-file signature footer")
    sig_start = comment[-6] | (comment[-5] << 8)
    return comment[len(comment) - sig_start : len(comment) - 6]


def load_signing_key(cert_path: Path) -> SigningKey:
    check_regular_file(cert_path)
    return SigningKey(cert_path, cert_spki_sha256(read_file_bytes(cert_path)))


def check_signature_binding(cert_rsa_der: bytes, cert_sf: bytes, signing_key: SigningKey, source: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        signature = tmp_dir / "CERT.RSA"
        signature.write_bytes(cert_rsa_der)
        content = tmp_dir / "CERT.SF"
        content.write_bytes(cert_sf)
        result = run_openssl(
            [
                "cms",
                "-verify",
                "-inform",
                "DER",
                "-in",
                str(signature),
                "-content",
                str(content),
                "-certfile",
                str(signing_key.cert_path),
                "-CAfile",
                str(signing_key.cert_path),
                "-no_check_time",
            ]
        )
    if result.returncode != 0:
        raise ValidationError(
            f"{source} signature over CERT.SF did not verify under {signing_key.cert_path}: "
            f"{result.stderr.decode(errors='replace').strip()}"
        )


def verify_signing(archive: zipfile.ZipFile, mdt: Path, signing_key: SigningKey) -> None:
    cert_rsa = archive.read("META-INF/CERT.RSA")
    if cert_spki_sha256(pkcs7_signer_cert_pem(cert_rsa)) != signing_key.spki_sha256:
        raise ValidationError(f"{mdt}:META-INF/CERT.RSA signer key does not match {signing_key.cert_path}")

    otacert = archive.read("META-INF/com/android/otacert")
    if cert_spki_sha256(otacert) != signing_key.spki_sha256:
        raise ValidationError(f"{mdt}:META-INF/com/android/otacert key does not match {signing_key.cert_path}")

    wholefile = pkcs7_signer_cert_pem(wholefile_signature_der(archive.comment))
    if cert_spki_sha256(wholefile) != signing_key.spki_sha256:
        raise ValidationError(f"{mdt} whole-file signature key does not match {signing_key.cert_path}")

    cert_sf = archive.read("META-INF/CERT.SF")
    check_signature_binding(cert_rsa, cert_sf, signing_key, f"{mdt}:META-INF/CERT.RSA")


def verify_file_swupdate_mdt(mdt: Path, dir_name: str, signing_key: SigningKey) -> None:
    if not zipfile.is_zipfile(mdt):
        raise ValidationError(f"{mdt} is not a valid zip archive")
    with zipfile.ZipFile(mdt) as archive:
        names = set(archive.namelist())
        missing = [name for name in REQUIRED_ZIP_ENTRIES if name not in names]
        if missing:
            raise ValidationError(f"{mdt} is missing entries: {', '.join(missing)}")
        verify_file_cert_rsa(archive, mdt)
        verify_file_cert_sf(archive, mdt)
        verify_file_manifest_mf(archive, mdt)
        verify_file_otacert(archive, mdt)
        verify_file_update_binary(archive, mdt)
        verify_file_updater_script(archive, mdt)
        verify_file_build_prop(archive, mdt)
        verify_file_vendor_build_prop(archive, mdt, dir_name)
        verify_file_sleep(archive, mdt)
        verify_signing(archive, mdt, signing_key)


def check_update_directory(directory: Path, signing_key: SigningKey) -> None:
    name = directory.name
    if DIR_NAME_PATTERN.fullmatch(name) is None:
        raise ValidationError(f"directory name {name} is not exactly 4 decimal digits")
    entries = list(directory.iterdir())
    if len(entries) != 1:
        raise ValidationError(f"{directory} has {len(entries)} entries; expected exactly 1")
    entry = entries[0]
    if entry.name != "SwUpdate.mdt":
        raise ValidationError(f"{directory} contains {entry.name}; expected only SwUpdate.mdt")
    if not is_regular_file(entry):
        raise ValidationError(f"{entry} is not a regular file")
    if entry.stat().st_size == 0:
        raise ValidationError(f"{entry} is empty")
    verify_file_swupdate_mdt(entry, name, signing_key)


def check_root_contents(root: Path, signing_key: SigningKey) -> None:
    swupdate2 = root / "SwUpdate2.txt"
    verify_file_swupdate2_txt(swupdate2)

    directories = []
    for entry in root.iterdir():
        if entry.name == "SwUpdate2.txt":
            continue
        if is_directory(entry):
            directories.append(entry)
        else:
            raise ValidationError(f"{entry} is neither SwUpdate2.txt nor a directory")

    if not directories:
        raise ValidationError(f"{root} has no directories; expected at least one")
    for directory in sorted(directories):
        check_update_directory(directory, signing_key)


def configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="validate a fat32 swupdate usb image")
    parser.add_argument(
        "--block-device",
        required=True,
        help="path to the whole-disk block device, e.g. /dev/sda",
    )
    parser.add_argument(
        "--signing-cert",
        required=True,
        help="path to the expected signing certificate (pem x509)",
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    configure_logging()
    args = parse_args(argv)
    block_device = Path(args.block_device)
    signing_key = load_signing_key(Path(args.signing_cert))

    logger.info("checking block device: %s", block_device)
    check_block_device_name(block_device)
    check_block_device(block_device)

    partition = partition_device_path(block_device)

    sector = read_leading_bytes(block_device, 512)
    partitions = parse_mbr_partitions(sector)
    logger.info("checking msdos partition table")
    check_msdos_partition_table(sector, partitions, str(block_device))
    check_single_first_partition(partitions, str(block_device))

    logger.info("checking partition: %s", partition)
    check_block_device(partition)
    boot_sector = read_leading_bytes(partition, 512)
    check_fat32(boot_sector, str(partition))

    mount_point = Path(tempfile.mkdtemp(prefix="swupdate-check-"))
    logger.info("mounting %s at %s", partition, mount_point)
    try:
        mount_filesystem(partition, mount_point)
        try:
            check_root_contents(mount_point, signing_key)
        finally:
            unmount_filesystem(mount_point)
    finally:
        try:
            mount_point.rmdir()
        except OSError:
            logger.warning("could not remove mount point: %s", mount_point)

    logger.info("all checks passed")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(run())
    except (ValidationError, OSError):
        logger.exception("validation failed")
        sys.exit(1)
