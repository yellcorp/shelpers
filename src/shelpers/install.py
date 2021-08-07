import functools
import os
import shlex
from pathlib import Path
from typing import Optional, Iterator, NamedTuple

from shelpers.shell import script_text, ALL_ARGS_QUOTED

_SH_SCRIPT_TEMPLATE = """\
#!/bin/sh
{command}
"""


def to_path(p):
    return Path(os.fspath(p))


def yes_or_no(prompt: str) -> bool:
    while True:
        response = input(prompt).lower()
        if response:
            if "yes".startswith(response):
                return True
            if "no".startswith(response):
                return False
        print("Enter y or n, or press Control-D to cancel")


def yes_or_no_requester(prompt: str):
    return functools.partial(yes_or_no, prompt)


class InstallContext(NamedTuple):
    root: Path
    bin: Path
    pipfile: Path


class FileCommand:
    def get_path(self) -> Path:
        raise NotImplementedError()

    def execute(self):
        raise NotImplementedError()


class ScriptFile(FileCommand):
    def __init__(self, path: Path, source: str):
        self.path = path
        self.source = source

    def get_path(self) -> Path:
        return self.path

    def execute(self):
        with open(self.path, "w", encoding="utf-8") as writer:
            writer.write(self.source)
        self.path.chmod(0o755)


class Symlink(FileCommand):
    def __init__(self, link_path: Path, link_content: str):
        self.link_path = link_path
        self.link_content = link_content

    def get_path(self) -> Path:
        return self.link_path

    def execute(self):
        os.symlink(self.link_content, self.link_path)


class BinCommand:
    def get_plan(self, context: InstallContext) -> Iterator[FileCommand]:
        raise NotImplementedError()


class PipenvPython(BinCommand):
    def __init__(self, py_name: str, name: Optional[str] = None, *insert_args):
        self.py_name = py_name
        self.name = name or to_path(self.py_name).stem
        self.insert_args = insert_args

    def get_plan(self, context: InstallContext) -> Iterator[FileCommand]:
        pipfile = shlex.quote(str(context.pipfile.absolute()))

        env = f"PIPENV_PIPFILE={pipfile}"
        command = ["pipenv", "run", "python", context.root / self.py_name]
        command.extend(str(a) for a in self.insert_args)
        command.append(ALL_ARGS_QUOTED)

        text = f"{env} {script_text(command)}"

        src = _SH_SCRIPT_TEMPLATE.format(command=text)
        yield ScriptFile(context.bin / self.name, src)


class Opener(BinCommand):
    def __init__(self, name: str):
        self.name = name

    def get_plan(self, context: InstallContext) -> Iterator[FileCommand]:
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

    def get_command(self):
        return ["exec", "/usr/bin/open", "-b", self.bundle_id, ALL_ARGS_QUOTED]


class Link(BinCommand):
    def __init__(self, link_target, link_name=None):
        self.link_target = link_target
        self.link_name = link_name

    def get_plan(self, context: InstallContext) -> Iterator[FileCommand]:
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
