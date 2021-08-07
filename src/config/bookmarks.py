from utils.bookmark_util import URL, FunctionDict, join_space

bookmark = FunctionDict()


@bookmark
@join_space
def search_google(arg):
    return URL("https://www.google.com/search", q=arg)


@bookmark
@join_space
def search_google_image(arg):
    return search_google(arg).update(tbm="isch")


@bookmark
@join_space
def search_google_video(arg):
    return search_google(arg).update(tbm="vid")


@bookmark
@join_space
def search_ddg(arg):
    return URL("https://duckduckgo.com/", q=arg, t="h_", ia="web")


@bookmark
@join_space
def search_ddg_image(arg):
    return search_ddg(arg).update(ia="images", iax="images")


@bookmark
@join_space
def search_ddg_video(arg):
    return search_ddg(arg).update(ia="videos", iax="videos")


@bookmark
@join_space
def search_youtube(arg):
    return URL("https://www.youtube.com/results", search_query=arg)


@bookmark
@join_space
def search_symbolhound(arg):
    return URL("http://symbolhound.com/", q=arg)


@bookmark
@join_space
def search_mdn(arg):
    return URL("https://developer.mozilla.org/en-US/search", q=arg)


def pydocs(version, query):
    return URL(
        f"https://docs.python.org/{version}/search.html",
        q=query,
        check_keywords="yes",
        area="default",
    )


@bookmark
@join_space
def search_pydocs2(arg):
    return pydocs("2", arg)


@bookmark
@join_space
def search_pydocs3(arg):
    return pydocs("3", arg)


@bookmark
@join_space
def search_github(arg):
    return URL("https://github.com/search", q=arg)


@bookmark
@join_space
def search_wolfram_alpha(arg):
    return URL("https://www.wolframalpha.com/input/", i=arg)
