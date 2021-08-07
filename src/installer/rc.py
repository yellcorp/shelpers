import os
import shutil
import subprocess
from pathlib import Path

from utils.fs import unlink_if_exists
from utils.shell import cli_filename, determine_shell, get_shell_info
from utils.subproc import subprocess_error_if
from utils.text import u8read, text_is_pretty_much_same, u8write
from .console import yes_or_no, OUTPUT_DIVIDER


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
        print(f"The following changes will be made to {str(target_path)!r}:")
        diff_basis = target_path

    print(OUTPUT_DIVIDER)
    subprocess_error_if(
        subprocess.run(
            ("diff", "-N", "-c", cli_filename(diff_basis), "-"),
            input=new_content.encode("utf-8"),
        ),
        lambda x: x > 1,
    )
    print(OUTPUT_DIVIDER)

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
