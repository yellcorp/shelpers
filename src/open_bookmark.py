import subprocess

import sys

from shelpers.bookmarks import bookmark


def main():
    func_name = sys.argv[1]
    func = bookmark[func_name]
    url = func(sys.argv[2:])

    subprocess.run(
        ["open", str(url)],
        stdin=subprocess.DEVNULL,
        check=True,
    )


if __name__ == "__main__":
    main()
