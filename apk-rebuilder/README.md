# Honda Civic APK Rebuilder

Script to extract, deodex, and decode system & vendor apps and framework jars from 10th gen Honda Civic `MRC<...>.zip` update files.

## Requirements

- A Honda Civic update file (Google `civicx "MRC_EU_SW_v12_4.zip"`)
- A recent version of Java (I'm using `openjdk 21.0.7-ea 2025-04-15`)
- A recent version of Python, Python 3.13+

## Usage

Instructions written for Linux; exact steps vary by operating system.

1. Ensure Java is installed
1. Ensure python3 is installed
1. Clone this repo and `cd` into `ic1101/apk-rebuilder`.
1. Find a 10th gen Honda Civic update file (see [Requirements](#requirements))
1. Copy the update file to `./input/MRC_EU_SW_v12_4.zip`
1. Create output directory: `mkdir -p output`
1. Run `python3 src/main.py --input-dir ./input --output-dir ./output`
1. See [Outputs](#outputs) for a description of what gets created.

## Performance

Expect the script to take 10-15 minutes. The logs should be verbose enough that you'll know if it's hanging. Otherwise just let it do its thing.

## Outputs

The following directories and files are created. All paths are relative to `--output-dir`:

| Directory                        | Description                                                                                  |
| -------------------------------- | -------------------------------------------------------------------------------------------- |
| `unzipped-zip`                   | Extracted contents of `MRC<...>.zip` update file                                             |
| `unzipped-mdt`                   | Extracted contents of `SwUpdate.mdt`; contains Android filesystem                            |
| `system-app-smali`               | Smali files produced by disassembling `system/app/*.odex` files with baksmali                |
| `system-app-classes`             | `classes.dex` files reassembled from system app smali files with smali                       |
| `system-app-apks-repacked`       | Rebuilt APKs with injected `classes.dex` files; ready for use with JADX                      |
| `vendor-app-smali`               | Smali files produced by disassembling `system/vendor/app/*.odex` files with baksmali         |
| `vendor-app-classes`             | `classes.dex` files reassembled from vendor app smali files with smali                       |
| `vendor-app-apks-repacked`       | Rebuilt APKs with injected `classes.dex` files; ready for use with JADX                      |
| `system-framework-smali`         | Smali files produced by disassembling `system/framework/*.odex` files with baksmali          |
| `system-framework-classes`       | `classes.dex` files reassembled from system framework smali files with smali                 |
| `system-framework-jars-repacked` | Rebuilt JARs with injected `classes.dex` files; ready for use with JADX                      |
| `vendor-framework-smali`         | Smali files produced by disassembling `system/vendor/framework/*.odex` files with baksmali   |
| `vendor-framework-classes`       | `classes.dex` files reassembled from vendor framework smali files with smali                 |
| `vendor-framework-jars-repacked` | Rebuilt JARs with injected `classes.dex` files; ready for use with JADX                      |
| `apktool-system-apps`            | Decoded resources for each system app (`system/app/*.apk`) via apktool                       |
| `apktool-vendor-apps`            | Decoded resources (XML layouts, drawables, values, manifest) for each vendor app via apktool |
| `apktool-vendor-framework`       | Decoded vendor framework resources from `framework-res.apk` via apktool                      |

## Running JADX

If you're on Linux and have flatpak, you can:

```bash
# Install JADX as a flatpak
flatpak install flathub com.github.skylot.jadx
# Run JADX, passing repacked paths
flatpak run com.github.skylot.jadx \
    output/system-app-apks-repacked/*.apk \
    output/system-framework-jars-repacked/*.jar \
    output/vendor-app-apks-repacked/*.apk \
    output/vendor-framework-jars-repacked/*.jar
```

## Compatibility

This script should be cross-platform, with minimal dependencies. If it doesn't work on your platform, open an issue or PR.

## Developer Guide

Install pre-commit hooks:

```bash
git clone https://github.com/librick/ic1101.git
cd ic1101
pre-commit install
```

Run tests:

```bash
cd apk-rebuilder
uv run pytest -v
```

## Motivation

Reverse-engineering the headunit software by hand is tedious and error-prone,
even with good open-source tools. You have to track down an update file,
extract it, deodex framework jars before apps (apps depend on framework
classes for vtable resolution), pass the repacked jars back in as
dependencies, and install the vendor `framework-res.apk` into apktool's
framework cache before resources will decode. Get the order or flags wrong and baksmali produces broken smali.

By automating this, other devs can get up to speed on the headunit code
quickly.

## About Mitsubishi's Custom `framework-res.apk`

- Mitsubishi developed the headunit software and licensed it to Honda
- On a stock Android 4.2.2 system, there's a single Android framework, including the base Android theme (Holo), stock layouts, drawables, strings, etc.
- But Mitsubishi replaced and extended the entire Android framework resource layer
- Unlike stock Android, there is NO `/system/framework/framework-res.apk` file
- Instead, Mitsubishi shipped their own, located at `/system/vendor/framework/framework-res.apk`
- The `/system/vendor/framework/framework-res.apk` file is approx. 38 MB
- This custom `framework-res.apk` contains all 4.2.2 AOSP resources plus Mitsubishi-specific additions
- The Mitsubishi additions include:
  - Vehicle-related layouts and drawables, custom themes
  - Resources for their custom Views in `UiLib.odex`
- The [AOSP 4.2.2 framework resources](https://android.googlesource.com/platform/frameworks/base/+/android-4.2.2_r1/core/res/res/) are available online, useful for diffing against our `framework-res.apk`
- `/system/vendor/framework` contains exclusively `framework-res.apk` AND `*.jar` and `*.odex` pairs
- Every `/system/vendor/framework/*.jar` file has had its `classes.dex` file stripped
- Custom Mitsubishi views are defined in the `UiLib.jar` and `UiLib.odex` pair
- Apps are in `/system/app/` and `/system/vendor/app`
- These app dirs consist exclusively of `<AppName>.apk` and `<AppName>.odex` pairs
- For apps, `classes.dex` are stripped from all `*.apk` files, the only bytecode is in the `*.odex` files

## Using apktool alongside JADX

JADX is great for constructing Java code; apktool is better for resource resolution.

- I wanted to reverse-engineer the layouts from the vendor APKs in `/system/vendor/app/*.apk`
- I tried to use JADX to extract the resources
- In compiled APKs, all resources are stored as 32-bit integer IDs, not symbolic names
- When JADX decompiles the APK, it needs to map integer IDs back to symbolic names
- JADX does this by using a resource table, either from the APK itself or from a framework reference
- But Honda's framework-res.apk has custom resources with IDs that don't match standard Android
- So when JADX sees a resource ID like `0x108129a` it either:
  - Can't find it at all, shows the raw hex ID `0x108129a`
  - Finds a different resource in modern Android SDK that happens to have the same ID
    - Shows wrong name like `?android:attr/collapseContentDescription`
- In reality, `0x108129a` is a reference to a drawable defined in Honda's `framework-res.apk`
- JADX doesn't correctly resolve the resource ID because it doesn't use framework-res.apk properly
- JADX uses hard-coded resource resolution w/ [jadx-core/src/main/resources/android/res-map.txt](https://github.com/skylot/jadx/blob/331c4aaa5ef0c6aa97fefafd1a818d5467040bd2/jadx-core/src/main/resources/android/res-map.txt)
- This means there are two underlying issues with resource resolution in JADX:
  - JADX maps resource IDs to resources that only exist in newer (> API 17) Android versions
    - So I would see a resource mapped to a resource string that was anachronistic
  - JADX does not know about custom resources in framework-res, so it fails to look up resource IDs
    - So I would just see a raw 32-bit hex value, representing the resource ID itself
- Apktool solved these symbol resolution issues because it can use a custom framework-res.apk
- Apktool decodes APK resources (layouts, drawables, values, manifest) to their original XML/file form
- I got the latest from https://apktool.org/
- At the time of writing this is `apktool_2.12.1.jar`
- Apktool produced better results than JADX

## Apktool and Custom `framework-res.apk`

- I solved the resource resolution issues by installing `framework-res.apk` as a framework named `mitsubishi`
- Then I was able to unpack the resources for a given vendor app (here, `AirCon.apk`)
- This is now automated to unpack resources for all vendor apps

```bash
apktool if system/vendor/framework/framework-res.apk -t mitsubishi
# I: Framework installed to: /home/user/.local/share/apktool/framework/1-mitsubishi.apk
java -jar apktool_2.12.1.jar d system/vendor/app/AirCon.apk -t mitsubishi -o AirCon-resources/
# I: Using Apktool 2.12.1 on AirCon.apk with 8 threads
# I: Loading resource table...
# I: Decoding file-resources...
# I: Loading resource table from file: /home/user/.local/share/apktool/framework/1-mitsubishi.apk
# I: Decoding values */* XMLs...
# I: Decoding AndroidManifest.xml with resources...
# I: Copying original files...
# I: Copying unknown files...
```

## Legal Notice

I am *NOT* affiliated with Honda Motor Co., Ltd. I am *NOT* affiliated with Mitsubishi. Honda and Honda Civic are registered trademarks. This repo does *NOT* contain proprietary APK files, source code, or software update files. This script is just a way to leverage existing tools and software update files that have been published elsewhere to produce .apk files locally.
