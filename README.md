# Honda Civic Reverse Engineering
An open research project into my 2021 Honda Civic infotainment system

## Getting Started
Documentation is provided as Markdown files in the `docs` directory.
Headunit files are provided in the `headunit-files` directory.
My goal is to keep project organization simple and let complexity develop naturally.
Contributions and PRs are welcome.
Use [GitHub discussions](https://github.com/librick/ic1101/discussions) for correspondance; this repo is your repo.

## Technical Overview
Infotainment SoC: NVIDIA Tegra 3, c. 2012  
SoC Arch: Quad-core ARM Cortex-A9 (ARM v7)
Infotainment OS: Android 4.2.2 (Jellybean), released Oct. 29, 2012  
Infotainment OS Framework: Mitsubishi-developed framework, codenamed "Andromeda"  
CAN buses: B-CAN and F-CAN

## Rooting your Honda Headunit
See: https://github.com/librick/ic1101/blob/main/docs/rooting.md  
**Assuming you have root access on your headunit, I highly recommend enabling adb *and* switching the USB port(s) to device mode. See docs/adb.md for more info. Do this before doing anything else, it may save you from bricking your device.**

## Explaining the Repo Name, IC 1101
The Mitsubishi headunit UI is codenamed "Andromeda".  
In an attempt to avoid takedown requests, I wanted to avoid using a trademarked name for the name of this project/repo. According to [this Wikipedia article](https://en.wikipedia.org/wiki/IC_1101), IC 1101 is the largest known galaxy in the universe. I.e., bigger than Andromeda. So I named this project "IC 1101".

![June 1995 image of IC 1101 taken by the Hubble Space Telescope](./ic1101.jpg)

## Project Goals and Thoughts for the Future
Here are few areas where I'd like to see public collaboration, contributions, and pull requests:
- **Boot and recovery images from different Honda Civic models and trims**
    - It would be beneficial to diff boot/recovery images across different vehicle trims
    - I'm particularly interested in `system/build.prop` and `system/vendor/build.prop` files
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

## Hacker News, Blog Post
I originally published this project on Hacker News.
The resulting discussion may be useful:  
https://news.ycombinator.com/item?id=36052753  
I also cover this project on my blog, [juniperspring.xyz](https://juniperspring.xyz/posts/honda-reverse-engineering/).

## Legal Notice
⚠️ I'm not affiliated with Honda Motor Co., Ltd. I'm not affiliated with Mitsubishi. Honda and Honda Civic are registered trademarks. This is for personal use only. I can't condone software piracy. ⚠️

I take no responsibility for bricked/damaged cars, headunits, etc.  
This is to document my own research only.
I will not be held liable if you break your car.

All information in this repo *should* already be in the public domain or otherwise be publicly discoverable. I've intentionally avoided directly including `.apk`/`.odex` files or other "confidential"/proprietary information.

## License
This project is MIT licensed.
Where this project includes code from Android and/or the AOSP, refer to [Android licenses](https://source.android.com/docs/setup/about/licenses). Where this project references code belonging to Mitsubishi Motors Corporation and/or Honda Motor Co., Ltd., it is understood that such code is proprietary and is the intellectual property of their respective owners. Any original research specific to this project is MIT licensed.

## Contributors and Thanks
Thanks to [@Tunas1337](https://github.com/Tunas1337) for all his help and late-night hacking sessions.
Much of this work is his in one form or another, particularly as it relates to more esoteric (but useful) knowledge of Android internals. Thanks :)

## Miscellaneous Articles and Resources
- [Radio Station Snafu in Seattle Bricks Some Mazda Infotainment Systems](https://arstechnica.com/cars/2022/02/radio-station-snafu-in-seattle-bricks-some-mazda-infotainment-systems/)
- [Flash Memory Wear Killing Older Teslas](https://www.tomshardware.com/news/flash-memory-wear-killing-older-teslas-due-to-excessive-data-logging-report)
- [TikTok Trend Helps Thieves Hack Kia, Hyundai Models](https://www.bloomberg.com/news/newsletters/2023-01-11/tiktok-trend-helps-thieves-hack-kia-hyundai-models)
- [Hyundai, Kia Patch Bug Allowing Car Thefts with a USB Cable](https://www.bleepingcomputer.com/news/security/hyundai-kia-patch-bug-allowing-car-thefts-with-a-usb-cable/)
- [Honda Hack Can Unlock and Start Your Car](https://www.tomsguide.com/news/honda-hack-can-unlock-and-start-your-car-what-you-need-to-know)
- [1.7 Million Hondas Are Being Investigated for Phantom Breaking](https://arstechnica.com/cars/2022/02/nhtsa-to-investigate-honda-accords-and-cr-vs-over-phantom-braking/)
- [Honda Civic CAN Bus Reverse Engineering](https://ashfaqahmad.ca/honda-civic-can-bus-reverse-engineering/)
- [GitHub, jersacct - 2016 Honda Pilot One-Click Root](https://github.com/jersacct/2016PilotOneClick)
- [greenluigi1, Hyundai Ioniq Hacking, Part 5](https://programmingwithstyle.com/posts/howihackedmycarpart5/)
- [greenluigi1, Hyundai Ioniq Hacking, Part 6](https://programmingwithstyle.com/posts/myhackedcarisdoomed/)
