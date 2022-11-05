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

from heuristics.utils import Event, Instance, MessageGroup
from dataset.utils import combat_dir_iterator, read_gzipped_file, write_jsonl

# hack to add avrae submodule to pypath
# if this errors, pip install -r avrae/requirements.txt
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), "avrae"))
from avrae.utils.argparser import argsplit
from avrae.cogs5e.models.character import Character
from avrae.cogs5e.initiative import Combat, Combatant, MonsterCombatant, PlayerCombatant
from avrae.cogs5e.initiative.combat import deserialize_combatant_sync
from avrae.gamedata import Monster

DATA_DIR = pathlib.Path("data/")
IN_DIR = pathlib.Path("extract/experiment2/")
OUT_DIR = pathlib.Path("extract/experiment4/")
RUN_PARALLEL = False
log = logging.getLogger("distill4")
loglevel = logging.WARNING


class Distill4Inst(Instance):
    def __init__(self, events):
        super().__init__(events)
        self.monkey_patch()
        self.characters = self.extract_characters()

    def monkey_patch(self):
        def from_dict(cls, raw, ctx, combat):
            inst = super().from_dict_sync(raw, ctx, combat)
            inst.character_id = raw["character_id"]
            inst.character_owner = raw["character_owner"]
            character = self.characters.get((raw["owner_id"], raw["character_id"]))
            if character is None:
                from avrae.cogs5e.models.errors import NoCharacter

                raise NoCharacter
            inst._character = character
            return inst

        PlayerCombatant.from_dict = PlayerCombatant.from_dict_sync = from_dict

    def extract_characters(self) -> dict:
        """Extract all of the characters by (owner, upstream_id) in a map from init joins"""
        characters = {}
        for event in self.find_all(lambda e: e["event_type"] == "command" and e["command_name"] == "init join"):
            caster = event["caster"]
            owner = caster["owner"]
            upstream = caster["upstream"]
            characters[(owner, upstream)] = Character.from_dict(caster)
        return characters

    def normalize_actor(self, actor: dict | Combatant, combat: Combat) -> dict:
        # make everything a Combatant
        if isinstance(actor, Combatant):
            combatant = actor
        elif "type" not in actor:
            # promote character/monster to PlayerCombatant/MonsterCombatant
            if "owner" in actor:
                # player
                character = Character.from_dict(actor)
                combatant = PlayerCombatant.from_character(
                    character, ctx=None, combat=combat, controller_id=0, init=0, private=False
                )
            else:
                # monster
                monster = Monster.from_data(actor)
                combatant = MonsterCombatant.from_monster(
                    monster, ctx=None, combat=combat, name=monster.name, controller_id=0, init=0, private=False
                )
        else:
            combatant = deserialize_combatant_sync(actor, None, combat)

        # extract common things
        name = combatant.name
        effects = ", ".join(e.name for e in combatant.get_effects())
        attacks = ", ".join(a.name for a in combatant.attacks)
        spells = ", ".join(s.name for s in combatant.spellbook.spells if s.prepared)

        race = None
        class_ = None
        description = None
        actions = None
        if isinstance(combatant, PlayerCombatant):
            race = combatant.character.race
            class_ = str(combatant.character.levels)
            description = combatant.character.description
            actions = ", ".join(a.name for a in combatant.character.actions)
        elif isinstance(combatant, MonsterCombatant):
            race = combatant.monster_name

        return {
            "name": name,
            "hp": combatant.hp_str(True),
            "class": class_,  # nullable
            "race": race,  # nullable
            "attacks": attacks,  # can be empty
            "spells": spells,  # can be empty
            "actions": actions,  # nullable, can be empty
            "effects": effects,  # can be empty
            "description": description,  # nullable
        }

    def stringify_actor(self, actor: dict | Combatant, combat: Combat):
        actor_attrs = self.normalize_actor(actor, combat)
        # Name (Race/creature type; class if available) <X/Y HP> [Effects]
        short_parts = [actor_attrs["name"]]
        # Description: ...
        #
        # ---
        # Name: NAME
        # Class:
        # Race:
        # Attacks:
        # Spells:
        # Actions:
        # Effects:
        long_parts = []

        # short parts
        race_and_class_parts = []
        if actor_attrs["race"]:
            race_and_class_parts.append(actor_attrs["race"])
        if actor_attrs["class"]:
            race_and_class_parts.append(actor_attrs["class"])
        race_and_class = "; ".join(race_and_class_parts)

        if race_and_class:
            short_parts.append(f"({race_and_class})")
        short_parts.append(actor_attrs["hp"])
        if actor_attrs["effects"]:
            short_parts.append(actor_attrs["effects"])

        # long parts
        if actor_attrs["description"]:
            long_parts.append(f"Description: {actor_attrs['description']}\n---")
        long_parts.append(f"Name: {actor_attrs['name']}")
        if actor_attrs["class"]:
            long_parts.append(f"Class: {actor_attrs['class']}")
        if actor_attrs["race"]:
            long_parts.append(f"Race: {actor_attrs['race']}")
        if actor_attrs["attacks"]:
            long_parts.append(f"Attacks: {actor_attrs['attacks']}")
        if actor_attrs["spells"]:
            long_parts.append(f"Spells: {actor_attrs['spells']}")
        if actor_attrs["actions"]:
            long_parts.append(f"Actions: {actor_attrs['actions']}")
        if actor_attrs["effects"]:
            long_parts.append(f"Effects: {actor_attrs['effects']}")

        return {"short": " ".join(short_parts), "long": "\n".join(long_parts)}

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

        # state before
        combat_before = Combat.from_dict_sync(self.combat_state_at_event(commands[0]), None)
        actor_list_before = [
            self.stringify_actor(actor, combat_before) for actor in combat_before.get_combatants(groups=False)
        ]

        # caster
        for e in self.find_all_of_type("command"):
            caster = e["caster"]
            if caster is not None:
                break  # guaranteed to break because of distill2
        caster_str = self.stringify_actor(caster, combat_before)

        # targets
        target_strs = []
        for e in self.find_all_of_type("command"):
            for target in e["targets"]:
                actor_str = self.stringify_actor(target, combat_before)
                if actor_str not in target_strs:
                    target_strs.append(actor_str)

        # TODO: stringify automation run for GPT-3

        # state after
        last_combat_update = self.find_all_of_type("combat_state_update")[-1]["data"]
        combat_after = Combat.from_dict_sync(last_combat_update, None)
        actor_list_after = [
            self.stringify_actor(actor, combat_after) for actor in combat_after.get_combatants(groups=False)
        ]

        return {
            "before_utterances": before_utterances,
            "combat_state_before": actor_list_before,  # list of actors
            "caster": caster_str,  # actor
            "targets": target_strs,  # list of actors
            "commands_norm": commands_norm,
            "automation_results": None,  # list of str
            "combat_state_after": actor_list_after,  # list of actors
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
