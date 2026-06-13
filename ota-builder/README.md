# Honda Civic OTA Builder

Builds custom OTA files for 10th generation Honda Civic vehicles.

## Quickstart

```bash
uv run src/main.py --overlay-dir examples/empty 
```

## Usage

- Place your files in `input/overlay/`, mimicking the structure of an Android 4.2.2rc1 filesystem.
- Run `uv run src/main.py`
- A file tree will be written to `output/<basicisotimestamp>/`.
- Format a USB drive as FAT-32 and ensure that it is empty
- Copy the *contents* of `output/<basicisotimestamp>/` to the root of the USB drive, NOT including the actual `output/<basicisotimestamp>/` directory itself
- Move to your car, buckle up, and put the car into accessory mode
- Make sure your car is in park with the headunit on
- Plug the USB drive into the front USB port; it *has* to be the front port, the port inside center console will NOT work
- If you see an update screen/popup appear, ignore it
- Press and hold the power button in the car, tap "Reboot" when prompted
- Wait for the car to reboot; it should enter recovery and start applying the update
- You should see the progress bar move to 100%; once it does, wait a few seconds, then unplug the USB drive
- ONLY unplug the USB drive a few seconds AFTER the progress bar reaches 100%; doing so before or after could corrupt your headunit

> [!WARNING] The headunit's recovery is a vendor-provided fork of the AOSP 4.2.2rc1 recovery.
> It does NOT render ui_print calls in updater-scripts to the screen,
> so it's impossible to user's step-by-step progress of updates.
> We use the progress bar as an indicator, paired with an ARMv7 sleep binary that waits for 30 seconds
> after the progress bar hits 100% before ending the update.
> If you disconnect the USB drive before the 30 second sleep window starts (before the progress bar shows 100%),
> you could corrupt your headunit's filesystem.
> If you don't disconnect the USB drive during the 30 second sleep window (when the progress bar shows 100%),
> then, because of the way we manipulate version checks,
> the headunit will boot normally, detect a valid update file, and reboot to recovery again, starting the update again.
> If this happens, just wait until the next 30 second sleep window (when the progress bar shows 100%),
> and pull the USB drive then.

## Permissions and ownership

To override permissions and ownership per file, create a file at `input/overlay-meta.txt` where each line is of the form `path uid gid mode`, where `path` represents the file whose ownership and/or permissions you want to modify, relative to the `input/overlay/` directory, and `mode` is octal (e.g. `0644`). This is optional. If a file in the `input/overlay/` directory does not have a corresponding entry in `input/overlay-meta.txt`, that file will be included in the generated updater-script with default UID of `0`, GID of `0`, and octal mode of `0644`.

## File locations

This code supports a subset of the full partition layout. Placing files in `input/overlay/` that fall outside these directories will cause the build to fail.

| Block Device                                    | Path             | Format |
| ----------------------------------------------- | ---------------- | ------ |
| `/dev/block/platform/sdhci-tegra.3/by-name/APP` | `/system`        | ext4   |
| `/dev/block/platform/sdhci-tegra.3/by-name/CAP` | `/system/vendor` | ext4   |

## updater-script

This code ships a `META-INF/com/google/android/updater-script` inside generated SwUpdate.mdt files.
It gets executed by a companion binary, `update-binary`.
Our `updater-script` targets Android 4.2.2, which supports full verbose edify script syntax.
It is highly encouraged to review the contents of SwUpdate.mdt and the generated `updater-script`
before attempting to install it on the headunit.

## Limitations

This tool exists to build simple OTA update files that mount a limited subset of partitions and copy files to the headunit. It does NOT support automatically generating and packaging arbitrary updater-scripts (e.g., that leverage calls like `format`, `symlink`, `run_program`).

## Developer guide

Run tests with `uv run pytest -v`

## Keys

The key at `input/keys/testkey.pk8` is Google's AOSP test key.
The signed production car firmware is signed with the public AOSP test key. Have fun :)

```bash
openssl x509 -in input/keys/testkey.x509.pem -noout -subject -fingerprint -sha256
#subject=C=US, ST=California, L=Mountain View, O=Android, OU=Android, CN=Android, emailAddress=android@android.com
# sha256 Fingerprint=A4:0D:A8:0A:59:D1:70:CA:A9:50:CF:15:C1:8C:45:4D:47:A3:9B:26:98:9D:8B:64:0E:CD:74:5B:A7:1B:F5:DC
```

## Preparing USB Drive (Linux)

The AOSP recovery binary needs to be able to find the flash drive.
The drive needs to be formatted as FAT32, and it also needs a proper partition table.
Using a filesystem written directly to the raw device (a "superfloppy") is not supported.

```bash
# Find the USB drive
lsblk -o NAME,SIZE,MODEL,TRAN
# Create a partition table (assumes your drive is /dev/sda, check against lsblk output!)
sudo parted -s /dev/sda mklabel msdos
sudo parted -s /dev/sda mkpart primary fat32 1MiB 100%
sudo parted -s /dev/sda set 1 lba on
# Create the FAT32 partition
sudo mkfs.vfat -F 32 /dev/sda1
```
