import logging

from models_parcelable import Parcelable
from parser_parcelables import parse_parcelable_file

logger = logging.getLogger(__name__)


def run_pipeline_parcelables(
    parcelable_paths: list[str],
) -> list[Parcelable]:
    """Parses Parcelable smali files into structured Parcelable definitions."""
    results: list[Parcelable] = []
    for path in parcelable_paths:
        result = parse_parcelable_file(path)
        if result is not None:
            results.append(result)
    logger.info("parsed %d parcelables with fields", len(results))
    return results
