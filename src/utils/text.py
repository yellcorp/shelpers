import functools
from typing import List

u8open = functools.partial(open, encoding="utf-8")


def u8read(path):
    with u8open(path, "r") as reader:
        return reader.read()


def u8write(path, text):
    with u8open(path, "w") as writer:
        return writer.write(str(text))


def significant_lines(text: str) -> List[str]:
    return [line for line in text.splitlines(keepends=False) if not line.isspace()]


def text_is_pretty_much_same(a: str, b: str) -> bool:
    return significant_lines(a) == significant_lines(b)
