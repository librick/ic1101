# Honda Civic Reverse Engineering
An open research project into 10th generation Honda Civic infotainment systems.
This covers most Honda Civics from 2016-2021, inclusive. Lower-end trims such as the 2021 Civic LX are not supported as they use a different headunit.

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

## Rooting 
See: https://github.com/librick/ic1101/blob/main/docs/rooting.md  
**Assuming you have root access on your headunit, I highly recommend enabling adb *and* switching the USB port(s) to device mode. See docs/adb.md for more info. Do this before doing anything else, it may save you from bricking your device.**

## Explaining the Repo Name, IC 1101
The Mitsubishi headunit UI is codenamed "Andromeda". I wanted to avoid using a trademarked name for the name of this project/repo. According to [this Wikipedia article](https://en.wikipedia.org/wiki/IC_1101), IC 1101 is the largest known galaxy in the universe. I.e., bigger than Andromeda. So I named this project "IC 1101".

![June 1995 image of IC 1101 taken by the Hubble Space Telescope](./ic1101.jpg)

## Hacker News, Blog Post
I originally published this project on [Hacker News](https://news.ycombinator.com/item?id=36052753).
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

## Miscellaneous Research and Resources
- [Honda Civic CAN Bus Reverse Engineering](https://ashfaqahmad.ca/honda-civic-can-bus-reverse-engineering/)
- [GitHub, jersacct - 2016 Honda Pilot One-Click Root](https://github.com/jersacct/2016PilotOneClick)
- [greenluigi1, Hyundai Ioniq Hacking, Part 5](https://programmingwithstyle.com/posts/howihackedmycarpart5/)
- [greenluigi1, Hyundai Ioniq Hacking, Part 6](https://programmingwithstyle.com/posts/myhackedcarisdoomed/)
