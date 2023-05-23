# earlyrvc
Available within the recovery image at `/sbin/earlyrvc`.  
The `earlyrvc` binary handles the reverse/backup camera at an early stage in the Android boot process.  
Running `file earlyrvc` yields:  
`earlyrvc: ELF 32-bit LSB executable, ARM, EABI5 version 1 (SYSV), statically linked, stripped`

I was working on creating an open source replacement, but abandoned the effort to pursue other priorities. In particular I was frustrated by a lack of NVIDIA documentation for Tegra 3 code, including ioctl calls. I can drive this car at 60mph on a freeway, but I can't read the (either non-public or non-existant) NVIDIA documentation to know how it works.

Although the binary is stripped, decompiling with Ghidra proved fruitful.
The decompiled output still contains debug logging, giving function names and hints as to their arguments.
My initial effort suggests that `earlyrvc` is basically a state machine; it reads/writes to/from Android system properties and reads/writes to/from GPIO pins via a (deprecated) sysfs interface.

- `gpio205` has direction `in`.
- `gpio205` is 0 when the car is in park
- `gpio205` is 1 when the car is in reverse
- `gpio227` and `gpio228` have the direction `out`
- `gpio227` and `gpio228` control field of view and camera rotation

Enumerating sysfs references:  
`strings earlyrvc | grep /sys/`:  
```
/sys/class/gpio/gpio205/value
/sys/devices/tegradc.0/winz_mode
/sys/class/gpio/gpio227/value
/sys/class/gpio/gpio228/value
/sys/devices/virtual/misc/nvmap/heap-camera/usage
/sys/bus/nvhost/devices/host1x/syncpt/%d/max
/sys/module/fuse/parameters/tegra_chip_id
/sys/module/fuse/parameters/tegra_chip_rev
/sys/devices/system/cpu
```

## GPIO References
Enumerating gpio references:  
`strings earlyrvc | grep gpio`:
```
/sys/class/gpio/gpio205/value
/sys/class/gpio/gpio227/value
/sys/class/gpio/gpio228/value
```

## Android System Properties
Enumerating (some) Android system property references:  
`strings earlyrvc | grep -e ^ro -e ^earlyrvc\. -e ^persist\. -e ^cameraapservice\. | sort`  
```
cameraapservice.er
earlyrvc.camappstatus
earlyrvc.er
earlyrvc.previewstatus
earlyrvc.previewtype
earlyrvc.sf
persist.sys.
persist.tegra.
persist.tegra.un_premult_alpha
ro.da.camera_mode
ro.da.car_model
ro.da.car_model
ro.da.cd_slot
ro.da.clr.rgb_d
ro.da.clr.rgb_n
ro.da.clr.yuv_d
ro.da.clr.yuv_n
ro.da.disp
ro.da.disp
ro.da.fmvss111
ro.da.ill
ro.da.ill
ro.da.mvc_connect
ro.da.reboot
ro.da.vol_knob
```

## Syscalls
I've found the following ioctl calls. The below table is neither exhaustive nor authoritative; most of the names of these calls are from comments/log messages left in the compiled binary, and were found using static analysis.
Feel free to perform dynamic analysis of the `earlyrvc` binary and provide more thorough documentation in a PR.  
|Hex ID|File Descriptor Source|Name|
|-|-|-|
|0x401c440a|/dev/tegra_dc_0|TEGRA_DC_EXT_SET_LUT|
|0x40144408|/dev/tegra_dc_0|TEGRA_DC_EXT_SET_CSC|
|0x4e04|?|NVMEM_IOC_FREE|
0xc0084e0d|?|NVMEM_IOC_GET_ID|
0xc00c4e0a|?|NVMEM_IOC_PIN_MULT|
0x400c4e0b|?|NVMEM_IOC_UNPIN_MULT|
0x401c4e07|?|NVMEM_IOC_READ|
0x401c4e06|?|NVMEM_IOC_WRITE|
0xc00c4e08|?|NVMEM_IOC_PARAM|
