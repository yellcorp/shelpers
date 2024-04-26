import os
import pathlib
import re
import subprocess
from functools import lru_cache
from typing import List, Optional

MDFIND = "/usr/bin/mdfind"


class BundleError(Exception):
    pass


def find_all_apps_by_bundle_id(bundle_id: str) -> List[str]:
    escaped = re.sub(r"[\x22\x27\x2A\x3F\x5C]", r"\\\g<0>", bundle_id)
    quoted = f'"{escaped}"'
    query = f"kMDItemCFBundleIdentifier={quoted}"
    args = [MDFIND, "-0", query]
    proc_result = subprocess.run(
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        check=True,
        text=True,
    )
    return [match for match in proc_result.stdout.split("\x00") if len(match) > 0]


@lru_cache(maxsize=128)
def find_app_by_bundle_id(bundle_id: str) -> Optional[str]:
    paths = find_all_apps_by_bundle_id(bundle_id)
    if len(paths) == 0:
        return None
    if len(paths) == 1:
        return paths[0]
    raise BundleError(f"Multiple results (bundle_id={bundle_id!r})")


class BundlePath:
    def __init__(self, bundle_id: str, rel_path=None):
        self.bundle_id = bundle_id
        self.rel_path = pathlib.Path(os.curdir if rel_path is None else rel_path)

    def __truediv__(self, other):
        return BundlePath(self.bundle_id, self.rel_path / other)

    def __repr__(self):
        return (
            "{0.__class__.__name__}"
            "(bundle_id={0.bundle_id!r},"
            " rel_path={0.rel_path!r})".format(self)
        )

    def __str__(self):
        return str(self.evaluate())

    def __fspath__(self):
        return os.fspath(self.evaluate())

    def evaluate(self):
        app_path = find_app_by_bundle_id(self.bundle_id)
        if app_path is None:
            raise BundleError(
                f"Application bundle not found (bundle_id={self.bundle_id!r})"
            )
        return pathlib.Path(app_path) / self.rel_path
