from pathlib import Path
from typing import Self

from file_utils import check_file_exists
from process.process_runner import ProcessResult, ProcessRunner


class JarCli:
    """Base class for wrappers around executable jar command-line tools.

    Subclasses add one method per subcommand. Each method builds the argv
    list specific to that subcommand and delegates to `_invoke`.
    Subclasses should never spawn processes directly.
    """

    def __init__(self, jar: Path, runner: ProcessRunner) -> None:
        self._jar = jar
        self._runner = runner

    @classmethod
    def build(cls, jar: Path, runner: ProcessRunner) -> Self:
        """Construct an instance, verifying the jar exists first."""
        check_file_exists(jar)
        return cls(jar, runner)

    async def _invoke(self, subcommand: str, args: list[str]) -> ProcessResult:
        argv = ["java", "-jar", str(self._jar), subcommand, *args]
        return await self._runner.run(argv)
