import enum
import os
import re
import subprocess
import sys
from argparse import ArgumentParser
from collections.abc import Iterable
from pathlib import Path
from typing import Optional


def get_arg_parser():
    p = ArgumentParser(
        description="""
            Extracts the contents of archive files to directories.
        """
    )

    p.add_argument(
        "files",
        nargs="+",
        help="""
            Files to extract.
        """,
    )

    p.add_argument(
        "--delete",
        action="store_true",
        help="""
            Delete archive files after successful extraction.
        """,
    )

    return p


class ArchiveFormat(enum.Enum):
    BZIP2 = enum.auto()
    GZIP = enum.auto()
    RAR = enum.auto()
    SEVENZ = enum.auto()
    TAR = enum.auto()
    XZ = enum.auto()
    ZIP = enum.auto()


def extract_tar(archive: Path, out_dir: Path):
    subprocess.run(
        ["tar", "-xvf", archive.absolute()],
        cwd=out_dir,
        check=True,
    )


def extract_7z(archive: Path, out_dir: Path):
    subprocess.run(
        ["7z", "x", f"-o{os.curdir}", archive.absolute()], cwd=out_dir, check=True
    )


def extract_zip(archive: Path, out_dir: Path):
    subprocess.run(
        ["unzip", archive.absolute(), "-d", os.curdir], cwd=out_dir, check=True
    )


EXTRACTORS = {
    ArchiveFormat.BZIP2: extract_tar,
    ArchiveFormat.GZIP: extract_tar,
    ArchiveFormat.RAR: extract_7z,
    ArchiveFormat.SEVENZ: extract_7z,
    ArchiveFormat.TAR: extract_tar,
    ArchiveFormat.XZ: extract_tar,
    ArchiveFormat.ZIP: extract_zip,
    None: extract_7z,
}


def identify_file(file: os.PathLike):
    with open(file, "rb") as reader:
        b = reader.read(6)
        if b == b"\xFD\x37\x7A\x58\x5A\x00":
            return ArchiveFormat.XZ
        if b == b"Rar!\x1a\x07":
            return ArchiveFormat.RAR
        if b == b"7z\xbc\xaf'\x1c":
            return ArchiveFormat.SEVENZ
        if b.startswith(b"\x1f\x8B"):
            return ArchiveFormat.GZIP
        if re.match(rb"^BZ[h0][1-9]", b):
            return ArchiveFormat.BZIP2
        if re.match(rb"^PK(\x03\x04|\x05\x06|\x07\x08)", b):
            return ArchiveFormat.ZIP

        reader.seek(257)
        b = reader.read(6)
        if re.match(rb"^ustar[\x00\x20]", b):
            return ArchiveFormat.TAR

        reader.seek(508)
        b = reader.read(4)
        if b == b"tar\x00":
            return ArchiveFormat.TAR

        return None


class Runner:
    def __init__(self, argv0: Optional[str]):
        self.warn_prefix = f"{argv0}: " if argv0 else ""

    def warn(self, message: str):
        print(f"{self.warn_prefix}{message}", file=sys.stderr)

    def extract_all(self, files: Iterable[os.PathLike], delete_archives: bool):
        for f in files:
            self.extract(f, delete_archives)

    def extract(self, archive_file: os.PathLike, delete_on_success: bool) -> bool:
        archive_path = Path(archive_file)
        out_dir = self.dir_for_archive_file(archive_path)
        if not self.should_extract_to(out_dir):
            self.warn(f"Skipping: {os.fspath(archive_path)!r}")
            return False
        out_dir.mkdir(parents=True, exist_ok=True)
        ok = self._do_extract(archive_path, out_dir)
        if ok and delete_on_success:
            try:
                os.remove(archive_path)
            except FileNotFoundError:
                pass
            except Exception as del_exc:
                self.warn(f"Deleting {os.fspath(archive_path)!r}: {del_exc}")
        return ok

    def dir_for_archive_file(self, file: Path) -> Path:
        return file.parent / f"{file.name}.d"

    def should_extract_to(self, dir: Path) -> bool:
        if dir.exists():
            self.warn(f"Exists: {os.fspath(dir)!r}")
            return False
        return True

    def _do_extract(self, archive: Path, out_dir: Path) -> bool:
        print(f"{os.fspath(archive)!r} -> {os.fspath(out_dir)!r}")
        # TODO: force extract type
        try:
            arc_type = identify_file(archive)
            extractor = EXTRACTORS.get(arc_type, EXTRACTORS[None])
            extractor(archive, out_dir)
        except Exception as extract_exc:
            self.warn("{}: {}".format(repr(os.fspath(archive)), extract_exc))
            return False
        return True


def main():
    argv0 = Path(__file__).name
    args = get_arg_parser().parse_args()
    runner = Runner(argv0)
    runner.extract_all(args.files, args.delete)


if __name__ == "__main__":
    main()
