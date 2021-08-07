import enum
from argparse import ArgumentParser
from typing import Optional


class TriState(enum.Enum):
    NO = enum.auto()
    YES = enum.auto()
    INDETERMINATE = enum.auto()


def to_tristate(value: Optional[bool]):
    if value is None:
        return TriState.INDETERMINATE
    return TriState.YES if value else TriState.NO


# This stuff wasn't added to stock argparse until py3.9
def add_tristate_argument(
    arg_parser: ArgumentParser,
    positive_flag: str,
    positive_help: str,
    negative_help: str,
    default_help: Optional[str] = None,
):
    flag_char = positive_flag[0]
    if flag_char not in arg_parser.prefix_chars:
        raise ValueError("Must be an option")

    punct_len = 0
    while positive_flag[punct_len] == flag_char:
        punct_len += 1

    punct = positive_flag[:punct_len]
    flag_text = positive_flag[punct_len:]

    # same logic as deep inside ArgumentParser
    dest = flag_text.replace("-", "_")

    negative_flag = f"{punct}no-{flag_text}"

    arg_parser.add_argument(
        positive_flag,
        action="store_const",
        const=TriState.YES,
        dest=dest,
        default=TriState.INDETERMINATE,
        help=f"{positive_help} {default_help}" if default_help else positive_help,
    )

    arg_parser.add_argument(
        negative_flag,
        action="store_const",
        const=TriState.NO,
        dest=dest,
        help=negative_help,
    )
