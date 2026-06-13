# Display Audio Update Files

Honda allows flashing arbitrary updates from USB flash drives as long as they pass a few format checks.
While updates must be signed by a valid signature, the headunit accepts the default, publicly-known AOSP test keys.

This means that, if the headunit has power and an attacker has access to the front-most USB port,
they can achieve arbitrary code execution on the headunit.

The following document provides an overview of the main moving parts.
We've since taken these checks and created a tool, [ota-builder](https://github.com/librick/ic1101/tree/main/ota-builder),
that allows anyone to generate an update file.

> [!CAUTION]
>
> It is trivial to enter a recovery loop and softbrick your headunit if you attempt to
> deploy your own update file, because Honda devs did not provide an easy way to exit recovery
> in the event that the recovery environment rejects a staged update.
> Read this entire document and make sure you understand the process before attempting
> to deploy any updates.
> This is generally an unsafe way to write files to the headunit.
> It can be used to root the headunit (by deploying a setuid su binary),
> but beyond that if you want to modify headunit files,
> just use adb. It's safer and faster.

> [!CAUTION]
>
> The ability to achieve arbitrary code execution on headunits,
> as well as the ability to avoid recovery loops (softbricks)
> is highly dependent on whether your specific headunit ships with the Android test key.
> While we've observed this to be true in two separate places (our headunit and in a published Honda update file),
> it's possible that this was an oversight that only affects a subset of shipped headunits.

## Known Versions, Display Audio Software

| Make  | Model | Year | Trim            | DA Version  | Tags           | ROM Type |
| ----- | ----- | ---- | --------------- | ----------- | -------------- | -------- |
| Honda | Civic | 2021 | EX Hatchback 4D | `1.F1A5.15` | `release-keys` | `1115`   |

> [!NOTE]
>
> Don't see your car in this table? One of the highest-value PRs you can make is to
> add yours.

You don't have to modify your headunit to get these values. You just need to connect
to the headunit using ADB and pull down the required files:

```bash
# DA Version
adb shell getprop ro.build.id
# Tags
adb shell getprop ro.build.tags
# ROM Type
adb shell cat /system/vendor/build.prop | grep custom_rom.type
```

## Overview

There are three distinct parts of the headunit code that process Android updates:

- `daupdater`: A binary that scans for an update on every boot and conditionally reboots to recovery
- `recovery`: The AOSP recovery binary itself, with Honda-specific additions
- `SystemUpdate`/`SystemUpdateApService`: An app-based update service, largely out of scope for this doc

## `daupdater`

The `daupdater` binary lives at `/sbin/daupdater` and is part of the recovery partition. It is similar to binaries found in `/system/vendor/bin` (e.g., similar compile flags and logging macros).

It almost certainly stands for "Display Audio Updater", as Honda refers to the headunit as the "Display Audio". See: https://web.archive.org/web/20260613044721/https://www.hondainfocenter.com/2021/Civic-Sedan/Feature-Guide/Interior-Features/Display-Audio-with-HondaLink-plus-Apple-CarPlay-and-Android-Auto/

It's responsible for scanning for `SwUpdate.txt`/`SwUpdate2.txt` files on USB storage media and then reading the corresponding `SwUpdate.mdt` update zip archive. If a number of conditions are met, it stages a recovery command and reboots the headunit into recovery mode, sending messages to the system controller ("syscon") to notify others.

### How `daupdater` starts on boot

The `daupdater` binary runs every time the headunit does a full boot. This is handled by an init service, which is then started by a vendor fork of `libsurfaceflinger.so`.

#### init service

A `daupdater` service is defined within the ramdisk. `init.rc` contains the line `import /init.${ro.hardware}.rc`. We've observed that this resolves to `import init.vcm30t30.rc`, set from the kernel command line (`androidboot.hardware=vcm30t30`).

The `init.vcm30t30.rc` file contains the following service definition (the full file is excluded for copyright reasons):

```
# Tegra force update process
service daupdater /sbin/daupdater
    class main
    user root
    group root
    oneshot
    disabled
```

The service is `disabled` by default. So init does not start it automatically. Instead, it's started explicitly by name, as part of `libsurfaceflinger.so`.

#### `libsurfaceflinger.so`

The Android boot process starts the compositor, SurfaceFlinger, loading the library `/system/lib/libsurfaceflinger.so`.
This library is modified by Honda. When the `startBootAnim` function is invoked, rather than the stock AOSP logic,
the code calls `property_set("ctl.start", "daupdater")`. This causes init to start the `daupdater` service, which causes the `daupdater` binary to execute.

The call graph within `libsurfaceflinger.so` looks like:

```
Android starts the compositor, SurfaceFlinger
  -> SurfaceFlinger::readyToRun()  (Thread hook, once per boot)
    -> SurfaceFlinger::startBootAnim()
      -> property_set("ctl.start", "daupdater")
```

### High-level control flow of `daupdater`

The following is a high-level control flow of `daupdater`:

- `main`:
  - checks that one of the sysfs paths exists:
    - `/sys/devices/platform/tegra-ehci.0/usb3/3-1`
    - `/sys/devices/platform/tegra-ehci.1/usb1/1-1`
    - `/sys/devices/platform/tegra-ehci.2/usb2/2-1`
  - opens each device's `bInterfaceClass` and requires the USB mass-storage class
  - checks that `/dev/block/sda1` exists
    - try/rewait/try; up to 15 attempts with a 1s sleep between each
  - mount-ownership check:
    - if `/mnt/usbdrive1/SwUpdate.txt` or `/mnt/usbdrive1/SwUpdate2.txt` is already present, the drive was mounted by something else; record this
      - daupdater only updates from a drive it mounted itself; a pre-mounted drive becomes a no-op later
    - otherwise, mount `/dev/block/sda1` (vfat) at `/mnt/usbdrive1`
  - selects the update path (in order, exclusive):
    - `/mnt/usbdrive1/SwUpdate2.txt` present:
      - sets `new_cmd = getNewCommandVersion("/mnt/usbdrive1/SwUpdate2.txt")`
        - reads the version string from the `Ver:` line
      - sets `have_swupdate2`; the newer, more flexible path
    - else `/mnt/usbdrive1/SwUpdate.txt` present:
      - sets `new_cmd = getNewCommandVersion("/mnt/usbdrive1/SwUpdate.txt")`
        - reads the version string from the `Ver:` line
      - sets `have_swupdate`; the older, less flexible path
  - reads installed-system state:
    - `cur_da = getCurrentDaVersion()`; from `/system/build.prop` `ro.build.id=`
    - `cur_rom = getCurrentCustomRomType()`; from `/system/vendor/build.prop` `custom_rom.type=`
    - `cur_cmd = getCurrentCommandVersion()`; from the single-line `/cache/.copy_complete`
  - calls `isCopyCompleteRemovable(new_cmd, cur_cmd)`:
    - if the `/cache/.copy_complete` version differs from the trigger-file version, deletes `/cache/.copy_complete`; otherwise a no-op
    - poorly named; it is a boolean check and a file deletion, not just a check
  - reads package state and builds the command (for either path):
    - `new_da = getNewDaVersion(pkg)`; parses the package zip's `system/build.prop` `ro.build.id=`
      - `pkg` is `/mnt/usbdrive1/<rom_type>/SwUpdate.mdt` for `have_swupdate2`, else `/mnt/usbdrive1/SwUpdate.mdt`
    - `new_rom = getNewCustomRomType(pkg)`; parses the package zip's `system/vendor/build.prop` `custom_rom.type=`
    - `cmd = makeUpdateCommand(cur_rom)` for `have_swupdate2`, or `makeUpdateCommand(0)` for `have_swupdate`:
      - probes the drive paths:
        - `/dev/block/platform/tegra-ehci.0/sda1` (maps to usbdrive1)
        - `/dev/block/platform/tegra-ehci.1/sda1` (maps to usbdrive2)
        - `/dev/block/platform/tegra-ehci.2/sda1` (maps to usbdrive1)
      - returns one of:
        - `--update_package=/mnt/usbdrive1/<rom_type>/SwUpdate.mdt` (have_swupdate2)
        - `--update_package=/mnt/usbdrive2/<rom_type>/SwUpdate.mdt` (have_swupdate2)
        - `--update_package=/mnt/usbdrive1/SwUpdate.mdt` (have_swupdate)
        - `--update_package=/mnt/usbdrive2/SwUpdate.mdt` (have_swupdate)
  - gating checks that must all pass before `cmd` is written:
    - the drive must have been mounted by daupdater itself, not pre-mounted
    - if `getNewDaVersion` returned 0, bail
    - if `getNewCustomRomType` returned 0, bail
    - if `makeUpdateCommand` returned 0, bail
    - `isUpdatableCustomRom` must return 0 (it returns `strcmp(cur_rom, new_rom)`):
      - host and package `custom_rom.type=` must match
    - `isUpdatable` must return non-zero:
      - host and package `ro.build.id=` must NOT match
    - note the asymmetry: rom type must match, DA version must differ
  - if we bail for any reason:
    - `__system_property_set("ctl.start", "inlinediag")`; no command staged, no reboot
  - if all is well:
    - `write_recovery_cmd_file(cmd)`:
      - mounts `CAC` (`/dev/block/platform/sdhci-tegra.3/by-name/CAC`, ext4) at `/cache`
      - ensures `/cache/recovery` exists at mode 0755
      - writes `cmd` to `/cache/recovery/command`, then sets it mode 0777
      - this is the handover to Android recovery
    - if daupdater mounted `/mnt/usbdrive1`, unmount it
      - `/mnt/usbdrive2` is never unmounted, assuming it exists
    - `write_version_file(cur_da, new_da)`:
      - `cur_da` and `new_da` are guaranteed unequal here
      - writes `<cur_da><new_da>` to `/cache/recovery/version` (where each ends in a newline)
        - this is later consumed by `recovery`'s `ShowVersionInfo` function
    - `startupseq_task_main()`:
      - notifies syscon of the pending reboot
      - calls `request_reboot_recovery()`, which calls `__reboot(0xdead0003, 0, "recovery")`
  - end of `main`

### `daupdater` checklist

Now that we have an (imperative) control flow, we can establish a (declarative) checklist.

Our goal is to convince `daupdater` to stage an update file and reboot into recovery for us. We use the more flexible update format, SwUpdate2, to support multiple custom ROM types.

This means we need the following:

- A USB 2.0 flash drive
- The USB flash drive connected to the port nearest the steering wheel in the 10th gen Honda Civic
  - This is either `tegra-ehci.0` or `tegra-ehci.2` on the host; either map to `usbdrive1`
  - Do NOT use the USB port located inside the center console
- The USB flash drive containing an MSDOS partition table and a single vfat partition
  - this is subtle; do NOT use a superblock (i.e., do not use vfat without a partition table)
  - if you use a superblock, the partition might enumerate as, e.g., `sda`, rather than `sda1`
- A `SwUpdate2.txt` file at the root of the USB drive
  - the file should use LF-style line endings, NOT CRLF
  - it must contain a line beginning with `Ver:` followed by a version string
    - parsed by `getNewCommandVersion`; the value itself is not gated, but the line must be present
    - it only feeds `isCopyCompleteRemovable`, which at most deletes `/cache/.copy_complete` on mismatch
  - no `SwUpdate.txt` is needed; `SwUpdate2.txt` is checked first and the two paths are exclusive
- The update package placed at `<rom_type>/SwUpdate.mdt` on the drive, NOT at the root
  - `<rom_type>` is a directory named exactly after the host's current `custom_rom.type` value (from `/system/vendor/build.prop` on the headunit)
  - the `have_swupdate2` path is built as `/mnt/usbdrive1/<rom_type>/SwUpdate.mdt` using the host's `cur_rom`
- `SwUpdate.mdt` is a zip archive, signed with a valid key
  - signature verification in `really_install_package` is vanilla AOSP 4.2.2
  - the archive must contain `system/build.prop` with a `ro.build.id=` line
    - parsed by `getNewDaVersion`; must be non-empty or `daupdater` bails
  - the archive must contain `system/vendor/build.prop` with a `custom_rom.type=` line
    - parsed by `getNewCustomRomType`; must be non-empty or `daupdater` bails
- The package's `custom_rom.type=` value must MATCH the host's `custom_rom.type=` value
  - `isUpdatableCustomRom` returns `strcmp(cur_rom, new_rom)`; staging requires it to return 0
  - in practice this value coincides three ways: the `<rom_type>` directory name, the host's vendor `build.prop`, and the package's vendor `build.prop`
- The package's `ro.build.id=` value must DIFFER from the host's `ro.build.id=` value
  - `isUpdatable` stages only when the two are not equal; an identical build id is refused as already installed
- Reboot the headunit to run `daupdater`
  - hold the physical power/volume button until the reboot dialog appears, then reboot
  - on the next boot, `daupdater` detects the drive, validates against the above, stages the command to `/cache/recovery/command`, then reboots itself into recovery via `startupseq_task_main` -> `request_reboot_recovery`
  - recovery applies the signed package on that boot

> [!CAUTION]
> This is the biggest footgun of the entire update process and can softbrick your headunit if you're not careful.
>
> Even if you craft an update that gets staged to recovery by `daupdater`,
> the `recovery` binary itself contains Honda-specific checks that can prevent the update from being applied.
> This can result in a recovery loop, because recovery sees that an update is staged,
> but fails while attempting to apply it, and does not clear the staged recovery command.
> On every subsequent boot, the headunit boots back into recovery.
> In this state, disconnecting the battery or pulling fuses won't save you,
> because the recovery command is written to non-volatile flash storage.
> Unplugging the USB drive doesn't exit the recovery loop,
> because the recovery command still exists, even if it points to a non-existent USB path.
>
> We were not initially aware of the `release-keys` check,
> which is only enforced by the Honda-modified `recovery` binary and not `daupdater`,
> and thus soft-bricked our headunit because we were unable to exit recovery.
> Fortunately we discovered the `release-keys` check and were able to connect a properly-structured USB drive,
> at which point recovery applied the update.
> But it underscores how dangerous/hacky the recovery process can be.

### `daupdater` version checks

> [!WARNING]
>
> Never ship an update that clobbers your headunit's files
> just to pass a `daupdater` check.
> Your update file should never contain an updater-script that installs
> files to system paths such as `/system/build.prop`

`daupdater` checks the `ro.build.id=` line in `system/build.prop` inside the `SwUpdate.mdt` file.
But AOSP update files also include an `updater-script` file that says exactly which files to install.

Fortunately for us, `daupdater` requires `SwUpdate.mdt` to contain this `system/build.prop` file,
but it does NOT verify that the `system/build.prop` file is actually installed to the host system.
This allows us to pass `daupdater` version checks (and thus stage updates) without ever actually
changing the version on the headunit. If you're trying to install these files as part of your update,
you're doing something horribly wrong and you WILL brick your headunit.

### `daupdater` and syscon

Before rebooting to recovery, `daupdater` makes a best-effort attempt to notify the rest of the system.

The relevant function looks something like this:

```
request_reboot_recovery:
    - calls cpu_com_send_request_exit_control(0x73)
    - calls cpu_com_send_notify_tegra_reboot(1)
    - calls send_syscon_control_message(state, 5)
        where state is a buffer containing "ASTLH" + NUL
    - calls __reboot(0xdead0003, 0, "recovery")
```

Where the `cpu_com_*` functions use FIFOs to talk to the outside world.

## `recovery`

The `recovery` binary in the recovery partition is likely based on AOSP's 4.2.2rc1 recovery code,
with Honda-specific modifications. Crucially, key verification is unchanged from stock
(updates are checked against authorized keys in `res/keys`). But Honda added additional checks
that occur prior to signature verification. Many of these mirror the checks enforced by `daupdater`,
but a few are unique to `recovery`.

> [!WARNING]
>
> If you don't understand how `recovery` works and rely only on
> `daupdater` validation, it's possible to hit a recovery loop and softbrick your device.
> Read this document fully and quadruple-check any update files
> before attempting to install an update via USB.
> Otherwise, `daupdater` might stage an update command that recovery refuses to apply,
> but that leaves the headunit stuck in recovery mode.

For brevity (and because it's largely stock AOSP code with Honda-specific changes) we omit a high-level control flow for the `recovery` binary.
However, we can note a few things:

- It adds a check that, if the headunit's tags are `release-keys`, the update must also set them (see checklist)
- It adds a check that, if a `gpt.img` file is at the root of the `SwUpdate.mdt` archive, it starts a flow to repartition the headunit
  - A `tmp/gpt.img` file toggles install-in-place, root `gpt.img` triggers repartition
- Actual signature verification (`verify_file()`) is unchanged from stock recovery

### `recovery` checklist

For our purposes, the `recovery` checklist contains everything from the `daupdater` checklist, with a few additions:

- The `SwUpdate.mdt`'s `system/build.prop` file must contain a `ro.build.tags=release-keys` line
  (technically, this is only enforced when the headunit's own tags are `release-keys`, which appears to be set for production units)
- The `SwUpdate.mdt` file must have a valid signature (stock `verify_file` against keys parsed from `/res/keys`)
- Do NOT include a `gpt.img` file at the root of the `SwUpdate.mdt` archive; this could lead to the headunit being repartitioned
  (technically this path is only reachable by v1 SwUpdate files but we include it here out of an abundance of caution)

### No ui_print in `recovery`

The vendor-forked `recovery` parses `ui_print` (in `really_install_package`) and dispatches to `ui->Print`,
but the vendor UI's `Print` is not rendered on screen. So if you include `ui_print` lines in updater-scripts,
they won't render while installing updates.

## `res/keys`

The recovery ramdisk contains the following `res/keys` file:

```
v2 {64,0x39366003,{800109909,3149852210,3237241190,758845730,3522235199,2315776204,406826398,2735624793,4025224939,296740523,1747317641,3982259836,461174917,2832253739,2928855991,3243154644,3795484575,401221240,2680832073,2234209347,2828621631,374364081,2829025117,3937233335,2270280490,3092596323,1795302967,214212866,3105605320,4026511126,312670124,3314468655,1700087755,2061432718,880148720,1925019211,2822493758,2776470189,4293326558,1802931975,3839625133,2350652342,3696857393,1043704347,4047004960,433987583,1213792208,3348137349,546269034,3979521195,1162407693,630745697,2949103981,3436349770,1525397076,2315297093,417125063,1364487768,2624944811,3349546374,3077289349,2632384655,4179545975,3133800370},{2429267880,3725033341,946943671,640614920,3969004475,1785872238,2530099955,433167889,3080564407,4245343576,3811351695,788290081,2903643060,1238252046,1564713505,3129405819,3076072368,388000934,2761241615,2046211587,4093571719,3467418602,1236522598,3979074052,843395166,2476418472,3696349172,2973947349,4135870562,4279024757,625003739,619730293,2113229769,3130965850,3714638002,1455003831,3552358256,1352094352,3862239389,1912854043,2538328126,272192946,1706278844,1826282426,113355197,984261737,3498970030,284576252,2934968426,1318389565,3901939221,4217963752,848549552,982744462,444199867,2997910013,2377161855,1290116747,2295767421,3523944465,950436007,3818645939,3321373877,1074563579}},
{64,0xc926ad21,{1795090719,2141396315,950055447,2581568430,4268923165,1920809988,546586521,3498997798,1776797858,3740060814,1805317999,1429410244,129622599,1422441418,1783893377,1222374759,2563319927,323993566,28517732,609753416,1826472888,215237850,4261642700,4049082591,3228462402,774857746,154822455,2497198897,2758199418,3019015328,2794777644,87251430,2534927978,120774784,571297800,3695899472,2479925187,3811625450,3401832990,2394869647,3267246207,950095497,555058928,414729973,1136544882,3044590084,465547824,4058146728,2731796054,1689838846,3890756939,1048029507,895090649,247140249,178744550,3547885223,3165179243,109881576,3944604415,1044303212,3772373029,2985150306,3737520932,3599964420},{3437017481,3784475129,2800224972,3086222688,251333580,2131931323,512774938,325948880,2657486437,2102694287,3820568226,792812816,1026422502,2053275343,2800889200,3113586810,165549746,4273519969,4065247892,1902789247,772932719,3941848426,3652744109,216871947,3164400649,1942378755,3996765851,1055777370,964047799,629391717,2232744317,3910558992,191868569,2758883837,3682816752,2997714732,2702529250,3570700455,3776873832,3924067546,3555689545,2758825434,1323144535,61311905,1997411085,376844204,213777604,4077323584,9135381,1625809335,2804742137,2952293945,1117190829,4237312782,1825108855,3013147971,1111251351,2568837572,1684324211,2520978805,367251975,810756730,2353784344,1175080310}}
```

These are RSA public keys, where each key is of the format:
`[v2 ]{ <len> , 0x<n0inv> , { <n0> , <n1> , ... , <n63> } , { <rr0> , ... , <rr63> } }`
Where:

- `len`: is the number of 32-bit words in the modulus; must be 64 (i.e., a 2048-bit key)
- `n0inv`: precomputed Montgomery constant, `-1/n[0] mod 2^32`
- `n[0..63]`: the RSA modulus as 64 decimal unsigned words, little-endian word order (`n[0]` is the least-significant)
- `rr[0..63]`: `R^2 mod n` with `R = 2^2048`, the other precomputed Montgomery constant, 64 decimal words
- `exponent`: not stored in the file; a bare `{` implies `e=3`, a `v2 {` implies `e = 65537`

The `e=3` key is a stock AOSP public key.
The ONLY cryptographic check in the headunit's main Android update process is `verify_file` in the `recovery` binary,
but verification is done using the stock AOSP test key that is widely publicly available.

**Given a well-crafted set of update files on a properly-formatted USB drive, anyone can achieve arbitrary code execution on 10th generation Honda Civic headunits.**

## Appendix: Boot loops with a valid update

We intentionally craft update files that don't change (or worse, ratchet) version numbers on the headunit itself.

But this leads to the following loop:

- A valid USB drive is connected
- The headunit boots normally
- `daupdater` executes
- `daupdater` sees a valid update file on the connected USB drive
- `daupdater` stages the update and reboots to recovery
- `recovery` applies the staged update command, then starts a normal boot
- And back to the start...

The only way to stop the loop is to either:

- Choose actual version numbers and persist them as part of the update
  - Don't actually do this, bad idea
- Disconnect the USB drive *after* recovery applies the update, but *before* daupdater can scan for it again
  - The "better" way, as long as you unplug it at the right time
  - But if you unplug it at the wrong time, you could corrupt flash and brick the headunit

The best solution we've found is to:

- Use `daupdater` rather than `SystemUpdate`, because the former has less strict version checks
- Craft `SwUpdate.mdt` to present files with crafted versions *without* actually installing those files to the headunit
- Use a `sleep` binary to force a 30 second delay at the end of the update script
- Use crafted `set_progress` calls in `updater-script` to show 100% only when we're about to sleep
- Tell users to disconnect the USB drive a few seconds after the progress bar reaches 100%

## Appendix: Finding references to `daupdater` across the filesystem

A grep (using ripgrep for speed) across all headunit files for the string "daupdater" shows three paths.
These are exactly:

- The `daupdater` binary itself
- The `daupdater` init service entry
- The `libsurfaceflinger.so` from Honda's fork of SurfaceFlinger that tells init to start the service

```bash
rg -l --hidden --no-ignore -a daupdater apk-rebuilder/
# apk-rebuilder/output/extracted-ramdisk/sbin/daupdater
# apk-rebuilder/output/extracted-ramdisk/init.vcm30t30.rc
# apk-rebuilder/output/unzipped-mdt/system/lib/libsurfaceflinger.so
```

## Appendix: Confirming `ro.hardware` from the boot image

You can confirm the `ro.hardware` value from the boot image's command line `androidboot.hardware` argument:

```sh
strings -t d apk-rebuilder/output/unzipped-mdt/boot.img | grep -i androidboot
# 64 androidboot.hardware=vcm30t30 androidboot.console=ttyS0 ...
```

This is then used to import the relevant `init.${ro.hardware}.rc` file from `init.rc`.

## Appendix: SystemUpdateApService

The app-based service is largely out of scope for this document. It supports applying updates beyond AOSP updates, such as for the car stereo.
It also has a nice UI that appears when a USB drive matching all requirements is connected. But in practice, this update path is undesirable for two reasons:

- It adds additional checks beyond what `daupdater` enforces
- It has more moving parts and it's less obvious when it runs compared to `daupdater`, which runs on every boot

In addition to the checks required by `daupdater`, `SystemUpdate` enforces additional version checks, i.e., checks on the SwUpdate.mdt's `system/build.prop`'s `ro.build.id=` line:

- The new version (from SwUpdate.mdt) must have the literal prefix `1.F1` and is of the format `1.F1<X><YYY><Z>`,
  - where `X`, `YYY`, `Z` form some hierarchical version number
- The new version (from SwUpdate.mdt) must be strictly greater than the current version (from /system/build.prop)
  - where strictly greater involves checking `X`, `YYY`, and `Z` in hierarchical order

Recall that `daupdater` will happily accept any version string *except* the currently installed one (i.e., it refuses to install the currently-installed version, to avoid boot loops when applying updates). When using `daupdater` (and when you don't want to persist a version change) it's recommended to use a version string that explicitly does NOT have a `1.F1` prefix, so that `SystemUpdate` does not show a UI to the user at all (instead allowing `daupdater` to automatically reboot into recovery).
