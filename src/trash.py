import os.path
import subprocess
import sys
from argparse import ArgumentParser


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
    local errorCount
    set errorCount to 0
    repeat with thePath in argv
        try
            tell application "Finder" to move (thePath as POSIX file) to trash
            log thePath
        on error errorText from errorSource
            set errorCount to errorCount + 1
            log thePath & ": " & errorText
        end try
    end repeat

    if errorCount > 0 then
        error "Failed to move " & errorCount & " file(s) to the Trash."
    end if
end run
"""


def main():
    args = get_arg_parser().parse_args()
    cmd = ["osascript", "-e", SCRIPT]
    cmd.extend(os.path.abspath(p) for p in args.files)
    return subprocess.run(cmd).returncode


if __name__ == "__main__":
    sys.exit(main())
