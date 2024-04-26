import html
import os.path
import subprocess
import sys
from argparse import ArgumentParser
from dataclasses import dataclass
from typing import Optional

from utils.errors import ErrorReporter


def get_arg_parser():
    p = ArgumentParser(
        description="""
            Deletes files or folders by moving them to the Trash.
        """
    )
    p.add_argument("files", nargs="+")
    return p


# [0] A crude html entity escaping is chosen because AppleScript has no
#     built-in hex conversion, and HTML entities are an established scheme
#     that can use base-10 for codepoints.
#
# [1] The `id` of a one-character string is a single integer. In all other
#     cases, it's a list of integers. The id of a zero-character string is
#     an empty list.
#
# [2] Don't know why this is necessary, but if it's not done, integer
#     equality never returns true. Got the idea from here
#     https://github.com/mgax/applescript-json/blob/master/json.applescript
#
# [3] Characters to escape. Everything below space, plus line delimiters
#     as understood by `str.splitlines`. Everything else including astral
#     plane characters should be ok.
#         32: space
#         38: ampersand
#        133: NEL (0x85)
#       8232: line separator (0x2028)
#       8233: paragraph separator (0x2029)

SCRIPT = """\
on escapeString(theString) -- [0]
    set escaped to ""

    set codepoints to id of theString
    if (class of codepoints) is not list
        set codepoints to {codepoints} -- [1]
    end

    repeat with cc in codepoints
        set cc to cc as integer -- [2]
        if cc < 32 or cc = 38 or cc = 133 or cc = 8232 or cc = 8233 then -- [3]
            set eseq to "&#" & cc & ";"
        else
            set eseq to character id cc
        end
        set escaped to escaped & eseq
    end repeat
    return escaped
end

on run argv
    repeat with thePath in argv
        log "fn:" & escapeString(thePath)
        try
            tell application "Finder" to move (thePath as POSIX file) to trash
            log "ok:1"
        on error errorText number errorNumber from errorSource
            log "ok:0"
            log "et:" & escapeString(errorText as text)
            log "en:" & escapeString(errorNumber as text)
        end try
    end repeat
end run
"""


@dataclass
class TrashResult:
    filename: str = ""
    ok: bool = False
    error_text: str = ""
    error_number: str = ""


def split_line(line: str) -> tuple[str, str, str]:
    return line[:2], line[2:3], line[3:]


class LineParser:
    def __init__(self, error_reporter: Optional[ErrorReporter] = None):
        self._error_reporter = error_reporter

        self._state = 0
        self._line_text = ""
        self._line_n = -1
        self._panics = 0

        self._result = TrashResult()
        self._accepted: list[TrashResult] = []

        self._dispatch = [
            ("fn", self._parse_filename),
            ("ok", self._parse_ok),
            ("et", self._parse_error_text),
            ("en", self._parse_error_number),
        ]

    @property
    def protocol_error_count(self):
        return self._panics

    def parse_lines(self, line_iter):
        for line_n, line in enumerate(line_iter):
            self._line_text = line
            self._line_n = line_n

            prefix, colon, detail_escaped = split_line(line.rstrip("\r\n"))
            if colon != ":":
                self._panic("Formatting error")
                continue

            detail = html.unescape(detail_escaped)
            expected_prefix, handler = self._dispatch[self._state]
            if prefix != expected_prefix:
                self._panic(f"Wrong prefix: {expected_prefix=!r}")
                continue

            self._state += 1
            handler(detail)

            if self._accepted:
                yield from self._accepted
                self._accepted.clear()

        if self._state != 0:
            self._panic("Unexpected end of input")

    def _parse_filename(self, detail: str):
        if detail:
            self._result.filename = detail
        else:
            self._panic("Empty filename")

    def _parse_ok(self, detail: str):
        if detail == "0":
            self._result.ok = False
        elif detail == "1":
            self._result.ok = True
            self._accept()
        else:
            self._panic("Invalid value for 'ok'")

    def _parse_error_text(self, detail: str):
        self._result.error_text = detail

    def _parse_error_number(self, detail: str):
        self._result.error_number = detail
        self._accept()

    def _accept(self):
        self._accepted.append(self._result)
        self._reset()

    def _panic(self, message: str):
        self._panics += 1

        if self._error_reporter is not None:
            self._error_reporter.print_error(
                f"{message} at line {self._line_n} line_text={self._line_text!r}"
            )
        self._reset()

    def _reset(self):
        self._result = TrashResult()
        self._state = 0


def main():
    args = get_arg_parser().parse_args()
    reporter = ErrorReporter.from_argv()

    cmd = ["/usr/bin/osascript", "-"]
    cmd.extend(os.path.abspath(p) for p in args.files)

    script_proc = subprocess.Popen(
        cmd,
        bufsize=1,
        text=True,
        stdin=subprocess.PIPE,
        stdout=None,  # AppleScript 'log' outputs to stderr
        stderr=subprocess.PIPE,
    )
    script_proc.stdin.write(SCRIPT)
    script_proc.stdin.close()

    parser = LineParser(reporter)
    consume_errors = 0
    failures = 0
    for file_index, result in enumerate(parser.parse_lines(script_proc.stderr)):
        if file_index < len(args.files):
            user_file = args.files[file_index]
            if result.ok:
                print(user_file)
            else:
                message = [
                    result.error_text or "<no error text>",
                ]

                if result.error_number:
                    message.append(f" ({result.error_number})")

                reporter.print_error("".join(message), subject_file=user_file)
                failures += 1
        else:
            consume_errors += 1
            reporter.print_error(f"Excess result: {result!r}")

    if consume_errors > 0 or parser.protocol_error_count > 0:
        return 2

    if failures > 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
