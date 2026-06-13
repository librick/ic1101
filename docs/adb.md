# ADB and Diagnostic Menu

You should enable ADB on your headunit. This is particularly useful to prevent softbricking your headunit.

This document covers gaining ADB access to the Mitsubishi Electric Honda/Acura head unit (vcm30t30, Android 4.2.2, Tegra SoC), which requires switching USB modes.

## Physical Connection

To use wired ADB, you need a USB-A to USB-A cable, with one end connected to the USB port closest to the car's steering wheel.
Do NOT use the the USB port inside the center console. The Tegra 3 SoC that is used by the headunit is wired up to two physical USB ports,
but in most vendor-provided native code there is a strong preference for the USB port closest to the car's steering wheel.

## USB Mode Switching

The head unit defaults to USB Host mode. ADB over USB requires Device mode.

### Via Hidden Diagnostic Menu (Physical)

- Hold Brightness + Phone + Volume/Power simultaneously
- A diagnostic menu should appear with two large horizontal buttons
- Tap "Detail Information and Settings"
- Hold Phone key → different menu opens
- Hold Home key → you'll hear three beeps, then a single beep
- You should now see a USB settings menu with a "Role" dropdown
- Change Role from Host → Device
- Connect USB-A to USB-A cable to your PC
- ADB should now enumerate

### Via Shell (Confirmed Working)

Switch to Device mode:

```bash
echo 0 > /sys/devices/platform/tegra-otg/enable_host
echo 1 > /sys/devices/platform/tegra-otg/enable_device
echo connect > /sys/devices/platform/tegra-udc.0/udc/tegra-udc.0/soft_connect
setprop sys.usb.config mtp,adb
```

Switch to Host mode:

```bash
echo 1 > /sys/devices/platform/tegra-otg/enable_host
echo 0 > /sys/devices/platform/tegra-otg/enable_device
setprop sys.usb.config host
```

Make persistent across reboots:

```bash
setprop persist.sys.usb1_mode device   # or host
```

Note: soft_connect is required for device mode to enumerate correctly on the host PC. Without it the port won't appear even after the OTG switch.

## Path Taken to Switch Roles

```
UsbCertActivity (UI dialog role change via secret menu)
↓
UsbCertJni.changeDeviceMode(listener, 0|1) [Java]
↓
changeDeviceModeNative(listener, param, ...) [JNI bridge]
↓
libusbcert_jni.so [Native]
↓
property_set("persist.sys.usb1_mode", "device"|"host")
↓
usbdetectd [watches property!]
↓
j_set_sysattr("/sys/devices/platform/tegra-otg/enable_device", "1")
j_set_sysattr("/sys/devices/platform/tegra-udc.0/.../soft_connect", "connect")
[confirmed from jmcs source]
↓
tegra-otg kernel driver [hardware]
↓
USB port physically switches role
```

## Source References

- USB role switch confirmed from `jmcs` decompilation: `platform_specific_usb_role_switch` in `vcm30t30_android.c`
- Syscon command `0x11 0x04` → `cpu_com_external_device_mode_on` — vehicle MCU can trigger device mode via syscon
- `usbdetectd` (`/system/vendor/bin/usbdetectd`) monitors USB state and may override manual sysfs writes
