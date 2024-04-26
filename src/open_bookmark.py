import subprocess
import sys

from config.bookmarks import bookmark


def main():
    func_name = sys.argv[1]
    func = bookmark[func_name]
    url = func(sys.argv[2:])
    return subprocess.run(["open", str(url)]).returncode


if __name__ == "__main__":
    sys.exit(main())
