import asyncio
from pathlib import Path

from conftest import RecordingRunner

from java.smali import Smali


class TestSmali:
    def test_assemble_builds_argv(self, recording_runner: RecordingRunner) -> None:
        smali = Smali(Path("/fake/smali.jar"), recording_runner)

        asyncio.run(
            smali.assemble(
                input_smali_dir=Path("/in/smali"),
                output_dex=Path("/out/classes.dex"),
            )
        )

        assert recording_runner.calls == [
            [
                "java",
                "-jar",
                "/fake/smali.jar",
                "assemble",
                "/in/smali",
                "--output",
                "/out/classes.dex",
            ]
        ]
