import os.path
import subprocess
from argparse import ArgumentParser
from collections import deque
from typing import Deque

import sys

from utils.errors import ErrorReporter


def get_arg_parser():
    p = ArgumentParser(
        description="""
                Deletes files or folders by moving them to the Trash.
            """
    )
    p.add_argument("files", nargs="+")
    return p


SCRIPT = """\
on run argv
    repeat with thePath in argv
        try
            tell application "Finder" to move (thePath as POSIX file) to trash
            log "ok:" & thePath
        on error errorText from errorSource
            log "ef:" & thePath
            log "et:" & errorText
        end try
    end repeat
end run
"""


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

    error_files: Deque[str] = deque()
    error_texts: Deque[str] = deque()
    error_count = 0

    def flush_errors():
        while len(error_files) > 0 and len(error_texts) > 0:
            error_file = error_files.popleft()
            error_message = error_texts.popleft()
            reporter.print_error(error_message, subject_file=error_file)

    for protocol_line in script_proc.stderr:
        if protocol_line.endswith("\n"):
            protocol_line = protocol_line[:-1]
        if protocol_line.startswith("ok:"):
            print(protocol_line[3:])
        elif protocol_line.startswith("ef:"):
            error_count += 1
            error_files.append(protocol_line[3:])
        elif protocol_line.startswith("et:"):
            error_texts.append(protocol_line[3:])
        else:
            print(f"?? {protocol_line!r}", file=sys.stderr)

        flush_errors()
    flush_errors()

    for prefix, queue in (("ef", error_files), ("et", error_texts)):
        for superfluous in queue:
            print(f"?? {prefix} {superfluous!r}", file=sys.stderr)

    osascript_exit = script_proc.wait(timeout=30)
    if osascript_exit != 0:
        return osascript_exit

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
