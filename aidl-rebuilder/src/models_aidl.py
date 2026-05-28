from dataclasses import dataclass, field


@dataclass
class Arg:
    type: str
    name: str | None
    direction: str = "in"


@dataclass
class Method:
    name: str
    args: list[Arg]
    return_type: str
    is_oneway: bool
    transaction_code: int | None = None  # None if no transact call found in proxy


@dataclass
class Constant:
    name: str
    type: str
    value: str


@dataclass
class Interface:
    interface_name: str
    package: str
    descriptor: str
    is_callback: bool
    stub: str
    proxy: str
    methods: list[Method] = field(default_factory=list)
    constants: list[Constant] = field(default_factory=list)
