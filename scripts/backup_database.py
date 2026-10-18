"""Create a consistent backend SQLite backup, including committed WAL contents."""

import argparse
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.parse import quote


def backup(source: Path, destination: Path):
    if not source.is_file() or destination.exists() or source.resolve() == destination.resolve():
        raise ValueError("Source must exist and destination must be a new file.")
    uri = "file:" + quote(source.resolve().as_posix(), safe="/:") + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as origin:
        if origin.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("Source integrity check failed")
        with closing(sqlite3.connect(destination)) as target:
            origin.backup(target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    arguments = parser.parse_args()
    backup(arguments.source, arguments.destination)
    print("Consistent SQLite backup created.")


if __name__ == "__main__":
    main()
