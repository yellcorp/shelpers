#!/bin/sh
./venv/bin/black src
./venv/bin/ruff check src
MYPYPATH=src ./venv/bin/mypy --explicit-package-bases src
