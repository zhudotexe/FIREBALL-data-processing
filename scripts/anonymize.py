"""Given a dataset instance, replace all IDs with md5(id) and usernames with "Player #"."""
import hashlib
import logging
import os
import pathlib
import re
import sys

import tqdm.contrib.concurrent
import tqdm.contrib.logging

sys.path.append("..")
from heuristics.utils import AVRAE_ID, Instance
from dataset import utils

DATA_DIR = pathlib.Path(os.path.dirname(__file__), "../data")
EXP4_DIR = pathlib.Path(os.path.dirname(__file__), "../extract/experiment4")
OUT_DIR = pathlib.Path(os.path.dirname(__file__), "../anonymized")

RUN_PARALLEL = True
log = logging.getLogger("anonymize")


def hash_id(user_id: int | str) -> str:
    """Deterministic 1-way method of transforming Discord snowflakes into other numbers"""
    user_id = str(user_id).encode()
    md5 = hashlib.md5(user_id)
    # return a number of length 18 to be compatible with naive discord regexes
    return "{0:0>18}".format(str(int.from_bytes(md5.digest(), "little", signed=False))[:18])


class AnonInst(Instance):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.author_name_map = {}
        self.id_hash_map = {}

    def anonymize_recursive(self, obj, replace_author_name=False):
        if isinstance(obj, int):
            if str(obj) in self.id_hash_map:
                return int(self.id_hash_map[str(obj)])
            return obj

        if isinstance(obj, str):
            if replace_author_name:
                for name, replacement in self.author_name_map.items():
                    obj = obj.replace(name, replacement)
            for uid, repl in self.id_hash_map.items():
                obj = obj.replace(uid, repl)
            return obj

        if isinstance(obj, list):
            for idx, elem in enumerate(obj):
                obj[idx] = self.anonymize_recursive(elem, replace_author_name)
            return obj

        if isinstance(obj, dict):
            for k in obj.copy():
                new_k = self.anonymize_recursive(k, replace_author_name)
                v = obj.pop(k)
                # weird case for author names to prevent them changing message contents
                obj[new_k] = self.anonymize_recursive(
                    v, replace_author_name or new_k in ("author_name", "author", "utterance_history")
                )
            return obj

        return obj

    def collect_info(self):
        """Removes mentions, emoji, etc; anonymize author names"""
        # collect all the names and IDs
        for msg in self.events:
            if msg["event_type"] != "message":
                continue
            content = msg["content"]

            # remove role, channel mentions
            content = re.sub(r"<@&\d{17,20}>", "<@&role>", content)
            content = re.sub(r"<#\d{17,20}>", "<#channel>", content)

            # replace user mentions with hash
            content = re.sub(r"<@!?(\d{17,20})>", lambda m: f"<@{hash_id(m[1])}>", content)

            # replace custom emoji with just their name
            content = re.sub(r"<a?(:\w+?:)\d{17,20}>", r"\1", content)

            msg["content"] = content

            # anonymize author nick, unless it's Avrae
            author_id = msg["author_id"]
            author_name = msg["author_name"]
            if author_id == AVRAE_ID:
                self.author_name_map[author_name] = f"Avrae"
                author_name = "Avrae"
            elif author_name in self.author_name_map:
                author_name = self.author_name_map[author_name]
            else:
                self.id_hash_map[author_id] = hash_id(author_id)
                self.author_name_map[author_name] = f"Player {len(self.author_name_map)}"
                author_name = self.author_name_map[author_name]
            msg["author_name"] = author_name

        # then go over and replace all the names and IDs we found
        for event in self.events:
            self.anonymize_recursive(event)

    def anonymize_event_stream(self, events):
        for event in events:
            yield self.anonymize_recursive(event)


def anonymize_instance(instance_path: pathlib.Path):
    # collect info from the main instance
    instance_id, *_ = instance_path.stem.split(".")
    event_stream = utils.combat_dir_iterator(instance_path)
    inst = AnonInst(event_stream)
    inst.collect_info()

    # and write all new events to data-anonymized
    (OUT_DIR / "data").mkdir(exist_ok=True)
    (OUT_DIR / "filtered").mkdir(exist_ok=True)
    utils.write_jsonl(OUT_DIR / "data" / f"{instance_id}.jsonl.gz", inst.events)

    # then anonymize all the experiment4 events
    exp4_data = EXP4_DIR / f"{instance_id}.jsonl"
    if not exp4_data.exists():
        log.info(f"{instance_id} was filtered out, no exp4 data")
        return
    filtered_events = utils.read_jsonl_file(exp4_data)
    utils.write_jsonl(OUT_DIR / "filtered" / f"{instance_id}.jsonl.gz", inst.anonymize_event_stream(filtered_events))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    dirs = sorted(utils.get_combat_dirs(DATA_DIR))
    with tqdm.contrib.logging.logging_redirect_tqdm():
        if RUN_PARALLEL:
            tqdm.contrib.concurrent.process_map(anonymize_instance, dirs, chunksize=10)
        else:
            for d in tqdm.tqdm(dirs):
                anonymize_instance(d)
