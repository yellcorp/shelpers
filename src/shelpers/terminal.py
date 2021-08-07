import io
import os
from base64 import standard_b64encode
from functools import lru_cache


@lru_cache(maxsize=1)
def is_tmux():
    return os.environ.get("TERM", "").startswith("screen")


@lru_cache(maxsize=1)
def get_osc_template():
    if is_tmux():
        # tmux sequence wrapper from iTerm's own imgcat
        # still doesn't really work as tmux can't track how far the cursor
        # advances after displaying the image
        return "\x1bPtmux;\x1b\x1b]{}\x07\x1b\\"
    return "\x1b]{}\x07"


def osc(content):
    return get_osc_template().format(content)


def base64_text(data):
    return standard_b64encode(data).decode("ascii")


def iterm_format_dict(d):
    return ";".join(f"{k}={v}" for k, v in d.items())


def iterm_encode_image(image, pil_save_args, name=None):
    transfer_file = io.BytesIO()
    image.save(transfer_file, **pil_save_args)

    transfer_bytes = transfer_file.getvalue()

    kwargs = dict(
        width="auto",
        height="auto",
        preserveAspectRatio=1,
        inline=1,
        size=len(transfer_bytes),
    )

    if name is not None:
        kwargs["name"] = base64_text(name.encode("utf-8"))

    return osc(
        "1337;File={kwargs}:{encoded_bytes}".format(
            kwargs=iterm_format_dict(kwargs),
            encoded_bytes=base64_text(transfer_bytes),
        )
    )
