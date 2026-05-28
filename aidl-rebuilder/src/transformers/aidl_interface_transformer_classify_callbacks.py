from dataclasses import replace

from models_aidl import Interface
from transformers.aidl_interface_transformer import AidlInterfaceTransformer
from patterns_vendor import VENDOR_CALLBACK_PATTERNS


class AidlInterfaceTransformerClassifyCallbacks(AidlInterfaceTransformer):
    """Classifies AIDL interfaces as callbacks.

    An AIDL interface is considered a callback if its descriptor appears as an
    argument type in any method of any other AIDL interface in the provided list,
    or if its name matches a known callback/listener naming pattern.
    """

    def transform(self, interfaces: list[Interface]) -> list[Interface]:
        callback_descriptors = {arg.type for iface in interfaces for method in iface.methods for arg in method.args}

        return [replace(iface, is_callback=self._is_callback(iface, callback_descriptors)) for iface in interfaces]

    def _is_callback(self, iface: Interface, callback_descriptors: set[str]) -> bool:
        return iface.descriptor in callback_descriptors or self._name_matches_pattern(iface.interface_name)

    def _name_matches_pattern(self, interface_name: str) -> bool:
        return any(p.search(interface_name) for p in VENDOR_CALLBACK_PATTERNS)
