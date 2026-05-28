from typing import IO

import yaml

from models_aidl import Interface
from utils import path_relative_to_root
from writers.aidl_interface_writer import AidlInterfaceWriter


class AidlInterfaceWriterYaml(AidlInterfaceWriter):
    """Serializes a list of Interface objects to YAML format."""

    def __init__(self, stream: IO[str]) -> None:
        self._stream = stream

    def write(self, interfaces: list[Interface], smali_dirs: list[str]) -> None:
        yaml.dump(
            [self._to_dict(i, smali_dirs) for i in interfaces],
            self._stream,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    def _to_dict(self, iface: Interface, smali_dirs: list[str]) -> dict:
        def rel(path):
            return "./" + path_relative_to_root(path, smali_dirs)

        return {
            "interface": iface.interface_name,
            "package": iface.package,
            "descriptor": iface.descriptor,
            "is_callback": iface.is_callback,
            "stub": rel(iface.stub),
            "proxy": rel(iface.proxy),
            "constants": [
                {
                    "name": c.name,
                    "type": c.type,
                    "value": c.value,
                }
                for c in iface.constants
            ],
            "methods": [
                {
                    "name": m.name,
                    "transaction_code": m.transaction_code,
                    "is_oneway": m.is_oneway,
                    "args": [{"name": a.name, "type": a.type, "direction": a.direction} for a in m.args],
                    "return_type": m.return_type,
                }
                for m in iface.methods
            ],
        }
