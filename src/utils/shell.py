import os
import shlex
from typing import NamedTuple, Optional


class ScriptLiteral:
    def __init__(self, text: str):
        self.text = text


ALL_ARGS_QUOTED = ScriptLiteral('"$@"')


def _script_token(s):
    if isinstance(s, ScriptLiteral):
        return s.text
    return shlex.quote(str(s))


def script_text(sequence):
    return " ".join(_script_token(s) for s in sequence)


def cli_filename(name):
    """
    Prepares a filename for passing to another command-line application. If
    the filename begins with '-', it is returned prepended with
    os.path.curdir ('.') to prevent confusion with command-line options.
    Otherwise it is returned as-is.
    """
    path = os.fspath(name)
    if isinstance(path, str) and path.startswith("-"):
        return os.path.join(os.path.curdir, path)
    if isinstance(path, bytes) and path.startswith(b"-"):
        return os.path.join(os.fsencode(os.path.curdir), path)
    return path


def determine_shell():
    shell = os.environ.get("SHELL")
    if not shell:
        return None
    return os.path.basename(shell)


class ShellInfo(NamedTuple):
    rc_name: str


_SHELL_INFO = dict(
    bash=ShellInfo(rc_name=".bash_profile"),
    zsh=ShellInfo(rc_name=".zshrc"),
)


def get_shell_info(shell_name: str) -> Optional[ShellInfo]:
    return _SHELL_INFO.get(shell_name)
