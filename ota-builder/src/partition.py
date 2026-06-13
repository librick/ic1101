from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class Partition:
    block_dev: str
    mount_point: str
    fs_type: str
    storage: str
    children: tuple[Partition, ...] = ()


def preorder(partitions: tuple[Partition, ...]) -> Iterator[Partition]:
    """Yield each partition before its children (mount order)."""
    for partition in partitions:
        yield partition
        yield from preorder(partition.children)


def postorder(partitions: tuple[Partition, ...]) -> Iterator[Partition]:
    """Yield each partition after its children (unmount order)."""
    for partition in partitions:
        yield from postorder(partition.children)
        yield partition


def owner(target: str, partitions: tuple[Partition, ...]) -> Partition | None:
    """Return the deepest partition whose mount point is a path-prefix of target, or None."""
    for partition in partitions:
        if target == partition.mount_point or target.startswith(partition.mount_point + "/"):
            return owner(target, partition.children) or partition
    return None
