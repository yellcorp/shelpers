from __future__ import division, print_function


import os.path
import sys


def format_error(message, exception = None, subject_file = None):
    source = os.path.basename(sys.argv[0])
    parts = [ "%s: " % source ]
    if subject_file is not None:
        parts.append("%s: " % subject_file)
    parts.append(message)
    if exception is not None:
        parts.append(" (%s)" % exception)

    return "".join(parts)


def print_error(message, exception = None, subject_file = None):
    print(
        format_error(message, exception, subject_file),
        file = sys.stderr
    )
