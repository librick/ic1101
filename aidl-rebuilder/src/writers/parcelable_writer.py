from abc import ABC, abstractmethod

from models_parcelable import Parcelable


class ParcelableWriter(ABC):
    """Abstract base class for serializing a list of Parcelable objects to an output stream."""

    def __enter__(self) -> "ParcelableWriter":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """Releases any resources held by the writer. Override if needed."""
        pass

    @abstractmethod
    def write(self, parcelables: list[Parcelable], smali_dirs: list[str]) -> None:
        """Writes parcelables to the writer's output destination."""
        ...
