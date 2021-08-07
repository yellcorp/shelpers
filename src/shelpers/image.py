import os
import re

import PIL.Image


def scaler_identity(image):
    return image


class Scaler:
    def __init__(self, filter=PIL.Image.BILINEAR):
        self.filter = filter

    def image_scale_by_factor(self, image, factor):
        if factor == 1:
            return image

        return image.resize(
            [max(1, int(axis * factor + 0.5)) for axis in image.size], self.filter
        )

    def image_scale_down_by_factor(self, image, factor):
        if factor >= 1:
            return image
        return self.image_scale_by_factor(image, factor)

    def scaler_fit(self, width, height):
        def scale(image):
            owidth, oheight = image.size
            factor = min(width / owidth, height / oheight)
            return self.image_scale_down_by_factor(image, factor)

        return scale

    def scaler_width(self, width):
        def scale(image):
            owidth, _height = image.size
            return self.image_scale_down_by_factor(image, width / owidth)

        return scale

    def scaler_factor(self, factor):
        def scale(image):
            return self.image_scale_by_factor(image, factor)

        return scale

    def parse(self, scale_spec: str):
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


def is_image_filename(name):
    name = name.lower()
    if name == ".icns":
        return True

    _, ext = os.path.splitext(name)
    return ext[1:].lower() in SUPPORTED_EXTS


def generate_checkerboard(dimensions, checker_size, color1, color2, mode="P"):
    if any(axis <= 0 for axis in dimensions):
        raise ValueError("Invalid dimensions")

    if checker_size <= 0:
        raise ValueError("Invalid checker_size")

    if mode not in ("P", "RGB"):
        raise ValueError("Mode must be one of 'P', 'RGB'")

    # ceil-divide dimensions by checker_size to get the canvas size
    # at which one checker = one pixel
    checker_dims = [(axis + checker_size - 1) // checker_size for axis in dimensions]

    # make sure the width is an odd number, so that a run of alternating
    # pixels, when wrapped to the width, will be offset every other row
    checker_dims[0] |= 1

    # how many checkers?
    checker_count = checker_dims[0] * checker_dims[1]

    # how many pairs? ceil-divide by 2
    pair_count = (checker_count + 1) // 2

    checker_raster = b"\x00\x01" * pair_count
    pix_image = PIL.Image.frombytes("P", checker_dims, checker_raster)

    palette = bytearray(768)
    palette[0:3] = color1
    palette[3:6] = color2
    pix_image.putpalette(palette)

    large_dims = [axis * checker_size for axis in checker_dims]
    oversized_image = pix_image.resize(large_dims, PIL.Image.NEAREST)
    del pix_image

    # a small touch: center the crop that we take from the oversized
    # checkerboard
    left, top = ((large - final) // 2 for large, final in zip(large_dims, dimensions))

    final_image = oversized_image.crop(
        (left, top, left + dimensions[0], top + dimensions[1]),
    )

    if mode == "P":
        final_image.load()
        return final_image

    return final_image.convert("RGB")


def composite_checkerboard(rgba_image, checker_size, color1, color2):
    checkerboard = generate_checkerboard(
        rgba_image.size, checker_size, color1, color2, "RGB"
    )
    checkerboard.paste(rgba_image, None, rgba_image)
    return checkerboard


def image_has_transparency(image):
    return image.mode in ("RGBA", "RGBa", "LA") or "transparency" in image.info


def deref_palette(image):
    if image.mode in ("L", "RGB", "RGBA"):
        return image

    if image.mode == "1":
        return image.convert("L")

    if image_has_transparency(image):
        return image.convert("RGBA")

    return image.convert("RGB")
