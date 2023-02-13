"""Given a dataset instance, replace all IDs with md5(id) and usernames with "Player #"."""
import hashlib
import os
import pathlib
import re
import sys

import tqdm

sys.path.append("..")
from heuristics.utils import AVRAE_ID, Instance
from dataset import utils

DATA_DIR = pathlib.Path(os.path.dirname(__file__), "../data")
OUT_DIR = pathlib.Path(os.path.dirname(__file__), "../data-anonymized")


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

    def anonymize_recursive(self, obj):
        if isinstance(obj, int):
            if str(obj) in self.id_hash_map:
                return int(self.id_hash_map[str(obj)])
            return obj

        if isinstance(obj, str):
            for name, replacement in self.author_name_map.items():
                obj = obj.replace(name, replacement)
            for uid, repl in self.id_hash_map.items():
                obj = obj.replace(uid, repl)
            return obj

        if isinstance(obj, list):
            for idx, elem in enumerate(obj):
                obj[idx] = self.anonymize_recursive(elem)
            return obj

        if isinstance(obj, dict):
            for k in obj.copy():
                obj[self.anonymize_recursive(k)] = self.anonymize_recursive(obj.pop(k))
            return obj

        return obj

    def anonymize(self):
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


def anonymize_instance(instance_path: pathlib.Path):
    instance_id, *_ = instance_path.stem.split(".")
    event_stream = utils.combat_dir_iterator(instance_path)
    inst = AnonInst(event_stream)
    inst.anonymize()
    # and write all new events to data-anonymized
    (OUT_DIR / instance_id).mkdir(exist_ok=True)
    utils.write_jsonl(OUT_DIR / instance_id / f"{instance_id}.jsonl.gz", inst.events)


if __name__ == "__main__":
    for fp in tqdm.tqdm(utils.get_combat_dirs(DATA_DIR)):
        anonymize_instance(fp)
