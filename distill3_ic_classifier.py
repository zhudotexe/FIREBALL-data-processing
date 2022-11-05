"""
Distill3: Given triples, filter the events in the triples:
- remove OOC utterances

Input: {"before": [Message...], "commands": [Event...], "after": [Message...]}

Output: {
    "before": [Message...],
    "commands": [Event...],
    "after": [Message...],
}
- with `after` filtered to only include IC-classified utterances (maybe `before` too - see how you feel about it)
"""
import glob
import logging
import os.path
import pathlib
import sys

import tqdm.contrib.concurrent
import tqdm.contrib.logging

from heuristics.utils import Instance
from dataset.utils import combat_dir_iterator, read_gzipped_file, write_jsonl

DATA_DIR = pathlib.Path("data/")
IN_DIR = pathlib.Path("extract/experiment2/")
OUT_DIR = pathlib.Path("extract/experiment3/")
RUN_PARALLEL = True
log = logging.getLogger("distill3")
loglevel = logging.INFO


def process_triple(triple: dict) -> dict:
    # TODO do the filtering based on triple["after"][*]["content"]
    # TODO if not (before or after): return (discard triples where everything is filtered out)
    pass


def process_file(fp: pathlib.Path):
    """
    Given a path to a file containing a list of triples, filter the triples and return a pair of
    (n_triples_in, n_triples_out).
    """
    triple_stream = read_gzipped_file(fp)
    num_triples_in = 0
    combat_id, *_ = fp.stem.split(".")
    out = []

    for triple in triple_stream:
        num_triples_in += 1
        processed = process_triple(triple)
        if processed is not None:
            out.append(processed)

    # discard if we have nothing
    if not out:
        return num_triples_in, 0

    # see what we get
    write_jsonl(OUT_DIR / f"{combat_id}.jsonl.gz", out)
    return num_triples_in, len(out)


if __name__ == "__main__":
    logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    filenames = sorted(glob.glob("*.gz", root_dir=IN_DIR))
    files = [pathlib.Path(IN_DIR, fn) for fn in filenames]
    with tqdm.contrib.logging.logging_redirect_tqdm():
        if RUN_PARALLEL:
            results = tqdm.contrib.concurrent.process_map(process_file, files, chunksize=10)
        else:
            results = []
            for d in tqdm.tqdm(files):
                results.append(process_file(d))

    kept_distill_count = sum(1 for (i, o) in results if o)
    n_triples_in = sum(i for i, o in results)
    n_triples_out = sum(o for i, o in results)
    print(
        f"Distill complete!\n"
        f"Instances: {len(filenames)} -> {kept_distill_count}\n"
        f"Triples: {n_triples_in} -> {n_triples_out}"
    )
