# we have a hacky introspection thing going on where it's assumed all names not
# beginning with _ are URL generation functions

# turns out imports from __future__ are visible name table entries too; i
# didn't know that

from __future__ import division as _division, print_function as _print_function

from collections import OrderedDict as _OrderedDict
from urllib import urlencode as _urlencode


class _URL(object):
    def __init__(self, url, **qs_params):
        self.url = url
        self.qs = _OrderedDict(qs_params)

    def update(self, *args, **kwargs):
        self.qs.update(*args, **kwargs)
        return self

    def __str__(self):
        if self.qs and len(self.qs) > 0:
            return "{!s}?{!s}".format(self.url, _urlencode(self.qs))
        return str(self.url)


def _space(inner_func):
    def wrapped(arg_array):
        return inner_func(" ".join(str(e) for e in arg_array))
    return wrapped


@_space
def search_google(arg):
    return _URL("https://www.google.com/search", q = arg)

@_space
def search_google_image(arg):
    return search_google(arg).update(tbm = "isch")

@_space
def search_google_video(arg):
    return search_google(arg).update(tbm = "vid")


@_space
def search_ddg(arg):
    return _URL("https://duckduckgo.com/", q = arg, t = "h_", ia = "web")

@_space
def search_ddg_image(arg):
    return search_ddg(arg).update(ia = "images", iax = "images")

@_space
def search_ddg_video(arg):
    return search_ddg(arg).update(ia = "videos", iax = "videos")


@_space
def search_youtube(arg):
    return _URL("https://www.youtube.com/results", search_query = arg)


@_space
def search_symbolhound(arg):
    return _URL("http://symbolhound.com/", q = arg)


@_space
def search_mdn(arg):
    return _URL("https://developer.mozilla.org/en-US/search", q = arg)


def _pydocs(version, query):
    return _URL(
        "https://docs.python.org/%s/search.html" % version,
        q = query,
        check_keywords = "yes",
        area = "default"
    )

@_space
def search_pydocs2(arg):
    return _pydocs("2", arg)

@_space
def search_pydocs3(arg):
    return _pydocs("3", arg)


@_space
def search_github(arg):
    return _URL("https://github.com/search", q = arg)


@_space
def search_bitbucket(arg):
    return _URL("https://bitbucket.org/repo/all/", name = arg)


@_space
def search_wolfram_alpha(arg):
    return _URL("https://www.wolframalpha.com/input/", i = arg)
