import re
from dataclasses import dataclass


LOG_LINE_RE = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}) "
    r"(?P<logger>[\w.]+)\((?P<line>\d+)\) "
    r"(?P<level>[A-Z]+): (?P<message>.*)$"
)


@dataclass
class ParsedLogLine:
    timestamp: str
    logger: str
    source_line: str
    level: str
    message: str
    raw: str


def parse_volttron_log(content: str) -> list[ParsedLogLine]:
    entries: list[ParsedLogLine] = []

    for line in content.splitlines():
        match = LOG_LINE_RE.match(line)
        if match:
            entries.append(
                ParsedLogLine(
                    timestamp=match.group("timestamp"),
                    logger=match.group("logger"),
                    source_line=match.group("line"),
                    level=match.group("level"),
                    message=match.group("message"),
                    raw=line,
                )
            )
        elif entries:
            entries[-1].message = f"{entries[-1].message}\n{line}"
            entries[-1].raw = f"{entries[-1].raw}\n{line}"
        elif line:
            entries.append(
                ParsedLogLine(
                    timestamp="",
                    logger="",
                    source_line="",
                    level="TEXT",
                    message=line,
                    raw=line,
                )
            )

    return entries

