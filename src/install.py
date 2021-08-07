#!/usr/bin/env python3

import re
from argparse import ArgumentParser
from pathlib import Path

from config.manifest import manifest
from installer.main import InstallJob
from installer.py import python_check
from utils.tristate import add_tristate_argument


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


def check_pipenv_version(version: bytes) -> bool:
    return bool(re.match(br"^pipenv, version 202\d\.", version))


def check_pipx_version(version: bytes) -> bool:
    return bool(re.match(br"^0\.16\.\d+$", version))


def main():
    args = get_arg_parser().parse_args()
    src_dir = Path(__file__).absolute().resolve().parent
    root = src_dir.parent
    job = InstallJob(
        root,
        python_check(PYTHON_EXE_NAMES, PYTHON3_MIN_VERSION),
        check_pipenv_version,
        check_pipx_version,
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
