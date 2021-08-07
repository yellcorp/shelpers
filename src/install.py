#!/usr/bin/env python3

import ast
import functools
import json
import os
import re
import shlex
import shutil
import subprocess
from argparse import ArgumentParser
from collections import OrderedDict
from pathlib import Path
from string import Template
from typing import Iterable

import sys

from _manifest import manifest
from shelpers.install import (
    InstallContext,
    BinCommand,
    to_path,
    yes_or_no_requester,
    yes_or_no,
)
from shelpers.shell import determine_shell, get_shell_info, cli_filename
from shelpers.subprocutil import subprocess_error_if
from shelpers.text import text_is_pretty_much_same
from shelpers.tristate import add_tristate_argument, TriState


def get_arg_parser():
    p = ArgumentParser(
        description="""
            Install shelpers.
        """
    )

    add_tristate_argument(
        p,
        "--install",
        positive_help="""Automatically install required utilities.""",
        negative_help="""Never install required utilities.""",
        default_help="""The default is to ask.""",
    )

    add_tristate_argument(
        p,
        "--editrc",
        positive_help="""Automatically update shell profile scripts.""",
        negative_help="""Never update shell profile scripts.""",
        default_help="""The default is to ask.""",
    )

    p.add_argument(
        "--rcfile",
        help="""
            The shell script to edit when updating PATH vars and sourcing
            function/alias scripts. The default is to try and automatically
            determine an appropriate file based on the current shell in use.
            Has no effect if --no-editrc is specified.
        """,
    )

    p.add_argument(
        "--templatize",
        action="store_true",
        help="""
            Development option. Updates Pipfile.template. All other options are
            ignored when this is specified.
        """,
    )

    return p


PYTHON_EXE_NAMES = ("python3", "python")
PYTHON3_MIN_VERSION = (3, 8)


def check_pipenv_version(version: bytes):
    return bool(re.match(br"^pipenv, version 202\d\.", version))


def check_pipx_version(version: bytes):
    return bool(re.match(br"^0\.16\.\d+$", version))


class InstallError(Exception):
    pass


run_check_noinput = functools.partial(
    subprocess.run, check=True, stdin=subprocess.DEVNULL
)

u8open = functools.partial(open, encoding="utf-8")


def u8read(path):
    with u8open(path, "r") as reader:
        return reader.read()


def u8write(path, text):
    with u8open(path, "w") as writer:
        return writer.write(str(text))


def run_stdout(cmd):
    return run_check_noinput(cmd, stdout=subprocess.PIPE).stdout


never = lambda: False
always = lambda: True


def make_install_requester(allow: TriState, prompt_name: str):
    if allow == TriState.NO:
        return never
    if allow == TriState.YES:
        return always
    return yes_or_no_requester(f"{prompt_name!r} is not installed. Install it? ")


def python_check():
    if os.environ.get("VIRTUAL_ENV"):
        raise InstallError("Not running with a virtualenv active")

    major_version, min_minor_version = PYTHON3_MIN_VERSION
    formatted_version = f"{major_version}.{min_minor_version}"

    for exe in PYTHON_EXE_NAMES:
        try:
            exe_version = json.loads(
                run_stdout(
                    (
                        exe,
                        "-c",
                        "import json;"
                        "import sys;"
                        "v = sys.version_info;"
                        "sys.stdout.write(json.dumps([v.major, v.minor]))",
                    )
                )
            )
            if exe_version[0] == 3 and exe_version[1] >= 6:
                return exe
        except subprocess.CalledProcessError:
            pass

    raise InstallError(
        "Could not find a Python interpreter in $PATH"
        f" with version >= {formatted_version} < {min_minor_version + 1}"
    )


def ensure_exe(name: str, get_version, check_version, confirm_install, install):
    for should_be_installed_by_now in (False, True):
        try:
            version = get_version()
            if check_version(version):
                return
            raise InstallError(f"Out of date: {name!r}")

        except (FileNotFoundError, subprocess.CalledProcessError) as process_error:
            pass

        if should_be_installed_by_now:
            raise InstallError(f"Failed to install {name!r}")

        if confirm_install is not None and install is not None and confirm_install():
            install()
        else:
            raise InstallError(f"Not installed: {name!r}")


def get_python_version_for_pipfile():
    return f"{sys.version_info.major}.{sys.version_info.minor}"


def chatty_file_edit(
    target_path, backup_path, new_content: str, interactive_confirm: bool
):
    creating = False
    try:
        current_content = u8read(target_path)
        if text_is_pretty_much_same(current_content, new_content):
            print(f"{str(target_path)!r}: No changes necessary")
            return
    except FileNotFoundError:
        creating = True

    if creating:
        print(f"{str(target_path)!r} will be created with the following contents:")
        diff_basis = os.devnull
    else:
        print(f"The following edits will be made to {str(target_path)!r}:")
        diff_basis = target_path

    subprocess_error_if(
        subprocess.run(
            ("diff", "-N", "-c", cli_filename(diff_basis), "-"),
            input=new_content.encode("utf-8"),
        ),
        lambda x: x > 1,
    )

    if interactive_confirm:
        if yes_or_no("Continue? "):
            print("Proceeding")
        else:
            print("Skipping")
            return

    if not creating:
        unlink_if_exists(backup_path)
        shutil.copy2(target_path, backup_path)

    u8write(target_path, new_content)


def unlink_if_exists(f):
    try:
        os.unlink(f)
    except FileNotFoundError:
        pass


class ReceiptLog:
    def __init__(self, path):
        self.path = to_path(path)

    def clear(self):
        self.path.unlink(missing_ok=True)

    def load(self):
        try:
            with u8open(self.path, "r") as reader:
                for line in reader:
                    line = line.rstrip()
                    if line:
                        yield ast.literal_eval(line)
        except FileNotFoundError:
            pass

    def append(self, text):
        with u8open(self.path, "a") as writer:
            print(repr(os.fspath(text)), file=writer)


def determine_shell_rc_path():
    shell_name = determine_shell()
    if shell_name is None:
        print(
            "Skipping profile edits because the SHELL environment var is"
            " not set, meaning a profile script cannot be determined"
        )
        return None

    shell_info = get_shell_info(shell_name)
    if shell_info is None:
        print(
            "Skipping profile edits because I don't know which file to"
            f" edit for the shell {shell_name!r}"
        )
        return None

    return Path.home() / shell_info.rc_name


class InstallJob:
    def __init__(
        self,
        root,
        python_exec: str,
        manifest: Iterable[BinCommand],
        allow_install_utilities: TriState,
        allow_edit_shell_rc: TriState,
        shell_rc_path=None,
    ):
        self.root = to_path(root)
        self.python_exec = python_exec
        self.manifest = list(manifest)
        self.allow_install_utilities = allow_install_utilities
        self.allow_edit_shell_rc = allow_edit_shell_rc
        self.shell_rc_path = shell_rc_path

        self._receipts = ReceiptLog(self.root / "bin.log")

    @property
    def bin_path(self):
        return self.root / "bin"

    @property
    def profile_path(self):
        return self.root / "profile"

    @property
    def pipfile_path(self):
        return self.root / "Pipfile"

    @property
    def pipfile_template_path(self):
        return self.root / "Pipfile.template"

    def run(self):
        self.ensure_pipenv()
        self.generate_pipfile()
        self.install_deps()
        self.clear_bins()
        self.generate_bins()
        self.edit_shell_rc()

    def ensure_pipenv(self):
        def get_version():
            return run_stdout(("pipenv", "--version"))

        ensure_exe(
            "pipenv",
            get_version,
            check_pipenv_version,
            make_install_requester(self.allow_install_utilities, "pipenv"),
            self.install_pipenv,
        )

    def install_pipenv(self):
        self.ensure_pipx()
        print("Installing pipenv")
        run_check_noinput(("pipx", "install", "pipenv"))

    def ensure_pipx(self):
        def get_version():
            return run_stdout(("pipx", "--version"))

        ensure_exe(
            "pipx",
            get_version,
            check_pipx_version,
            make_install_requester(self.allow_install_utilities, "pipx"),
            self.install_pipx,
        )

    def install_pipx(self):
        print("Installing pipx")
        run_check_noinput(
            (self.python_exec, "-m", "pip", "install", "--user", "pipx"),
        )

        if self.allow_install_utilities == TriState.YES or (
            self.allow_install_utilities == TriState.INDETERMINATE
            and yes_or_no(
                "pipx has been installed."
                " Do you want it to check and potentially adjust the PATH"
                " in your shell profile? "
            )
        ):
            self.pipx_ensurepath()

    def pipx_ensurepath(self):
        run_check_noinput((self.python_exec, "-m", "pipx", "ensurepath"))

        # find out the new path
        new_env_path = run_stdout((os.environ["SHELL"], "-i", "-c", 'printf "$PATH"'))
        os.environb[b"PATH"] = new_env_path
        print(f'PATH is now {os.environ["PATH"]!r}')

    def generate_pipfile(self):
        python_version = get_python_version_for_pipfile()
        print(f"Updating Pipfile for Python version {python_version}")

        with u8open(self.pipfile_template_path, "r") as reader, u8open(
            self.pipfile_path, "w"
        ) as writer:
            template = Template(reader.read())
            writer.write(template.substitute({"python_version": python_version}))

    def templatize_pipfile(self):
        print(f"Templatizing Pipfile")

        # The opposite of generate_pipfile - creates a template from the
        # working copy of the Pipfile. Only used in development.
        state = 0

        with u8open(self.pipfile_path) as reader, u8open(
            self.pipfile_template_path, "w"
        ) as writer:
            for line in reader:
                if state == 0:
                    if line.rstrip() == "[requires]":
                        state = 1
                elif state == 1:
                    if re.match(r"python_version\s*=", line):
                        writer.write('python_version = "${python_version}"\n')
                        state = 2
                        continue
                    elif line.startswith("["):
                        state = 2
                writer.write(line)

    def install_deps(self):
        print("Running pipenv install")
        run_check_noinput(("pipenv", "install"), cwd=self.root)

    def clear_bins(self):
        print("Clearing bin directory")
        receipts = list(self._receipts.load())
        for name in receipts:
            (self.bin_path / name).unlink(missing_ok=True)
        self._receipts.clear()

        leftovers = [e for e in self.bin_path.iterdir() if not e.name.startswith(".")]
        if leftovers:
            print("Not clearing:")
            for l in leftovers:
                print(f"  {l.name}")

    def generate_bins(self):
        print("Populating bin directory")
        self.bin_path.mkdir(parents=True, exist_ok=True)
        context = InstallContext(
            root=self.root, bin=self.bin_path, pipfile=self.pipfile_path
        )
        plan = OrderedDict()

        for item in manifest:
            for p in item.get_plan(context):
                path = p.get_path()
                k = str(path)
                if k in plan:
                    raise ValueError(
                        f"Multiple entries in manifest attempting to write to the same file {k!r}"
                    )
                plan[k] = p

        for command in plan.values():
            receipt_path = command.get_path().relative_to(self.bin_path)
            self._receipts.append(receipt_path)
            print(f"  + {str(receipt_path)!r}")
            command.execute()

    def edit_shell_rc(self):
        if self.allow_edit_shell_rc == TriState.NO:
            print("Skipping profile edits because they have been disallowed")
            return

        rc_path = (
            determine_shell_rc_path()
            if self.shell_rc_path is None
            else to_path(self.shell_rc_path)
        )
        rc_backup_path = rc_path.parent / f"{rc_path.name}.shelpers-backup"

        path_comment = "# Adds shelpers to PATH"
        include_comment = "# Sources init scripts from shelpers"
        my_additions = re.compile(
            r"(?:{alts})$".format(
                alts="|".join(
                    re.escape(comment) for comment in (path_comment, include_comment)
                )
            )
        )

        bin_path = self.bin_path.absolute().resolve()
        profile_path = self.profile_path.absolute().resolve()

        new_lines = [
            'export PATH="$PATH":{addend}  {comment}'.format(
                addend=shlex.quote(str(bin_path)),
                comment=path_comment,
            ),
            (
                "for file in {profile_path}/init-*.sh;"
                ' do [ -r "$file" ] && . "$file";'
                " done  {comment}"
            ).format(
                profile_path=shlex.quote(str(profile_path)),
                comment=include_comment,
            ),
        ]

        try:
            with u8open(rc_path) as reader:
                rc_lines = [
                    line for line in reader if not my_additions.search(line.rstrip())
                ]
        except FileNotFoundError:
            rc_lines = []

        if rc_lines:
            last = rc_lines[-1]
            if last and not last.isspace():
                rc_lines.append("\n")

        rc_lines.extend(f"{line}\n" for line in new_lines)
        chatty_file_edit(
            rc_path,
            rc_backup_path,
            "".join(rc_lines),
            self.allow_edit_shell_rc == TriState.INDETERMINATE,
        )


def main():
    args = get_arg_parser().parse_args()
    src_dir = Path(__file__).absolute().resolve().parent
    root = src_dir.parent
    job = InstallJob(
        root,
        python_check(),
        manifest,
        args.install,
        args.editrc,
        args.rcfile,
    )

    if args.templatize:
        job.templatize_pipfile()
    else:
        job.run()


if __name__ == "__main__":
    main()
