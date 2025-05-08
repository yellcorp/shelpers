import os
import shlex
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from utils.macos.appbundle import BundleError, find_app_by_bundle_id
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


def _fsstr(value) -> str:
    return str(os.fspath(value) if isinstance(value, os.PathLike) else value)


def _fsstrlist(values) -> list[str]:
    return [] if values is None else [_fsstr(v) for v in values]


@dataclass
class InstallContext:
    root: Path
    bin: Path
    venv_python_bin: Path


class BinAction:
    def get_plan(self, context: InstallContext) -> Iterator[FileAction]:
        raise NotImplementedError()


class PythonScript(BinAction):
    def __init__(self, script, args=None, bin_name: Optional[str] = None):
        self.script = Path(script)
        self.args = _fsstrlist(args)
        self.bin_name = self.script.stem if bin_name is None else bin_name

    def __repr__(self):
        return (
            "{0.__class__.__name__}({0.script!r}, {0.args!r}, {0.bin_name!r})".format(
                self
            )
        )

    def get_plan(self, context: InstallContext) -> Iterator[FileAction]:
        script = self.script
        if not script.is_absolute():
            script = context.root / script
        command = ["exec", context.venv_python_bin, script, *self.args, ALL_ARGS_QUOTED]
        src = _SH_SCRIPT_TEMPLATE.format(command=script_text(command))
        yield ScriptFile(context.bin / self.bin_name, src)


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
        self.path = Path(path)
        if not name:
            name = self.path.stem
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


class IfBundle(BinAction):
    """
    A BinAction that depends on the existence of an application bundle.

    Uses `mdfind` to search for the specified bundle identifier, and if
    found, passes the .app path to the factory function, which should use it
    to create another BinAction. If the bundle is not found, get_plan yields
    nothing.
    """

    # This is a bit of a cheesy hack to remedy something I thought was
    # clever at the time, but led to overeager Exceptions when importing
    # config.manifest and the requested bundle was not installed. Not all
    # apps are installed on all computers!

    def __init__(self, bundle_id: str, factory: Callable[[Path], BinAction]):
        self.bundle_id = bundle_id
        self.factory = factory

    def __repr__(self):
        return "{0.__class__.__name__}({0.bundle_id!r}, {0.action!r})".format(self)

    def get_plan(self, context: InstallContext) -> Iterator[FileAction]:
        try:
            app_dir_str = find_app_by_bundle_id(self.bundle_id)
        except BundleError:
            app_dir_str = None

        if app_dir_str is not None:
            app_dir = Path(app_dir_str)
            yield from self.factory(app_dir).get_plan(context)

    def bundle_exists(self, context: InstallContext) -> bool:
        raise NotImplementedError()


class Link(BinAction):
    def __init__(self, link_target, link_name: Optional[str] = None):
        self.link_target = Path(link_target)
        self.link_name = self.link_target.stem if link_name is None else link_name

    def __repr__(self):
        return "{0.__class__.__name__}({0.link_target!r}, {0.link_name!r})".format(self)

    def get_plan(self, context: InstallContext) -> Iterator[FileAction]:
        link_path = context.bin / self.link_name
        link_base = link_path.parent

        link_target = self.link_target
        if not link_target.is_absolute():
            link_target = context.root / link_target
        link_target = link_target.resolve()

        # Make symlinks relative if they point within this repo
        if link_target.is_relative_to(context.root):
            link_content = os.path.relpath(link_target, link_base)
        else:
            link_content = os.fspath(link_target)

        yield Symlink(link_path, link_content)


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
