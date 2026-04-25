import asyncio
import contextlib
from asyncio.subprocess import PIPE
from pathlib import Path

from process.process_runner import (
    ProcessFailed,
    ProcessResult,
    ProcessRunner,
    ProcessSpawnFailed,
    ProcessTimeout,
    StreamHandler,
)

_READ_CHUNK_SIZE = 8192


async def _drain(
    stream: asyncio.StreamReader,
    chunks: list[bytes],
    handler: StreamHandler | None,
) -> None:
    """Read `stream` to EOF, emitting each newline-terminated line to `chunks` and `handler`.

    Unlike `StreamReader.readline`, this has no per-line size limit - lines
    of any length are buffered until a newline arrives or the stream hits
    EOF. At EOF, any trailing unterminated content is emitted as a final
    line.
    """
    buffer = bytearray()
    while True:
        data = await stream.read(_READ_CHUNK_SIZE)
        if not data:
            # EOF; flush any trailing unterminated line.
            if buffer:
                final = bytes(buffer)
                chunks.append(final)
                if handler is not None:
                    handler(final)
            return
        buffer.extend(data)
        # Emit every complete (newline-terminated) line currently in the buffer.
        while True:
            newline_index = buffer.find(b"\n")
            if newline_index == -1:
                break
            line = bytes(buffer[: newline_index + 1])
            del buffer[: newline_index + 1]
            chunks.append(line)
            if handler is not None:
                handler(line)


class ProcessRunnerAsyncio(ProcessRunner):
    def __init__(
        self,
        *,
        default_cwd: Path | None = None,
        default_timeout: float | None = None,
        default_stdout_handler: StreamHandler | None = None,
        default_stderr_handler: StreamHandler | None = None,
    ) -> None:
        self._default_cwd = default_cwd
        self._default_timeout = default_timeout
        self._default_stdout_handler = default_stdout_handler
        self._default_stderr_handler = default_stderr_handler

    async def run(
        self,
        argv: list[str],
        *,
        cwd: Path | None = None,
        stdout_handler: StreamHandler | None = None,
        stderr_handler: StreamHandler | None = None,
        timeout: float | None = None,  # noqa: ASYNC109 - drives subprocess kill/reap; caller-side timeout would leak child
    ) -> ProcessResult:
        effective_cwd = cwd if cwd is not None else self._default_cwd
        effective_timeout = timeout if timeout is not None else self._default_timeout
        effective_stdout = stdout_handler if stdout_handler is not None else self._default_stdout_handler
        effective_stderr = stderr_handler if stderr_handler is not None else self._default_stderr_handler

        try:
            proc = await asyncio.create_subprocess_exec(*argv, cwd=effective_cwd, stdout=PIPE, stderr=PIPE)
        except (FileNotFoundError, PermissionError, OSError) as e:
            raise ProcessSpawnFailed(argv, str(e)) from e

        if proc.stdout is None or proc.stderr is None:
            # Should never happen - we requested PIPE for both
            raise RuntimeError(f"{argv[0]}: subprocess pipes unexpectedly None")

        stdout_chunks: list[bytes] = []
        stderr_chunks: list[bytes] = []

        drain_and_wait = asyncio.gather(
            _drain(proc.stdout, stdout_chunks, effective_stdout),
            _drain(proc.stderr, stderr_chunks, effective_stderr),
            proc.wait(),
        )

        try:
            try:
                if effective_timeout is None:
                    await drain_and_wait
                else:
                    await asyncio.wait_for(drain_and_wait, timeout=effective_timeout)
            except TimeoutError as e:
                if effective_timeout is None:
                    # Should never happen - wait_for only entered when set
                    raise RuntimeError(f"{argv[0]}: TimeoutError raised with no effective_timeout") from e
                with contextlib.suppress(ProcessLookupError):
                    proc.kill()
                await proc.wait()
                raise ProcessTimeout(argv, effective_timeout) from e
        except BaseException:
            # Cancellation or any other unexpected exception: make sure the
            # child is not left running before the exception propagates.
            if proc.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    proc.kill()
                await proc.wait()
            raise

        return_code = proc.returncode
        if return_code is None:
            # Should never happen
            raise RuntimeError(f"{argv[0]}: returncode is None after wait() completed")

        result = ProcessResult(
            return_code=return_code,
            stdout=b"".join(stdout_chunks),
            stderr=b"".join(stderr_chunks),
        )
        if return_code != 0:
            raise ProcessFailed(argv, result)
        return result
