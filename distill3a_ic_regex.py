"""
Distill3a: Given time-grouped triples, filter the events in the triples:
- remove portions of utterances matching regex patterns likely to be out of character

Input: {"before": [Message...], "commands": [Event...], "after": [Message...]}

Output: {
    "before": [Message...],
    "commands": [Event...],
    "after": [Message...],
}
- with `before` and `after` filtered to only include utterances from the user who ran `commands` or a DM
"""
import glob
import logging
import pathlib
import re

import tqdm.contrib.concurrent
import tqdm.contrib.logging

from dataset.utils import combat_dir_iterator, read_gzipped_file, write_jsonl
from heuristics.utils import Instance

DATA_DIR = pathlib.Path("data/")
# IN_DIR = pathlib.Path("extract/experiment1/")
# OUT_DIR = pathlib.Path("extract/experiment2/")
IN_DIR = pathlib.Path("extract/regression/experiment2/")
OUT_DIR = pathlib.Path("extract/regression/experiment3a/")
RUN_PARALLEL = False
log = logging.getLogger("distill3a")
loglevel = logging.INFO


def sub_content(self, filter, message):
    content = message['content']
    if re.search(filter, content):
        # print(content)
        content = re.sub(filter,"",content)
        # print(content)
        message['content'] = content
    return message

def process_triple(self, triple: dict) -> dict | None:
    """Given a triple, return a processed triple - main entrypoint"""
    before = triple["before"]
    commands = triple["commands"]
    after = triple["after"]

    filters = [r"\(.*\)"]
    for filter in filters:
        before = [self.sub_content(filter,message) for message in before]
        after = [self.sub_content(filter,message) for message in after]
    # discard if we have no filtered utterances
    if not (before or after):
        return None

    return {
        "before": before,
        "commands": commands,
        "after": after,
    }


def process_file(fp: pathlib.Path):
    triple_stream = read_gzipped_file(fp)
    num_triples_in = 0
    combat_id, *_ = fp.stem.split(".")
    event_stream = combat_dir_iterator(DATA_DIR / combat_id)
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
