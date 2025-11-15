import os
import re
from collections.abc import Callable

from PIL.Image import alpha_composite, frombytes, Image, Resampling

ColorRGB = tuple[int, int, int]


DEFAULT_CHECKER_SIZE = 16
DEFAULT_CHECKER_COLORS = (
    (111, 111, 111),
    (143, 143, 143),
)


def scaler_identity(image):
    return image


ImageFunction = Callable[[Image], Image]


class Scaler:
    def __init__(self, filter: Resampling = Resampling.BILINEAR):
        self.filter = filter

    def image_scale_by_factor(self, image: Image, factor: float) -> Image:
        if factor == 1:
            return image

        w, h = [int(axis * factor + 0.5) for axis in image.size]
        return image.resize((w, h), self.filter)

    def image_scale_down_by_factor(self, image: Image, factor: float) -> Image:
        if factor >= 1:
            return image
        return self.image_scale_by_factor(image, factor)

    def scaler_fit(self, width: float, height: float) -> ImageFunction:
        def scale(image: Image) -> Image:
            owidth, oheight = image.size
            factor = min(width / owidth, height / oheight)
            return self.image_scale_down_by_factor(image, factor)

        return scale

    def scaler_width(self, width: float) -> ImageFunction:
        def scale(image: Image) -> Image:
            owidth, _height = image.size
            return self.image_scale_down_by_factor(image, width / owidth)

        return scale

    def scaler_factor(self, factor: float) -> ImageFunction:
        def scale(image: Image) -> Image:
            return self.image_scale_by_factor(image, factor)

        return scale

    def parse(self, scale_spec: str) -> ImageFunction:
        if scale_spec.endswith("%"):
            factor = float(scale_spec[:-1]) / 100
            if factor == 1:
                return scaler_identity
            return self.scaler_factor(factor)

        if re.match(r"^\d+$", scale_spec):
            return self.scaler_width(float(scale_spec))

        width, height = re.split(r"[^\s\d]+", scale_spec, 1)
        return self.scaler_fit(float(width), float(height))


SUPPORTED_EXTS = frozenset(
    (
        "bmp",
        "eps",
        "gif",
        "icns",
        "ico",
        "jpg",
        "jpe",
        "jpeg",
        "jfif",
        "jp2",
        "pcx",
        "png",
        "pbm",
        "pgm",
        "ppm",
        "sgi",
        "spi",
        "spider",
        "tga",
        "targa",
        "tif",
        "tiff",
        "webp",
        "xbm",
        "blp",
        "blp1",
        "blp2",
        "cur",
        "dcx",
        "dds",
        "fli",
        "flc",
        "fpx",
        "ftex",
        "gbr",
        "imt",
        "mic",
        "mpo",
        "pcd",
        "psd",
        "xpm",
    )
)


def is_image_filename(name: str) -> bool:
    name = name.lower()
    if name == ".icns":
        return True

    _, ext = os.path.splitext(name)
    return ext[1:].lower() in SUPPORTED_EXTS


def generate_checkerboard(
    dimensions: tuple[int, int],
    checker_size: int,
    color1: ColorRGB,
    color2: ColorRGB,
    mode: str = "P",
) -> Image:
    if any(axis <= 0 for axis in dimensions):
        raise ValueError("Invalid dimensions")

    if checker_size <= 0:
        raise ValueError("Invalid checker_size")

    # ceil-divide dimensions by checker_size to get the canvas size
    # at which one checker = one pixel
    countx, county = ((axis + checker_size - 1) // checker_size for axis in dimensions)

    # make sure the width is an odd number, so that a run of alternating
    # pixels, when wrapped to the width, will be offset every other row
    countx |= 1

    # how many checkers?
    checker_count = countx * county
    # how many pairs? ceil-divide by 2
    pair_count = (checker_count + 1) // 2

    checker_raster = b"\x00\x01" * pair_count
    pix_image = frombytes("P", (countx, county), checker_raster)

    palette = bytearray(768)
    palette[0:3] = color1
    palette[3:6] = color2
    pix_image.putpalette(palette)

    cpix_w, cpix_h = [axis * checker_size for axis in (countx, county)]
    ceil_pixel_size = cpix_w, cpix_h
    oversized_image = pix_image.resize(ceil_pixel_size, Resampling.NEAREST)
    del pix_image

    # a small touch: center the crop that we take from the oversized
    # checkerboard
    left, top = (
        (large - final) // 2 for large, final in zip(ceil_pixel_size, dimensions)
    )

    checker_image = oversized_image.crop(
        (left, top, left + dimensions[0], top + dimensions[1])
    )

    if mode == "P":
        checker_image.load()
        return checker_image

    return checker_image.convert(mode)


def composite_checkerboard(
    rgba_image: Image,
    checker_size: int,
    color1: ColorRGB,
    color2: ColorRGB,
) -> Image:
    checkerboard = generate_checkerboard(
        rgba_image.size,
        checker_size,
        color1,
        color2,
        "RGBA",
    )
    return alpha_composite(checkerboard, rgba_image).convert("RGB")


def image_has_transparency(image: Image) -> bool:
    return image.mode in ("RGBA", "RGBa", "LA") or (
        image.mode == "P" and "transparency" in image.info
    )


def deref_palette(image: Image) -> Image:
    if image.mode in ("L", "RGB", "RGBA"):
        return image

    if image.mode == "1":
        return image.convert("L")

    if image_has_transparency(image):
        return image.convert("RGBA")

    return image.convert("RGB")
