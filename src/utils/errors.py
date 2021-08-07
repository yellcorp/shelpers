import os.path
import sys


class ErrorReporter:
    def __init__(self, argv0):
        self.argv0 = argv0

    def format_error(self, message, exception=None, subject_file=None):
        parts = [f"{self.argv0}: "]
        if subject_file is not None:
            parts.append(f"{os.fspath(subject_file)}: ")
        parts.append(message)
        if exception is not None:
            parts.append(f" ({exception})")

        return "".join(parts)

    def print_error(self, message, exception=None, subject_file=None, file=sys.stderr):
        print(self.format_error(message, exception, subject_file), file=file)

    @classmethod
    def from_argv(cls):
        return cls(os.path.basename(sys.argv[0]))
