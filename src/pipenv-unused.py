import logging
import os
import shutil
import sys
from argparse import ArgumentParser
from pathlib import Path

_logger = logging.getLogger(__name__)


def get_arg_parser():
    p = ArgumentParser(
        description="""
            Identify and optionally delete unused virtual environments
            created by pipenv.
        """
    )

    p.add_argument(
        "--rm",
        action="store_true",
        help="""
            Delete unused virtual environments. The default is to only
            display them.
        """,
    )

    p.add_argument(
        "--verbose",
        action="store_true",
        help="""
            Show detailed log messages.
        """,
    )

    p.add_argument(
        "--force",
        action="store_true",
        help="""
            Force deletion of all orphaned virtual environments. By
            default, if a virtual environment is orphaned because its
            project's volume is not mounted, deletion will be skipped.
        """,
    )

    return p


def should_delete(project_path):
    # So far, this detects the macOS convention only, and only does a text
    # match at that. We can't detect the state of the filesystem when the
    # venv was made, but if it has a /Volumes/*/ prefix it's pretty safe to
    # assume it was on a removable or network mount.
    parts = str(project_path.absolute()).split(os.sep)

    # A split of a mounted path will begin ['', 'Volumes', name, ...]
    if len(parts) >= 3 and parts[0] == "" and parts[1] == "Volumes" and parts[2]:
        parent_volume = os.sep.join(parts[:3])
        if not Path(parent_volume).is_dir():
            _logger.debug(
                "Not considering %s because its parent volume %s is not present",
                project_path,
                parent_volume,
            )
            return False

    return True


def main():
    args = get_arg_parser().parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)

    venv_base = Path.home() / ".local" / "share" / "virtualenvs"
    orphaned = []

    if venv_base.is_dir():
        for entry in venv_base.iterdir():
            project_file = entry / ".project"
            if project_file.is_file():
                try:
                    project_path_str = project_file.read_text(encoding="utf-8")
                    project_path = Path(project_path_str)
                    if not project_path.exists():
                        if args.force or should_delete(project_path):
                            print(entry)
                            orphaned.append(entry)
                except OSError:
                    _logger.debug(
                        "Could not read project_file: %s", project_file, exc_info=True
                    )
            else:
                _logger.debug("project_file is not a file: %s", project_file)
    else:
        _logger.debug("venv_base is not a directory: %s", venv_base)

    if args.rm:
        for orphan in orphaned:
            _logger.debug("Attempting to remove orphan: %s", orphan)
            try:
                shutil.rmtree(orphan)
            except OSError as os_error:
                print(f"Error removing {orphan}: {os_error}", file=sys.stderr)


if __name__ == "__main__":
    main()
