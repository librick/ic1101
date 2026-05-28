# aidl-rebuilder

Tool to reconstruct the AIDL interfaces used throughout the Honda Civic headunit's Android services, emitting structured YAML that shows what each service exposes and what arguments it takes.

## Usage

This tool requires output from [apk-rebuilder](https://github.com/librick/ic1101/tree/main/apk-rebuilder). If you haven't used apk-rebuilder yet, check it out first.

Once you've run apk-rebuilder, you're ready to run this tool:

```bash
cd aidl-rebuilder
# Create an output directory for aidl-rebuilder output (distinct from apk-rebuilder output)
mkdir output
# The following assumes you have an output tree at ../apk-rebuilder/output
uv run src/main.py \
    --vendor-app-smali-dir ../apk-rebuilder/output/vendor-app-smali \
    --vendor-framework-smali-dir ../apk-rebuilder/output/vendor-framework-smali \
    --system-framework-smali-dir ../apk-rebuilder/output/system-framework-smali \
    --output-dir output/
```

## Output

The following files are created:

- `./output/interfaces.yaml`
- `./output/parcelables.yaml`

## Motivation

The original source code made extensive use of Android Interface Definition Language (AIDL)
to define contracts between Android services. Knowing what interfaces exist allows us to rapidly understand which software components talk to each other and how on the headunit.

The remnants of these interfaces are preserved in \*.smali files that we reconstruct
using apk-rebuilder. With these files in place, aidl-rebuilder parses them to generate yaml files
that describe which AIDL interfaces existed in the original source code.
Crucially, this entire pipeline (apk-rebuilder -> aidl-rebuilder) can be modeled as a single function
that takes as input a Honda Civic update file and produces useful structured output
that can be consumed by software devs, hackers, and LLMs.
There is NO proprietary code in this repo.

## AI Disclosure

AI was used heavily to write this code with a lot of manual hand-holding. The code has been manually reviewed. PRs to clean up AI cruft are welcome.

## Legal Notice

I am *NOT* affiliated with Honda Motor Co., Ltd. I am *NOT* affiliated with Mitsubishi. Honda and Honda Civic are registered trademarks. This repo does *NOT* contain proprietary APK files, source code, or software update files. This script is just a way to leverage existing tools and software update files that have been published elsewhere to produce .apk files locally.
