# Mapping of single-letter JVM type descriptors to Java primitive names
PRIMITIVES: dict[str, str] = {
    "B": "byte",
    "C": "char",
    "D": "double",
    "F": "float",
    "I": "int",
    "J": "long",
    "S": "short",
    "V": "void",
    "Z": "boolean",
}


def parse_jvm_type_erased(s: str) -> str:
    """Converts a single erased JVM type descriptor token to a Java type string.

    Examples:
        >>> parse_jvm_type_erased('I')
        'int'
        >>> parse_jvm_type_erased('Ljava/lang/String;')
        'java.lang.String'
        >>> parse_jvm_type_erased('[I')
        'int[]'
        >>> parse_jvm_type_erased('[[I')
        'int[][]'
    """
    array_depth = 0
    while s.startswith("["):
        array_depth += 1
        s = s[1:]

    if s.startswith("L") and s.endswith(";"):
        java_type = s[1:-1].replace("/", ".")
    elif s in PRIMITIVES:
        java_type = PRIMITIVES[s]
    else:
        java_type = s

    return java_type + "[]" * array_depth


def parse_jvm_type_list_erased(args_str: str) -> list[str]:
    """Parses the argument portion of an erased JVM method descriptor into a list of Java type strings.

    The input should be the content between '(' and ')' in a method descriptor.

    Examples:
        >>> parse_type_list_erased('Ljava/lang/String;I[Lcom/foo/Bar;')
        ['java.lang.String', 'int', 'com.foo.Bar[]']
        >>> parse_type_list_erased('[I')
        ['int[]']
        >>> parse_type_list_erased('')
        []
    """
    types = []
    i = 0
    while i < len(args_str):
        array_prefix = ""
        while i < len(args_str) and args_str[i] == "[":
            array_prefix += "["
            i += 1
        if i >= len(args_str):
            break
        c = args_str[i]
        if c == "L":
            end = args_str.index(";", i)
            raw = array_prefix + args_str[i : end + 1]
            types.append(parse_jvm_type_erased(raw))
            i = end + 1
        elif c in PRIMITIVES:
            types.append(parse_jvm_type_erased(array_prefix + c))
            i += 1
        else:
            i += 1
    return types


def _parse_jvm_type_generic_recursive(s: str, i: int) -> tuple[str, int]:
    """Recursive descent parser for a single generic JVM type starting at index i.

    Returns a tuple of (java_type_string, new_index). Handles primitives,
    object types, generic types, arrays, wildcards, type variables, and
    nested generics.

    Examples:
        >>> _parse_jvm_type_generic_recursive('I', 0)
        ('int', 1)
        >>> _parse_jvm_type_generic_recursive('Ljava/lang/String;', 0)
        ('java.lang.String', 18)
        >>> _parse_jvm_type_generic_recursive('[I', 0)
        ('int[]', 2)
        >>> _parse_jvm_type_generic_recursive('Ljava/util/List<Lcom/honda/displayaudio/system/traffic/LtnSid;>;', 0)
        ('java.util.List<com.honda.displayaudio.system.traffic.LtnSid>', 64)
        >>> _parse_jvm_type_generic_recursive('IIZI', 2)
        ('boolean', 3)
    """
    array_depth = 0
    while i < len(s) and s[i] == "[":
        array_depth += 1
        i += 1

    if i >= len(s):
        return ("", i)

    c = s[i]

    # Primitive
    if c in PRIMITIVES:
        return (PRIMITIVES[c] + "[]" * array_depth, i + 1)

    # Object or generic type: L<classname>(<type_args>)?;
    if c == "L":
        i += 1
        j = i
        while j < len(s) and s[j] not in ("<", ";"):
            j += 1
        class_name = s[i:j].replace("/", ".")

        if j < len(s) and s[j] == "<":
            j += 1  # skip '<'
            type_args = []
            while j < len(s) and s[j] != ">":
                if s[j] == "*":
                    type_args.append("?")
                    j += 1
                elif s[j] == "+":
                    j += 1
                    arg, j = _parse_jvm_type_generic_recursive(s, j)
                    type_args.append(f"? extends {arg}")
                elif s[j] == "-":
                    j += 1
                    arg, j = _parse_jvm_type_generic_recursive(s, j)
                    type_args.append(f"? super {arg}")
                else:
                    arg, j = _parse_jvm_type_generic_recursive(s, j)
                    type_args.append(arg)
            j += 1  # skip '>'
            if j < len(s) and s[j] == ";":
                j += 1
            result = f"{class_name}<{', '.join(type_args)}>" + "[]" * array_depth
        else:
            if j < len(s) and s[j] == ";":
                j += 1
            result = class_name + "[]" * array_depth

        return (result, j)

    # Type variable: T<name>;
    if c == "T":
        i += 1
        j = i
        while j < len(s) and s[j] != ";":
            j += 1
        type_var = s[i:j]
        j += 1  # skip ';'
        return (type_var + "[]" * array_depth, j)

    # Unknown character, skip
    return ("", i + 1)


def parse_jvm_type_generic(s: str) -> str:
    """Parse a single generic JVM type descriptor to a Java type string."""
    result, _ = _parse_jvm_type_generic_recursive(s, 0)
    return result


def parse_jvm_type_list_generic(s: str) -> list[str]:
    """Parses the argument portion of a generic JVM method signature into a list of Java type strings.

    The input should be the content between '(' and ')' in the concatenated
    Signature annotation value.

    Examples:
        >>> parse_type_list_generic('IIZILjava/util/List<Lcom/honda/displayaudio/system/traffic/LtnSid;>;')
        ['int', 'int', 'boolean', 'int', 'java.util.List<com.honda.displayaudio.system.traffic.LtnSid>']
        >>> parse_type_list_generic('ILjava/util/List<Lcom/honda/displayaudio/system/traffic/RDSTMCServiceInfo;>;')
        ['int', 'java.util.List<com.honda.displayaudio.system.traffic.RDSTMCServiceInfo>']
    """
    types = []
    i = 0
    while i < len(s):
        t, i = _parse_jvm_type_generic_recursive(s, i)
        if t:
            types.append(t)
    return types


def parse_signature_arg_str(sig_str: str) -> str | None:
    """Given a concatenated Signature annotation value like
    '(Ljava/util/List<Lcom/foo/Bar;>;I)Z', extract and return the argument
    portion between '(' and ')'.

    Tracks '<>' depth so that a ')' inside a type argument is not mistaken
    for the closing paren of the argument list.
    Returns None if the string is not a well-formed method signature.
    """
    if not sig_str.startswith("("):
        return None

    depth = 0
    i = 1
    while i < len(sig_str):
        c = sig_str[i]
        if c == "<":
            depth += 1
        elif c == ">":
            depth -= 1
        elif c == ")" and depth == 0:
            return sig_str[1:i]
        i += 1

    return None  # no closing ')' found
