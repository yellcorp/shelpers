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
