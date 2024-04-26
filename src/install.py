import os
import sys

PYTHON_MIN_VERSION = (3, 9)


def is_virtualenv_active():
    return bool(os.environ.get("VIRTUAL_ENV"))


def is_python_version_sufficient():
    this_version = (sys.version_info.major, sys.version_info.minor)
    return this_version >= PYTHON_MIN_VERSION


def main():
    if is_virtualenv_active():
        print("Refusing to run installer while a virtualenv is active")
        return 1

    if not is_python_version_sufficient():
        req_version_string = ".".join(str(x) for x in PYTHON_MIN_VERSION)

        print(
            "These scripts require a Python version of at least %s" % req_version_string
        )
        print("The currently running Python version is:")
        print("  %s" % sys.version)
        print("At the path:")
        print("  %s" % sys.executable)

        return 1

    import installer.main

    return installer.main.main()


if __name__ == "__main__":
    sys.exit(main())
