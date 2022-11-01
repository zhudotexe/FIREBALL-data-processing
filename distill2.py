"""
Distill2: Given time-grouped triples, normalize the utterances:
- filter IC/OOC utterances (TODO)
- remove utterances from irrelevant users
and normalize the commands:
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
- with `before` and `after` filtered to only include utterances from the user who ran `commands` or a DM
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
IN_DIR = pathlib.Path("extract/experiment1/")
OUT_DIR = pathlib.Path("extract/experiment2/")
RUN_PARALLEL = False
log = logging.getLogger("distill2")


class Distill2Inst(Instance):
    def __init__(self, events):
        super().__init__(events)
        self.dms = self.extract_dms_from_events()
        self.characters = self.extract_characters()

    # ==== init: extract info ====
    def extract_dms_from_events(self) -> set[str]:
        """Given events, return a set of user IDs who were DMs at any point during the combat."""
        out = set()
        for event in self.find_all(lambda e: e["event_type"] == "combat_state_update"):
            out.add(str(event["data"]["dm"]))
        return out

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

    def get_caster_id(self, caster: dict):
        if "owner_id" in caster and "character_id" in caster:
            return f"{caster['owner_id']}-{caster['character_id']}"
        if "owner" in caster and "upstream" in caster:
            return f"{caster['owner']}-{caster['upstream']}"
        return caster.get("id")

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
        command_author = commands[0]["author_id"]

        # normalize utterances
        author_filter = lambda msg: msg["author_id"] == command_author or msg["author_id"] in self.dms
        before = list(filter(author_filter, before))
        before_utterances = [msg["content"] for msg in before]
        after = list(filter(author_filter, after))
        after_utterances = [msg["content"] for msg in after]

        # discard if we have no filtered utterances
        if not (before or after):
            return None

        # normalize commands
        commands_grouped = Instance(commands).message_groups
        assert sum(len(g) for g in commands_grouped) == len(commands)
        commands_norm = []
        for g in commands_grouped:
            norm = self.normalize_command_group(g)
            if norm:
                commands_norm.append(norm)

        # ensure the caster is the same for all commands and present
        seen_casters = set()
        for g in commands_grouped:
            command = g.find_event_of_type("command")
            if command is None:
                continue
            seen_casters.add(self.get_caster_id(command["caster"]))
        if len(seen_casters) != 1:
            log.warning(f"triple has {len(seen_casters)} different casters, discarding")
            return None

        # TODO: stringify automation run for GPT-3
        # TODO: stringify caster attributes for GPT-3

        return {
            # "before": before,
            "before_utterances": before_utterances,
            # "commands": commands,
            "commands_norm": commands_norm,
            # "after": after,
            "after_utterances": after_utterances,
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
    write_jsonl(OUT_DIR / f"{combat_id}.jsonl", out)
    return num_triples_in, len(out)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
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
