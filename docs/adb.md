# ADB and Diagnostic Menu
Assuming you have root on your headunit, you should enable ADB.
I suggest installing a network ADB app (I don't think ADB over TCP is available natively in Android 4.2.2)
and setting your headunit to look for Wi-Fi at a known BSSID and password.
This will help avoid softbricking your headunit.

Additionally, you can access ADB over physical USB (via the USB port nearest the steering wheel, assuming a US car).
But for this to work you need to set the headunit USB to "Device" rather than "Host" mode.
This can be done through a hidden diagnostic menu.

Steps:
- On the headunit, hold down the following buttons: Brightness+Phone+Volume/Power
- A diagnostic menu should appear with two large horizontal buttons
- Tap "Detail Information and Settings"
- On the headunit, hold down the phone key, you'll open a different menu
- On the headunit, hold down the home key, you'll hear three beeps, then single beep
- You should now see a USB settings menu with a "Role" dropdown
- Change "Role" dropdown from "Host" to "Device"
- Connect a USB-A to USB-A cable to a laptop
- Assuming adb is running on the headunit, you should be able to connect via USB now

I'm not sure which Android activity contains this USB settings menu.  
A faster method would be to just launch the USB settings activity via a local shell on the headunit.
This would also probably be more cross-platform and work for a larger variety of car models with slightly different headunits.
Feel free to make a PR that address this, documenting the activity name and the appropriate command to start it.
