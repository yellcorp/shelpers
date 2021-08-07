import subprocess
from typing import Callable, Optional

from .errors import InstallError


def add_executable(
    name: str,
    get_version: Callable[[], bytes],
    check_version: Callable[[bytes], bool],
    confirm_install: Optional[Callable[[], bool]],
    install: Optional[Callable[[], None]],
):
    for should_be_installed_by_now in (False, True):
        try:
            version = get_version()
            if check_version(version):
                return
            raise InstallError(f"Unexpected version: {name!r} ({version!r})")

        except (FileNotFoundError, subprocess.CalledProcessError):
            pass

        if should_be_installed_by_now:
            raise InstallError(f"Failed to install {name!r}")

        if confirm_install is not None and install is not None and confirm_install():
            install()
        else:
            raise InstallError(f"Not installed: {name!r}")
