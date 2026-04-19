from pathlib import Path

from java._jar_cli import JarCli


class Smali(JarCli):
    """Python wrapper around the smali jar's command-line interface.

    Each public method maps one-to-one to a smali subcommand.
    """

    async def assemble(
        self,
        *,
        input_smali_dir: Path,
        output_dex: Path,
    ) -> None:
        """Run `smali assemble` to compile a directory of .smali files into a .dex.

        Args:
            input_smali_dir: Directory containing .smali source files to
                assemble.
            output_dex: Path where the resulting .dex file will be
                written.
        """
        await self._invoke("assemble", [str(input_smali_dir), "--output", str(output_dex)])
