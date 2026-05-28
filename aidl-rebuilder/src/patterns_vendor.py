import re

VENDOR_CALLBACK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"Callback"),
    re.compile(r"CallBack"),
    re.compile(r"CallBacks"),
    re.compile(r"Listener"),
    re.compile(r"Listner"),  # common misspelling in this codebase
    re.compile(r"Observer$"),  # anchor to end to avoid false positives
]
