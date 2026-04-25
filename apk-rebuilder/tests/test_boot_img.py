import asyncio
import struct
from pathlib import Path

import pytest

from boot_img import BootImgError, carve_out_ramdisk, extract_ramdisk


def _build_boot_img(
    kernel: bytes,
    ramdisk: bytes,
    *,
    page_size: int = 2048,
    magic: bytes = b"ANDROID!",
    declared_ramdisk_size: int | None = None,
) -> bytes:
    header = struct.pack(
        "<8sIIIIIIII",
        magic,
        len(kernel),
        0,
        declared_ramdisk_size if declared_ramdisk_size is not None else len(ramdisk),
        0,
        0,
        0,
        0,
        page_size,
    )
    header_page = header.ljust(page_size, b"\x00")
    kernel_pages = (len(kernel) + page_size - 1) // page_size
    kernel_padded = kernel.ljust(kernel_pages * page_size, b"\x00")
    return header_page + kernel_padded + ramdisk


class _RecordingRunner:
    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def run(self, argv: list[str], *, cwd: Path, timeout: float) -> None:  # noqa: ASYNC109
        self.calls.append(argv)


class TestCarveOutRamdisk:
    def test_extracts_ramdisk_bytes(self, tmp_path: Path) -> None:
        kernel = b"K" * 5000
        ramdisk = b"RAMDISK-PAYLOAD-\x00\x01\x02"
        boot_img = tmp_path / "boot.img"
        out_path = tmp_path / "ramdisk.bin"
        boot_img.write_bytes(_build_boot_img(kernel, ramdisk))

        carve_out_ramdisk(boot_img, out_path)

        assert out_path.read_bytes() == ramdisk
        assert not out_path.with_suffix(out_path.suffix + ".tmp").exists()

    def test_raises_on_bad_magic(self, tmp_path: Path) -> None:
        boot_img = tmp_path / "boot.img"
        out_path = tmp_path / "ramdisk.bin"
        boot_img.write_bytes(_build_boot_img(b"K", b"R", magic=b"IOS"))

        with pytest.raises(BootImgError) as exc_info:
            carve_out_ramdisk(boot_img, out_path)

        assert str(exc_info.value) == "bad boot.img magic: b'IOS'"
        assert not out_path.exists()
        assert not out_path.with_suffix(out_path.suffix + ".tmp").exists()

    def test_raises_on_truncated_ramdisk(self, tmp_path: Path) -> None:
        boot_img = tmp_path / "boot.img"
        out_path = tmp_path / "ramdisk.bin"
        boot_img.write_bytes(_build_boot_img(b"K" * 100, b"R" * 20, declared_ramdisk_size=10000))

        with pytest.raises(BootImgError) as exc_info:
            carve_out_ramdisk(boot_img, out_path)

        assert str(exc_info.value) == (f"ramdisk in {boot_img} truncated: got 20 of 10000 bytes")
        assert not out_path.exists()
        assert not out_path.with_suffix(out_path.suffix + ".tmp").exists()


class TestExtractRamdisk:
    def test_raises_on_unrecognized_magic(self, tmp_path: Path) -> None:
        ramdisk = tmp_path / "ramdisk"
        ramdisk.write_bytes(b"GARBAGE!")
        out_dir = tmp_path / "out"
        runner = _RecordingRunner()

        with pytest.raises(BootImgError) as exc_info:
            asyncio.run(extract_ramdisk(ramdisk, out_dir, runner))  # pyright: ignore[reportArgumentType]

        assert str(exc_info.value) == (f"ramdisk {ramdisk} has unrecognized magic bytes: 474152424147")
        assert runner.calls == []
