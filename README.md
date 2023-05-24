# Honda Civic Reverse Engineering
An open research project into my 2021 Honda Civic infotainment system

**Assuming you have root access on your headunit, I highly recommend enabling adb *and* switching the USB port(s) to device mode. See docs/adb.md for more info. Do this before doing anything else, it may save you from bricking your device.**

## Legal Notice
⚠️ I'm not affiliated with Honda Motor Co., Ltd. I'm not affiliated with Mitsubishi. Honda and Honda Civic are registered trademarks. This is for personal use only. I can't condone software piracy. ⚠️

I take no responsibility for bricked/damaged cars, headunits, etc.  
This is to document my own research only.
I will not be held liable if you break your car.

All information in this repo *should* already be in the public domain or otherwise be publicly discoverable. I've intentionally avoided directly including `.apk`/`.odex` files or other "confidential"/proprietary information.

## Technical Overview
Infotainment SoC: NVIDIA Tegra 3, c. 2012  
Infotainment OS: Android 4.2.2 (Jellybean), released Oct. 29, 2012  
Infotainment OS Framwork: Mitsubishi-developed framework, codenamed "Andromeda"  
CAN buses: B-CAN and F-CAN

## eMMC and Flash
- There are three `mmc<n>` devices under `/sys/class/mmc_host`:
    - `mmc0`
    - `mmc1`
    - `mmc2`
- `cat /sys/class/mmc_host/mmc0/mmc0:0001/name` gives the string `R1J55A`
- The eMMC interface is used for **flash storage** and for **Wi-Fi and Bluetooth**

### Flash Storage
- The infotainment unit uses a Micron 8GB eMMC flash chip for storage
- Its CID is R1J55A, confirmed via the sysfs interface
- The flash is available via the sysfs interface at `/sys/class/mmc_host/mmc0/mmc:0001`
- It is exposed via sysfs at `/sys/class/mmc_host/mmc0/`

I haven't validated that the ordering of `mmc_host` devices within sysfs is constant.  
Check the `name` property/file:  
`cat /sys/class/mmc_host/mmc0/mmc0:0001/name`.  
On my system it returns `R1J55A`, the CID of the flash chip.

### Wi-Fi and Bluetooth
- Wi-Fi and Bluetooth are provided by a shared TI WiLink 8 chip
- The TI WiLink 8 chip is connected via eMMC (similar to a Raspberry Pi)
- It uses the `wl18xx` kernel module
- It is exposed via sysfs at `/sys/class/mmc_host/mmc1/`

## SPI
- The A3G4250D chip is connected via SPI
- The product page for A3G4250D describes it as a
>3-axis digital gyroscope for automotive telematics, navigation applications, AEC-Q100 qualified ...
>The A3G4250D is a low-power 3-axis angular rate sensor able to provide unprecedented stability at zero rate level and sensitivity over temperature and time. It includes a sensing element and an IC interface capable of providing the measured angular rate to the external world through a standard SPI digital interface. An I2C-compatible interface is also available.
- `a3g4250d_temp` is registered as an input at `/devices/platform/spi_tegra.4/spi4.2/input/input2`

## GPIO
- The infotainment unit makes use of several GPIO pins
- Many apks and native libraries hard-code specific GPIO numbers
- They can be accessed and enumerated via a (deprecated) sysfs interface: `/sys/class/gpio`
- The `earlyrvc` reverse camera uses `gpio205`, `gpio227` and `gpio228`
- `gpio205` is an input; it was observed to have the value `0` when the car is in park, `1` when the car is in reverse
- There are also inputs under `/sys/devices/platform/gpio-keys/`, in which GPIO keys are mapped as keyboard inputs

## What's with the repo name?
The Mitsubishi headunit UI appears to be codenamed "Andromeda".  
In an attempt to avoid takedown requests, I wanted to avoid using a trademarked name for the name of this project/repo. According to [this Wikipedia article](https://en.wikipedia.org/wiki/IC_1101), IC 1101 is the largest known galaxy in the universe. I.e., bigger than Andromeda. So I named this project "IC 1101".

![June 1995 image of IC 1101 taken by the Hubble Space Telescope](./ic1101.jpg)

## Glossary
The source code contains a lot of acronyms. I've documented some here.

- ERC - Early Reverse Camera
    - This refers to the application/process that runs early in the Android boot process
    - You can find it at `/sbin/earlyrvc` in the recovery image
- RVC - Reverse Camera
- HFL - Hands Free Link
- LVDS - Low Voltage Differential Signalling
    - This is used in the context of an LVDS serializer
    - I think this is what the infotainment system uses to interface with CAN

## Hacker News
I originally published this project on Hacker News.
The resulting discussion may be useful:  
https://news.ycombinator.com/item?id=36052753

## Contributors and Thanks
Thanks to [@Tunas1337](https://github.com/Tunas1337) for all his help and late-night hacking sessions.
Much of this work is his in one form or another, particularly as it relates to more esoteric (but useful) knowledge of Android internals. Thanks :)
