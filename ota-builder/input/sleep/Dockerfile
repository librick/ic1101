############################
# Stage 1: fetch the NDK.
# Modern base so the TLS stack and CA bundle reaching dl.google.com are current.
############################
FROM debian@sha256:f9c6a2fd2ddbc23e336b6257a5245e31f996953ef06cd13a59fa0a1df2d5c252 AS downloads

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install --yes --no-install-recommends \
        ca-certificates \
        curl \
        bzip2 \
    && rm -rf /var/lib/apt/lists/*

ARG NDK_URL="https://dl.google.com/android/ndk/android-ndk-r8e-linux-x86_64.tar.bz2"
ARG NDK_SHA256="07371eaa242490096be1bf494ecea1e5a6b7839cbead329fb868c0f54b716f24"
RUN curl --fail --location --silent --show-error --output /tmp/ndk.tar.bz2 "${NDK_URL}" \
 && echo "${NDK_SHA256}  /tmp/ndk.tar.bz2" | sha256sum --check --strict --status \
 && mkdir -p /opt \
 && tar -xjf /tmp/ndk.tar.bz2 -C /opt \
 && rm /tmp/ndk.tar.bz2
# NDK now lives at /opt/android-ndk-r8e

############################
# Stage 2: build.
# Bullseye still ships libtinfo5, which the 2013-era r8e gcc needs to run.
############################
FROM debian@sha256:1a4701c321b1d28b1ff5f0230e766791e4b79b1d4c6c7a70064f4b297b1a330f AS build

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install --yes --no-install-recommends \
        build-essential \
        file \
        libtinfo5 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=downloads /opt/android-ndk-r8e /opt/ndk

# Link against the NDK's own platform tree, which carries headers, the static
# libs, and the crt objects. That is what makes a fully static link possible;
# the header-only diff sysroot is deliberately not involved here.
ARG NDK_PLATFORM=android-14
ENV TOOLCHAIN=/opt/ndk/toolchains/arm-linux-androideabi-4.6/prebuilt/linux-x86_64/bin
ENV SYSROOT=/opt/ndk/platforms/${NDK_PLATFORM}/arch-arm
ENV CC=${TOOLCHAIN}/arm-linux-androideabi-gcc
ENV STRIP=${TOOLCHAIN}/arm-linux-androideabi-strip
ENV READELF=${TOOLCHAIN}/arm-linux-androideabi-readelf

WORKDIR /build
COPY src/sleep.c /build/sleep.c

# Compile, strip, then assert it really is a static ARMv7 binary so a broken
# toolchain fails the build instead of emitting a bad artifact.
RUN "${CC}" --sysroot="${SYSROOT}" \
        -std=gnu99 -static -march=armv7-a -mthumb -Os -Wall -Wextra -Werror \
        -o /build/sleep /build/sleep.c \
 && "${STRIP}" /build/sleep \
 && file /build/sleep \
 && "${READELF}" -A /build/sleep \
 && file /build/sleep | grep -q "ELF 32-bit LSB" \
 && file /build/sleep | grep -q "ARM" \
 && file /build/sleep | grep -q "statically linked" \
 && "${READELF}" -A /build/sleep | grep -Eq "Tag_CPU_arch:[[:space:]]*v7" \
 && sha256sum /build/sleep

############################
# Stage 3: export only the binary.
############################
FROM scratch AS export
COPY --from=build /build/sleep /sleep
