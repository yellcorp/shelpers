import argparse
import os
import shutil
import subprocess
import sys
import tempfile

from shelpers.shell import cli_filename
from shelpers.errors import ErrorReporter


def get_arg_parser():
    p = argparse.ArgumentParser(
        description="""\
            Use jpegtran to optimize JPEG image files
            in-place."""
    )

    p.add_argument(
        "paths", nargs="+", help="The jpeg files to optimize", metavar="PATH"
    )

    return p


EXIT_CODE_UNEXPECTED = 65

reporter = ErrorReporter.from_argv()


def jpegopt_with_tempfile(path, temp_file):
    try:
        input_size = os.path.getsize(path)
    except OSError as env_err:
        reporter.print_error("Could not get file size.", env_err, path)
        input_size = None

    exit_code = subprocess.run(
        ("jpegtran", "-copy", "none", "-optimize", cli_filename(path)),
        stdout=temp_file,
    )

    replace = True
    if exit_code != 0:
        reporter.print_error("jpegtran failed.", subject_file=path)
        replace = False

    elif input_size is not None:
        output_size = temp_file.tell()
        if output_size == 0:
            reporter.print_error(
                "New file size is 0. Not replacing.", subject_file=path
            )
            exit_code = EXIT_CODE_UNEXPECTED
            replace = False
        elif output_size >= input_size:
            reporter.print_error(
                "File increased in size. Not replacing.", subject_file=path
            )
            replace = False

    if replace:
        try:
            temp_file.seek(0)
            with open(path, "wb") as writer:
                shutil.copyfileobj(temp_file, writer)
        except OSError as env_err:
            reporter.print_error("Could not replace file.", env_err, path)
            exit_code = 1

    return exit_code


def jpegopt(path):
    temp_fd, temp_path = tempfile.mkstemp(suffix=".jpg")
    temp_file = os.fdopen(temp_fd, "w+b")

    try:
        return jpegopt_with_tempfile(path, temp_file)
    finally:
        temp_file.close()
        try:
            os.remove(temp_path)
        except OSError as env_err:
            reporter.print_error("Could not delete temp file.", env_err, temp_path)


def main():
    config = get_arg_parser().parse_args()
    try:
        max_code = max(jpegopt(path) for path in config.paths)
    except Exception as jpegopt_error:
        reporter.print_error("Unexpected error.", jpegopt_error)
        return EXIT_CODE_UNEXPECTED
    return max_code


if __name__ == "__main__":
    sys.exit(main())
