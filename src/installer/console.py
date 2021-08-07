import functools

from utils.tristate import TriState

SINGLE_LINE = "\u2500"
DOUBLE_LINE = "\u2550"
CORN = "\U0001f33d"

STEP_DIVIDER = DOUBLE_LINE * 60
OUTPUT_DIVIDER = SINGLE_LINE * len(STEP_DIVIDER)


def yes_or_no(prompt: str) -> bool:
    while True:
        response = input(prompt).lower()
        if response:
            if "yes".startswith(response):
                return True
            if "no".startswith(response):
                return False
        print("Enter y or n, or press Control-D to cancel")


def yes_or_no_requester(prompt: str):
    return functools.partial(yes_or_no, prompt)


def _never():
    return False


def _always():
    return True


def make_install_requester(allow: TriState, prompt_name: str):
    if allow == TriState.NO:
        return _never
    if allow == TriState.YES:
        return _always
    return yes_or_no_requester(f"{prompt_name!r} is not installed. Install it? ")
