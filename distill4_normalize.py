"""
Distill4: Given time-grouped IC/OOC filtered triples, normalize the utterances and the commands:
- resolve aliases
- resolve snippets
- normalize the prefix

Input: {"before": [Message...], "commands": [Event...], "after": [Message...]}

Output: {
    "before": [Message...],
    "before_utterances": [str...],
    "commands": [Event...],
    "commands_norm": [str...],
    "after": [Message...],
    "after_utterances": [str...],
}
"""
import glob
import logging
import os.path
import pathlib
import sys

import tqdm.contrib.concurrent
import tqdm.contrib.logging

from heuristics.utils import Instance, MessageGroup
from utils import combat_dir_iterator, read_gzipped_file, write_jsonl

# hack to add avrae submodule to pypath
# if this errors, pip install -r avrae/requirements.txt
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), "avrae"))
from avrae.utils.argparser import argsplit

DATA_DIR = pathlib.Path("data/")
IN_DIR = pathlib.Path("extract/experiment3/")
OUT_DIR = pathlib.Path("extract/experiment4/")
RUN_PARALLEL = True
log = logging.getLogger("distill4")
loglevel = logging.WARNING


class Distill4Inst(Instance):
    def __init__(self, events):
        super().__init__(events)
        self.characters = self.extract_characters()

    # ==== unused code but I need somewhere to put it ====
    def extract_characters(self) -> dict:
        """Extract all of the characters by (owner, upstream_id) in a map from init joins"""
        characters = {}
        for event in self.find_all(lambda e: e["event_type"] == "command" and e["command_name"] == "init join"):
            caster = event["caster"]
            owner = caster["owner"]
            upstream = caster["upstream"]
            characters[(owner, upstream)] = caster
        return characters

    def hydrate_combatant(self, combatant: dict) -> dict:
        """Hydrates a sparse PlayerCombatant with attributes from the character."""
        if combatant.get("type") != "player":
            return combatant
        character = self.characters.get((combatant["owner_id"], combatant["character_id"]))
        if character is None:
            log.warning("Could not find character")
            return combatant
        # combatant.py#L728
        hydrate_character_attributes = (
            "stats",
            "levels",
            "skills",
            "saves",
            "spellbook",
            "hp",
            "temp_hp",
            "actions",
            "description",
            "race",
        )
        return {
            **combatant,
            **{k: character[k] for k in hydrate_character_attributes},
        }

    # ==== normalizers =====
    def normalize_command_group(self, group: MessageGroup) -> str | None:
        command = group.find_event_of_type("command")
        if command is None:
            return None
        # use post-alias content
        content: str = command["content"]

        # normalize prefix
        content = content.replace(command["prefix"], "!", 1)

        # normalize snippets
        snippet_resolutions = group.find_all_of_type("snippet_resolution")
        if snippet_resolutions:
            try:
                content_words = argsplit(content)
            except:
                content_words = content.split()
            for snippet_resolution in snippet_resolutions:
                for idx, word in enumerate(content_words):
                    if word == snippet_resolution["snippet_name"]:
                        content_words[idx] = snippet_resolution["content_after"]
                        break
            content = " ".join(content_words)

        # TODO: we can probably rebuild cast/attack invocations by importing avrae
        # lets us reference exact action/attack/spell names
        return content

    def process_triple(self, triple: dict) -> dict | None:
        """Given a triple, return a processed triple - main entrypoint"""
        before = triple["before"]
        commands = triple["commands"]
        after = triple["after"]

        # normalize utterances
        before_utterances = [msg["content"] for msg in before]
        after_utterances = [msg["content"] for msg in after]

        # normalize commands
        commands_grouped = Instance(commands).message_groups
        assert sum(len(g) for g in commands_grouped) == len(commands)
        commands_norm = []
        for g in commands_grouped:
            norm = self.normalize_command_group(g)
            if norm:
                commands_norm.append(norm)

        # TODO: stringify automation run for GPT-3
        # TODO: stringify caster attributes for GPT-3

        return {
            "before": before,
            "before_utterances": before_utterances,
            "commands": commands,
            "commands_norm": commands_norm,
            "after": after,
            "after_utterances": after_utterances,
        }


def process_file(fp: pathlib.Path):
    triple_stream = read_gzipped_file(fp)
    num_triples_in = 0
    combat_id, *_ = fp.stem.split(".")
    event_stream = combat_dir_iterator(DATA_DIR / combat_id)
    inst = Distill4Inst(event_stream)
    out = []

    for triple in triple_stream:
        num_triples_in += 1
        processed = inst.process_triple(triple)
        out.append(processed)

    # see what we get
    write_jsonl(OUT_DIR / f"{combat_id}.jsonl", out)
    return num_triples_in, len(out)


if __name__ == "__main__":
    logging.basicConfig(level=loglevel, format="%(levelname)s: %(message)s")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    filenames = sorted(glob.glob("*.gz", root_dir=IN_DIR))
    files = [pathlib.Path(IN_DIR, fn) for fn in filenames]
    with tqdm.contrib.logging.logging_redirect_tqdm():
        if RUN_PARALLEL:
            tqdm.contrib.concurrent.process_map(process_file, files, chunksize=10)
        else:
            for d in tqdm.tqdm(files):
                process_file(d)

    print(f"Normalization complete!")
