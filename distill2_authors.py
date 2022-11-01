"""
Distill2: Given time-grouped triples, filter the events in the triples:
- remove utterances from irrelevant users

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
import os.path
import pathlib
import sys

import tqdm.contrib.concurrent
import tqdm.contrib.logging

from heuristics.utils import Instance
from utils import combat_dir_iterator, read_gzipped_file, write_jsonl

# hack to add avrae submodule to pypath
# if this errors, pip install -r avrae/requirements.txt
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), "avrae"))

DATA_DIR = pathlib.Path("data/")
IN_DIR = pathlib.Path("extract/experiment1/")
OUT_DIR = pathlib.Path("extract/experiment2/")
RUN_PARALLEL = True
log = logging.getLogger("distill2")
loglevel = logging.WARNING


class Distill2Inst(Instance):
    def __init__(self, events):
        super().__init__(events)
        self.dms = self.extract_dms_from_events()

    # ==== init: extract info ====
    def extract_dms_from_events(self) -> set[str]:
        """Given events, return a set of user IDs who were DMs at any point during the combat."""
        out = set()
        for event in self.find_all(lambda e: e["event_type"] == "combat_state_update"):
            out.add(str(event["data"]["dm"]))
        return out

    def get_caster_id(self, caster: dict):
        if "owner_id" in caster and "character_id" in caster:
            return f"{caster['owner_id']}-{caster['character_id']}"
        if "owner" in caster and "upstream" in caster:
            return f"{caster['owner']}-{caster['upstream']}"
        return caster.get("id")

    def process_triple(self, triple: dict) -> dict | None:
        """Given a triple, return a processed triple - main entrypoint"""
        before = triple["before"]
        commands = triple["commands"]
        after = triple["after"]
        command_author = commands[0]["author_id"]

        # normalize utterances
        author_filter = lambda msg: msg["author_id"] == command_author or msg["author_id"] in self.dms
        before = list(filter(author_filter, before))
        after = list(filter(author_filter, after))

        # discard if we have no filtered utterances
        if not (before or after):
            return None

        # ensure the caster is the same for all commands
        seen_casters = set()
        for e in commands:
            if e["event_type"] != "command":
                continue
            command = e
            if command is None:
                continue
            caster = command["caster"]
            if caster is None:
                continue
            seen_casters.add(self.get_caster_id(command["caster"]))
        if len(seen_casters) != 1:
            log.info(f"triple has {len(seen_casters)} different casters, discarding")
            return None

        # TODO: stringify automation run for GPT-3
        # TODO: stringify caster attributes for GPT-3

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
    inst = Distill2Inst(event_stream)
    out = []

    for triple in triple_stream:
        num_triples_in += 1
        processed = inst.process_triple(triple)
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
