import os
import re
import subprocess
from typing import Iterable, Tuple

from utils.subproc import run_stdout
from .errors import InstallError


def python_check(executable_names: Iterable[str], version: Tuple[int, int]):
    if os.environ.get("VIRTUAL_ENV"):
        raise InstallError("Refusing to run installer while a virtualenv is active")

    required_major_version, min_minor_version = version
    formatted_version = f"{required_major_version}.{min_minor_version}"

    for exe_name in executable_names:
        try:
            exe_version = run_stdout((exe_name, "--version"))
        except subprocess.CalledProcessError:
            continue

        version_match = re.match(rb"Python (\d+)\.(\d+)\.", exe_version)
        if version_match:
            exe_major = int(version_match[1])
            exe_minor = int(version_match[2])
            if exe_major == 3 and exe_minor >= 8:
                return exe_name

    raise InstallError(
        "Could not find a Python interpreter in $PATH"
        f" with version >= {formatted_version} < {min_minor_version + 1}"
    )
