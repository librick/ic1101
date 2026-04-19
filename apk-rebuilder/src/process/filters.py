import re

from process.process_runner import StreamHandler


def filter_lines(
    downstream: StreamHandler,
    drop_patterns: list[re.Pattern[str]],
) -> StreamHandler:
    """Wrap a StreamHandler so lines matching any drop_pattern are silently discarded.

    Patterns are applied as str (UTF-8 decoded with errors='replace');
    the downstream handler still receives the original bytes unchanged.
    """

    def filtered(line: bytes) -> None:
        line_str = line.decode("utf-8", errors="replace")
        if any(p.match(line_str) for p in drop_patterns):
            return
        downstream(line)

    return filtered
