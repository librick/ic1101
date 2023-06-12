# daupdater

## Overview
The daupdater binary can be found in the boot ramdisk at `/sbin/daupdater`.
It appears to be responsible for parsing update files from USB flash drives, applying them, and rebooting the headunit to recovery mode, at which point it is presumed that updates are installed.

## USB Updates
For an update file to be applied, the flash drive must contain at least two files: a SwUpdate2.txt (or SwUpdate.txt) text file and a SwUpdate.mdt zip archive. The SwUpdate.mdt zip archive must contain `system/build.prop` and `/system/vendor/build.prop` files.

The daupdater binary parses the `system/build.prop` file and reads its `ro.build.id` property. The daupdater binary also parses the `system/vendor/build.prop` file and reads its `custom_rom.type` property. In order for the update to be applied, the values of these properties (as parsed from the SwUpdate.mdt zip archive) must match the values of these properties as found on the headunit.

## Ghidra Static Analysis
Static analysis was performed using Ghidra.

### Logic
Looks for a SwUpdate.txt or SwUpdate2.txt file on the root of a USB flash drive.
The following possible paths are hard-coded:
- "/sys/devices/platform/tegra-ehci.0/usb3/3-1"
- "/sys/devices/platform/tegra-ehci.1/usb1/1-1"
- "/sys/devices/platform/tegra-ehci.2/usb2/2-1"

The USB device must have a USB class of LIBUSB_CLASS_MASS_STORAGE.
The USB block device is expected at /dev/block/sda1.
/dev/block/sda1 gets mounted to /mnt/usbdrive1 as vfat.

SwUpdate2.txt is given priority over SwUpdate.txt.
If /mnt/usbdrive1/SwUpdate2.txt exists,
we run getNewCommandVersion("/mnt/usbdrive1/SwUpdate2.txt").
Else if /mnt/usbdrive1/SwUpdate.txt exists,
we run getNewCommandVersion("/mnt/usbdrive1/SwUpdate.txt").

Then the following functions are run:
- getCurrentDaVersion()
- getCurrentCustomRomType()
- getCurrentCommandVersion()

`getCurrentDaVersion()`
- mounts /dev/block/platform/sdhci-tegra.3/by-name/APP to /system as ext4
- opens /system/build.prop for reading
- parses the line beginning with "ro.build.id=".

`getCurrentCustomRomType()`
- mounts /dev/block/platform/sdhci-tegra.3/by-name/CAP to /system/vendor as ext4
- opens /system/vendor/build.prop for reading
- parses the line beginning with "custom_rom.type=".

`getCurrentCommandVersion()`
- parses a custom /cache/.copy_complete file

Next, the following functions are run:
- getNewDaVersion()
- getNewCustomRomType()
- makeUpdateCommand()

`getNewDaVersion()`
- attempts to parse a SwUpdate.mdt file as a zip archive.
- extracts system/build.prop to /dev/log/build.prop
- opens /dev/log/build.prop for reading
- parses the line beginning with "ro.build.id="

`getNewCustomRomType()`
- attempts to parse a SwUpdate.mdt file as a zip archive.
- extracts system/vendor/build.prop to /dev/log/build.prop
- opens /dev/log/build.prop for reading
- parses the line beginning with "custom_rom.type="

`makeUpdateCommand()` generates a string depending on which EHCI device was used,
where `%s` is some templated string:
- /dev/block/platform/tegra-ehci.0/sda1
    - --update_package=/mnt/usbdrive1/SwUpdate.mdt
    - --update_package=/mnt/usbdrive1/%s/SwUpdate.mdt
- /dev/block/platform/tegra-ehci.1/sda1
    - --update_package=/mnt/usbdrive2/SwUpdate.mdt
    - --update_package=/mnt/usbdrive2/%s/SwUpdate.mdt
- /dev/block/platform/tegra-ehci.2/sda1
    - --update_package=/mnt/usbdrive1/SwUpdate.mdt
    - --update_package=/mnt/usbdrive1/%s/SwUpdate.mdt

It's worth emphasizing that both `tegra-ehci.2` and `tegra-ehci.0` map to `/mnt/usbdrive1`. I would expect `tegra-ehci.2` to map to `/mnt/usbdrive3`.

An update is able to be applied when all of the following hold:
- currentCustomRomType matches newCustomRomType
- currentDaVersion matches newDaVersion

Assuming this is true, a function named `write_recovery_cmd_file()` is called.
- it mounts /dev/block/platform/sdhci-tegra.3/by-name/CAC /cache ext4 0x20
- ensures the directory /cache/recovery exists
- opens /cache/recovery/command for writing
- writes something to that file, presumably the result of `makeUpdateCommand()`

Finally, we call a function called `startupseq_task_main()`, which talks to some sort of cpu_com library, then reboots into recovery:
- cpu_com_send_request_exit_control(0x73);
- cpu_com_send_notify_tegra_reboot(1);
- …
- FUN_000102cc(0xdead0003,0,"recovery");

### Sources, Libraries, Headers
I worked under the assumption that compiled code was built against the [4.2.2 R1 AOSP release](https://android.googlesource.com/platform/bionic/+/refs/tags/android-4.2.2_r1). Additionally, it appears that the `daupdater` binary was built against [minzip](https://android.googlesource.com/platform/bootable/recovery.git/+/android-4.2.2_r1/minzip) and [libusb](https://android.googlesource.com/platform/external/libusb/+/refs/tags/android-4.2.2_r1/libusb/).
