from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

StreamHandler = Callable[[bytes], None]


@dataclass(frozen=True)
class ProcessResult:
    return_code: int
    stdout: bytes
    stderr: bytes


class ProcessSpawnFailed(Exception):
    def __init__(self, argv: list[str], reason: str) -> None:
        super().__init__(f"failed to spawn {argv[0]}: {reason}")
        self.argv = argv
        self.reason = reason


class ProcessFailed(Exception):
    _STDERR_SAMPLE_BYTES = 200

    def __init__(self, argv: list[str], result: ProcessResult) -> None:
        stderr_sample = result.stderr[: self._STDERR_SAMPLE_BYTES].decode("utf-8", errors="replace")
        super().__init__(f"{argv[0]} exited with code {result.return_code}: {stderr_sample}")
        self.argv = argv
        self.result = result


class ProcessTimeout(Exception):
    def __init__(self, argv: list[str], timeout: float) -> None:
        super().__init__(f"{argv[0]} exceeded timeout of {timeout}s and was killed")
        self.argv = argv
        self.timeout = timeout


class ProcessRunner(Protocol):
    async def run(
        self,
        argv: list[str],
        *,
        cwd: Path | None = None,
        stdout_handler: StreamHandler | None = None,
        stderr_handler: StreamHandler | None = None,
        timeout: float | None = None,  # noqa: ASYNC109 - drives subprocess kill/reap; caller-side timeout would leak child
    ) -> ProcessResult:
        """Run `argv` to completion.

        Raises:
            ProcessSpawnFailed: The subprocess could not be started
                (e.g. executable not found, permission denied).
            ProcessFailed: The subprocess exited with a non-zero code.
            ProcessTimeout: The subprocess did not complete within
                `timeout` seconds and was killed.
        """
        ...
