#!/usr/bin/env python3
"""Parse Parcelable classes from deodexed .smali files.

Extracts field names, types, and serialization order by analyzing
the writeToParcel() method body. Requires fully deodexed smali
(no invoke-virtual-quick or iget-quick opcodes).
"""

import dataclasses
import logging
import re

from utils import read_file_lines
from models_parcelable import Parcelable, ParcelableEntry
from parser_jvm_types import parse_jvm_type_erased, parse_jvm_type_generic
from utils import find_line
from parser_smali import (
    match_array_length,
    match_const,
    match_iget,
    match_implements,
    match_move_result,
    parse_class_directive,
    parse_field_generic_types,
)

logger = logging.getLogger(__name__)


# Matches the writeToParcel public method declaration
# Example: `.method public writeToParcel(Landroid/os/Parcel;I)V`
# Example: `.method public final writeToParcel(Landroid/os/Parcel;I)V`
_METHOD_WRITE_TO_PARCEL_RE = re.compile(r"^\.method\s+public\s+(?:final\s+)?writeToParcel\(Landroid/os/Parcel;I\)V")

# Matches an invoke-virtual getter call (get* method with no arguments).
# Captures:
#   (1) register (the object the getter is called on),
#   (2) owner class (JVM class path),
#   (3) method name (full name including 'get' prefix, e.g. "getAppId"),
#   (4) JVM return type descriptor.
# Example: `invoke-virtual {p0}, Lcom/example/MyClass;->getAppId()I`
# Example: `invoke-virtual {p0}, Lcom/example/MyClass;->getName()Ljava/lang/String;`
_GETTER_RE = re.compile(
    r"invoke-virtual\s+\{"
    r"(\w+)"
    r"\},\s*L"
    r"([^;]+)"
    r";->"
    r"(get\w+)"
    r"\(\)"
    r"(.+)"
)

# Matches an invoke-virtual call to a Parcel.writeXxx() method.
# Generic type parameters are erased by the time they appear here, e.g., `List<Foo>` devolves to `List`.
# Captures:
#   (1) register list,
#   (2) write method name.
# Example: `invoke-virtual {p1, v0}, Landroid/os/Parcel;->writeString(Ljava/lang/String;)V`
# Example: `invoke-virtual {p1, v0}, Landroid/os/Parcel;->writeInt(I)V`
# Example: `invoke-virtual {p1, v0}, Landroid/os/Parcel;->writeTypedList(Ljava/util/List;)V`
_PARCEL_WRITE_RE = re.compile(
    r"invoke-virtual\s+\{"
    r"([^}]+)"
    r"\},\s*Landroid/os/Parcel;->"
    r"(\w+)"
    r"\("
)


# Matchers whose dest_reg should invalidate pending register tracking.
_CLOBBER_MATCHERS = [match_array_length, match_const]


def _implements_parcelable(lines: list[str]) -> bool:
    """Check whether the file contains an .implements Parcelable directive."""
    return any(
        (impl := match_implements(line)) is not None and impl.interface_path == "android/os/Parcelable"
        for line in lines
    )


@dataclasses.dataclass(frozen=True)
class _GetterCall:
    """A parsed getter call on an object.

    Attributes:
        register: Register of the object the getter is called on, e.g. "p0".
        owner_class: JVM class path of the owner, e.g. "com/example/MyClass".
        method_name: Full method name including 'get' prefix, e.g. "getAppId".
        return_type: JVM return type descriptor, e.g. "I" or "Ljava/lang/String;".
    """

    register: str
    owner_class: str
    method_name: str
    return_type: str


@dataclasses.dataclass(frozen=True)
class ReadFromParcelCall:
    """Parsed readFromParcel call on a p-register.

    Attributes:
        register_num: The p-register index, e.g. 1.
    """

    register_num: int


def _match_getter(line: str) -> _GetterCall | None:
    """Match an invoke-virtual getter call (get* method with no arguments).

    Example: `invoke-virtual {p0}, Lcom/example/MyClass;->getAppId()I`
    Example: `invoke-virtual {p0}, Lcom/example/MyClass;->getName()Ljava/lang/String;`
    """
    m = _GETTER_RE.match(line.strip())
    if not m:
        return None
    return _GetterCall(
        register=m.group(1),
        owner_class=m.group(2),
        method_name=m.group(3),
        return_type=m.group(4),
    )


def _parse_write_to_parcel(
    lines: list[str],
    generic_types: dict[str, str],
) -> list[ParcelableEntry]:
    """Parse the writeToParcel method body for serialization entries.

    Uses register-level tracking to correctly pair field loads with Parcel
    writes. This handles three serialization patterns:

    1. iget-based (direct field access):
        # v0 = this.mName
        iget-object v0, p0, Lcom/example/MyClass;->mName:Ljava/lang/String;
        # p1.writeString(v0)
        invoke-virtual {p1, v0}, Landroid/os/Parcel;->writeString(Ljava/lang/String;)V

    2. getter-based:
        # v0 = this.getName()
        invoke-virtual {p0}, Lcom/example/MyClass;->getName()Ljava/lang/String;
        move-result-object v0
        # p1.writeString(v0)
        invoke-virtual {p1, v0}, Landroid/os/Parcel;->writeString(Ljava/lang/String;)V

    3. chained-call (method on a field value):
        # v0 = this.mStartTime
        iget-object v0, p0, Lcom/example/MyClass;->mStartTime:Ljava/util/Date;
        # v0 = v0.getTime()
        invoke-virtual {v0}, Ljava/util/Date;->getTime()J
        move-result-wide v0
        # p1.writeLong(v0)
        invoke-virtual {p1, v0, v1}, Landroid/os/Parcel;->writeLong(J)V

    Register tracking rejects false matches from intermediate transformations
    like getDate().getTime() -> writeLong (the move-result from getTime()
    overwrites the pending register, invalidating the getter's field info)
    or array-length -> writeInt (the array-length result lands in a different
    register than the getter's result).

    Entries are returned in serialization order.
    """
    entries: list[ParcelableEntry] = []

    # Move to the first writeToParcel method line
    method_line = find_line(lines, _METHOD_WRITE_TO_PARCEL_RE)
    if method_line is None:
        return entries

    # Start scanning the method body (line after the declaration)
    i = method_line + 1

    # Values to track a register.
    # We need a field value to be loaded into a register AND actually used in a Parcel.writeXxx call.
    # If something clobbers that register before the write happens, reset this tracking state.
    pending: tuple[str, str, str] | None = None  # (name, resolved_type, name_source)
    pending_reg: str | None = None
    pending_is_boolean: bool = False
    awaiting_move_result: tuple[str, str, str] | None = None  # from getter or chained call

    while i < len(lines):
        stripped = lines[i].strip()

        # We've reached the end of the method, bail
        if stripped == ".end method":
            break

        # Parse iget-based (direct field access)
        iget = match_iget(stripped)
        if iget:
            # If we have a generic type associated with that field name, parse the generic type
            if iget.field_name in generic_types:
                resolved_type = parse_jvm_type_generic(generic_types[iget.field_name])
            # Otherwise, it's not generic, parse the erased type
            else:
                resolved_type = parse_jvm_type_erased(iget.type_descriptor)

            # Consider this field as "pending" and track its register.
            # If something clobbers this register before we see a Parcel.writeXxx that uses it,
            # invalidate the pending state.
            pending = (iget.field_name, resolved_type, "field")
            pending_reg = iget.dest_reg
            pending_is_boolean = iget.variant == "boolean"
            awaiting_move_result = None
            i += 1
            continue

        # Parse getter-based (only on this/p0)
        getter = _match_getter(stripped)
        if getter and getter.register == "p0":
            # Strip prefix and lowercase first letter to recover property name
            name = getter.method_name.removeprefix("get")
            name = name[0].lower() + name[1:]
            resolved_type = parse_jvm_type_erased(getter.return_type)
            # At this point, the next line we want looks like:
            # - `move-result v0` or
            # - `move-result-object v1`
            # where the destination register can be anything (v0, v1, etc.)
            awaiting_move_result = (name, resolved_type, "getter")
            pending = None
            pending_reg = None
            pending_is_boolean = False
            i += 1
            continue

        # Parcel.writeXxx - consumes the pending entry if registers match.
        # Checked before move-result and chained calls so that a direct
        # iget -> writeXxx pair is consumed immediately.
        write_match = _PARCEL_WRITE_RE.match(stripped)
        if write_match:
            regs = [r.strip() for r in write_match.group(1).split(",")]
            method_name = write_match.group(2)
            data_reg = regs[1] if len(regs) >= 2 else None

            if pending is not None and pending_reg is not None and data_reg == pending_reg:
                entries.append(
                    ParcelableEntry(
                        name=pending[0],
                        name_source=pending[2],
                        type=pending[1],
                        parcel_method=method_name,
                    )
                )

            pending = None
            pending_reg = None
            pending_is_boolean = False
            awaiting_move_result = None
            i += 1
            continue

        # Chained call: invoke-virtual on the pending register (e.g. mStartTime.getTime()).
        # The return value is still derived from the pending field, so preserve
        # the field name through the upcoming move-result.
        if stripped.startswith("invoke-virtual") and pending is not None and pending_reg is not None:
            reg_match = re.search(r"\{(\w+)", stripped)
            if reg_match and reg_match.group(1) == pending_reg:
                awaiting_move_result = (pending[0], pending[1], pending[2])
                pending = None
                pending_reg = None
                pending_is_boolean = False
                i += 1
                continue

        # move-result: stores the return value of a previous invoke
        move = match_move_result(stripped)
        if move:
            if awaiting_move_result is not None:
                pending = awaiting_move_result
                pending_reg = move.dest_reg
                awaiting_move_result = None
            elif pending_reg is not None and move.dest_reg == pending_reg:
                # Something else wrote to our pending register, invalidate
                pending = None
                pending_reg = None
            i += 1
            continue

        # Instructions that clobber a register: invalidate pending if they
        # overwrite the register we're tracking. Exception: iget-boolean
        # followed by const/4 is the standard boolean-to-int conversion
        # pattern (writeInt(val ? 1 : 0)), so we preserve pending.
        for matcher in _CLOBBER_MATCHERS:
            result = matcher(stripped)
            if result is not None:
                if pending_reg is not None and result.dest_reg == pending_reg:
                    if not pending_is_boolean:
                        pending = None
                        pending_reg = None
                break

        i += 1

    return entries


def parse_parcelable_file(smali_path: str) -> Parcelable | None:
    """Parse a single .smali file into a Parcelable, if it is one.

    Returns None if the class does not implement Parcelable or has no
    writeToParcel method.
    """
    lines = read_file_lines(smali_path)

    if not _implements_parcelable(lines):
        return None

    class_directive = parse_class_directive(lines)
    if class_directive is None:
        logger.warning("could not parse class directive from: %s", smali_path)
        return None

    generic_types = parse_field_generic_types(lines)
    entries = _parse_write_to_parcel(lines, generic_types)

    return Parcelable(
        class_name=class_directive.class_name,
        package=class_directive.package,
        full_jvm_class=class_directive.jvm_class_path,
        serialization=entries,
        source_file=smali_path,
    )
