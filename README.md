# Honda Civic Reverse Engineering
An open research project into my 2021 Honda Civic infotainment system

## Project Goals and Thoughts for the Future
Since first sharing this project, I've gotten some great feedback and wanted to document some areas where PRs would be most welcome.
Here are few areas where I'd like to see public collaboration, contributions, and pull requests. Feel free to start a fork:
- **Boot and recovery images from different Honda Civic models and trims**
    - Having access to these would make it easier to develop public-interest exploits, upgrade Android, and boot different Android ROMs or operating systems
- **Open source versions of native/compiled binaries and libraries**
    - These would provide documentation to other developers and lower the barrier to entry for writing Honda-specific code
    - This would make it easier for third-parties to design replacement parts such as backup cameras, making replacement parts cheaper
    - This would make upgrading/flashing newer versions of Android easier, as propriertary binaries are used in the headunit update process
    - See `/sbin/earlyrvc` in the boot/recovery ramdisks
    - See `/sbin/daupdater` in the boot ramdisk
- **Open source exploit chains to root headunits**
    - This would allow anyone to root their headunit for free
    - By being open source, these exploit chains/rooting tools would safer and more widely audited than paid third-party rooting services
    - This would also encourage research into specific exisiting headunit vulnerabilities, creating opportunities to patch them
- **Open-access documentation of CAN IDs and packet formats**
    - Honda vehicles have two CAN networks, F-CAN and B-CAN. They implement some standard CAN messages but otherwise gatekeep proprietary CAN message formats
    - Having publicly-available docs on known CAN messages would make comprehensive diagnostic tools cheaper for third-party mechanics
    - Having cheaper diagnostic tools would make repairs cheaper for consumers
    - Having open-access diagnostics would empower consumers to make educated decisions when taking their vehicles in for repair
- **Support for vehicles beyond the Honda Civic**
    - I started with the Honda Civic because I have it on hand, but the same or similar software is used for several Honda lines
    - There's no reason this project can't encompass cars beyond the Honda Civic

**Assuming you have root access on your headunit, I highly recommend enabling adb *and* switching the USB port(s) to device mode. See docs/adb.md for more info. Do this before doing anything else, it may save you from bricking your device.**

## Legal Notice
⚠️ I'm not affiliated with Honda Motor Co., Ltd. I'm not affiliated with Mitsubishi. Honda and Honda Civic are registered trademarks. This is for personal use only. I can't condone software piracy. ⚠️

I take no responsibility for bricked/damaged cars, headunits, etc.  
This is to document my own research only.
I will not be held liable if you break your car.

All information in this repo *should* already be in the public domain or otherwise be publicly discoverable. I've intentionally avoided directly including `.apk`/`.odex` files or other "confidential"/proprietary information.

## Rooting your Honda Headunit
See: https://github.com/librick/ic1101/blob/main/docs/rooting.md

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
    - LVDS is commonly used for high-speed video, graphics, and video camera data transfers
    - It's possible that LVDS is used for the headunit display and/or backup camera; more research is needed to confirm this

## Hacker News
I originally published this project on Hacker News.
The resulting discussion may be useful:  
https://news.ycombinator.com/item?id=36052753

## Blog Post
In addition to the content here, I've also covered this project on my blog, [juniperspring.xyz](https://juniperspring.xyz/posts/honda-reverse-engineering/).

## News Articles (Why we need open source vehicle software)
- [Radio Station Snafu in Seattle Bricks Some Mazda Infotainment Systems](https://arstechnica.com/cars/2022/02/radio-station-snafu-in-seattle-bricks-some-mazda-infotainment-systems/)
- [Flash Memory Wear Killing Older Teslas](https://www.tomshardware.com/news/flash-memory-wear-killing-older-teslas-due-to-excessive-data-logging-report)
- [TikTok Trend Helps Thieves Hack Kia, Hyundai Models](https://www.bloomberg.com/news/newsletters/2023-01-11/tiktok-trend-helps-thieves-hack-kia-hyundai-models)
- [Hyundai, Kia Patch Bug Allowing Car Thefts with a USB Cable](https://www.bleepingcomputer.com/news/security/hyundai-kia-patch-bug-allowing-car-thefts-with-a-usb-cable/)
- [Honda Hack Can Unlock and Start Your Car](https://www.tomsguide.com/news/honda-hack-can-unlock-and-start-your-car-what-you-need-to-know)
- [1.7 Million Hondas Are Being Investigated for Phantom Breaking](https://arstechnica.com/cars/2022/02/nhtsa-to-investigate-honda-accords-and-cr-vs-over-phantom-braking/)


## Hackaday Article on Hyundai Ionic
I found an interesting article on Hackaday on the Hyundai Ioniq’s infotainment system, including it here for reference:
https://hackaday.com/2023/06/08/hacking-a-hyundai-ioniqs-infotainment-system-again-after-security-fixes/

## Contributors and Thanks
Thanks to [@Tunas1337](https://github.com/Tunas1337) for all his help and late-night hacking sessions.
Much of this work is his in one form or another, particularly as it relates to more esoteric (but useful) knowledge of Android internals. Thanks :)

## License
This project is MIT licensed.
Where this project includes code from Android and/or the AOSP, refer to [Android licenses](https://source.android.com/docs/setup/about/licenses). Where this project references code belonging to Mitsubishi Motors Corporation and/or Honda Motor Co., Ltd., it is understood that such code is proprietary and is the intellectual property of their respective owners. Any original research specific to this project is MIT licensed.
