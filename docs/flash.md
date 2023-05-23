# Flash Storage
- The infotainment unit uses a Micron 8GB eMMC flash chip for storage
- Its CID is R1J55A, confirmed via the sysfs interface
- The chip's datasheet is available on IPFS; eMMC-R1J55A-3151144.pdf
- The flash is available via the sysfs interface at `/sys/class/mmc_host/mmc0/mmc:0001`
- For the eMMC standard itself, see: JESD84-B51.pdf
- It is exposed via sysfs at `/sys/class/mmc_host/mmc0/`

## Boot and Recovery
The `/system` and `/system/vendor` partitions are stored on the flash.  
The flash is accessible as a block device at `/dev/block/mmcblk0p<n>`, where `n` is a partition number.  
`mmcblk0boot0` and `mmcblk0boot1` refer to the boot and recovery partitions respectively.
**The boot and recovery partitions are not stored on the flash; they're stored on the Soc!**

If you try to create images of the boot and/or recovery partitions with `dd` via their block devices, you'll get 8MB 
files of all zeros:
- `dd if=/dev/block/mmcblk0boot0 of=/sdcard/mmcblk0boot0-backup.img`
- `dd if=/dev/block/mmcblk0boot1 of=/sdcard/mmcblk0boot1-backup.img`
- `hexdump -C mmcblk0boot0-backup.img` // all zeros, 8388608 bytes
- `hexdump -C mmcblk0boot1-backup.img` // all zeros, 8388608 bytes

Within the NVIDIA Tegra 3 Technical Reference Manual, find the "2.0 ADDRESS AND INTERRUPT MAP" section.  
"Table 1. System Memory Map" includes the following row:  
`NOR Flash  4800:0000   4fff:ffff   128 MB`

While attempting to back up the boot and recovery partitions, I found the following quote from a book on embedded Linux.
See: https://www.oreilly.com/library/view/mastering-embedded-linux/9781787283282/64271306-bd52-47d8-8118-6b618630d307.xhtml
>The mtdblock driver is little used. Its purpose is to present flash memory as a block device you can use to format and mount as a filesystem. However, it has severe limitations because it does not handle bad blocks in NAND flash, it does not do wear leveling, and it does not handle the mismatch in size between filesystem blocks and flash erase blocks. In other words, it does not have a flash translation layer, which is essential for reliable file storage. The only case where the mtdblock device is useful is to mount read-only file systems such as Squashfs on top of reliable flash memory such as NOR.

So it seems as though `/dev/block/mmcblk0boot0` and `/dev/block/mmcblk0boot1` are just some kind of emulated/virtual devices. The only way I was able to get non-zero boot and recovery images was by running:
- `dd if=/dev/block/mtdblock1 of=/sdcard/mtd1-recovery.img`
- `dd if=/dev/block/mtdblock2 of=/sdcard/mtd2-boot.img`

Both resulting images are 8MB in length.  
I've included a table of all `/proc/mtd` devices in this document.  

Running `file mtd1-recovery.img` yields:  
`mtd1-recovery.img: Android bootimg, kernel (0x8000), ramdisk (0x11000000), page size: 2048, cmdline (androidboot.hardware=vcm30t30 androidboot.console=ttyS0 mtdparts=tegra-nor:2M@21504K(USP),8M@4864K(recovery),8M@13056K(boot),2M)`

Running `file mtd2-boot.img` yields:  
`mtd2-boot.img: Android bootimg, kernel (0x8000), ramdisk (0x11000000), page size: 2048, cmdline (androidboot.hardware=vcm30t30 androidboot.console=ttyS0 mtdparts=tegra-nor:2M@21504K(USP),8M@4864K(recovery),8M@13056K(boot),2M)`  

## Tables and stdout

Table of `/dev/block` devices, their corresponding sysfs names, and mount points:
|`/dev/block/<device>`|Sysfs Name|Directory|
|-|-|-|
|mmcblk0boot0|||
|mmcblk0boot1|||
|mmcblk0p1 |CAC|/cache|
|mmcblk0p2 |CAP|/system/vendor|
|mmcblk0p3 |APP|/system|
|mmcblk0p4 |LOG|/log|
|mmcblk0p5|MITSU|/data/MitsubishiElectric|
|mmcblk0p6 |SDA|/mnt/data1|
|mmcblk0p7|SDA2|/mnt/data2|
|mmcblk0p8|SDC|/mnt/media|
|mmcblk0p9|UDA|/data|


`ls -la /dev/block/platform/sdhci-tegra.3`:
```
drwxr-xr-x root root 1969-12-31 16:00 by-name
drwxr-xr-x root root 1969-12-31 16:00 by-num
lrwxrwxrwx root root 1969-12-31 16:00 mmcblk0 -> /dev/block/mmcblk0
lrwxrwxrwx root root 1969-12-31 16:00 mmcblk0boot0 -> /dev/block/mmcblk0boot0
lrwxrwxrwx root root 1969-12-31 16:00 mmcblk0boot1 -> /dev/block/mmcblk0boot1
lrwxrwxrwx root root 1969-12-31 16:00 mmcblk0p1 -> /dev/block/mmcblk0p1
lrwxrwxrwx root root 1969-12-31 16:00 mmcblk0p2 -> **/dev/**block/mmcblk0p2
lrwxrwxrwx root root 1969-12-31 16:00 mmcblk0p3 -> /dev/block/mmcblk0p3
lrwxrwxrwx root root 1969-12-31 16:00 mmcblk0p4 -> /dev/block/mmcblk0p4
lrwxrwxrwx root root 1969-12-31 16:00 mmcblk0p5 -> /dev/block/mmcblk0p5
lrwxrwxrwx root root 1969-12-31 16:00 mmcblk0p6 -> /dev/block/mmcblk0p6
lrwxrwxrwx root root 1969-12-31 16:00 mmcblk0p7 -> /dev/block/mmcblk0p7
lrwxrwxrwx root root 1969-12-31 16:00 mmcblk0p8 -> /dev/block/mmcblk0p8
lrwxrwxrwx root root 1969-12-31 16:00 mmcblk0p9 -> /dev/block/mmcblk0p9
```

`ls -la /dev/block/platform/sdhci-tegra.3/by-name/`:
```
lrwxrwxrwx root root 1969-12-31 16:00 APP -> /dev/block/mmcblk0p3
lrwxrwxrwx root root 1969-12-31 16:00 CAC -> /dev/block/mmcblk0p1
lrwxrwxrwx root root 1969-12-31 16:00 CAP -> /dev/block/mmcblk0p2
lrwxrwxrwx root root 1969-12-31 16:00 LOG -> /dev/block/mmcblk0p4
lrwxrwxrwx root root 1969-12-31 16:00 MITSU -> /dev/block/mmcblk0p5
lrwxrwxrwx root root 1969-12-31 16:00 SDA -> /dev/block/mmcblk0p6
lrwxrwxrwx root root 1969-12-31 16:00 SDA2 -> /dev/block/mmcblk0p7
lrwxrwxrwx root root 1969-12-31 16:00 SDC -> /dev/block/mmcblk0p8
lrwxrwxrwx root root 1969-12-31 16:00 UDA -> /dev/block/mmcblk0p9
```

`cat /proc/partitions`:
```
major minor  #blocks  name
31        0       2048 mtdblock0
31        1       8192 mtdblock1
31        2       8192 mtdblock2
31        3       2048 mtdblock3
31        4        256 mtdblock4
31        5       2048 mtdblock5
31        6       3072 mtdblock6
31        7      65536 mtdblock7
253        0     307200 zram0
179        0    7512064 mmcblk0
179        1    1048576 mmcblk0p1
179        2     786432 mmcblk0p2
179        3     524288 mmcblk0p3
179        4     131072 mmcblk0p4
179        5    1048576 mmcblk0p5
179        6     131072 mmcblk0p6
179        7     131072 mmcblk0p7
259        0    1048576 mmcblk0p8
259        1    2490368 mmcblk0p9
179       16       8192 mmcblk0boot1
179        8       8192 mmcblk0boot0
```

`cat /proc/mtd`:
```
dev:    size   erasesize  name
mtd0: 00200000 00020000 "USP"
mtd1: 00800000 00020000 "recovery"
mtd2: 00800000 00020000 "boot"
mtd3: 00200000 00020000 "app_datas"
mtd4: 00040000 00020000 "app_datas_ex"
mtd5: 00200000 00020000 "misc"
mtd6: 00300000 00020000 "kpanic"
mtd7: 04000000 00020000 "whole_device"
```

`busybox fdisk -l /dev/block/mmcblk0`
```
Disk /dev/block/mmcblk0: 7336 MB, 7692353536 bytes, 15024128 sectors
931 cylinders, 256 heads, 63 sectors/track
Units: cylinders of 16128 * 512 = 8257536 bytes
Device Boot StartCHS EndCHS StartLBA EndLBA Sectors Size Id Type
/dev/block/mmcblk0p1 0,0,2 1023,255,63 1 14712831 14712831 7183M ee EFI GPT
Partition 1 has different physical/logical end:
phys=(1023,255,63) logical=(912,65,1)
```

`df`, formatted as a table.  
Some information is redacted for privacy.
Where there are redactions, it's clearly noted.

|Filesystem|Size|Used|Free|Blksize|
|-|-|-|-|-|
|/dev|480M|REDACTED|REDACTED|4096|
/mnt/secure|480M|0K|480M|4096|
/mnt/asec|480M|0K|480M|4096|
/mnt/obb|480M|0K|480M|4096|
/dev/veshm|480M|REDACTED|REDACTED|4096|
/system|503M|REDACTED|REDACTED|4096|
/cache|1007M|REDACTED|REDACTED|4096|
/data|2G|REDACTED|REDACTED|4096|
/system/vendor|755M|REDACTED|REDACTED|4096|
/log|125M|REDACTED|REDACTED|4096|
/mnt/data1|125M|REDACTED|REDACTED|4096|
/mnt/data2|125M|REDACTED|REDACTED|4096|
/mnt/media|1007M|REDACTED|REDACTED|4096|
/data/MitsubishiElectric|1007M|REDACTED|REDACTED|4096|
/mnt/shell/emulated|1007M|REDACTED|REDACTED|4096|
