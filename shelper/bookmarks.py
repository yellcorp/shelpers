from __future__ import division, print_function

import urllib # 2


class _URL(object):
    def __init__(self, url, **get_params):
        self.url = url
        self.get = dict(get_params)

    def update(self, *args, **kwargs):
        self.get.update(*args, **kwargs)
        return self

    def to_url(self):
        if self.get and len(self.get) > 0:
            return "%s?%s" % (self.url, urllib.urlencode(self.get))
        return "%s" % self.url


def google(arg):
    return _URL("https://www.google.com/search", q = arg)

def google_image(arg):
    return google(arg).update(tbm = "isch")

def google_video(arg):
    return google(arg).update(tbm = "vid")


def duckduckgo(arg):
    return _URL("https://duckduckgo.com/", q = arg)

def duckduckgo_image(arg):
    return duckduckgo(arg).update(ia = "images", iax = "images")

def duckduckgo_video(arg):
    return duckduckgo(arg).update(ia = "videos", iax = "videos")


def youtube(arg):
    return _URL("https://www.youtube.com/results", search_query = arg)


def symbolhound(arg):
    return _URL("http://symbolhound.com/", q = arg)


def mdn(arg):
    return _URL("https://developer.mozilla.org/en-US/search", q = arg)


def _pydocs(version, arg):
    return _URL(
        "https://docs.python.org/%s/search.html" % version,
        q = arg,
        check_keywords = "yes",
        area = "default"
    )

def pydocs2(arg):
    return _pydocs("2", arg)

def pydocs3(arg):
    return _pydocs("3", arg)


def github(arg):
    return _URL("https://github.com/search", q = arg)

def bitbucket(arg):
    return _URL("https://bitbucket.org/repo/all/", name = arg)
