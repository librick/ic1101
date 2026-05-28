from functools import reduce

from models_aidl import Interface
from parser_interfaces import parse_interfaces
from transformers.aidl_interface_transformer import AidlInterfaceTransformer
from transformers.aidl_interface_transformer_classify_callbacks import (
    AidlInterfaceTransformerClassifyCallbacks,
)


def _transform_interfaces(
    interfaces: list[Interface],
    transformers: list[AidlInterfaceTransformer],
) -> list[Interface]:
    return reduce(lambda ifaces, t: t.transform(ifaces), transformers, interfaces)


def run_pipeline_interfaces(
    proxy_paths: list[str],
    stub_paths: list[str],
) -> list[Interface]:
    """Parses proxy and stub files into AIDL interfaces and applies all transformations."""
    interfaces = parse_interfaces(proxy_paths, stub_paths)
    return _transform_interfaces(
        interfaces,
        [
            AidlInterfaceTransformerClassifyCallbacks(),
        ],
    )
