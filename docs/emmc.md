# eMMC and Flash
The eMMC interface is used for flash storage and for Wi-Fi and Bluetooth.
There are three `mmc<n>` devices under `/sys/class/mmc_host`:
- `mmc0`
- `mmc1`
- `mmc2`

I haven't validated that the ordering of `mmc_host` devices within sysfs is constant; I assume it is. For example, you can check the `name` file within sysfs for `mmc0`:  
`cat /sys/class/mmc_host/mmc0/mmc0:0001/name`.  
On my system it returns `R1J55A`, the CID of the flash chip.
