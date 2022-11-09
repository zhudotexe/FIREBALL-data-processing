import glob
import gzip
import json
import logging
import os
import pathlib
from typing import Iterable, Union

import dirhash

AnyPath = Union[str, bytes, os.PathLike]

log = logging.getLogger(__name__)


def read_gzipped_file_raw(fp: AnyPath) -> Iterable[bytes]:
    """Given a path to a gzipped data file, return an iterator of lines in the file."""
    try:
        with gzip.open(fp, mode="r") as f:
            yield from f
    except gzip.BadGzipFile as e:
        log.warning(f"Could not read file {os.path.relpath(fp)}: {e}")


def read_gzipped_file(fp: AnyPath) -> Iterable[dict]:
    """Given a path to a gzipped data file, return an iterator of events in the file."""
    for line in read_gzipped_file_raw(fp):
        yield json.loads(line)


def read_jsonl_file(fp: AnyPath) -> Iterable[dict]:
    """Given a path to a JSONL file, return an iterator of events in the file."""
    with open(fp, "r") as f:
        for line in f:
            yield json.loads(line)


def combat_dir_iterator(dirpath: AnyPath) -> Iterable[dict]:
    """Given a path to a directory of gzipped combat event files, return an iterator of events in the dir."""
    for fp in sorted(glob.glob("*.gz", root_dir=dirpath)):
        yield from read_gzipped_file(os.path.join(dirpath, fp))


def combat_dir_iterator_raw(dirpath: AnyPath) -> Iterable[bytes]:
    """
    Given a path to a directory of gzipped combat event files, return an iterator of events (as JSON bytes, each ending
    with a newline) in the dir.
    """
    for fp in sorted(glob.glob("*.gz", root_dir=dirpath)):
        for event_bytes in read_gzipped_file_raw(os.path.join(dirpath, fp)):
            # files do not necessarily have ending newlines - we have to provide them for stream consumers
            # who expect one on each line, otherwise the file sep puts 2 events on the same line
            if event_bytes.endswith(b"\n"):
                yield event_bytes
            else:
                yield event_bytes + b"\n"


def get_combat_dirs(datapath: AnyPath) -> list[pathlib.Path]:
    """Given the path to the raw data root, return a list of combat dir paths."""
    return [pathlib.Path(d.path) for d in os.scandir(datapath) if d.is_dir()]


def dataset_checksum(datapath: AnyPath) -> str:
    """Returns the checksum of the dataset at the given path."""
    num_cores = os.cpu_count() or 1
    return dirhash.dirhash(datapath, "md5", match=("*.gz",), jobs=num_cores)


def write_jsonl(fpath: AnyPath, data: list):
    """
    Write a list of data to the file at *fpath*. If the supplied path ends with `.gz`, zips the output file.
    """
    if isinstance(fpath, pathlib.Path):
        should_compress = fpath.suffix.endswith(".gz")
    else:
        should_compress = fpath.endswith(".gz")

    if should_compress:
        f = gzip.open(fpath, "wt")
    else:
        f = open(fpath, "w")

    for line in data:
        f.write(json.dumps(line, default=lambda obj: obj.dict()) + "\n")

    f.close()
