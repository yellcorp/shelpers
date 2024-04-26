import argparse
import re
import shlex
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Iterable, Optional

from config.manifest import manifest
from utils.macos.appbundle import BundleError
from utils.shell import cli_filename
from utils.text import u8open
from .binactions import BinAction, InstallContext
from .console import CORN, OUTPUT_DIVIDER, STEP_DIVIDER
from .rc import chatty_file_edit, determine_shell_rc_path
from .receipts import ReceiptLog


def get_arg_parser():
    p = argparse.ArgumentParser(
        description="""
            Install shelpers.
        """
    )

    p.add_argument(
        "--force-venv",
        action="store_true",
        help="""
            Create a new virtual environment for shelpers even if one
            already exists.  The default is to only create one if it doesn't
            exist.
        """,
    )

    p.add_argument(
        "--editrc",
        action=argparse.BooleanOptionalAction,
        help="""
            Whether to automatically update shell profile scripts.
            If not specified, the default is to ask.
        """,
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

    return p


class InstallJob:
    def __init__(
        self,
        root: Path,
        python_exec: Path,
        manifest: Iterable[BinAction],
        force_venv: bool,
        allow_edit_shell_rc: Optional[bool],
        shell_rc_path: Optional[Path],
    ):
        self.root = root
        self.python_exec = python_exec
        self.manifest = list(manifest)
        self.force_venv = force_venv
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
    def venv_path(self):
        return self.root / "venv"

    @property
    def venv_python_bin(self):
        return self.venv_path / "bin" / "python"

    def run(self):
        self.create_venv()
        self.install_requirements()
        self.clear_bins()
        self.generate_bins()
        self.edit_shell_rc()

        print(STEP_DIVIDER)
        print(f"{CORN} Complete!")
        print("Remember to restart your shell to see PATH updates.")

    def create_venv(self):
        print(STEP_DIVIDER)

        venv_exists = self.venv_path.is_dir()

        if venv_exists and not self.force_venv:
            print("Virtual environment already exists")
            return

        clear_args = ["--clear"] if venv_exists else []

        print("Creating virtual environment")
        subprocess.run(
            [
                cli_filename(self.python_exec),
                "-m",
                "venv",
                cli_filename(self.venv_path),
                "--prompt",
                "shelpers-venv",
                *clear_args,
            ],
            check=True,
        )

    def install_requirements(self):
        print(STEP_DIVIDER)
        print("Installing dependencies")
        print(OUTPUT_DIVIDER)

        pip = [
            cli_filename(self.venv_python_bin),
            "-m",
            "pip",
        ]

        subprocess.run(
            [
                *pip,
                "install",
                "--upgrade",
                "pip",
            ],
            check=True,
        )

        subprocess.run(
            [
                *pip,
                "install",
                "-r",
                cli_filename(self.root / "requirements.txt"),
            ],
            check=True,
        )

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
            root=self.root,
            bin=self.bin_path,
            venv_python_bin=self.venv_python_bin,
        )
        plan = {}  # Ordered since 3.7

        for manifest_item in self.manifest:
            try:
                for p in manifest_item.get_plan(context):
                    path = p.get_path()
                    k = str(path)
                    if k in plan:
                        raise ValueError(
                            f"Multiple entries in manifest attempting to write to the same file {k!r}"
                        )
                    plan[k] = p
            except BundleError:
                print(f"Skipping {manifest_item!r} due to non-critical error")
                traceback.print_exc()
                continue

        for command in plan.values():
            receipt_path = command.get_path().relative_to(self.bin_path)
            self._receipts.append(receipt_path)
            print(f"  {str(receipt_path)!r}")
            command.execute()

    def edit_shell_rc(self):
        print(STEP_DIVIDER)
        if self.allow_edit_shell_rc is False:
            print("Skipping profile edits because they have been disallowed")
            return

        rc_path = (
            determine_shell_rc_path()
            if self.shell_rc_path is None
            else self.shell_rc_path
        )
        if rc_path is None:
            return

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
            self.allow_edit_shell_rc is None,
        )


def main():
    this_file = Path(__file__).absolute().resolve()
    installer_module = this_file.parent
    src_dir = installer_module.parent
    repo_root = src_dir.parent
    assert repo_root.is_dir()

    python_path = Path(sys.executable)
    assert python_path.is_file()

    args = get_arg_parser().parse_args()

    rcfile = Path(args.rcfile) if args.rcfile else None
    job = InstallJob(
        repo_root,
        python_path,
        manifest,
        args.force_venv,
        args.editrc,
        rcfile,
    )

    return job.run()
