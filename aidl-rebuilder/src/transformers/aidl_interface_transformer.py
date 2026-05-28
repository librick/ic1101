from abc import ABC, abstractmethod

from models_aidl import Interface


class AidlInterfaceTransformer(ABC):
    """Abstract base class for transforming AIDL interfaces."""

    @abstractmethod
    def transform(self, interfaces: list[Interface]) -> list[Interface]:
        """Returns a new list of AIDL interfaces with transformation applied."""
        ...
