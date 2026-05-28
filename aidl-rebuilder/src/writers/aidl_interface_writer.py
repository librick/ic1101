from abc import ABC, abstractmethod

from models_aidl import Interface


class AidlInterfaceWriter(ABC):
    """Abstract base class for serializing a list of Interface objects to an output stream."""

    def __enter__(self) -> "AidlInterfaceWriter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Releases any resources held by the writer. Override if needed."""
        pass

    @abstractmethod
    def write(self, interfaces: list[Interface], smali_dirs: list[str]) -> None:
        """Writes interfaces to the writer's output destination."""
        ...
