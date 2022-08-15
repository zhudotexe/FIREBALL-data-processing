"""
Usage: python heuristic_worker.py
Given a heuristic that maps a list of events to a float [0.0..1.0], outputs a metadata file indexing the heuristic
score of each combat in data/.
"""
import csv
import functools
import glob
import gzip
import json
import logging
import os
from typing import Callable, Iterable, Union

import heuristics

# ===== typing =====
AnyPath = Union[str, bytes, os.PathLike]
Event = dict  # todo
Heuristic = Callable[[Iterable[Event]], float]

log = logging.getLogger(__name__)


# ===== impl =====
def read_gzipped_file(fp: AnyPath) -> Iterable[Event]:
    """Given a path to a gzipped data file, return an iterator of events in the file."""
    try:
        with gzip.open(fp, mode="r") as f:
            for line in f:
                yield json.loads(line)
    except gzip.BadGzipFile as e:
        log.warning(f"Could not read file {os.path.basename(fp)}: {e}")


def combat_dir_iterator(dirpath: AnyPath) -> Iterable[Event]:
    """Given a path to a directory of gzipped combat event files, return an iterator of events in the dir."""
    for fp in sorted(glob.glob("*.gz", root_dir=dirpath)):
        yield from read_gzipped_file(os.path.join(dirpath, fp))


def get_combat_dirs(datapath: AnyPath) -> list[str]:
    """Given the path to the raw data root, return a list of combat dir paths."""
    return [d.path for d in os.scandir(datapath) if d.is_dir()]


def get_heuristic(name: str) -> Heuristic:
    """Returns the heuristic with the given name (utility method for CLI)"""
    return getattr(heuristics, name)


def worker_entrypoint(heuristic: Heuristic, combat_dir: str) -> tuple[str, float]:
    """Multiprocessing worker entrypoint, applies the given heuristic to one dir"""
    return os.path.basename(combat_dir), heuristic(combat_dir_iterator(combat_dir))


# ===== CLI =====
def run_cli():
    import tqdm.contrib.concurrent

    # config
    # todo make this read from CLI
    heuristic = get_heuristic("message_to_command_ratio")
    data_dir_path = os.path.join(os.path.dirname(__file__), "data")
    result_file_path = os.path.join(os.path.dirname(__file__), "heuristic_results", f"{heuristic.__name__}.csv")
    entrypoint = functools.partial(worker_entrypoint, heuristic)

    # execution
    results = tqdm.contrib.concurrent.process_map(entrypoint, get_combat_dirs(data_dir_path), chunksize=10)
    results.sort(key=lambda pair: pair[1])

    # save results
    os.makedirs(os.path.dirname(result_file_path), exist_ok=True)
    with open(result_file_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(results)
    print("Done!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_cli()
