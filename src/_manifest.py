from shelpers.appbundle import BundlePath
from shelpers.bookmark_util import name_func_to_fs
from shelpers.bookmarks import bookmark
from shelpers.install import BundleOpener, Link, PipenvPython

scripts = [
    Link("src/chmod-default.sh"),
    Link("src/chmod-noexec.sh"),
    Link("src/git-reset-perms.sh"),
    Link("src/myip.sh"),
    Link("src/tmuxmain.sh"),
    Link("src/unzipdir.sh"),
    Link("src/vnc.sh"),
    Link("src/sheet_new.sh", "sheet.new"),
    Link("src/finder-set-hidden.sh", "finder-set-hidden"),
    Link("src/finder-set-hidden.sh", "finder-show-hidden"),
    Link("src/finder-set-hidden.sh", "finder-hide-hidden"),
    Link("src/git-zip.sh", "git-zip"),
    Link("src/git-zip.sh", "git-tbz"),
    Link("src/git-zip.sh", "git-tgz"),
    PipenvPython("src/imgcat.py"),
    PipenvPython("src/jpegopt.py"),
    PipenvPython("src/trash.py"),
]

bookmarks = [
    PipenvPython("src/open_bookmark.py", name_func_to_fs(name), name)
    for name in bookmark.keys()
]

launchers = [
    #
    # generate launchers
    #
    BundleOpener("com.adobe.bridge11", "bridge"),
    BundleOpener("net.sourceforge.grandperspectiv", "gpersp"),
    BundleOpener("com.ridiculousfish.HexFiend", "hex"),
    BundleOpener("com.adobe.Photoshop", "photoshop"),
    BundleOpener("org.videolan.vlc", "vlc"),
    #
    # launchers included with apps
    #
    Link(BundlePath("com.torusknot.SourceTreeNotMAS") / "Contents/Resources/stree"),
    Link(
        BundlePath("com.ScooterSoftware.BeyondCompare") / "Contents/MacOS/BCompare",
        "bcompare",
    ),
    Link(
        BundlePath("com.ScooterSoftware.BeyondCompare") / "Contents/MacOS/bcomp",
    ),
    Link(
        BundlePath("com.microsoft.VSCode") / "Contents/Resources/app/bin/code", "vscode"
    ),
]

manifest = scripts + bookmarks + launchers
