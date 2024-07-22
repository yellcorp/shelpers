import io
import os
from base64 import standard_b64encode
from functools import lru_cache


@lru_cache(maxsize=1)
def is_tmux():
    if os.environ.get("TERM_PROGRAM", "") == "tmux":
        return True
    term = os.environ.get("TERM", "")
    if term in ("tmux", "screen") or term.startswith(("tmux-", "screen-")):
        return True
    return False


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


# Must be less than 1048576 (2**20). Since v3.5.0, iTerm will abort
# parsing of any sequences longer than 1048576 bytes.
DEFAULT_MULTIPART_CHUNK_SIZE = 0xEC000


def iterm_encode_image(image, pil_save_args, name=None, multipart_chunk_size=None):
    if multipart_chunk_size is None:
        multipart_chunk_size = DEFAULT_MULTIPART_CHUNK_SIZE

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

    kwargs_str = iterm_format_dict(kwargs)
    encoded_content = base64_text(transfer_bytes)

    if multipart_chunk_size > 0:
        # This multipart protocol is not documented at the time of writing. A
        # reference implementation is here:
        # https://raw.githubusercontent.com/gnachman/iTerm2-shell-integration/main/utilities/imgcat
        yield osc(f"1337;MultipartFile={kwargs_str}")
        for offset in range(0, len(encoded_content), multipart_chunk_size):
            chunk = encoded_content[offset : offset + multipart_chunk_size]
            yield osc(f"1337;FilePart={chunk}")
        yield osc("1337;FileEnd")
    else:
        yield osc(f"1337;File={kwargs_str}:{encoded_content}")
