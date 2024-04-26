import os
import os.path
from collections import OrderedDict
from functools import wraps
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def name_func_to_fs(name: str):
    return name.replace("_", "-")


def name_fs_to_func(name: str):
    return name.replace("-", "_")


def name_path_to_func(path: str):
    stem, _ = os.path.splitext(os.path.basename(path))
    return name_fs_to_func(stem)


class URL:
    def __init__(self, url: str, **qs_params):
        self.url = url
        self.qs = OrderedDict(qs_params)

    def update(self, *args, **kwargs):
        self.qs.update(*args, **kwargs)
        return self

    def __str__(self):
        scheme, netloc, path, query, fragment = urlsplit(self.url, allow_fragments=True)
        sum_qs = OrderedDict(
            parse_qsl(
                query,
                keep_blank_values=True,
            )
        )

        sum_qs.update(self.qs)

        return urlunsplit((scheme, netloc, path, urlencode(sum_qs), fragment))


class FunctionDict(dict):
    def __call__(self, func):
        key = func.__name__
        self[key] = func
        return func


def join_space(inner_func):
    @wraps(inner_func)
    def wrapped(args):
        text = " ".join(str(a) for a in args)
        return inner_func(text)

    return wrapped
