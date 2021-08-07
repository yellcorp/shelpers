import sys

from config.bookmarks import bookmark
from utils.subproc import run_check_noinput


def main():
    func_name = sys.argv[1]
    func = bookmark[func_name]
    url = func(sys.argv[2:])

    run_check_noinput(
        ("open", str(url)),
    )


if __name__ == "__main__":
    main()
