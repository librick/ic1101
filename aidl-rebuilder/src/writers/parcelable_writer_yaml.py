from typing import IO

import yaml

from models_parcelable import Parcelable
from utils import path_relative_to_root
from writers.parcelable_writer import ParcelableWriter


class ParcelableWriterYaml(ParcelableWriter):
    """Writes a list of Parcelables to a YAML stream."""

    def __init__(self, stream: IO[str]):
        self._stream = stream

    def write(self, parcelables: list[Parcelable], smali_dirs: list[str]) -> None:
        output = []
        for p in parcelables:
            rel_path = path_relative_to_root(p.source_file, smali_dirs) if p.source_file else None
            output.append(
                {
                    "class_name": p.class_name,
                    "package": p.package,
                    "full_jvm_class": p.full_jvm_class,
                    "source_file": rel_path,
                    "serialization": [
                        {
                            "name": e.name,
                            "name_source": e.name_source,
                            "type": e.type,
                            "parcel_method": e.parcel_method,
                        }
                        for e in p.serialization
                    ],
                }
            )
        yaml.dump(
            output,
            self._stream,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
