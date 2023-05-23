# Bluetooth, RFCOMM, and HondaLink
The headunit supports many diffrent Bluetooth BR/EDR profiles and protocols.
Cross-reference these with this Wikipedia article: https://en.wikipedia.org/wiki/List_of_Bluetooth_profiles

Bluetooth profiles on the 2021 Honda Civic, non-exhaustive:
- Audio/Video Remote Control Profile (AVRCP)
- Advanced Audio Distribution Profile (A2DP)
- Hands-Free Profile (HFP)
- Generic Audio/Video Distribution Profile (GAVDP)
- Phone Book Access Profile (PBAP, PBA)
- Object Exchange Protocol (OBEX)
    - Used to transfer SMS messages and phone contacts

Bluetooth protocols on the 2021 Honda Civic, non-exaustive:
- Audio/Video Distribution Transport Protocol
- RFCOMM Protocol

The RFCOMM protocol is of particular interest.  
I've observed Bluetooth traffic using RFCOMM from the car to dial out to a Japanese domain name. It establishes some sort of tunnel, using `HTTP CONNECT` and I think point-to-point protocol.

```
CONNECT www.jp.hondalink.com:443 HTTP/1.1
Host: www.jp.hondalink.com
User-Agent: Dalvik/1.6.0 (Linux; U; Android id 4.2.2; MY16AD A Build/1.F1A5.15)
Proxy-Connection: Keep-Alive
```
I've then observed an HTTP POST sent over the same RFCOMM channel, presumably over a locally-established tunnel, where the body is my VIN number:
```
POST http://192.168.1.1:80/kvs/vin/ HTTP/1.1
Connetion: Close
Content-Length: <REDACTED_SMALL_INTEGER>
Content-Type: text/plain; charset=UTF-8
Host: 192.168.1.1:80
User-Agent: Apache-HttpClient/UNAVAILABLE (java 1.4)
<REDACTED_MY_VIN_HERE>
```

I would have to investigate further before I can say this definitively, but **it appears that 2021 Honda Civics self-report their VINs to Honda's HondaLink server(s) when you pair your phone to your car over Bluetooth.**
Further, this is all sent over a locally-unencrypted (TCP port 80) tunnel, and I've seen no evidence that the Bluetooth traffic is itself encrypted (having captured Bluetooth traffic logs through my phone). And running `cat /system/etc/bluetooth/network.conf` shows
```
# Configuration file for the network service

[General]

# Disable link encryption: default=false
DisableSecurity=true
```
