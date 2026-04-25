from pathlib import Path

import pytest

from process.process_runner import ProcessResult, StreamHandler


class RecordingRunner:
    """ProcessRunner stub that records argv and returns a success result."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    async def run(
        self,
        argv: list[str],
        *,
        cwd: Path | None = None,
        stdout_handler: StreamHandler | None = None,
        stderr_handler: StreamHandler | None = None,
        timeout: float | None = None,  # noqa: ASYNC109 - matches ProcessRunner protocol
    ) -> ProcessResult:
        self.calls.append(argv)
        return ProcessResult(return_code=0, stdout=b"", stderr=b"")


@pytest.fixture
def recording_runner() -> RecordingRunner:
    return RecordingRunner()
