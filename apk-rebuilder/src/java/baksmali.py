from pathlib import Path

from java._jar_cli import JarCli


class Baksmali(JarCli):
    """Python wrapper around the baksmali jar's command-line interface.

    Each public method maps one-to-one to a baksmali subcommand.
    """

    async def deodex(
        self,
        *,
        input_odex: Path,
        output_dir: Path,
        api_level: int,
        bootclasspath: list[Path],
        classpath_dirs: list[Path] | None = None,
    ) -> None:
        """Disassemble a single .odex file to .smali via `baksmali deodex`.

        Produces a tree of .smali text files under `output_dir`, one per
        class, organized into directories matching each class's package.
        Smali is the human-readable assembly form of Dalvik bytecode;
        `baksmali deodex` resolves the quick/inline opcodes in the odex
        back to symbolic references using `bootclasspath`, so the emitted
        smali matches what you'd get by disassembling the pre-optimization
        dex directly.

        Args:
            input_odex: Passed as the final positional argument. The .odex
                file to deodex.
            output_dir: Passed as `--output`. Directory where the resulting
                .smali files will be written.
            api_level: Passed as `--api`. The Android API level the .odex was
                compiled for (e.g. 17 for Android 4.2.2).
            bootclasspath: Ordered list of jars; joined with `:` and passed as
                `--bootclasspath`. Order should match the device's BOOTCLASSPATH
                so baksmali resolves class references the same way dexopt did.
                On fully-odexed devices these jars are typically stubs containing
                only a manifest; the actual bytecode lives in sibling .odex files
                that baksmali locates via `classpath_dirs`.
            classpath_dirs: Each is passed as a separate `--classpath-dir` flag;
                None means no `--classpath-dir` flags are passed. These are the
                directories baksmali will search to locate the jars named in
                `bootclasspath` and their paired .odex files.
        """
        args = [
            "--api",
            str(api_level),
            "--bootclasspath",
            ":".join(str(j) for j in bootclasspath),
        ]
        for d in classpath_dirs or []:
            args += ["--classpath-dir", str(d)]
        args += ["--output", str(output_dir), str(input_odex)]
        await self._invoke("deodex", args)
