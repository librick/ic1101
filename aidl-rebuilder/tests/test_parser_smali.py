from parser_smali import (
    SmaliArrayLengthInstruction,
    SmaliConstInstruction,
    SmaliConstStringInstruction,
    SmaliFieldDirective,
    SmaliIgetInstruction,
    SmaliImplementsDirective,
    SmaliInvokeInterfaceInstruction,
    SmaliInvokeVirtualInstruction,
    SmaliLocalDirective,
    SmaliMethodDirective,
    SmaliMoveResultInstruction,
    SmaliParamDirective,
    match_array_length,
    match_const,
    match_const_string,
    match_field,
    match_iget,
    match_implements,
    match_invoke_interface,
    match_invoke_virtual,
    match_local,
    match_method,
    match_move_result,
    match_param,
)


def test_match_implements():
    result = match_implements(".implements Landroid/widget/ListAdapter;")
    assert result == SmaliImplementsDirective(interface_path="android/widget/ListAdapter")


def test_match_implements_rejects_class():
    assert match_implements(".class public final Lcom/example/MyClass;") is None


def test_match_field_object():
    result = match_field(".field volatile thread:Ljava/lang/Thread;")
    assert result == SmaliFieldDirective(
        modifiers=frozenset({"volatile"}),
        field_name="thread",
        type_descriptor="Ljava/lang/Thread;",
        value=None,
    )


def test_match_field_primitive():
    result = match_field(".field windowFlags:I")
    assert result == SmaliFieldDirective(
        modifiers=frozenset(),
        field_name="windowFlags",
        type_descriptor="I",
        value=None,
    )


def test_match_field_underscore_prefix():
    result = match_field(".field _texCoordPointer:Ljava/nio/Buffer;")
    assert result == SmaliFieldDirective(
        modifiers=frozenset(),
        field_name="_texCoordPointer",
        type_descriptor="Ljava/nio/Buffer;",
        value=None,
    )


def test_match_field_static():
    result = match_field(".field static sIsLogging:Z")
    assert result == SmaliFieldDirective(
        modifiers=frozenset({"static"}),
        field_name="sIsLogging",
        type_descriptor="Z",
        value=None,
    )


def test_match_field_static_final_with_value():
    result = match_field('.field static final WALLPAPER_INFO:Ljava/lang/String; = "wallpaper_info.xml"')
    assert result == SmaliFieldDirective(
        modifiers=frozenset({"static", "final"}),
        field_name="WALLPAPER_INFO",
        type_descriptor="Ljava/lang/String;",
        value='"wallpaper_info.xml"',
    )


def test_match_field_rejects_method():
    assert match_field(".method public getAppId()I") is None


def test_match_method_public():
    result = match_method(".method public writeUintArray([JII)V")
    assert result == SmaliMethodDirective(
        modifiers=frozenset({"public"}),
        descriptor="writeUintArray([JII)V",
    )


def test_match_method_package_private():
    result = match_method(".method writeLength(I)V")
    assert result == SmaliMethodDirective(
        modifiers=frozenset(),
        descriptor="writeLength(I)V",
    )


def test_match_method_private():
    result = match_method(".method private writeThumbnail(Lcom/android/gallery3d/exif/OrderedDataOutputStream;)V")
    assert result == SmaliMethodDirective(
        modifiers=frozenset({"private"}),
        descriptor="writeThumbnail(Lcom/android/gallery3d/exif/OrderedDataOutputStream;)V",
    )


def test_match_method_static():
    result = match_method(".method static weekDay(III)I")
    assert result == SmaliMethodDirective(
        modifiers=frozenset({"static"}),
        descriptor="weekDay(III)I",
    )


def test_match_method_multiple_modifiers():
    result = match_method(".method synthetic constructor <init>(Ljava/security/Security$1;)V")
    assert result == SmaliMethodDirective(
        modifiers=frozenset({"synthetic", "constructor"}),
        descriptor="<init>(Ljava/security/Security$1;)V",
    )


def test_match_method_rejects_field():
    assert match_method(".field private mFoo:Ljava/lang/String;") is None


def test_match_param_object():
    result = match_param('    .param p9, "x8"    # Landroid/view/View;')
    assert result == SmaliParamDirective(register="p9", name="x8", comment="Landroid/view/View;")


def test_match_param_primitive():
    result = match_param('    .param p9, "audioCodec"    # I')
    assert result == SmaliParamDirective(register="p9", name="audioCodec", comment="I")


def test_match_param_underscore_prefix():
    result = match_param('    .param p7, "_requiredPermission"    # Ljava/lang/String;')
    assert result == SmaliParamDirective(register="p7", name="_requiredPermission", comment="Ljava/lang/String;")


def test_match_param_rejects_local():
    assert match_param('    .local p1, "list":Ljava/util/List;') is None


def test_match_local_p_register():
    result = match_local('    .local p1, "list":Ljava/util/List;')
    assert result == SmaliLocalDirective(register="p1", name="list", type_descriptor="Ljava/util/List;")


def test_match_local_v_register():
    result = match_local('    .local v9, "win":Landroid/view/Window;')
    assert result == SmaliLocalDirective(register="v9", name="win", type_descriptor="Landroid/view/Window;")


def test_match_local_rejects_param():
    assert match_local('    .param p1, "macAddr"    # Ljava/lang/String;') is None


def test_match_const_bare():
    result = match_const("    const v0, 0x7f1000ba")
    assert result == SmaliConstInstruction(variant=None, width=None, dest_reg="v0", value="0x7f1000ba")


def test_match_const_4():
    result = match_const("    const/4 v2, 0x0")
    assert result == SmaliConstInstruction(variant=None, width="4", dest_reg="v2", value="0x0")


def test_match_const_16():
    result = match_const("    const/16 v21, 0x0")
    assert result == SmaliConstInstruction(variant=None, width="16", dest_reg="v21", value="0x0")


def test_match_const_wide():
    result = match_const("    const-wide/32 v2, 0x5265c00")
    assert result == SmaliConstInstruction(variant="wide", width="32", dest_reg="v2", value="0x5265c00")


def test_match_const_rejects_const_string():
    assert match_const('    const-string v0, "hello"') is None


def test_match_const_string():
    result = match_const_string('    const-string v9, "Unrecognized URI:"')
    assert result == SmaliConstStringInstruction(variant=None, dest_reg="v9", value="Unrecognized URI:")


def test_match_const_string_jumbo():
    result = match_const_string('    const-string/jumbo v1, "ro.build.version.codename"')
    assert result == SmaliConstStringInstruction(
        variant="jumbo",
        dest_reg="v1",
        value="ro.build.version.codename",
    )


def test_match_const_string_rejects_const_wide():
    assert match_const_string("    const-wide v0, 0x0L") is None


def test_match_const_string_rejects_const_int():
    assert match_const_string("    const/4 v4, 0x5") is None


def test_match_iget_bare():
    result = match_iget("    iget v9, v6, Landroid/content/pm/UserInfo;->id:I")
    assert result == SmaliIgetInstruction(
        variant=None,
        dest_reg="v9",
        source_reg="v6",
        owner_class="android/content/pm/UserInfo",
        field_name="id",
        type_descriptor="I",
    )


def test_match_iget_boolean():
    result = match_iget("    iget-boolean v0, p0, Landroid/animation/AnimatorSet;->mStarted:Z")
    assert result == SmaliIgetInstruction(
        variant="boolean",
        dest_reg="v0",
        source_reg="p0",
        owner_class="android/animation/AnimatorSet",
        field_name="mStarted",
        type_descriptor="Z",
    )


def test_match_iget_byte():
    result = match_iget("    iget-byte v3, v3, Landroid/os/BatteryStats$HistoryItem;->batteryLevel:B")
    assert result == SmaliIgetInstruction(
        variant="byte",
        dest_reg="v3",
        source_reg="v3",
        owner_class="android/os/BatteryStats$HistoryItem",
        field_name="batteryLevel",
        type_descriptor="B",
    )


def test_match_iget_object():
    result = match_iget("    iget-object v9, v9, Landroid/content/pm/ActivityInfo;->name:Ljava/lang/String;")
    assert result == SmaliIgetInstruction(
        variant="object",
        dest_reg="v9",
        source_reg="v9",
        owner_class="android/content/pm/ActivityInfo",
        field_name="name",
        type_descriptor="Ljava/lang/String;",
    )


def test_match_iget_wide():
    result = match_iget("    iget-wide v9, v8, Lcom/android/internal/os/BatteryStatsImpl$Timer;->mTotalTime:J")
    assert result == SmaliIgetInstruction(
        variant="wide",
        dest_reg="v9",
        source_reg="v8",
        owner_class="com/android/internal/os/BatteryStatsImpl$Timer",
        field_name="mTotalTime",
        type_descriptor="J",
    )


def test_match_iget_rejects_iput():
    assert match_iget("    iput-object v0, p0, Lcom/example/Foo;->mBar:Ljava/lang/String;") is None


def test_match_iget_rejects_sget():
    assert match_iget("    sget-object v0, Lcom/example/Foo;->INSTANCE:Lcom/example/Foo;") is None


def test_match_array_length_v_registers():
    result = match_array_length("    array-length v0, p1")
    assert result == SmaliArrayLengthInstruction(dest_reg="v0", source_reg="p1")


def test_match_array_length_p_registers():
    result = match_array_length("    array-length p1, p2")
    assert result == SmaliArrayLengthInstruction(dest_reg="p1", source_reg="p2")


def test_match_array_length_rejects_iget():
    assert match_array_length("    iget v1, v0, Lcom/example/Foo;->mCount:I") is None


def test_match_move_result_bare():
    result = match_move_result("    move-result v0")
    assert result == SmaliMoveResultInstruction(variant=None, dest_reg="v0")


def test_match_move_result_object():
    result = match_move_result("    move-result-object v10")
    assert result == SmaliMoveResultInstruction(variant="object", dest_reg="v10")


def test_match_move_result_wide():
    result = match_move_result("    move-result-wide v2")
    assert result == SmaliMoveResultInstruction(variant="wide", dest_reg="v2")


def test_match_invoke_virtual_multi_arg():
    result = match_invoke_virtual(
        "    invoke-virtual {v9, v8, v10, v3}, Lcom/android/org/bouncycastle/crypto/PBEParametersGenerator;->init([B[BI)V"
    )
    assert result == SmaliInvokeVirtualInstruction(
        registers=["v9", "v8", "v10", "v3"],
        owner_class="com/android/org/bouncycastle/crypto/PBEParametersGenerator",
        method_name="init",
        arg_descriptor="[B[BI",
        return_descriptor="V",
    )


def test_match_invoke_virtual_array_return():
    result = match_invoke_virtual(
        "        invoke-virtual {v9, v7, v8}, Lcom/android/inputmethod/keyboard/Keyboard;->getNearestKeys(II)[Lcom/android/inputmethod/keyboard/Key;"
    )
    assert result == SmaliInvokeVirtualInstruction(
        registers=["v9", "v7", "v8"],
        owner_class="com/android/inputmethod/keyboard/Keyboard",
        method_name="getNearestKeys",
        arg_descriptor="II",
        return_descriptor="[Lcom/android/inputmethod/keyboard/Key;",
    )


def test_match_invoke_virtual_float_return():
    result = match_invoke_virtual("        invoke-virtual {v9, v7}, Landroid/view/MotionEvent;->getX(I)F")
    assert result == SmaliInvokeVirtualInstruction(
        registers=["v9", "v7"],
        owner_class="android/view/MotionEvent",
        method_name="getX",
        arg_descriptor="I",
        return_descriptor="F",
    )


def test_match_invoke_virtual_chained_return():
    result = match_invoke_virtual(
        "         invoke-virtual {v9, v6}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;"
    )
    assert result == SmaliInvokeVirtualInstruction(
        registers=["v9", "v6"],
        owner_class="java/lang/StringBuilder",
        method_name="append",
        arg_descriptor="Ljava/lang/String;",
        return_descriptor="Ljava/lang/StringBuilder;",
    )


def test_match_invoke_virtual_rejects_invoke_interface():
    assert match_invoke_virtual("    invoke-interface {v8}, Lcom/example/IFoo;->bar()V") is None


def test_match_invoke_interface_no_args():
    result = match_invoke_interface("    invoke-interface {v8}, Ljavax/xml/transform/SourceLocator;->getLineNumber()I")
    assert result == SmaliInvokeInterfaceInstruction(
        registers=["v8"],
        owner_class="javax/xml/transform/SourceLocator",
        method_name="getLineNumber",
        arg_descriptor="",
        return_descriptor="I",
    )


def test_match_invoke_interface_primitive_arg():
    result = match_invoke_interface("    invoke-interface {v9, v5}, Landroid/database/Cursor;->getInt(I)I")
    assert result == SmaliInvokeInterfaceInstruction(
        registers=["v9", "v5"],
        owner_class="android/database/Cursor",
        method_name="getInt",
        arg_descriptor="I",
        return_descriptor="I",
    )


def test_match_invoke_interface_array_types():
    result = match_invoke_interface(
        "    invoke-interface {v9, v10}, Ljava/util/List;->toArray([Ljava/lang/Object;)[Ljava/lang/Object;"
    )
    assert result == SmaliInvokeInterfaceInstruction(
        registers=["v9", "v10"],
        owner_class="java/util/List",
        method_name="toArray",
        arg_descriptor="[Ljava/lang/Object;",
        return_descriptor="[Ljava/lang/Object;",
    )


def test_match_invoke_interface_multi_arg():
    result = match_invoke_interface(
        "    invoke-interface {v9, p2, p3, v0}, Landroid/text/Spanned;->getSpans(IILjava/lang/Class;)[Ljava/lang/Object;"
    )
    assert result == SmaliInvokeInterfaceInstruction(
        registers=["v9", "p2", "p3", "v0"],
        owner_class="android/text/Spanned",
        method_name="getSpans",
        arg_descriptor="IILjava/lang/Class;",
        return_descriptor="[Ljava/lang/Object;",
    )


def test_match_invoke_interface_rejects_invoke_virtual():
    assert (
        match_invoke_interface("    invoke-virtual {p1, v1}, Lcom/example/Foo;->readFromParcel(Landroid/os/Parcel;)V")
        is None
    )
