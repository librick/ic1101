import asyncio
from pathlib import Path

from conftest import RecordingRunner

from java.apktool import Apktool


class TestApktool:
    def test_install_framework_builds_argv(self, recording_runner: RecordingRunner) -> None:
        apktool = Apktool(Path("/fake/apktool.jar"), recording_runner)

        asyncio.run(
            apktool.install_framework(
                framework_apk=Path("/in/framework-res.apk"),
                framework_tag="android",
            )
        )

        assert recording_runner.calls == [
            [
                "java",
                "-jar",
                "/fake/apktool.jar",
                "install-framework",
                "/in/framework-res.apk",
                "--frame-tag",
                "android",
            ]
        ]

    def test_decode_builds_argv(self, recording_runner: RecordingRunner) -> None:
        apktool = Apktool(Path("/fake/apktool.jar"), recording_runner)

        asyncio.run(
            apktool.decode(
                input_apk=Path("/in/app.apk"),
                output_dir=Path("/out/app"),
                framework_tag="android",
            )
        )

        assert recording_runner.calls == [
            [
                "java",
                "-jar",
                "/fake/apktool.jar",
                "decode",
                "/in/app.apk",
                "--frame-tag",
                "android",
                "--output",
                "/out/app",
            ]
        ]
