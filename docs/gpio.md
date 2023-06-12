# GPIO
- The infotainment unit makes use of several GPIO pins
- Many apks and native libraries hard-code specific GPIO numbers
- They can be accessed and enumerated via a (deprecated) sysfs interface: `/sys/class/gpio`
- The `earlyrvc` reverse camera binary uses `gpio205`, `gpio227` and `gpio228`
- `gpio205` is an input; it was observed to have the value `0` when the car is in park, `1` when the car is in reverse
- There are also inputs under `/sys/devices/platform/gpio-keys/`, in which GPIO keys are mapped as keyboard inputs
