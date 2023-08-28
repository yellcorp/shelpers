"""
Adobe Bridge includes its version number in its bundle identifier, so if I
want this to work across multiple machines with possibly different versions
installed, or if I just don't want to reupdate the launcher every major
version bump, it's a little more fussy that just using BundleOpener to drop
a shell script that calls open -b. I blame myself for being someone who
actually sometimes uses Bridge.
"""

import plistlib
import subprocess
import sys
import os.path

from utils.macos.appbundle import MDFIND

OPEN = "/usr/bin/open"

CF_BUNDLE_VERSION = "CFBundleVersion"
CF_BUNDLE_IDENTIFIER = "CFBundleIdentifier"
K_MD_ITEM_BUNDLE_IDENTIFIER = f"kMDItem{CF_BUNDLE_IDENTIFIER}"
MDFIND_EXPR = K_MD_ITEM_BUNDLE_IDENTIFIER + " == 'com.adobe.bridge*'"


def bundle_version_sort_key(app_path: str):
    try:
        # get the version number from the bundle info plist
        bundle_info_path = os.path.join(app_path, "Contents", "Info.plist")
        with open(bundle_info_path, "rb") as f:
            plist_dict = plistlib.load(f)
        version = plist_dict[CF_BUNDLE_VERSION]

        # convert the version number to a tuple of ints
        version_parts = version.split(".")
        version_part_ints = [int(v) for v in version_parts if v.isdigit()]
        # only succeed if we parsed at least one int
        if len(version_part_ints) > 0:
            return 1, *version_part_ints
    except Exception:
        pass
    # fallback sort key
    return 0, app_path


def main():
    search_result = subprocess.run(
        [
            MDFIND,
            "-0",
            "-onlyin",
            "/Applications/",
            MDFIND_EXPR,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    )

    paths = [p for p in search_result.stdout.split("\0") if p]
    if len(paths) == 0:
        print(f"No Application matches {MDFIND_EXPR!r}", file=sys.stderr)
        return 63
    if len(paths) > 1:
        paths.sort(key=bundle_version_sort_key, reverse=True)
    path = paths[0]

    launch_result = subprocess.run(
        [
            OPEN,
            "-a",
            path,
            *sys.argv[1:],
        ],
        check=False,
    )

    return launch_result.returncode


if __name__ == "__main__":
    sys.exit(main())
