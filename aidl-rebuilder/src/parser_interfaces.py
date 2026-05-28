#!/usr/bin/env python3

from dataclasses import dataclass
import logging
import re
import os

from utils import read_file_lines
from models_aidl import (
    Arg,
    Constant,
    Method,
    Interface,
)

from parser_smali import (
    map_p_registers_to_arg_indices,
    match_const,
    match_const_string,
    match_field,
    match_invoke_interface,
    match_invoke_virtual,
    match_local,
    match_method,
    match_param,
    parse_signature_annotation,
)
from parser_jvm_types import (
    parse_jvm_type_erased,
    parse_jvm_type_list_erased,
    parse_jvm_type_list_generic,
    parse_signature_arg_str,
)

logger = logging.getLogger(__name__)

# Regexes for methods that appear in *$Stub$Proxy.smali files
# but that are Binder boilerplate, not actual AIDL methods.
STUB_PROXY_METHOD_SKIP_PATTERNS: list[re.Pattern[str]] = [
    # The `$Stub$Proxy` constructor.
    # In Java: `Proxy(IBinder remote)`
    # All observed *$Stub$Proxy.smali files define this method.
    re.compile(r"^<init>\(Landroid/os/IBinder;\)V$"),
    # The asBinder method. Part of the IInterface contract.
    # On the proxy returns this.mRemote; on the stub returns this.
    # In Java: `public IBinder asBinder()`
    # All observed *$Stub$Proxy.smali files define this method.
    re.compile(r"^asBinder\(\)Landroid/os/IBinder;$"),
    # The getInterfaceDescriptor method. Returns the DESCRIPTOR string.
    # In Java: `public String getInterfaceDescriptor()`
    # Only a subset of observed *$Stub$Proxy.smali files define this method.
    re.compile(r"^getInterfaceDescriptor\(\)Ljava/lang/String;$"),
]

# Types that are always 'in' per AIDL rules, regardless of what the proxy does.
_ALWAYS_IN_TYPES = {
    "int",
    "long",
    "short",
    "byte",
    "char",
    "float",
    "double",
    "boolean",
    "java.lang.String",
    "java.lang.CharSequence",
    "android.os.IBinder",
}


@dataclass(frozen=True)
class _TransactInfo:
    """Parsed info from an IBinder.transact() call site.

    Attributes:
        is_oneway: True if the oneway flag (1) is set.
        transaction_code: Integer transaction code, or None if not resolved.
        line_index: Line index of the transact() call in the file.
    """

    is_oneway: bool
    transaction_code: int | None
    line_index: int


def should_skip_method(descriptor: str) -> bool:
    return any(p.match(descriptor) for p in STUB_PROXY_METHOD_SKIP_PATTERNS)


def _resolve_arg_names(
    types: list[str],
    param_names_by_reg: dict[int, str],
) -> list[Arg]:
    """Build the final Arg list by correlating register numbers to arg indices.

    Ensures that wide types (long, double) are handled correctly.
    Any arg whose register has no recorded name gets name=None.
    """
    reg_to_idx = map_p_registers_to_arg_indices(types)
    idx_to_name = {idx: name for reg, name in param_names_by_reg.items() if (idx := reg_to_idx.get(reg)) is not None}
    return [Arg(type=t, name=idx_to_name.get(i)) for i, t in enumerate(types)]


def _extract_transact_info(lines: list[str], start: int, end: int) -> _TransactInfo | None:
    """Find the transact() call and extract the transaction code, oneway flag, and line index."""
    for i in range(start, end):
        inv = match_invoke_interface(lines[i])
        if inv is None:
            continue
        if inv.method_name != "transact" or inv.owner_class != "android/os/IBinder":
            continue
        if len(inv.registers) < 2:
            continue
        code_reg = inv.registers[1]
        transaction_code = _find_const_for_register(lines, i, code_reg)
        flags_value = None
        if len(inv.registers) >= 5:
            flags_reg = inv.registers[4]
            flags_value = _find_const_for_register(lines, i, flags_reg)
        return _TransactInfo(
            is_oneway=flags_value == 1,
            transaction_code=transaction_code,
            line_index=i,
        )
    return None


def _find_const_for_register(lines: list[str], search_from: int, register: str) -> int | None:
    """Scan backwards from search_from for the most recent const* assignment to
    the given register. Returns the integer value, or None if not found.
    Skips const-wide since transaction codes and flags are always 32-bit.

    Handles all Dalvik const opcodes:
    const/4    vX, #
    const/16   vX, #
    const      vX, #
    const/high16 vX, #   (value is shifted; we return the raw literal)
    """
    for i in range(search_from - 1, -1, -1):
        const = match_const(lines[i])
        if const and const.variant != "wide" and const.dest_reg == register:
            try:
                raw = const.value
                return int(raw, 16) if raw.startswith("0x") or raw.startswith("-0x") else int(raw)
            except ValueError:
                return None
    return None


def _find_out_arg_indices(
    lines: list[str],
    transact_line: int,
    method_end: int,
    reg_to_arg: dict[int, int],
) -> set[int]:
    """Scan after transact() for readFromParcel calls on p-registers."""
    out_indices = set()
    for i in range(transact_line + 1, method_end):
        inv = match_invoke_virtual(lines[i])
        if inv is None:
            continue
        if inv.method_name != "readFromParcel":
            continue
        first_reg = inv.registers[0]
        if not first_reg.startswith("p"):
            continue
        p_num = int(first_reg[1:])
        arg_idx = reg_to_arg.get(p_num)
        if arg_idx is not None:
            out_indices.add(arg_idx)
    return out_indices


def _was_written_before_transact(
    lines: list[str],
    start: int,
    transact_line: int,
    p_reg: str,
) -> bool:
    """Check whether a p-register was passed to a Parcel write method before transact.

    Scans for invoke-virtual calls where the p-register appears as an argument
    to a Parcel write method (writeParcelable, writeTypedObject, writeValue, etc.).
    """
    for i in range(start, transact_line):
        inv = match_invoke_virtual(lines[i])
        if inv is None:
            continue
        if not inv.method_name.startswith("write"):
            continue
        if p_reg in inv.registers:
            return True
    return False


def _resolve_arg_directions(
    args: list[Arg],
    lines: list[str],
    method_body_start: int,
    method_end: int,
    transact_info: _TransactInfo,
    reg_to_arg: dict[int, int],
) -> list[Arg]:
    """Determine in/out/inout direction for each argument.

    Primitives and Strings are always 'in'. For other types, we check
    whether readFromParcel is called after transact (out), and whether
    the parameter was written before transact (in). Both means inout.
    """
    out_indices = _find_out_arg_indices(lines, transact_info.line_index, method_end, reg_to_arg)

    if not out_indices:
        return args

    arg_to_reg = {v: k for k, v in reg_to_arg.items()}
    result = []
    for idx, arg in enumerate(args):
        if idx in out_indices and arg.type not in _ALWAYS_IN_TYPES:
            p_reg = f"p{arg_to_reg[idx]}"
            was_written = _was_written_before_transact(lines, method_body_start, transact_info.line_index, p_reg)
            result.append(
                Arg(
                    type=arg.type,
                    name=arg.name,
                    direction="inout" if was_written else "out",
                )
            )
        else:
            result.append(arg)
    return result


def _parse_descriptor_from_stub_file(stub_path: str) -> str:
    """Extract the AIDL interface descriptor from a $Stub.smali file.

    Scans the no-arg constructor <init>()V for the first const-string
    loaded into a local register, which is always the descriptor string
    passed to attachInterface.

    Raises OSError if the file cannot be read.
    Raises ValueError if no descriptor is found.
    """
    lines = read_file_lines(stub_path)

    in_init = False
    for line in lines:
        stripped = line.strip()

        method = match_method(stripped)
        if method and "constructor" in method.modifiers and method.descriptor == "<init>()V":
            in_init = True
            continue

        if in_init:
            if stripped == ".end method":
                break
            const_str = match_const_string(stripped)
            if const_str:
                return const_str.value

    raise ValueError(f"could not extract descriptor from stub file: {stub_path} (no const-string found in <init>()V)")


def _parse_constants_from_stub_file(stub_path: str) -> list[Constant]:
    """Extract AIDL constants from a $Stub.smali file, excluding Binder internals."""
    lines = read_file_lines(stub_path)
    return [
        Constant(
            name=f.field_name,
            type=parse_jvm_type_erased(f.type_descriptor),
            value=f.value,
        )
        for f in (match_field(line) for line in lines)
        if f is not None
        and "static" in f.modifiers
        and "final" in f.modifiers
        and f.value is not None
        and not f.field_name.startswith("TRANSACTION_")
        and f.field_name != "DESCRIPTOR"
    ]


def _parse_proxy_file(proxy_path: str) -> list[Method]:
    """Parse a $Stub$Proxy.smali file into a list of Methods.

    For each public method:
      - Argument types are parsed from the plain method descriptor.
      - If a Ldalvik/annotation/Signature annotation is present in the method
        body, its fragments are concatenated and parsed with the generic type
        parser, and the result overrides the erased types positionally.
      - Parameter names are collected from .param directives.
      - Directional tags (in/out/inout) are inferred from whether parameters
        are written before transact and/or read back after transact.

    If .param lines are absent or fewer than the number of arguments, the
    missing names are set to None.
    """
    methods = []
    lines = read_file_lines(proxy_path)
    if lines is None:
        return methods

    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        method = match_method(stripped)
        if not method or "public" not in method.modifiers:
            i += 1
            continue

        sig = method.descriptor
        if should_skip_method(sig):
            i += 1
            continue

        paren_open = sig.index("(")
        paren_close = sig.index(")")
        method_name = sig[:paren_open]
        types = parse_jvm_type_list_erased(sig[paren_open + 1 : paren_close])
        return_type = parse_jvm_type_erased(sig[paren_close + 1 :])

        # Scan the method body until .end method, collecting:
        #   param_names_by_reg: register→name from .param and .local p* directives
        #   generic_types: from Ldalvik/annotation/Signature (overrides erased
        #                  types if present and count matches)
        #
        # Both .param and .local on a p-register carry parameter names.
        # .param is used for non-generic parameters; .local is used for generic
        # ones (e.g. List<Foo>). Keying by register number rather than collecting
        # positionally ensures correctness in the presence of wide types (long,
        # double) and makes the two sources interchangeable.
        param_names_by_reg: dict[int, str] = {}
        generic_types = None
        i += 1
        method_body_start = i

        while i < len(lines):
            body = lines[i].strip()

            if body == ".end method":
                i += 1
                break

            # .param p<n>, "<name>" - non-generic parameter name
            param = match_param(body)
            if param:
                p_num = int(param.register[1:])
                param_names_by_reg[p_num] = param.name
                i += 1
                continue

            # .local p<n>, "<name>":... - generic parameter name
            local = match_local(body)
            if local and local.register.startswith("p"):
                p_num = int(local.register[1:])
                param_names_by_reg[p_num] = local.name
                i += 1
                continue

            # Signature annotation: generic type information
            sig_ann = parse_signature_annotation(lines, i)
            if sig_ann is not None:
                i = sig_ann.next_line
                arg_str = parse_signature_arg_str(sig_ann.generic_signature)
                if arg_str is not None:
                    parsed = parse_jvm_type_list_generic(arg_str)
                    if len(parsed) == len(types):
                        generic_types = parsed
                    else:
                        logger.warning(
                            "generic signature arg count mismatch in %s: %s"
                            + " (expected %d, got %d); using erased types",
                            proxy_path,
                            method_name,
                            len(types),
                            len(parsed),
                        )
                continue

            i += 1

        final_types = generic_types if generic_types is not None else types
        args = _resolve_arg_names(final_types, param_names_by_reg)
        transact_info = _extract_transact_info(lines, method_body_start, i)

        # Resolve directional tags (in/out/inout)
        if transact_info is not None:
            reg_to_arg = map_p_registers_to_arg_indices(final_types)
            args = _resolve_arg_directions(args, lines, method_body_start, i, transact_info, reg_to_arg)

        methods.append(
            Method(
                name=method_name,
                args=args,
                return_type=return_type,
                transaction_code=transact_info.transaction_code if transact_info else None,
                is_oneway=transact_info.is_oneway if transact_info else False,
            )
        )

    return methods


def _parse_proxy_and_stub_file(proxy_path: str, stub_path: str) -> tuple[str, list[Method]]:
    methods = _parse_proxy_file(proxy_path)
    descriptor = _parse_descriptor_from_stub_file(stub_path)
    return descriptor, methods


@dataclass
class ProxyPathMetadata:
    interface_name: str
    package: str


def _extract_proxy_path_metadata(proxy_path: str) -> ProxyPathMetadata:
    """Extracts the interface name and package from a $Stub$Proxy.smali file path."""
    basename = os.path.basename(proxy_path)
    interface_name = basename.replace("$Stub$Proxy.smali", "")
    parts = os.path.dirname(proxy_path).split(os.sep)
    pkg_start = next(
        (i for i, p in enumerate(parts) if p in ("com", "org", "net", "jp", "android")),
        None,
    )
    package = ".".join(parts[pkg_start:]) if pkg_start is not None else ""

    return ProxyPathMetadata(interface_name=interface_name, package=package)


def parse_interfaces(
    proxy_paths: list[str],
    stub_paths: list[str],
) -> list[Interface]:
    """Parses a list of proxy and stub file paths into a list of AIDL interfaces."""
    interfaces = []
    for proxy_path, stub_path in zip(proxy_paths, stub_paths):
        meta = _extract_proxy_path_metadata(proxy_path)
        descriptor, methods = _parse_proxy_and_stub_file(proxy_path, stub_path)
        constants = _parse_constants_from_stub_file(stub_path)
        interfaces.append(
            Interface(
                interface_name=meta.interface_name,
                package=meta.package,
                descriptor=descriptor,
                is_callback=False,
                stub=stub_path,
                proxy=proxy_path,
                methods=methods,
                constants=constants,
            )
        )
    return interfaces
