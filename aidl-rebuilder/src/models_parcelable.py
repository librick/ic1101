from dataclasses import dataclass, field


@dataclass
class ParcelableEntry:
    """A single entry in a Parcelable's writeToParcel serialization sequence."""

    name: str
    """Name associated with this entry. May be a field name (from iget) or
    a property name inferred from a getter (from getXxx)."""

    name_source: str
    """How the name was determined: 'field' (from iget, reliable) or 
    'getter' (inferred from method name, best-guess)."""

    type: str
    """Java type name (e.g. 'String', 'int', 'ArrayList<Foo>')."""

    parcel_method: str
    """The Parcel.writeXxx method used to serialize this entry (e.g. 'writeString', 'writeInt')."""


@dataclass
class Parcelable:
    """A parsed Parcelable class."""

    class_name: str
    """Simple class name (e.g. 'WifiRegisterDeviceData')."""

    package: str
    """Dotted package name (e.g. 'com.mitsubishielectric.ada.framework.vehicledbmanager')."""

    full_jvm_class: str
    """Full JVM class path (e.g. 'com/mitsubishielectric/ada/framework/vehicledbmanager/WifiRegisterDeviceData')."""

    serialization: list[ParcelableEntry] = field(default_factory=list)
    """Entries in serialization order (as they appear in writeToParcel)."""

    source_file: str | None = None
    """Path to the .smali file this was parsed from."""
