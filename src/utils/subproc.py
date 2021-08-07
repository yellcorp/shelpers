import collections.abc
import functools
import subprocess
from typing import Container, Union, Callable

IntegerSet = Union[int, Container[int], Callable[[int], bool]]


def integer_compare(value: int, value_set: IntegerSet) -> bool:
    if callable(value_set):
        return bool(value_set(value))
    if isinstance(value_set, int):
        return value == value_set
    if isinstance(value_set, collections.abc.Container):
        return value in value_set
    raise ValueError("Unsupported predicate")


def subprocess_error_if(
    cp: subprocess.CompletedProcess, bad_exit_code_func: IntegerSet
):
    if integer_compare(cp.returncode, bad_exit_code_func):
        raise subprocess.CalledProcessError(
            cp.returncode,
            cp.args,
            output=cp.stderr,
            stderr=cp.stderr,
        )
    return cp


run_check_noinput = functools.partial(
    subprocess.run, check=True, stdin=subprocess.DEVNULL
)


def run_stdout(cmd):
    return run_check_noinput(cmd, stdout=subprocess.PIPE).stdout
