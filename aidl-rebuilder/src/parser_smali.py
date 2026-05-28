import dataclasses
import re


# Matches a smali class directive.
# Captures:
#     (1) JVM class path between `L` and `;`.
# Directives follow the format `.class <access-modifiers> Lcom/some/class/package`.
# Example: `.class public abstract Landroid/os/Bundle;`
# Example: `.class public final Lcom/example/MyClass;`
_SMALI_CLASS_RE = re.compile(r"^\.class\s+.*\s+L([^;]+);")


# Matches a smali implements directive.
# Captures:
#     (1) JVM interface path (without L prefix and ; suffix).
# Example: `.implements Landroid/os/Parcelable;`
# Example: `.implements Landroid/os/IInterface;`
_SMALI_IMPLEMENTS_RE = re.compile(
    r"^\.implements\s+L"
    r"([^;]+)"
    r";"
)


# Matches a smali field directive.
# Captures:
#     (1) modifiers (may be empty).
#     (2) field name.
#     (3) JVM type descriptor.
#     (4) initial value (optional, None if absent).
# Example: `.field private mFoo:Ljava/lang/String;`
# Example: `.field mFoo:Ljava/util/ArrayList;`
# Example: `.field static final WALLPAPER_INFO:Ljava/lang/String; = "wallpaper_info.xml"`
_SMALI_FIELD_RE = re.compile(
    r"^\.field\s+"
    r"(.*\s+)?"
    r"(\w+):"
    r"(\S+)"
    r"(?:\s+=\s+(.+))?"
)


# Matches a smali method directive.
# Captures:
#     (1) access modifiers and qualifiers (may be empty).
#     (2) method descriptor (name, parameter types, and return type).
# Example: `.method public asBinder()Landroid/os/IBinder;`
# Example: `.method synthetic constructor <init>(Ljava/security/Security$1;)V`
_SMALI_METHOD_RE = re.compile(
    r"^\.method\s+"
    r"(.*\s+)?"
    r"(\S+)$"
)


# Matches a smali param directive.
# Captures:
#     (1) register name.
#     (2) parameter name.
#     (3) trailing comment (optional, None if absent).
# In baksmali output, .param directives carry debug info for non-generic
# parameters; generic parameters use .local instead.
# Example: `.param p1, "macAddr"    # Ljava/lang/String;`
# Example: `.param p2, "deviceType"    # I`
_SMALI_PARAM_RE = re.compile(
    r"^\.param\s+"
    r"(p\d+)"
    r',\s+"'
    r'([^"]+)'
    r'"'
    r"(?:\s+#\s+(.+))?"
)


# Matches a smali local directive.
# Captures:
#     (1) register name.
#     (2) variable name.
#     (3) type descriptor after the colon.
# In baksmali output, .local directives carry debug info for local variables
# and generic parameters (e.g. List<Foo>); non-generic parameters use .param.
# Example: `.local p1, "list":Ljava/util/List;`
# Example: `.local v9, "win":Landroid/view/Window;`
_SMALI_LOCAL_RE = re.compile(
    r"^\.local\s+"
    r"(\w+)"
    r',\s+"'
    r'([^"]+)'
    r'":'
    r"(.+)"
)


# Matches a smali const instruction.
# Captures:
#     (1) variant: "wide" for const-wide, or None for plain const.
#     (2) width suffix: "4", "16", "32", "high16", or None for bare const/const-wide.
#     (3) destination register.
#     (4) integer value.
# Handles const, const/4, const/16, const/high16, const-wide, const-wide/16,
# const-wide/32, const-wide/high16. Does not match const-string.
# Example: `const/4 v4, 0x5`
# Example: `const-wide/32 v2, 0x5265c00`
# Example: `const v0, 0x7f1000ba`
_SMALI_CONST_RE = re.compile(
    r"^const(?:-(wide))?(?:/(\d+|high16))?\s+"
    r"(\w+),\s+"
    r"([-\w]+)"
)


# Matches a smali const-string instruction.
# Captures:
#     (1) destination register.
#     (2) string literal value.
# Example: `const-string v0, "com.example.IFoo"`
# Example: `const-string v1, "hello world"`
_SMALI_CONST_STRING_RE = re.compile(
    r'^const-string(?:/(jumbo))?\s+(\w+),\s+"'
    r"(.+)"
    r'"$'
)


# Matches a smali iget instruction.
# Captures:
#     (1) variant (object|wide|boolean|byte|char|short) or None for bare iget.
#     (2) destination register.
#     (3) source register.
#     (4) owner class (JVM class path).
#     (5) field name.
#     (6) JVM type descriptor.
# Example: `iget-object v0, p0, Lcom/example/MyClass;->mBar:Ljava/lang/String;`
# Example: `iget v1, p0, Lcom/example/MyClass;->mCount:I`
_SMALI_IGET_RE = re.compile(
    r"iget(?:-(object|wide|boolean|byte|char|short))?\s+"
    r"(\w+),\s*"
    r"(\w+),\s*"
    r"L([^;]+);->"
    r"(\w+):"
    r"(.+)"
)


# Matches a smali array-length instruction.
# Captures:
#     (1) destination register.
#     (2) source register (the array).
# Example: `array-length v1, v0`
# Example: `array-length v2, v3`
_SMALI_ARRAY_LENGTH_RE = re.compile(
    r"array-length\s+"
    r"(\w+),\s*"
    r"(\w+)"
)


# Matches a smali move-result instruction.
# Captures:
#     (1) variant (object|wide) or None for bare move-result.
#     (2) destination register.
# Example: `move-result v0`
# Example: `move-result-object v1`
_SMALI_MOVE_RESULT_RE = re.compile(
    r"move-result(?:-(object|wide))?\s+"
    r"(\w+)"
)


# Matches a smali invoke-virtual instruction.
# Captures:
#     (1) register list.
#     (2) owner class (JVM class path).
#     (3) method name.
#     (4) argument type descriptor.
#     (5) return type descriptor.
# Example: `invoke-virtual {p1, v1}, Lcom/example/Foo;->readFromParcel(Landroid/os/Parcel;)V`
# Example: `invoke-virtual {p0}, Lcom/example/Foo;->getAppId()I`
_SMALI_INVOKE_VIRTUAL_RE = re.compile(
    r"invoke-virtual\s+\{"
    r"([^}]+)"
    r"\},\s*L"
    r"([^;]+)"
    r";->"
    r"(\w+)"
    r"\("
    r"([^)]*)"
    r"\)"
    r"(.+)"
)


# Matches a smali invoke-interface instruction.
# Captures:
#     (1) register list.
#     (2) owner class (JVM class path).
#     (3) method name.
#     (4) argument type descriptor.
#     (5) return type descriptor.
# Example: `invoke-interface {v3, v4}, Landroid/os/IBinder;->transact(I)Z`
# Example: `invoke-interface {p0}, Lcom/example/IFoo;->doSomething()V`
_SMALI_INVOKE_INTERFACE_RE = re.compile(
    r"invoke-interface\s+\{"
    r"([^}]+)"
    r"\},\s*L"
    r"([^;]+)"
    r";->"
    r"(\w+)"
    r"\("
    r"([^)]*)"
    r"\)"
    r"(.+)"
)


# Matches a smali signature fragment directive.
# Captures:
#     (1) fragment string.
# Each fragment is one quoted string inside a Ldalvik/annotation/Signature
# value block. Concatenating fragments yields the full generic signature.
# Example: `"("`
# Example: `"Ljava/util/List"`
_SMALI_SIGNATURE_FRAGMENT_RE = re.compile(
    r'^\s*"'
    r'([^"]*)'
    r'"'
)


@dataclasses.dataclass(frozen=True)
class SmaliClassDirective:
    """Class identity extracted from a .class directive.

    Attributes:
        jvm_class_path: Slash-separated JVM class path, e.g. "com/example/MyClass".
        package: Dot-separated package name, e.g. "com.example".
        class_name: Simple class name, e.g. "MyClass".
    """

    jvm_class_path: str
    package: str
    class_name: str


@dataclasses.dataclass(frozen=True)
class SmaliImplementsDirective:
    """Parsed .implements directive.

    Attributes:
        interface_path: JVM interface path, e.g. "android/os/Parcelable".
    """

    interface_path: str


@dataclasses.dataclass(frozen=True)
class SmaliFieldDirective:
    """Parsed field declaration.

    Attributes:
        modifiers: Frozenset of modifiers, e.g. frozenset({"private", "static"}).
        field_name: Field name, e.g. "mFoo".
        type_descriptor: JVM type descriptor, e.g. "Ljava/lang/String;".
        value: Initial value if present, e.g. '"wallpaper_info.xml"', or None.
    """

    modifiers: frozenset[str]
    field_name: str
    type_descriptor: str
    value: str | None


@dataclasses.dataclass(frozen=True)
class SmaliMethodDirective:
    """Parsed .method declaration.

    Attributes:
        modifiers: Sorted frozenset of modifiers, e.g. frozenset({"public", "static"}).
        descriptor: Full method descriptor, e.g. "getAppId()I".
    """

    modifiers: frozenset[str]
    descriptor: str


@dataclasses.dataclass(frozen=True)
class SmaliParamDirective:
    """Parsed .param directive.

    Attributes:
        register: Full register name, e.g. "p1".
        name: Parameter name from debug info, e.g. "macAddr".
        comment: Trailing comment, e.g. "Ljava/lang/String;", or None.
    """

    register: str
    name: str
    comment: str | None


@dataclasses.dataclass(frozen=True)
class SmaliLocalDirective:
    """Parsed .local directive.

    Attributes:
        register: Full register name, e.g. "p1" or "v9".
        name: Variable name from debug info, e.g. "list".
        type_descriptor: Type string after the colon, e.g. "Ljava/util/List;".
    """

    register: str
    name: str
    type_descriptor: str


@dataclasses.dataclass(frozen=True)
class SmaliConstInstruction:
    """Parsed const instruction.

    Attributes:
        variant: "wide" for const-wide, None for plain const.
        width: Width suffix like "4", "16", "32", "high16", or None for bare const/const-wide.
        dest_reg: Destination register, e.g. "v4".
        value: Integer value as a string, e.g. "0x5".
    """

    variant: str | None
    width: str | None
    dest_reg: str
    value: str


@dataclasses.dataclass(frozen=True)
class SmaliConstStringInstruction:
    """Parsed const-string instruction.

    Attributes:
        variant: "jumbo" for const-string/jumbo, None for plain const-string.
        dest_reg: Destination register, e.g. "v0".
        value: String literal value.
    """

    variant: str | None
    dest_reg: str
    value: str


@dataclasses.dataclass(frozen=True)
class SmaliIgetInstruction:
    """Parsed iget instruction.

    Attributes:
        variant: Suffix like "object", "wide", "boolean", or None for bare iget.
        dest_reg: Destination register, e.g. "v0".
        source_reg: Source object register, e.g. "p0".
        owner_class: JVM class path of the field's owner, e.g. "com/example/MyClass".
        field_name: Field name, e.g. "mCount".
        type_descriptor: JVM type descriptor, e.g. "I" or "Ljava/lang/String;".
    """

    variant: str | None
    dest_reg: str
    source_reg: str
    owner_class: str
    field_name: str
    type_descriptor: str


@dataclasses.dataclass(frozen=True)
class SmaliArrayLengthInstruction:
    """Parsed array-length instruction.

    Attributes:
        dest_reg: Destination register (receives the length), e.g. "v1".
        source_reg: Source register (the array), e.g. "v0".
    """

    dest_reg: str
    source_reg: str


@dataclasses.dataclass(frozen=True)
class SmaliMoveResultInstruction:
    """Parsed move-result instruction.

    Attributes:
        variant: Suffix like "object", "wide", or None for bare move-result.
        dest_reg: Destination register, e.g. "v0".
    """

    variant: str | None
    dest_reg: str


@dataclasses.dataclass(frozen=True)
class SmaliInvokeVirtualInstruction:
    """Parsed invoke-virtual instruction.

    Attributes:
        registers: List of registers, e.g. ["p1", "v1"].
        owner_class: JVM class path, e.g. "com/example/Foo".
        method_name: Method name, e.g. "readFromParcel".
        arg_descriptor: JVM argument type descriptor, e.g. "Landroid/os/Parcel;".
        return_descriptor: JVM return type descriptor, e.g. "V".
    """

    registers: list[str]
    owner_class: str
    method_name: str
    arg_descriptor: str
    return_descriptor: str


@dataclasses.dataclass(frozen=True)
class SmaliInvokeInterfaceInstruction:
    """Parsed invoke-interface instruction.

    Attributes:
        registers: List of registers, e.g. ["v3", "v4", "v0", "v1", "v5"].
        owner_class: JVM class path, e.g. "android/os/IBinder".
        method_name: Method name, e.g. "transact".
        arg_descriptor: JVM argument type descriptor, e.g. "ILandroid/os/Parcel;Landroid/os/Parcel;I".
        return_descriptor: JVM return type descriptor, e.g. "Z".
    """

    registers: list[str]
    owner_class: str
    method_name: str
    arg_descriptor: str
    return_descriptor: str


@dataclasses.dataclass(frozen=True)
class SmaliSignatureAnnotation:
    """Result of collecting a Signature annotation's fragments.

    Attributes:
        generic_signature: Concatenated fragment string, e.g. "Ljava/util/ArrayList<...>;".
        next_line: Line index immediately after .end annotation.
    """

    generic_signature: str
    next_line: int


def match_implements(line: str) -> SmaliImplementsDirective | None:
    """Match a .implements directive.

    Examples:
        >>> match_implements('.implements Landroid/os/Parcelable;')
        SmaliImplementsDirective(interface_path='android/os/Parcelable')
    """
    m = _SMALI_IMPLEMENTS_RE.match(line.strip())
    if not m:
        return None
    return SmaliImplementsDirective(interface_path=m.group(1))


def match_field(line: str) -> SmaliFieldDirective | None:
    """Match a field declaration.

    Examples:
        >>> match_field('.field private mFoo:Ljava/lang/String;')
        SmaliFieldDirective(modifiers=frozenset({'private'}), field_name='mFoo', type_descriptor='Ljava/lang/String;', value=None)
    """
    m = _SMALI_FIELD_RE.match(line.strip())
    if not m:
        return None
    modifiers = frozenset(m.group(1).split()) if m.group(1) else frozenset()
    return SmaliFieldDirective(
        modifiers=modifiers,
        field_name=m.group(2),
        type_descriptor=m.group(3),
        value=m.group(4),
    )


def match_method(line: str) -> SmaliMethodDirective | None:
    """Match a .method declaration.

    Examples:
        >>> match_method('.method public getAppId()I')
        SmaliMethodDirective(modifiers=frozenset({'public'}), descriptor='getAppId()I')
    """
    m = _SMALI_METHOD_RE.match(line.strip())
    if not m:
        return None
    modifiers = frozenset(m.group(1).split()) if m.group(1) else frozenset()
    return SmaliMethodDirective(modifiers=modifiers, descriptor=m.group(2))


def match_param(line: str) -> SmaliParamDirective | None:
    """Match a .param directive.

    Examples:
        >>> match_param('.param p1, "macAddr"    # Ljava/lang/String;')
        SmaliParamDirective(register='p1', name='macAddr', comment='Ljava/lang/String;')
    """
    m = _SMALI_PARAM_RE.match(line.strip())
    if not m:
        return None
    return SmaliParamDirective(register=m.group(1), name=m.group(2), comment=m.group(3))


def match_local(line: str) -> SmaliLocalDirective | None:
    """Match a .local directive.

    Examples:
        >>> match_local('.local p1, "list":Ljava/util/List;')
        SmaliLocalDirective(register='p1', name='list', type_descriptor='Ljava/util/List;')
    """
    m = _SMALI_LOCAL_RE.match(line.strip())
    if not m:
        return None
    return SmaliLocalDirective(register=m.group(1), name=m.group(2), type_descriptor=m.group(3))


def match_const(line: str) -> SmaliConstInstruction | None:
    """Match a const instruction.

    Examples:
        >>> match_const('const/4 v4, 0x5')
        SmaliConstInstruction(variant=None, width='4', dest_reg='v4', value='0x5')
    """
    m = _SMALI_CONST_RE.match(line.strip())
    if not m:
        return None
    return SmaliConstInstruction(
        variant=m.group(1) or None,
        width=m.group(2) or None,
        dest_reg=m.group(3),
        value=m.group(4),
    )


def match_const_string(line: str) -> SmaliConstStringInstruction | None:
    """Match a const-string instruction.

    Examples:
        >>> match_const_string('const-string v0, "com.example.IFoo"')
        SmaliConstStringInstruction(variant=None, dest_reg='v0', value='com.example.IFoo')
    """
    m = _SMALI_CONST_STRING_RE.match(line.strip())
    if not m:
        return None
    return SmaliConstStringInstruction(variant=m.group(1), dest_reg=m.group(2), value=m.group(3))


def match_iget(line: str) -> SmaliIgetInstruction | None:
    """Match an iget instruction that loads an instance field into a register.

    The destination register can be anything (v0, v1, etc.).
    The source register is the object to read from; in instance methods this is p0 (this).

    Examples:
        >>> match_iget('iget v0, p0, Lcom/example/MyClass;->mCount:I')
        SmaliIgetInstruction(variant=None, dest_reg='v0', source_reg='p0', owner_class='com/example/MyClass', field_name='mCount', type_descriptor='I')
    """
    m = _SMALI_IGET_RE.match(line.strip())
    if not m:
        return None
    return SmaliIgetInstruction(
        variant=m.group(1),
        dest_reg=m.group(2),
        source_reg=m.group(3),
        owner_class=m.group(4),
        field_name=m.group(5),
        type_descriptor=m.group(6),
    )


def match_array_length(line: str) -> SmaliArrayLengthInstruction | None:
    """Match an array-length instruction.

    Examples:
        >>> match_array_length('array-length v1, v0')
        SmaliArrayLengthInstruction(dest_reg='v1', source_reg='v0')
    """
    m = _SMALI_ARRAY_LENGTH_RE.match(line.strip())
    if not m:
        return None
    return SmaliArrayLengthInstruction(dest_reg=m.group(1), source_reg=m.group(2))


def match_move_result(line: str) -> SmaliMoveResultInstruction | None:
    """Match a move-result instruction.

    Examples:
        >>> match_move_result('move-result v0')
        SmaliMoveResultInstruction(variant=None, dest_reg='v0')
    """
    m = _SMALI_MOVE_RESULT_RE.match(line.strip())
    if not m:
        return None
    return SmaliMoveResultInstruction(variant=m.group(1), dest_reg=m.group(2))


def match_invoke_virtual(line: str) -> SmaliInvokeVirtualInstruction | None:
    """Match an invoke-virtual instruction.

    Examples:
        >>> match_invoke_virtual('invoke-virtual {p1, v1}, Lcom/example/Foo;->readFromParcel(Landroid/os/Parcel;)V')
        SmaliInvokeVirtualInstruction(registers=['p1', 'v1'], owner_class='com/example/Foo', method_name='readFromParcel', arg_descriptor='Landroid/os/Parcel;', return_descriptor='V')
    """
    m = _SMALI_INVOKE_VIRTUAL_RE.match(line.strip())
    if not m:
        return None
    regs = [r.strip() for r in m.group(1).split(",")]
    return SmaliInvokeVirtualInstruction(
        registers=regs,
        owner_class=m.group(2),
        method_name=m.group(3),
        arg_descriptor=m.group(4),
        return_descriptor=m.group(5),
    )


def match_invoke_interface(line: str) -> SmaliInvokeInterfaceInstruction | None:
    """Match an invoke-interface instruction.

    Examples:
        >>> match_invoke_interface('invoke-interface {v3, v4, v0, v1, v5}, Landroid/os/IBinder;->transact(ILandroid/os/Parcel;Landroid/os/Parcel;I)Z')
        SmaliInvokeInterfaceInstruction(registers=['v3', 'v4', 'v0', 'v1', 'v5'], owner_class='android/os/IBinder', method_name='transact', arg_descriptor='ILandroid/os/Parcel;Landroid/os/Parcel;I', return_descriptor='Z')
    """
    m = _SMALI_INVOKE_INTERFACE_RE.match(line.strip())
    if not m:
        return None
    regs = [r.strip() for r in m.group(1).split(",")]
    return SmaliInvokeInterfaceInstruction(
        registers=regs,
        owner_class=m.group(2),
        method_name=m.group(3),
        arg_descriptor=m.group(4),
        return_descriptor=m.group(5),
    )


def map_p_registers_to_arg_indices(types: list[str]) -> dict[int, int]:
    """Map p-register numbers to argument indices, accounting for wide types.

    p0 is always 'this' (skipped). long and double each occupy two consecutive
    registers; all other types occupy one. For example:

        types = ['long', 'int']  =>  {1: 0, 3: 1}
        types = ['int',  'int']  =>  {1: 0, 2: 1}
    """
    reg = 1  # p0 is 'this'; args start at p1
    result = {}
    for idx, t in enumerate(types):
        result[reg] = idx
        reg += 2 if t in ("long", "double") else 1
    return result


def parse_class_directive(lines: list[str]) -> SmaliClassDirective | None:
    """Parse the .class directive for the JVM class path.

    Returns a SmaliClassDirective or None.

    Examples:
        >>> parse_class_directive(['.class public final Lcom/example/MyClass;'])
        SmaliClassDirective(jvm_class_path='com/example/MyClass', package='com.example', class_name='MyClass')
    """
    for line in lines:
        m = _SMALI_CLASS_RE.match(line.strip())
        if m:
            full_path = m.group(1)
            parts = full_path.rsplit("/", 1)
            package = parts[0].replace("/", ".") if len(parts) == 2 else ""
            class_name = parts[-1]
            return SmaliClassDirective(jvm_class_path=full_path, package=package, class_name=class_name)
    return None


# Exact-match string for the opening line of a Dalvik generic method signature
# annotation block. Used as a string equality check to detect the start of a
# Ldalvik/annotation/Signature block.
_SIGNATURE_ANNOTATION_LINE = ".annotation system Ldalvik/annotation/Signature;"


def _collect_signature_annotation_from_fragments(lines: list[str], start: int) -> SmaliSignatureAnnotation:
    """Collect and concatenate Signature annotation fragments.

    Call this with start pointing to the line after the
    .annotation system Ldalvik/annotation/Signature; header.
    Reads until .end annotation and concatenates all quoted fragments.

    Args:
        lines: All lines from the smali file.
        start: Index of the first line inside the annotation body.
    """
    frags = []
    i = start
    while i < len(lines):
        ann_line = lines[i].strip()
        if ann_line == ".end annotation":
            i += 1
            break
        fm = _SMALI_SIGNATURE_FRAGMENT_RE.match(ann_line)
        if fm:
            frags.append(fm.group(1))
        i += 1
    return SmaliSignatureAnnotation(generic_signature="".join(frags), next_line=i)


def parse_signature_annotation(lines: list[str], i: int) -> SmaliSignatureAnnotation | None:
    """If the current line is a Signature annotation header, collect its fragments.

    Returns a SmaliSignatureAnnotation if line i is the annotation header, or None otherwise.
    The caller can use result.next_line to advance past the annotation.
    """
    if i < len(lines) and lines[i].strip() == _SIGNATURE_ANNOTATION_LINE:
        return _collect_signature_annotation_from_fragments(lines, i + 1)
    return None


def parse_field_generic_types(lines: list[str]) -> dict[str, str]:
    """Scan instance field declarations for Signature annotations.

    E.g.,
    ```smali
    .field private mEpgList:Ljava/util/ArrayList;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ljava/util/ArrayList<",
            "Lcom/example/Foo;",
            ">;"
        }
    .end annotation
    ```
    Returns a dict mapping field name to the reassembled generic JVM type string.
    E.g. the fragments above become:
    {'mEpgList': 'Ljava/util/ArrayList<Lcom/example/Foo;>;'}.

    Only fields with a Signature annotation are included; fields without
    generics are omitted since their erased type from iget is sufficient.
    """
    generic_types: dict[str, str] = {}
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()

        # Field declarations come before method declarations in smali files.
        # Once we hit a .method line, there can't be any more .field lines, so bail early.
        if stripped.startswith(".method"):
            break

        field = match_field(stripped)
        if field:
            field_name = field.field_name
            i += 1

            # Skip over blank lines
            while i < len(lines) and not lines[i].strip():
                i += 1

            # The smali format places annotations after their field.
            # If we reach a Signature annotation after the .field line,
            # it belongs to the preceding field.
            sig_ann = parse_signature_annotation(lines, i)
            if sig_ann is not None:
                i = sig_ann.next_line
                if sig_ann.generic_signature:
                    generic_types[field_name] = sig_ann.generic_signature
            continue

        i += 1

    return generic_types
