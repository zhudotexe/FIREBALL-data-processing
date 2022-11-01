import collections
import itertools
import logging
import pathlib

import tqdm.contrib.concurrent
import tqdm.contrib.logging

from dev_constants import DEV_DIRS
from heuristics.utils import Event, Instance, MessageGroup, is_bot_message
from utils import combat_dir_iterator, get_combat_dirs, write_jsonl

DATA_DIR = pathlib.Path("data/")
OUT_DIR = pathlib.Path("extract/experiment1/")
RUN_PARALLEL = True
USE_DEV_DIRS = False
log = logging.getLogger("distill1")


def fix_missing_casters(inst: Instance):
    """
    Fills the `caster` key for `!i a` and `!i cast` command events before Nov 1, 2022
    ignore `!i rc` and `!i aoo` commands, and `!i a`/`!i cast` if current combatant is a group
    otherwise assume the caster is the current combatant
    https://github.com/avrae/avrae/pull/1873
    """
    needs_fixing = inst.find_all(
        lambda e: e["event_type"] == "command"
        and e["caster"] is None
        and e["command_name"] in {"init attack", "init cast"}
    )
    i = 0
    j = 0
    for event in needs_fixing:
        j += 1
        state = inst.combat_state_at_event(event)
        if state is None:
            continue
        if state["current"] is None:
            continue
        current_combatant = state["combatants"][state["current"]]
        if current_combatant["type"] == "group":
            continue
        i += 1
        event["caster"] = current_combatant

    # if needs_fixing:
    #     log.info(f"Fixed {i}/{j} events")


def group_utterances(combat_dir: pathlib.Path):
    """Assign each message to the nearest automation run, chronologically."""
    inst = Instance(combat_dir_iterator(combat_dir))
    triples = collections.defaultdict(lambda: ([], []))  # run -> (before, after)

    if not inst.message_groups:
        return

    # Nov 1 bug
    fix_missing_casters(inst)

    # group consecutive message groups
    message_group_lookups = {}
    grouped_message_groups = itertools.groupby(
        inst.message_groups, key=lambda mgrp: (mgrp.is_only_message(), mgrp.message["author_id"])
    )
    for (is_only_message, author_id), gs in grouped_message_groups:
        gs = list(gs)
        if not is_only_message and len(gs) > 1:
            new_g = MessageGroup.concat(gs)
            for g in gs:
                message_group_lookups[g] = new_g

    # do the tagging
    automation_runs: list[MessageGroup] = [g for g in inst.message_groups if g.has_event_of_type("automation_run")]
    all_utterances: list[Event] = [g.message for g in inst.message_groups if g.is_only_message()]

    def nearest_automation_run(event):
        nearest_sorted = sorted(automation_runs, key=lambda grp: abs(grp.message["timestamp"] - event["timestamp"]))
        if nearest_sorted:
            return nearest_sorted[0]
        return None

    for message in all_utterances:
        # FILTERS
        # ignore short messages
        if len(message["content"].split()) < 5:
            continue
        # ignore bot messages
        if is_bot_message(message):
            continue

        # GROUP
        nearest_group = nearest_automation_run(message)
        if nearest_group is None:
            continue
        tagged_group = message_group_lookups.get(nearest_group, nearest_group)
        if message["timestamp"] < nearest_group.message["timestamp"]:
            triples[tagged_group][0].append(message)
        else:
            triples[tagged_group][1].append(message)

    out = [
        {"before": before, "commands": commands.events, "after": after} for commands, (before, after) in triples.items()
    ]

    # discard if we have nothing
    if not out:
        return False

    # see what we get
    write_jsonl(OUT_DIR / f"{combat_dir.stem}.jsonl.gz", out)
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dirs_to_distill = get_combat_dirs(DATA_DIR) if not USE_DEV_DIRS else DEV_DIRS
    with tqdm.contrib.logging.logging_redirect_tqdm():
        if RUN_PARALLEL:
            results = tqdm.contrib.concurrent.process_map(group_utterances, dirs_to_distill, chunksize=10)
        else:
            results = []
            for d in tqdm.tqdm(dirs_to_distill):
                results.append(group_utterances(d))

    kept_distill_count = sum(1 for b in results if b)
    print(
        f"Distill finished! {len(dirs_to_distill)} ->"
        f" {kept_distill_count} ({len(dirs_to_distill) - kept_distill_count} discarded)"
    )
