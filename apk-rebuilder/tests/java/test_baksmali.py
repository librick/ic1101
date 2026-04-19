import asyncio
from pathlib import Path

from conftest import RecordingRunner

from java.baksmali import Baksmali


class TestBaksmali:
    def test_deodex_minimal_argv(self, recording_runner: RecordingRunner) -> None:
        baksmali = Baksmali(Path("/fake/baksmali.jar"), recording_runner)

        asyncio.run(
            baksmali.deodex(
                input_odex=Path("/in/services.odex"),
                output_dir=Path("/out/services"),
                api_level=31,
                bootclasspath=[Path("/bcp/core.jar")],
                classpath_dirs=None,
            )
        )

        assert recording_runner.calls == [
            [
                "java",
                "-jar",
                "/fake/baksmali.jar",
                "deodex",
                "--api",
                "31",
                "--bootclasspath",
                "/bcp/core.jar",
                "--output",
                "/out/services",
                "/in/services.odex",
            ]
        ]

    def test_deodex_joins_multiple_bootclasspath_with_colon(self, recording_runner: RecordingRunner) -> None:
        baksmali = Baksmali(Path("/fake/baksmali.jar"), recording_runner)

        asyncio.run(
            baksmali.deodex(
                input_odex=Path("/in/services.odex"),
                output_dir=Path("/out/services"),
                api_level=31,
                bootclasspath=[Path("/bcp/core.jar"), Path("/bcp/ext.jar")],
                classpath_dirs=None,
            )
        )

        argv = recording_runner.calls[0]
        bootclasspath_value = argv[argv.index("--bootclasspath") + 1]
        assert bootclasspath_value == "/bcp/core.jar:/bcp/ext.jar"

    def test_deodex_emits_classpath_dir_per_entry(self, recording_runner: RecordingRunner) -> None:
        baksmali = Baksmali(Path("/fake/baksmali.jar"), recording_runner)

        asyncio.run(
            baksmali.deodex(
                input_odex=Path("/in/services.odex"),
                output_dir=Path("/out/services"),
                api_level=31,
                bootclasspath=[Path("/bcp/core.jar")],
                classpath_dirs=[Path("/dep/a"), Path("/dep/b")],
            )
        )

        assert recording_runner.calls == [
            [
                "java",
                "-jar",
                "/fake/baksmali.jar",
                "deodex",
                "--api",
                "31",
                "--bootclasspath",
                "/bcp/core.jar",
                "--classpath-dir",
                "/dep/a",
                "--classpath-dir",
                "/dep/b",
                "--output",
                "/out/services",
                "/in/services.odex",
            ]
        ]
