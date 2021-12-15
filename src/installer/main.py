import os
import re
import shlex
import traceback
from collections import OrderedDict
from string import Template
from typing import Iterable, Callable

import sys

from utils.fs import to_path
from utils.macos.appbundle import BundleError
from utils.subproc import run_check_noinput, run_stdout
from utils.text import u8open
from utils.tristate import TriState
from .binactions import BinAction, InstallContext
from .console import (
    make_install_requester,
    yes_or_no,
    STEP_DIVIDER,
    OUTPUT_DIVIDER,
    CORN,
)
from .rc import chatty_file_edit, determine_shell_rc_path
from .receipts import ReceiptLog
from .system import add_executable


class InstallJob:
    def __init__(
        self,
        root,
        python_exec: str,
        check_pipenv_version: Callable[[bytes], bool],
        check_pipx_version: Callable[[bytes], bool],
        manifest: Iterable[BinAction],
        allow_install_utilities: TriState,
        allow_edit_shell_rc: TriState,
        shell_rc_path=None,
    ):
        self.root = to_path(root)
        self.python_exec = python_exec
        self.check_pipenv_version = check_pipenv_version
        self.check_pipx_version = check_pipx_version
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

        print(STEP_DIVIDER)
        print(f"{CORN} Complete!")
        print("Remember to restart your shell to see PATH updates.")

    def ensure_pipenv(self):
        print(STEP_DIVIDER)
        print("Checking pipenv")

        def get_version():
            return run_stdout(("pipenv", "--version"))

        add_executable(
            "pipenv",
            get_version,
            self.check_pipenv_version,
            make_install_requester(self.allow_install_utilities, "pipenv"),
            self.install_pipenv,
        )

    def install_pipenv(self):
        self.ensure_pipx()
        print(STEP_DIVIDER)
        print("Installing pipenv")
        print(OUTPUT_DIVIDER)

        run_check_noinput(("pipx", "install", "pipenv"))

    def ensure_pipx(self):
        print(STEP_DIVIDER)
        print("Checking pipx")

        def get_version():
            return run_stdout(("pipx", "--version"))

        add_executable(
            "pipx",
            get_version,
            self.check_pipx_version,
            make_install_requester(self.allow_install_utilities, "pipx"),
            self.install_pipx,
        )

    def install_pipx(self):
        print(STEP_DIVIDER)
        print("Installing pipx")
        print(OUTPUT_DIVIDER)

        run_check_noinput(
            (self.python_exec, "-m", "pip", "install", "--user", "pipx"),
        )

        if self.allow_install_utilities == TriState.YES or (
            self.allow_install_utilities == TriState.INDETERMINATE
        ):
            print(OUTPUT_DIVIDER)
            if yes_or_no(
                "pipx has been installed."
                " Do you want it to check and potentially adjust the PATH"
                " in your shell profile? "
            ):
                self.pipx_ensurepath()

    def pipx_ensurepath(self):
        print(STEP_DIVIDER)
        print("Running pipx ensurepath")
        print(OUTPUT_DIVIDER)

        run_check_noinput((self.python_exec, "-m", "pipx", "ensurepath"))

        # find out the new path
        new_env_path = run_stdout((os.environ["SHELL"], "-i", "-c", 'printf "$PATH"'))
        os.environb[b"PATH"] = new_env_path

        print(OUTPUT_DIVIDER)
        print(f'PATH is now {os.environ["PATH"]!r}')

    def generate_pipfile(self):
        python_version = get_python_version_for_pipfile()

        print(STEP_DIVIDER)
        print(f"Updating Pipfile for Python version {python_version}")

        with u8open(self.pipfile_template_path, "r") as reader, u8open(
            self.pipfile_path, "w"
        ) as writer:
            template = Template(reader.read())
            writer.write(template.substitute({"python_version": python_version}))

    def templatize_pipfile(self):
        print(STEP_DIVIDER)
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
        print(STEP_DIVIDER)
        print("Running pipenv install")
        print(OUTPUT_DIVIDER)

        run_check_noinput(("pipenv", "install"), cwd=self.root)

    def clear_bins(self):
        print(STEP_DIVIDER)
        print("Clearing bin directory")

        receipts = list(self._receipts.load())
        for name in receipts:
            (self.bin_path / name).unlink(missing_ok=True)
        self._receipts.clear()

        try:
            leftovers = [
                entry
                for entry in self.bin_path.iterdir()
                if not entry.name.startswith(".")
            ]
            if leftovers:
                print(OUTPUT_DIVIDER)
                print("Not clearing:")
                for entry in leftovers:
                    print(f"  {entry.name!r}")
        except FileNotFoundError:
            pass

    def generate_bins(self):
        print(STEP_DIVIDER)
        print("Populating bin directory")
        print(OUTPUT_DIVIDER)

        self.bin_path.mkdir(parents=True, exist_ok=True)
        context = InstallContext(
            root=self.root, bin=self.bin_path, pipfile=self.pipfile_path
        )
        plan = OrderedDict()

        for item in self.manifest:
            try:
                for p in item.get_plan(context):
                    path = p.get_path()
                    k = str(path)
                    if k in plan:
                        raise ValueError(
                            f"Multiple entries in manifest attempting to write to the same file {k!r}"
                        )
                    plan[k] = p
            except BundleError:
                print(f"Skipping {item!r} due to non-critical error")
                traceback.print_exc()
                continue

        for command in plan.values():
            receipt_path = command.get_path().relative_to(self.bin_path)
            self._receipts.append(receipt_path)
            print(f"  {str(receipt_path)!r}")
            command.execute()

    def edit_shell_rc(self):
        print(STEP_DIVIDER)
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


def get_python_version_for_pipfile():
    return f"{sys.version_info.major}.{sys.version_info.minor}"
