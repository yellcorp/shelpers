def significant_lines(a):
    return [line for line in a.splitlines(keepends=False) if not line.isspace()]


def text_is_pretty_much_same(a: str, b: str):
    return significant_lines(a) == significant_lines(b)
