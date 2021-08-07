import os
from pathlib import Path


def to_path(p):
    return Path(os.fspath(p))


def unlink_if_exists(f):
    try:
        os.unlink(f)
    except FileNotFoundError:
        pass
