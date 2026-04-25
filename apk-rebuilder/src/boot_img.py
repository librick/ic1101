import gzip
import shutil
import struct
import tempfile
from pathlib import Path

from process import ProcessRunner


class BootImgError(Exception):
    pass


def _check_magic_bytes(b: bytes) -> None:
    if b != b"ANDROID!":
        raise BootImgError(f"bad boot.img magic: {b!r}")


def carve_out_ramdisk(boot_img: Path, out_path: Path) -> None:
    tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
    replaced = False
    try:
        with Path.open(boot_img, "rb") as f:
            header = f.read(40)
            magic, kernel_size, _, ramdisk_size, _, _, _, _, page_size = struct.unpack("<8sIIIIIIII", header)
            _check_magic_bytes(magic)

            num_kernel_pages = (kernel_size + page_size - 1) // page_size
            ramdisk_offset = page_size * (num_kernel_pages + 1)

            f.seek(ramdisk_offset)
            remaining = ramdisk_size
            with Path.open(tmp_path, "wb") as out:
                while remaining:
                    chunk = f.read(min(64 * 1024, remaining))
                    if not chunk:
                        raise BootImgError(
                            f"ramdisk in {boot_img} truncated: got {ramdisk_size - remaining} of {ramdisk_size} bytes"
                        )
                    out.write(chunk)
                    remaining -= len(chunk)

        tmp_path.replace(out_path)
        replaced = True
    finally:
        if not replaced:
            tmp_path.unlink(missing_ok=True)


async def extract_ramdisk(
    ramdisk: Path,
    out_dir: Path,
    runner: ProcessRunner,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    with Path.open(ramdisk, "rb") as f:
        magic = f.read(6)
    if magic[:2] == b"\x1f\x8b":
        decompress = gzip.open
    elif magic[:6] == b"070701":
        # Raw cpio
        decompress = None
    else:
        raise BootImgError(f"ramdisk {ramdisk} has unrecognized magic bytes: {magic.hex()}")

    with tempfile.NamedTemporaryFile(suffix=".cpio", delete=True) as tmp:
        tmp_path = Path(tmp.name)
        if decompress is None:
            shutil.copyfile(ramdisk, tmp_path)
        else:
            with decompress(ramdisk, "rb") as src, Path.open(tmp_path, "wb") as dst:
                shutil.copyfileobj(src, dst, length=64 * 1024)

        await runner.run(
            [
                "cpio",
                "--extract",
                "--make-directories",
                "--preserve-modification-time",
                "--no-absolute-filenames",
                "--file",
                str(tmp_path),
            ],
            cwd=out_dir,
            timeout=60.0,
        )
