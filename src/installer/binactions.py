import os
import shlex
from pathlib import Path
from typing import Any, Iterable, Iterator, NamedTuple, Optional, Union

from utils.fs import to_path
from utils.shell import ALL_ARGS_QUOTED, script_text
from .fsactions import FileAction, ScriptFile, Symlink

_SH_SCRIPT_TEMPLATE = """\
#!/bin/sh
{command}
"""

_HABIT_CHANGER_TEMPLATE = """\
#!/bin/sh
echo {old_name}: Use {new_name} instead. >&2
exit 1
"""


class InstallContext(NamedTuple):
    root: Path
    bin: Path
    pipfile: Path


class BinAction:
    def get_plan(self, context: InstallContext) -> Iterator[FileAction]:
        raise NotImplementedError()


class PipenvPython(BinAction):
    def __init__(self, py_name: Union[str, Iterable[Any]], name: Optional[str] = None):
        if isinstance(py_name, str):
            self.py_name = py_name
            self.extra_args = []
        else:
            i = iter(py_name)
            self.py_name = next(i)
            self.extra_args = list(i)

        self.name = name or to_path(self.py_name).stem

    def __repr__(self):
        return "{0.__class__.__name__}({1!r}, {0.name!r})".format(
            self, [self.py_name] + self.extra_args
        )

    def get_plan(self, context: InstallContext) -> Iterator[FileAction]:
        env = dict(
            PIPENV_PIPFILE=context.pipfile.absolute(),
            PIPENV_IGNORE_VIRTUALENVS=1,
            PIPENV_VERBOSITY=-1,
        )
        env_prefix = " ".join(f"{k}={shlex.quote(str(v))}" for k, v in env.items())

        command = ["pipenv", "run", "python", context.root / self.py_name]
        command.extend(self.extra_args)
        command.append(ALL_ARGS_QUOTED)

        text = f"{env_prefix} {script_text(command)}"

        src = _SH_SCRIPT_TEMPLATE.format(command=text)
        yield ScriptFile(context.bin / self.name, src)


class Opener(BinAction):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return "{0.__class__.__name__}({0.name!r})".format(self)

    def get_plan(self, context: InstallContext) -> Iterator[FileAction]:
        src = _SH_SCRIPT_TEMPLATE.format(command=script_text(self.get_command()))
        yield ScriptFile(context.bin / self.name, src)

    def get_command(self):
        raise NotImplementedError()


class PathOpener(Opener):
    """
    Generates a stub shell script to launch the specified app bundle from a
    shell. The app bundle is located by its path.
    """

    def __init__(self, path, name: Optional[str] = None):
        self.path = path
        if not name:
            name = to_path(path).stem
        super().__init__(name)

    def __repr__(self):
        return "{0.__class__.__name__}({0.name!r}, {0.path!r})".format(self)

    def get_command(self):
        return ["exec", "/usr/bin/open", "-a", os.fspath(self.path), ALL_ARGS_QUOTED]


class BundleOpener(Opener):
    """
    Generates a stub shell script to launch the specified app bundle from a
    shell. The app bundle is located by its bundle id.
    """

    def __init__(self, bundle_id: str, name: str):
        super().__init__(name)
        self.bundle_id = bundle_id

    def __repr__(self):
        return "{0.__class__.__name__}({0.bundle_id!r}, {0.name!r})".format(self)

    def get_command(self):
        return ["exec", "/usr/bin/open", "-b", self.bundle_id, ALL_ARGS_QUOTED]


class Link(BinAction):
    def __init__(self, link_target, link_name=None):
        self.link_target = link_target
        self.link_name = link_name

    def __repr__(self):
        return ("{0.__class__.__name__}({0.link_target!r}, {0.link_name!r})").format(
            self
        )

    def get_plan(self, context: InstallContext) -> Iterator[FileAction]:
        link_target = to_path(self.link_target)
        if not link_target.is_absolute():
            link_target = context.root / link_target
        link_target = link_target.resolve()

        # Path.is_relative_to added in py3.9
        try:
            _ = link_target.relative_to(context.root)
            # drop back to os.path api, because that inserts updirs.
            # Path.relative_to raises an error instead
            link_content = os.path.relpath(link_target, context.bin)
        except ValueError:
            link_content = str(link_target)

        name = self.link_name
        if not name:
            name = link_target.stem

        yield Symlink(context.bin / name, link_content)


class HabitChanger(BinAction):
    """
    Creates a shell script that just echoes a reminder to use a
    different command, and exits with error code 1. This is used when
    switching from one command to another after long-term usage of the
    former.
    """

    def __init__(self, old_name: str, new_name: str):
        self.old_name = old_name
        self.new_name = new_name

    def __repr__(self):
        return "{0.__class__.__name__}({0.old_name!r}, {0.new_name!r})".format(self)

    def get_plan(self, context: InstallContext) -> Iterator[FileAction]:
        src = _HABIT_CHANGER_TEMPLATE.format(
            old_name=shlex.quote(self.old_name),
            new_name=shlex.quote(self.new_name),
        )
        yield ScriptFile(context.bin / self.old_name, src)
