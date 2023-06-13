# Contributing

Thanks for stopping by 😀  
This document outlines different ways people can contribute.
Also see this repo's [discussions](https://github.com/librick/ic1101/discussions). 

## Code We're Looking For
### Open-Source Rooting Tools
**This is a major priority for the project.** It would be beneficial to have an open-source rooting solution for people to use freely. Preferably this would use a well-known Android exploit such as [Dirty COW](https://en.wikipedia.org/wiki/Dirty_COW) to copy over a `su` binary to `/system/bin`.

### Open-Source Binaries and Libraries
It would be beneficial to have open-source versions of existing binaries such as `/sbin/earlyrvc` and `/sbin/daupdate`. The same goes for libraries. I've done some static analysis with Ghidra, but more work could be done here. If you're interested in this, mention it in a [discussion](https://github.com/librick/ic1101/discussions).

## Files We're Looking For
### Pictures
If you have any pictures of your headunit, please add them to this repo.
They can be committed to the `pictures` directory in the root of the repo.
We're looking for images of the outside of the headunit display (including buttons), images of the back of the headunit (electrical connectors), and images of the circuit boards inside the headunit enclosure. Pictures should be high-res but be mindful of exorbiantly large file sizes. The word "picture" is used specifically rather than "image" as the word "image" is overloaded; e.g., "imaging internal flash".

Picture filenames should start with a prefix denoting the make and model of the car. Filenames should use dashes (-) rather than spaces and should be all lowercase. This convention makes things like terminal autocomplete easier to use.
Some examples are given below:
- `2021-honda-civic-hatchback-civic-lx-headunit-front.png`
- `2021-honda-civic-hatchback-civic-lx-headunit-motherboard.png`
- `2021-honda-civic-hatchback-civic-lx-headunit-back.png`
- `2021-honda-civic-hatchback-civic-ex-l-headunit-front.png`
- `2021-honda-civic-hatchback-civic-ex-l-headunit-motherboard.png`
- `2021-honda-civic-hatchback-civic-ex-l-headunit-back.png`

Consider the prefix format to be a general guideline; the important thing is to document which trims correspond with which headunit models.

### Update Files (SwUpdate2.txt, SwUpdate.mtd)
Software updates are applied via USB drive. This process is managed by the `/sbin/daupdater` binary, which looks for `SwUpdate2.txt`/`SwUpdate.txt` and `SwUpdate.mtd` files. More info can be found in the docs. Usually only dealerships have access to these files; if you have any or can link to somewhere that does, please make a PR or start a [discussion](https://github.com/librick/ic1101/discussions).

### System & Vendor build.prop Files
The file `sbin/daupdater` allows updates to proceed only if certain expected values are present in the headunit's `/system/build.prop` and `/system/vendor/build.prop` files.

If you can copy these files from your headunit (e.g., using ADB or FTP), please make a PR adding the files to this repo's `build-props` directory. Prefix the filenames with the make/model of your vehicle. Suffix the files with either `system-build.prop` or `vendor-build.prop`, depending on the file.  
Some examples are given below:
- `2021-honda-civic-hatchback-civic-lx-system-build.prop`
- `2021-honda-civic-hatchback-civic-lx-vendor-build.prop`
- `2021-honda-civic-hatchback-civic-ex-l-system-build.prop.png`
- `2021-honda-civic-hatchback-civic-ex-l-vendor-build.prop.png`

This will elucidate different headunit versions and accelerate the development of custom ROMs. 

## Git Conventions and Naming Schemes

### Git Branching Strategy
- Create your own fork of the repo
- Create a branch off of your fork's `main` branch
- Name this branch according to the guidelines in this document
- Commit your changes to this branch
- When you're ready, create a pull request
- If applicable, add "Fixes #<issue-number>" to the pull request body

### Commit Messages
- commit messages should be in the imperitive form
- commit messages should be lowercase (i.e., not start with a capital letter)

### Branch Names
- When creating a new feature, use the branch name format `feat-<issue-number>`
- When fixing a bug, use the branch name format `bugfix-<issue-number>`
- When fixing an issue that is not a bug, use the generic branch name format `issue-<issue-number>`
- If no issue is applicable to your branch, use a descriptive branch name
- Prefer dashes (-) to underscores (_)
- Don't use slashes (/)

## Sponsorship
If you want to sponsor me, I've set up a [GitHub sponsors page](https://github.com/sponsors/librick).
Not at all required, very much appreciated  
~ Eric (librick) 🌱
