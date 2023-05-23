# Motivation
Honda is shipping new cars (as of 2021) with software from 2012.  
The 2021 Honda Civic is based on an NVIDIA Tegra 3 SoC, which has little to no publicly-available documentation.
In particular, there is very little information on NVIDIA kernel modules and ioctl calls,
and no publicly-available documentation on native C libraries and binaries included in the headunit.

Honda Motor Co., Ltd. is putting cars on the road that are black boxes. This is the status quo in the automotive industry. While there are standards for some interfaces such as ODB-II, CAN, and well-documented technical requirements for specific areas of government regulation (e.g., emissions tests), my research shows that cars are still largely close source ecosystems.

If I can't read the source code of my car, I don't trust it.
More importantly, if *other* people (including security researchers and engineers) can't read the source code of my car, I don't trust it. I risk a speeding ticket if I go even a few miles over the posted limit on a public freeway. Yet companies including Honda are allowed to put cars on the road with outdated software, minimal security guarantees, and evidently insufficient oversight.
My 2021 Honda Civic weighs over a metric ton. It can travel up to 126mph. And I'm supposed to take Honda at their word when they say that their software is secure, respects my privacy, and ensures my safety.

For example, I'm pretty sure the headunit is vulnerable to Stagefright exploits c. 2014, a host of webkit exploits, and a plethora of the several other Linux/Android exploits that surfaced between the launch of Android Jellybean (4.2) and when I bought my car.

I can't just buy a more privacy-respecting car or a car with better software.
Certainly, car manufacturers compete on the user-facing technology in cars. But car companies also represent massive economies of scale across complex supply chains requiring massive investment and multinational government support. The free market alone won't bring me a car that respects my digital freedoms.

We need open source hardware, open source software, and incentives for automtive companies to build better, safer, more transparent vehicles. And Honda wanted me to buy a more expensive model to get a built-in GPS app, which I think is B.S. A car also has unique (and I think underappreciated) properties as a generic computational node; it's very intentionally ruggedized and people tend to keep it close by at all times.
And this project is just fun.

Hack the Planet 🌍  
~ Rick
