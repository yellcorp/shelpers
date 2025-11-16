from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

import PIL.Image

from utils.image import (
    composite_checkerboard,
    DEFAULT_CHECKER_COLORS,
    DEFAULT_CHECKER_SIZE,
    image_has_transparency,
)

PREVIEW_MAX_SIZE = (1920, 1080)
PREVIEW_JPEG_QUALITY = 70

EXIT_SHIFT = 64


class ExitCode(IntEnum):
    DECLINE = 0
    PREVIEW_STDOUT = EXIT_SHIFT + 0
    NO_PREVIEW = EXIT_SHIFT + 1
    PREVIEW_AS_PLAIN_TEXT = EXIT_SHIFT + 2
    CONST_WIDTH = EXIT_SHIFT + 3
    CONST_HEIGHT = EXIT_SHIFT + 4
    CONST_SIZE = EXIT_SHIFT + 5
    PREVIEW_AS_IMAGE_AT_CACHE_PATH = EXIT_SHIFT + 6
    PREVIEW_AS_IMAGE = EXIT_SHIFT + 7


@dataclass
class RangerScopeArgs:
    argv0: Path
    file_path: Path
    n_cols: int
    n_rows: int
    image_cache_path: Path
    image_preview_enabled: bool

    @classmethod
    def from_argv(cls, argv: list[str]) -> RangerScopeArgs:
        argv0, file_path, n_cols, n_rows, image_cache_path, image_preview_enabled = argv

        return cls(
            argv0=Path(argv0),
            file_path=Path(file_path),
            n_cols=int(n_cols),
            n_rows=int(n_rows),
            image_cache_path=Path(image_cache_path),
            image_preview_enabled=image_preview_enabled == "True",
        )


def render_image_preview(source_path: Path, cache_path: Path) -> None:
    image = PIL.Image.open(source_path)
    image.apply_transparency()
    image.thumbnail(PREVIEW_MAX_SIZE)

    if image_has_transparency(image):
        image = composite_checkerboard(
            image.convert("RGBA"),
            DEFAULT_CHECKER_SIZE,
            DEFAULT_CHECKER_COLORS[0],
            DEFAULT_CHECKER_COLORS[1],
        )

    image = image.convert("RGB")
    image.save(cache_path, format="JPEG", quality=PREVIEW_JPEG_QUALITY)


def main():
    is_test = os.getenv("YELLCORP_TEST") == "1"
    if is_test:
        argv0, in_path, out_path = sys.argv
        terminal_size = shutil.get_terminal_size()
        args = RangerScopeArgs(
            argv0=Path(argv0),
            file_path=Path(in_path),
            n_cols=terminal_size.columns,
            n_rows=terminal_size.lines,
            image_cache_path=Path(out_path),
            image_preview_enabled=True,
        )
    else:
        args = RangerScopeArgs.from_argv(sys.argv)

    if args.image_preview_enabled:
        try:
            render_image_preview(args.file_path, args.image_cache_path)
            return ExitCode.PREVIEW_AS_IMAGE_AT_CACHE_PATH
        except Exception:
            if is_test:
                raise
            else:
                pass
    return ExitCode.DECLINE


if __name__ == "__main__":
    sys.exit(main())
