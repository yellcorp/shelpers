import ast
import os

from utils.fs import to_path
from utils.text import u8open


class ReceiptLog:
    def __init__(self, path):
        self.path = to_path(path)

    def clear(self):
        self.path.unlink(missing_ok=True)

    def load(self):
        try:
            with u8open(self.path, "r") as reader:
                for line in reader:
                    line = line.rstrip()
                    if line:
                        yield ast.literal_eval(line)
        except FileNotFoundError:
            pass

    def append(self, name):
        with u8open(self.path, "a") as writer:
            print(repr(os.fspath(name)), file=writer)
