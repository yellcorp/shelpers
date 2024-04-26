from config.bookmarks import bookmark
from installer.binactions import (
    BundleOpener,
    HabitChanger,
    IfBundle,
    Link,
    PythonScript,
)
from utils.bookmark_util import name_func_to_fs

scripts = [
    Link("src/chmod-default.sh"),
    Link("src/chmod-noexec.sh"),
    Link("src/git-reset-perms.sh"),
    Link("src/myip.sh"),
    Link("src/tmuxmain.sh"),
    Link("src/vnc.sh"),
    Link("src/sheet_new.sh", "sheet.new"),
    Link("src/finder-set-hidden.sh", "finder-set-hidden"),
    Link("src/finder-set-hidden.sh", "finder-show-hidden"),
    Link("src/finder-set-hidden.sh", "finder-hide-hidden"),
    Link("src/git-zip.sh", "git-zip"),
    Link("src/git-zip.sh", "git-tbz"),
    Link("src/git-zip.sh", "git-tgz"),
    PythonScript("src/bridge.py"),
    PythonScript("src/imgcat.py"),
    PythonScript("src/jpegopt.py"),
    PythonScript("src/pipenv-unused.py"),
    PythonScript("src/trash.py"),
    PythonScript("src/unzipdir.py"),
]

bookmarks = [
    PythonScript("src/open_bookmark.py", [name], name_func_to_fs(name))
    for name in bookmark.keys()
]

launchers = [
    #
    # generate launchers
    #
    BundleOpener("net.sourceforge.grandperspectiv", "gpersp"),
    BundleOpener("com.ridiculousfish.HexFiend", "hex"),
    BundleOpener("com.adobe.Photoshop", "photoshop"),
    BundleOpener("org.videolan.vlc", "vlc"),
    #
    # launchers included with apps
    #
    IfBundle(
        "com.torusknot.SourceTreeNotMAS",
        lambda sourcetree: Link(sourcetree / "Contents/Resources/stree"),
    ),
    # Both names link to {bundle}/.../bcomp, so I presume it must modify its
    # behavior based on argv[0]. 'bcomp' waits for the tab to close / app to
    # exit, 'bcompare' exits immediately
    IfBundle(
        "com.ScooterSoftware.BeyondCompare",
        lambda bc: Link(bc / "Contents/MacOS/bcomp", "bcomp"),
    ),
    IfBundle(
        "com.ScooterSoftware.BeyondCompare",
        lambda bc: Link(bc / "Contents/MacOS/bcomp", "bcompare"),
    ),
    IfBundle(
        "com.microsoft.VSCode",
        lambda vscode: Link(vscode / "Contents/Resources/app/bin/code", "vscode"),
    ),
]

habit_changers = [
    HabitChanger("youtube-dl", "yt-dlp"),
]

manifest = scripts + bookmarks + launchers + habit_changers
