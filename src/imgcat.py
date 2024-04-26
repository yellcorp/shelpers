import os
import sys
from argparse import ArgumentParser
from functools import partial

import PIL.Image

from utils.image import (
    Scaler,
    composite_checkerboard,
    deref_palette,
    image_has_transparency,
    is_image_filename,
)
from utils.iterm import iterm_encode_image

CHECKER_SIZE = 16
CHECKER_COLORS = (
    (111, 111, 111),
    (143, 143, 143),
)


def get_arg_parser():
    p = ArgumentParser(
        description="""\
            Displays images in iTerm format.
        """
    )

    p.add_argument("paths", nargs="+", help="The files to display")

    p.add_argument(
        "--size",
        "-s",
        type=SCALER.parse,
        default="640x480",
        help="""\
            The size at which to display the image. If specified as dimensions
            #x#, the image will be proportionately scaled down to fit if
            necessary.  If a single dimension is specified, the image's width
            will be scaled to this. If a percentage #%%, the image will be
            scaled by that amount.  Specify 100%% to display it without
            transformation.  The default is %(default)s.
        """,
    )

    p.add_argument(
        "--recurse",
        "-r",
        action="store_true",
        help="""\
            Recursively search directories for images and display them.
        """,
    )

    p.add_argument(
        "--alpha",
        "-a",
        action="store_true",
        help="""\
            Preserve alpha. If not specified (the default), images with alpha
            channels are composited against a checkerboard pattern.
        """,
    )

    return p


SCALER = Scaler(PIL.Image.Resampling.BILINEAR)

IMAGE_TRANSFER_FORMAT_KWARGS = dict(
    format="jpeg",
    quality=70,
    subsampling="4:2:0",
)


def report_error(argv0, message, path=None, exc=None):
    parts = [argv0, ": "]
    if path is not None:
        parts.extend((path, ": "))

    parts.extend(message)
    if exc is not None:
        parts.extend((" (", str(exc), ")"))

    print("".join(parts), file=sys.stderr)


def recursive_file_iter(paths, onerror):
    def walk_error(os_error):
        onerror("Error recursing", path=os_error.filename, exc=os_error)

    for path in paths:
        try:
            realpath = os.path.realpath(path)
        except OSError as rp_error:
            onerror("Error resolving path", path=path, exc=rp_error)
            realpath = path

        if os.path.isdir(realpath) or os.path.ismount(realpath):
            for container, dirnames, filenames in os.walk(realpath, onerror=walk_error):
                dirnames[:] = [d for d in dirnames if not d.startswith(".")]
                for f in filenames:
                    if is_image_filename(f):
                        yield os.path.join(container, f)
        else:
            yield path


class App:
    def __init__(self, resize_func, alpha: bool, onerror):
        self.resize_func = resize_func
        self.alpha = alpha
        self.onerror = onerror

    def run(self, paths):
        for path in paths:
            self.show_image(path)

    def show_image(self, path):
        try:
            image = PIL.Image.open(path)
        except Exception as problem:
            self.onerror("Error while reading", path=path, exc=problem)
            return

        image = self.resize_func(deref_palette(image))

        if image_has_transparency(image) and not self.alpha:
            image = composite_checkerboard(
                image, CHECKER_SIZE, CHECKER_COLORS[0], CHECKER_COLORS[1]
            )

        print(path)
        print(iterm_encode_image(image, IMAGE_TRANSFER_FORMAT_KWARGS, name=path))


def main():
    config = get_arg_parser().parse_args()

    reporter = partial(report_error, sys.argv[0])
    if config.recurse:
        files = recursive_file_iter(config.paths, reporter)
    else:
        files = config.paths

    app = App(
        resize_func=config.size,
        alpha=config.alpha,
        onerror=reporter,
    )

    app.run(files)


if __name__ == "__main__":
    main()
