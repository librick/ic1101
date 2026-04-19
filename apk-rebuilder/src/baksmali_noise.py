import re
from typing import Final

# Noise lines that baksmali-2.5.2 emits to stderr on every `deodex` invocation.
# Only add lines that are genuinely noise; don't use this to hide real errors.
BAKSMALI_DEODEX_NOISE_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"^WARNING: A terminally deprecated method in sun\.misc\.Unsafe has been called$"),
    re.compile(
        r"^WARNING: sun\.misc\.Unsafe::objectFieldOffset has been called by "
        + r"com\.google\.common\.util\.concurrent\.AbstractFuture\$UnsafeAtomicHelper "
        + r"\(file:.*baksmali-2\.5\.2\.jar\)$"
    ),
    re.compile(
        r"^WARNING: Please consider reporting this to the maintainers of class "
        + r"com\.google\.common\.util\.concurrent\.AbstractFuture\$UnsafeAtomicHelper$"
    ),
    re.compile(r"^WARNING: sun\.misc\.Unsafe::objectFieldOffset will be removed in a future release$"),
]
