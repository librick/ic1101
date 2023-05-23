# Extracting Recovery and Boot Images
How to pull recovery and boot partitions from your headunit.
This assumes that your headunit is rooted.  

## Pulling Recovery and Boot from MTD Partitions

First, use `dd` to image the raw `mtdblock<n>` devices:
- `dd if=/dev/block/mtdblock1 of=/sdcard/mtd1-recovery.img`
- `dd if=/dev/block/mtdblock2 of=/sdcard/mtd2-boot.img`

Copy these images to your workstation via `adb`, FTP, etc.  
See the [headunit adb docs](./adb.md) for more info on connecting to the headunit via ADB.

## Verifying the Contents of Recovery and Boot Images
The `mtd1-recovery.img` file should start with the magic string `ANDROID!`

`hexdump -C mtd1-recovery.img | head`
`hexdump -C mtd2-boot.img | head`

View more information with the `file` command, e.g.,
On my machine, `file mtd1-recovery.img` yields:
```
mtd1-recovery.img: Android bootimg, kernel (0x8000), ramdisk (0x11000000), page size: 2048, cmdline (androidboot.hardware=vcm30t30 androidboot.console=ttyS0 mtdparts=tegra-nor:2M@21504K(USP),8M@4864K(recovery),8M@13056K(boot),2M)
```
On my machine, `file mtd2-boot.img` yields:
```
mtd2-boot.img: Android bootimg, kernel (0x8000), ramdisk (0x11000000), page size: 2048, cmdline (androidboot.hardware=vcm30t30 androidboot.console=ttyS0 mtdparts=tegra-nor:2M@21504K(USP),8M@4864K(recovery),8M@13056K(boot),2M)
```
- `kernel (0x8000)` indicates that the kernel starts at address `0x8000`
- `ramdisk (0x11000000)` indicates that the ramdisk starts at address `0x11000000`

Note the `mtdparts` argument: `8M@4864K(recovery),8M@13056K(boot)`. This confirms that
- The Android recovery partition starts at NOR flash address 4864K
- The Android boot partition starts at NOR flash address 13056K

Both of these addresses are within the range (4800:0000, 4fff:ffff) listed as `NOR Flash` in the Tegra 3 SoC "System Memory Map" table.


## Recovery Ramdisk and Boot Ramdisk

**⚠️ Non-AOSP files (such as images and executables) from the boot and recovery ramdisks are the intellectual property of Honda Motor Co., Ltd. I do not condone the use of these images for commercial use.
I have included these images here for my personal use only as the owner of my car. ⚠️**

- *You can find the recovery ramdisk files in the mtd1-recovery-ramdisk directory of this repo.*
- *You can find the boot ramdisk files in the mtd2-boot-ramdisk directory of this repo.*

The boot partition and recovery partition follow the standard Android format.
I.e., they contain a kernel (zImage) and ramdisk (gzipped cpio archive)

### Extracting ramdisk from mtd1-recovery.img

1. I checked the structure of `mtd1-recovery.img` using `binwalk`:  
`binwalk mtd1-recovery.img`  
which yielded (in part):  
`5888000 0x59D800 gzip compressed data`  
2. I carved out the compressed ramdisk from `mtd1-recovery.img` using dd:  
`dd if=mtd1-recovery.img bs=5888000 skip=1 of=recovery-ramdisk.gz`  
3. I checked that resulting file was a gzip archive using `file`:  
`file recovery-ramdisk.gz`  
4. I extracted `recovery-ramdisk.gz` using `gunzip`:  
`gunzip -k recovery-ramdisk.gz`  
5. I confirmed that the resulting file was a cpio archive using `file`:  
`file recovery-ramdisk`  
6. I made a new directory to hold the extracted cpio archive:  
`mkdir out-recovery-ramdisk`  
7. I copied the cpio archive into the new directory:  
`cp recovery-ramdisk out-recovery-ramdisk/`  
8. I changed into the new directory:  
`cd out-recovery-ramdisk`  
9. I extracted the cpio archive:  
`cpio -i < recovery-ramdisk`  

### Extracting ramdisk from mtd2-boot.img
1. I checked the structure of `mtd2-boot.img` using `binwalk`:  
`binwalk mtd2-boot.img`  
which yielded (in part):  
`5888000 0x59D800 gzip compressed data`  
2. I carved out the compressed ramdisk from `mtd2-boot.img` using dd:  
`dd if=mtd2-boot.img bs=5888000 skip=1 of=boot-ramdisk.gz`  
3. I checked that resulting file was a gzip archive using `file`:  
`file boot-ramdisk.gz`  
4. I extracted `boot-ramdisk.gz` using `gunzip`:  
`gunzip -k boot-ramdisk.gz`  
5. I confirmed that the resulting file was a cpio archive using `file`:  
`file boot-ramdisk`  
6. I made a new directory to hold the extracted cpio archive:  
`mkdir out-boot-ramdisk`  
7. I copied the cpio archive into the new directory:  
`cp boot-ramdisk out-boot-ramdisk/`  
8. I changed into the new directory:  
`cd out-boot-ramdisk`  
9. I extracted the cpio archive:  
`cpio -i < recovery-ramdisk`  

## Appendix: Hardware
The boot ramdisk's `init.vcm30t30.rc` file provides some documentation of
hardware connected to the headunit and various sysfs interfaces to hardware devices
and kernel modules.

### Wi-Fi and Bluetooth (TI WiLink 8)
I know from looking at loaded kernel modules (dynamic analysis) that the headunit uses the TI WiLink 8 chip (wl18xx).
This is further evidenced by this section of the boot ramdisk's `init.vcm30t30.rc` file:
```
# Load WiFi driver
    insmod /system/lib/modules/compat/compat.ko
    insmod /system/lib/modules/compat/cfg80211.ko
    insmod /system/lib/modules/compat/mac80211.ko
    insmod /system/lib/modules/compat/wlcore.ko
    insmod /system/lib/modules/compat/wl18xx.ko
    insmod /system/lib/modules/compat/wlcore_sdio.ko
```

### Gyroscope (A3G4250D)
I know from looking at loaded kernel modules (dynamic analysis) that the headunit uses this MEMS motion sensor gyroscope chip:
[A3G4250D](https://www.st.com/resource/en/datasheet/a3g4250d.pdf). Cross-referencing this with the `init.vcm30t30.rc` provides good evidence that it's connected to the Tegra 3 SoC via SPI:
```
# chown Gyroscope driver sysfs
    chown system system /sys/devices/platform/spi_tegra.4/spi4.2/enable_device
    chown system system /sys/devices/platform/spi_tegra.4/spi4.2/pollrate_ms
    chown system system /sys/devices/platform/spi_tegra.4/spi4.2/pollrate_temp_ms
    chown system system /sys/devices/platform/spi_tegra.4/spi4.2/temp
```

### Ramdisks and GPIO
Honda developers provided a few comments in the ramdisk `init.rc` files describing various GPIO pins.
Given the lack of source code for binaries in `/sbin` (such as `earlyrvc`, the software interface for the reverse camera),
the comments in these `init.rc` files are relatively useful.

#### Recovery Ramdisk GPIO
The recovery ramdisk's `init.rc` file contains some documentation of GPIO pins:
```
write /sys/class/gpio/export 83
    write /sys/class/gpio/export 84
    write /sys/class/gpio/export 85
    write /sys/class/gpio/gpio83/direction "out"
    write /sys/class/gpio/gpio84/direction "out"
    write /sys/class/gpio/gpio85/direction "in"
    write /sys/class/gpio/gpio85/edge "falling"
    chown system system /sys/class/gpio/gpio83/value
    chown system system /sys/class/gpio/gpio84/value
    write /sys/class/gpio/gpio83/value "1"
    write /sys/class/gpio/gpio84/value "0"
…
# GPIO Setting for LVDS Serializer
    write /sys/class/gpio/export 130
    write /sys/class/gpio/export 131
    write /sys/class/gpio/export 134
    write /sys/class/gpio/export 135
    write /sys/class/gpio/export 156
    write /sys/class/gpio/export 159
    write /sys/class/gpio/export 176
    write /sys/class/gpio/export 177
    write /sys/class/gpio/gpio156/direction "in"
    write /sys/class/gpio/gpio159/direction "out"
    write /sys/class/gpio/gpio176/direction "out"
    write /sys/class/gpio/gpio177/direction "in"
    write /sys/class/gpio/gpio156/edge "falling"
    write /sys/class/gpio/gpio177/edge "falling"
```
#### Boot Ramdisk GPIO
The boot ramdisk's `init.rc` file contains some documentation of GPIO pins:
```
# GPIO Setting for LVDS Serializer
    write /sys/class/gpio/export 129
    write /sys/class/gpio/export 130
    write /sys/class/gpio/export 131
    write /sys/class/gpio/export 134
    write /sys/class/gpio/export 135
    write /sys/class/gpio/export 156
    write /sys/class/gpio/export 159
    write /sys/class/gpio/export 176
    write /sys/class/gpio/export 177
    write /sys/class/gpio/gpio156/direction "in"
    write /sys/class/gpio/gpio159/direction "out"
    write /sys/class/gpio/gpio176/direction "out"
    write /sys/class/gpio/gpio177/direction "in"
    write /sys/class/gpio/gpio156/edge "falling"
    write /sys/class/gpio/gpio177/edge "falling"

# Rear Wide Camera view mode setting
    write /sys/class/gpio/export 227
    write /sys/class/gpio/gpio227/direction out
    chown vehicle_rw vehicle_rw /sys/class/gpio/gpio227/value
    chown vehicle_rw vehicle_rw /sys/class/gpio/gpio227/direction
    chmod 0664 /sys/class/gpio/gpio227/value
    chmod 0664 /sys/class/gpio/gpio227/direction
    write /sys/class/gpio/export 228
    write /sys/class/gpio/gpio228/direction out
    chown vehicle_rw vehicle_rw /sys/class/gpio/gpio228/value
    chown vehicle_rw vehicle_rw /sys/class/gpio/gpio228/direction
    chmod 0664 /sys/class/gpio/gpio228/value
    chmod 0664 /sys/class/gpio/gpio228/direction

## for ReverseGPIO begin
    write /sys/class/gpio/export 205
    write /sys/class/gpio/gpio205/direction in
    write /sys/class/gpio/gpio205/edge both
    chmod 0664 /sys/class/gpio/gpio205/value
    chown vehicle_rw vehicle_rw /sys/class/gpio/gpio205/value
## for ReverseGPIO end
```

## Appendix: PPP Files
The headunit does something sketchy with point-to-point protocol (PPP).
At the time of writing I'm not sure what. It also uses Bluetooth BR/EDR RFCOMM to establish some sort of tunnel
for HondaLink. The boot ramdisk's `init.vcm30t30.rc` file has a few lines related to PPP that might be of interest:
```
# initialize PPP files
service init_ppp_files /vendor/bin/init_ppp_files.sh
    user root
    group root
    oneshot
    disabled
```



## Appendix: ADB
I rooted my headunit, so some of the adb-specific settings in this repo may not be stock.
PRs are welcome. I'm curious to have more data points as to what is and isn't part of the stock ramdisk(s).
In other words, the following lines from the recovery ramdisk's `init.rc` file may not be accurate:
```
# Always start adbd on userdebug and eng builds
on property:ro.debuggable=1
    write /sys/class/android_usb/android0/enable 1
    start adbd

# Restart adbd so it can run as root
on property:service.adb.root=1
    write /sys/class/android_usb/android0/enable 0
    restart adbd
    write /sys/class/android_usb/android0/enable 1
```

## Appendix: Binwalk Output

Result of `binwalk mtd1-recovery.img`:
```
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
0             0x0             Android bootimg, kernel size: 5885564 bytes, kernel addr: 0x8000, ramdisk size: 1294570 bytes, ramdisk addr: 0x11000000, product name: ""
5169855       0x4EE2BF        Unix path: /var/lib/jenkins/workspace/18-1
5217958       0x4F9EA6        Unix path: /var/lib/jenkins/workspace/18-1
5888000       0x59D800        gzip compressed data, from Unix, last modified: 1970-01-01 00:00:00 (null date)
```

Result of `binwalk mtd2-boot.img`:
```
DECIMAL       HEXADECIMAL     DESCRIPTION
--------------------------------------------------------------------------------
0             0x0             Android bootimg, kernel size: 5885564 bytes, kernel addr: 0x8000, ramdisk size: 536339 bytes, ramdisk addr: 0x11000000, product name: ""
5169855       0x4EE2BF        Unix path: /var/lib/jenkins/workspace/18-1
5217958       0x4F9EA6        Unix path: /var/lib/jenkins/workspace/18-1
5888000       0x59D800        gzip compressed data, from Unix, last modified: 1970-01-01 00:00:00 (null date)
```
