import shutil
import zipfile
from pathlib import Path

from file_utils import check_dir_exists, check_file_exists


def _extract_flat(zip_path: Path, dest_dir: Path) -> None:
    """Extract a zip file, ignoring a top-level directory and putting contents directly into dest_dir."""
    with zipfile.ZipFile(zip_path, "r") as zf:
        all_names = [info.filename for info in zf.infolist() if info.filename.strip()]
        tops = {name.split("/", 1)[0] for name in all_names if "/" in name}
        root = tops.pop() if len(tops) == 1 else None

        for info in zf.infolist():
            orig = info.filename
            if not orig or orig.endswith("/"):
                continue

            rel_path = Path(orig)
            if root and rel_path.parts[0] == root:
                rel_path = Path(*rel_path.parts[1:])

            target = dest_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)

            with zf.open(info) as src, target.open("wb") as dst:
                shutil.copyfileobj(src, dst)


def unzip_outer_zip(zip_path: Path, dest_dir: Path, update_id: str) -> Path:
    """Extract the user-provided update .zip and return the path to the SwUpdate.mdt file inside.

    `update_id` names the directory inside the archive that holds the SwUpdate.mdt file;
    this value changes across update images.
    """
    _extract_flat(zip_path, dest_dir=dest_dir)

    path_sw_update = dest_dir / "SwUpdate2.txt"
    path_update_id = dest_dir / update_id
    path_sw_update_mdt = path_update_id / "SwUpdate.mdt"

    check_file_exists(path_sw_update)
    check_dir_exists(path_update_id)
    check_file_exists(path_sw_update_mdt)

    return path_sw_update_mdt


def unzip_mdt_zip(zip_path: Path, dest_dir: Path) -> None:
    _extract_flat(zip_path, dest_dir=dest_dir)

    check_dir_exists(dest_dir / "system")
    check_dir_exists(dest_dir / "system" / "app")
    check_dir_exists(dest_dir / "system" / "framework")
    check_dir_exists(dest_dir / "system" / "lib")
    check_dir_exists(dest_dir / "system" / "vendor")

    check_dir_exists(dest_dir / "system" / "vendor" / "app")
    check_dir_exists(dest_dir / "system" / "vendor" / "framework")
    check_dir_exists(dest_dir / "system" / "vendor" / "lib")
