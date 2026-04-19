import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from logger import configure_logging
from pipeline import PipelineError, run_pipeline
from process.process_runner import ProcessFailed, ProcessSpawnFailed, ProcessTimeout

logger = logging.getLogger(__name__)


def _positive_int(value: str) -> int:
    n = int(value)
    if n < 1:
        raise argparse.ArgumentTypeError(f"must be >= 1, got {n}")
    return n


async def main() -> None:
    parser = argparse.ArgumentParser(description="Deodex and decode an Android update image.")
    parser.add_argument(
        "--input-dir",
        type=Path,
        required=True,
        help="Directory containing the tool jars (baksmali, smali, apktool) and the input .zip archive.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where all pipeline output will be written.",
    )
    parser.add_argument(
        "--jvm-jobs",
        type=_positive_int,
        default=os.process_cpu_count() or 1,
        help=(
            "Maximum number of Java tool subprocesses to run concurrently within each "
            + "pipeline phase. Higher values use more memory (~100-200MB per JVM) but "
            + "reduce wall-clock time roughly proportionally up to the CPU count. "
            + "Defaults to the number of CPUs available to this process."
        ),
    )
    args = parser.parse_args()

    configure_logging()

    try:
        await run_pipeline(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            jvm_jobs=args.jvm_jobs,
        )
    except (PipelineError, OSError, ProcessFailed, ProcessTimeout, ProcessSpawnFailed):
        logger.exception("pipeline failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
