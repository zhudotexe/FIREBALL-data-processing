"""
Distill4: Given time-grouped IC/OOC filtered triples, normalize the utterances and the commands:
- resolve aliases
- resolve snippets
- normalize the prefix

Input: {"before": [Message...], "commands": [Event...], "after": [Message...]}

Output: {
    "before_utterances": before_utterances,     # list of str
    "combat_state_before": actor_list_before,   # list of actors
    "current_actor": current_actor,             # actor, nullable
    "commands_norm": commands_norm,             # list of str
    "automation_results": automation_norm,      # list of str
    "caster_after": caster_norm,                # actor
    "targets_after": targets,                   # list of actors
    "combat_state_after": actor_list_after,     # list of actors
    "after_utterances": after_utterances,       # list of str
    "before_idxs": [],                          # list of int (indexes of events in instance)
    "command_idxs": [],                         # list of int (indexes of events in instance)
    "after_idxs": [],                           # list of int (indexes of events in instance)
}
"""
import copy
import glob
import logging
import os.path
import pathlib
import re
import sys

import tqdm.contrib.concurrent
import tqdm.contrib.logging

from dataset.utils import combat_dir_iterator, read_gzipped_file, write_jsonl
from heuristics.utils import Event, Instance, MessageGroup

# hack to add avrae submodule to pypath
# if this errors, pip install -r avrae/requirements.txt
sys.path.append(os.path.join(os.path.abspath(os.path.dirname(__file__)), "avrae"))
from avrae.utils.argparser import argsplit
from avrae.cogs5e.models.character import Character
from avrae.cogs5e.initiative import Combat, Combatant, CombatantGroup, MonsterCombatant, PlayerCombatant
from avrae.cogs5e.initiative.combat import deserialize_combatant_sync
from gamedata import Monster  # this import is wonky because of namespace weirdness

DATA_DIR = pathlib.Path("data/")
IN_DIR = pathlib.Path("extract/experiment3/")
OUT_DIR = pathlib.Path("extract/experiment4/")
RUN_PARALLEL = True
log = logging.getLogger("distill4")
loglevel = logging.INFO


# object to make interacting with avrae work
class FakeContext:
    def __getattr__(self, _):
        return self

    def __int__(self):
        return 0


ctx = FakeContext()


class Distill4Inst(Instance):
    def __init__(self, events):
        super().__init__(events)
        self.monkey_patch()
        self.characters = {}

    def monkey_patch(self):
        @classmethod
        def from_dict(cls, raw, ctx, combat):
            inst = super(PlayerCombatant, cls).from_dict(raw, ctx, combat)
            inst.character_id = raw["character_id"]
            inst.character_owner = raw["character_owner"]
            character = self.characters.get((raw["character_owner"], raw["character_id"]))
            if character is None:
                from cogs5e.models.errors import NoCharacter

                raise NoCharacter
            inst._character = character
            return inst

        PlayerCombatant.from_dict = PlayerCombatant.from_dict_sync = from_dict

    def _extract_character_from_event(self, event):
        if event["event_type"] not in ("command", "automation_run"):
            return
        caster = event["caster"]
        if caster is None or "upstream" not in caster:
            return
        owner = caster["owner"]
        upstream = caster["upstream"]
        self.characters[(owner, upstream)] = Character.from_dict(copy.deepcopy(caster))

    def extract_characters_forward(self, until):
        """Extract all of the characters by (owner, upstream_id) in all events from the start until *until*"""
        idx = self.events.index(until)
        for event in self.events[:idx]:
            self._extract_character_from_event(event)

    def extract_characters_backward(self, until):
        """Extract all of the characters by (owner, upstream_id) in all events from the end until *until*"""
        idx = self.events.index(until)
        for event in self.events[:idx:-1]:
            self._extract_character_from_event(event)

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
                    character, ctx=ctx, combat=combat, controller_id=0, init=0, private=False
                )
            else:
                # monster
                monster = Monster.from_bestiary(actor, "Unknown Source")
                combatant = MonsterCombatant.from_monster(
                    monster, ctx=ctx, combat=combat, name=monster.name, controller_id=0, init=0, private=False
                )
        else:
            combatant = deserialize_combatant_sync(actor, ctx, combat)

        # extract common things
        name = combatant.name
        effects = ", ".join(e.name for e in combatant.get_effects())
        attacks = ", ".join(a.name for a in combatant.attacks)
        spells = ", ".join(set(s.name for s in combatant.spellbook.spells if s.prepared))

        race = None
        class_ = None
        description = None
        actions = None
        if isinstance(combatant, PlayerCombatant):
            race = combatant.character.race
            class_ = str(combatant.character.levels)
            description = combatant.character.description
            actions = ", ".join(set(a.name for a in combatant.character.actions))
        elif isinstance(combatant, MonsterCombatant):
            race = combatant.monster_name
        elif isinstance(combatant, CombatantGroup):
            race = "Group"

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
            "controller_id": str(combatant.controller_id),  # TODO make this not use discord ID
        }

    def stringify_automation_run(self, event):
        caster = event["caster"]["name"]
        targets = [(t["name"] if not isinstance(t, str) else t) for t in event["targets"]]

        current_target = None

        def stringify_many(nodes):
            out = []
            for child in nodes:
                if result := stringify(child):
                    out.append(result)
            return "\n".join(out)

        def stringify(result_node):
            nonlocal current_target
            match result_node:
                case {"type": "root" | "condition" | "spell"}:
                    return stringify_many(result_node["children"])
                case {"type": "target"}:
                    return stringify_many(result_node["results"])
                case {"type": "target_iteration", "target_type": "self"}:
                    previous_target = current_target
                    current_target = caster
                    result = stringify_many(result_node["results"])
                    current_target = previous_target
                    return result
                case {"type": "target_iteration", "target_index": int()}:
                    previous_target = current_target
                    current_target = targets[result_node["target_index"]]
                    result = stringify_many(result_node["results"])
                    current_target = previous_target
                    return result
                case {"type": "attack", "did_hit": hit, "did_crit": crit}:
                    children = stringify_many(result_node["children"])
                    base = f"{caster} attacked {current_target} "
                    if crit:
                        base += "and crit!"
                    elif hit:
                        base += "and hit."
                    else:
                        base += "but missed."
                    return f"{base}\n{children}"
                case {"type": "save", "ability": ability, "did_save": success}:
                    children = stringify_many(result_node["children"])
                    base = f"{current_target} rolled a {ability[:-4].title()} save " + (
                        "and succeeded." if success else "but failed."
                    )
                    return f"{base}\n{children}"
                case {"type": "damage", "damage": amount}:
                    if amount < 0:
                        return f"{current_target} healed for {amount} health."
                    return f"{current_target} took {amount} damage."
                case {"type": "temphp", "amount": amount}:
                    return f"{current_target} gained {amount} temp HP."
                case {"type": "ieffect", "effect": effect}:
                    return f"{current_target} gained {effect['name']}."
                case {"type": "remove_ieffect", "removed_effect": effect}:
                    return f"{current_target} is no longer {effect['name']}."
                case {"type": "check", "skill_name": skill_name, "did_succeed": success, "contest_skill_name": None}:
                    children = stringify_many(result_node["children"])
                    base = f"{current_target} rolled a {skill_name} check " + (
                        "and succeeded." if success else "but failed."
                    )
                    return f"{base}\n{children}"
                case {
                    "type": "check",
                    "skill_name": skill_name,
                    "did_succeed": success,
                    "contest_skill_name": contest_skill,
                }:
                    children = stringify_many(result_node["children"])
                    base = f"{current_target} rolled a {skill_name} contest against {caster}'s {contest_skill} " + (
                        "and succeeded." if success else "but failed."
                    )
                    return f"{base}\n{children}"

        return stringify(event["automation_result"])

    # ==== normalizers =====
    def normalize_message(self, msg: Event) -> str:
        content = msg["content"]
        msg_idx = self.events.index(msg)
        # remove any Tupper markers
        similar_message = self.find(
            lambda e: e["event_type"] == "message"
            and e["author_id"] != msg["author_id"]
            and e["content"] in content
            and e["content"]
            and e.get("author_bot", True),
            after=msg_idx,
            before=msg_idx + 16,
        )
        if similar_message is not None:
            similar_content = similar_message["content"]
            # the new content must be at least 80% of the old
            len_ratio = len(similar_content) / len(content)
            if 0.7 < len_ratio < 1:
                log.info(f"GREEDY: Replaced message content:\n{content!r}\n---\n{similar_content!r}\n")
                content = similar_content
            else:
                log.info(
                    f"GREEDY: Found similar message but ratio is weird ({len_ratio * 100:.2f}):\n{content!r}\n"
                    f"---\n{similar_content!r}\n"
                )

        # remove user, role, channel mentions
        content = re.sub(r"<(@[!&]?|#)\d{17,20}>", "", content)

        # replace custom emoji with just their name
        content = re.sub(r"<a?(:\w+?:)\d{17,20}>", r"\1", content)
        return content

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
        speaker_id = str(commands[0]["author_id"])  # TODO make this not use discord ID
        before_utterances = [self.normalize_message(msg) for msg in before]
        after_utterances = [self.normalize_message(msg) for msg in after]

        # normalize commands
        commands_inst = Instance(commands)
        commands_grouped = commands_inst.message_groups
        assert sum(len(g) for g in commands_grouped) == len(commands)
        commands_norm = []
        for g in commands_grouped:
            norm = self.normalize_command_group(g)
            if norm:
                commands_norm.append(norm)

        # state before
        self.extract_characters_forward(commands[0])
        combat_state_before = self.combat_state_at_event(commands[0])
        before_state_index = self.events.index(combat_state_before)
        combat_before = Combat.from_dict_sync(copy.deepcopy(combat_state_before["data"]), ctx)
        actor_list_before = [
            self.normalize_actor(actor, combat_before) for actor in combat_before.get_combatants(groups=False)
        ]

        # current turn
        current = combat_before.current_combatant
        current_actor = self.normalize_actor(current, combat_before) if current is not None else None

        # caster
        for e in commands_inst.find_all_of_type("automation_run"):
            caster = e["caster"]
            if caster is not None:
                break  # guaranteed to break because of distill2
        caster_norm = self.normalize_actor(copy.deepcopy(caster), combat_before)

        # targets
        targets = []
        for e in commands_inst.find_all_of_type("automation_run"):
            for target in e["targets"]:
                if isinstance(target, str):
                    log.info("Skipping string target")
                    return
                actor_str = self.normalize_actor(copy.deepcopy(target), combat_before)
                if actor_str not in targets:
                    targets.append(actor_str)

        # stringify automation run
        automation_norm = []
        for e in commands_inst.find_all_of_type("automation_run"):
            automation_norm.append(self.stringify_automation_run(e))

        # state after
        self.extract_characters_backward(commands[-1])
        update_in_commands = commands_inst.find_all_of_type("combat_state_update")
        if not update_in_commands:
            last_combat_update = self.combat_state_after_event(commands[-1])
            if last_combat_update is None:
                log.info("Could not find final combat state update")
                return
        else:
            last_combat_update = update_in_commands[-1]
        after_state_idx = self.events.index(last_combat_update)
        combat_after = Combat.from_dict_sync(copy.deepcopy(last_combat_update["data"]), ctx)
        actor_list_after = [
            self.normalize_actor(actor, combat_after) for actor in combat_after.get_combatants(groups=False)
        ]

        return {
            "speaker_id": speaker_id,
            "before_utterances": before_utterances,
            "combat_state_before": actor_list_before,  # list of actors
            "current_actor": current_actor,  # actor, nullable
            "commands_norm": commands_norm,
            "automation_results": automation_norm,  # list of str
            "caster_after": caster_norm,  # actor
            "targets_after": targets,  # list of actors
            "combat_state_after": actor_list_after,  # list of actors
            "after_utterances": after_utterances,
            # triple
            "before_idxs": [self.events.index(b) for b in before],
            "before_state_idx": before_state_index,
            "command_idxs": [self.events.index(b) for b in commands],
            "after_state_idx": after_state_idx,
            "after_idxs": [self.events.index(b) for b in after],
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
        try:
            processed = inst.process_triple(triple)
            if processed:
                out.append(processed)
        except Exception:
            log.exception(f"something went wrong processing {fp}")

    if not out:
        return num_triples_in, 0

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
            results = tqdm.contrib.concurrent.process_map(process_file, files, chunksize=10)
        else:
            results = []
            for d in tqdm.tqdm(files):
                results.append(process_file(d))

    kept_distill_count = sum(1 for (i, o) in results if o)
    n_triples_in = sum(i for i, o in results)
    n_triples_out = sum(o for i, o in results)
    print(
        f"Normalization complete!\n"
        f"Instances: {len(filenames)} -> {kept_distill_count}\n"
        f"Triples: {n_triples_in} -> {n_triples_out}"
    )
