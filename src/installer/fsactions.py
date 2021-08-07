import os
from pathlib import Path


class FileAction:
    def get_path(self) -> Path:
        raise NotImplementedError()

    def execute(self):
        raise NotImplementedError()


class ScriptFile(FileAction):
    def __init__(self, path: Path, source: str):
        self.path = path
        self.source = source

    def get_path(self) -> Path:
        return self.path

    def execute(self):
        with open(self.path, "w", encoding="utf-8") as writer:
            writer.write(self.source)
        self.path.chmod(0o755)


class Symlink(FileAction):
    def __init__(self, link_path: Path, link_content: str):
        self.link_path = link_path
        self.link_content = link_content

    def get_path(self) -> Path:
        return self.link_path

    def execute(self):
        os.symlink(self.link_content, self.link_path)
