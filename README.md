# Honda Civic Reverse Engineering

Tools and documentation for reverse engineering 10th generation
Honda Civic infotainment systems (headunits).

This covers most Honda Civics from 2016-2021, inclusive. Lower-end trims such as the 2021 Civic LX are not supported as they use completely different headunits.

## Technical Overview

- Infotainment SoC: NVIDIA Tegra 3, c. 2012
- SoC Arch: Quad-core ARM Cortex-A9 (ARM v7)
- Infotainment OS: Android 4.2.2 (Jellybean), released Oct. 29, 2012
- Infotainment OS Framework: Mitsubishi-developed framework, codenamed "Andromeda"

## Documentation

Docs are provided as Markdown files in https://github.com/librick/ic1101/tree/main/docs. Contributions and PRs are welcome.

## Tools

This repo is a monorepo and contains several top-level subdirectories that contain tools for working with Honda Civic software and update files.

### [aidl-rebuilder](https://github.com/librick/ic1101/tree/main/aidl-rebuilder)

Given files extracted from an official update file, aidl-rebuilder parses the low-level smali code to generate an authoritative list of Android Interface Definition Language (AIDL) interfaces. These interfaces are a key part to how Mitsubishi-authored Android apps and services communicate with each other.

### [apk-rebuilder](https://github.com/librick/ic1101/tree/main/apk-rebuilder)

Given an official update file, apk-rebuilder extracts it and does numerous post-processing steps to create an output directory that contains every relevant precursor for subsequent reverse engineering work, such as .smali code, repacked APK files, and extracted ramdisk files. If you're looking to explore headunit apps, start here.

### [apk-renderer](https://github.com/librick/ic1101/tree/main/apk-renderer)

This is a hacky vibe-coded attempt at rendering headunit app layouts without additional tools. Useful for understanding how Mitsubishi forked the AOSP framework and theming. Largely a failed experiment, this code is kept for posterity.

### [ota-builder](https://github.com/librick/ic1101/tree/main/ota-builder)

Given an overlay directory (among other inputs), ota-builder builds Android update files that mimic authentic Honda USB updates. The resulting files can be put on a USB drive that, when inserted into the headunit, cause it to reboot to recovery and apply the update. Because Honda allows update files to be signed with a widely-known AOSP test key, this allows for arbitrary code execution on the headunit.

## Repo Name

The Mitsubishi headunit UI is codenamed "Andromeda". According to [Wikipedia](https://en.wikipedia.org/wiki/IC_1101), IC 1101 is the largest known galaxy in the universe. I.e., bigger than Andromeda.

![June 1995 image of IC 1101 taken by the Hubble Space Telescope](./ic1101.jpg)

## Media Coverage

This project is covered in the following sources:

- [Hacker News](https://news.ycombinator.com/item?id=36052753)
- [Juniperspring - Honda Civic Reverse Engineering](https://juniperspring.org/posts/honda-reverse-engineering/)
- [Hackaday - Honda Headunit Reverse Engineering, And The Dismal State Of Infotainment Systems](https://hackaday.com/2023/06/27/honda-headunit-reverse-engineering-and-the-dismal-state-of-infotainment-systems/)

## Contributors and Thanks

Thanks to [@Tunas1337](https://github.com/Tunas1337) for all his help and late-night hacking sessions.
Much of this work is his in one form or another, particularly as it relates to more esoteric (but useful) knowledge of Android internals. Thanks :)

## License

Original work in this repository is released under the MIT License; see [LICENSE](LICENSE).

Portions derive from or bundle code from the Android Open Source Project (for example
the AOSP test key, `signapk.jar`, and `update-binary`), licensed under the Apache
License 2.0; see [Android licenses](https://source.android.com/docs/setup/about/licenses)
and the bundled license texts under `LICENSES/`. Any code or data belonging to Honda
Motor Co., Ltd. or Mitsubishi Electric Corporation remains the proprietary property of
its respective owner and is not relicensed here.

## Legal Notice

> [!WARNING]
>
> Any code or instructions in this repository are inherently experimental and are
> used entirely at your own risk. The authors accept no responsibility and no
> liability for any resulting damage, including damaged vehicles, hard-bricked or
> soft-bricked headunits, and headunits left stuck in recovery or boot loops.
> This repository documents the authors' own research, with no guarantee that
> anything here will work or is safe for your hardware.
>
> The authors of this repository and its contents are not affiliated with,
> endorsed by, or sponsored by Honda Motor Co., Ltd. or Mitsubishi Electric.
> Honda, Honda Civic, and all other names are trademarks of their respective owners.
> Provided for personal and educational use only; the authors do not condone
> software piracy or copyright infringement.
