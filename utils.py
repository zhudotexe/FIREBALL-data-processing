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


def read_gzipped_file(fp: AnyPath) -> Iterable[dict]:
    """Given a path to a gzipped data file, return an iterator of events in the file."""
    try:
        with gzip.open(fp, mode="r") as f:
            for line in f:
                yield json.loads(line)
    except gzip.BadGzipFile as e:
        log.warning(f"Could not read file {os.path.relpath(fp)}: {e}")


def combat_dir_iterator(dirpath: AnyPath) -> Iterable[dict]:
    """Given a path to a directory of gzipped combat event files, return an iterator of events in the dir."""
    for fp in sorted(glob.glob("*.gz", root_dir=dirpath)):
        yield from read_gzipped_file(os.path.join(dirpath, fp))


def get_combat_dirs(datapath: AnyPath) -> list[pathlib.Path]:
    """Given the path to the raw data root, return a list of combat dir paths."""
    return [pathlib.Path(d.path) for d in os.scandir(datapath) if d.is_dir()]


def dataset_checksum(datapath: AnyPath) -> str:
    """Returns the checksum of the dataset at the given path."""
    num_cores = os.cpu_count() or 1
    return dirhash.dirhash(datapath, "md5", match=("*.gz",), jobs=num_cores)
