# Wi-Fi and Bluetooth
- Wi-Fi and Bluetooth are provided by a shared TI WiLink 8 chip
- The TI WiLink 8 chip is connected via eMMC (similar to a Raspberry Pi)
- It uses the `wl18xx` kernel module
- It is exposed via sysfs at `/sys/class/mmc_host/mmc1/`