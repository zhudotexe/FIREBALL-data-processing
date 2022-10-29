"""
For each combat instance in the supplied input data dir, extract event subsets of the form
(rp utterances, commands + state changes) such that the extracted utterances are the most likely ones
to have motivated the subsequent commands, which in turn caused the recorded state changes.
"""

import collections
import logging
import pathlib

import tqdm.contrib.concurrent
import tqdm.contrib.logging

import heuristics.utils
import utils
from dev_constants import DEV_DIRS

DATA_DIR = pathlib.Path("data/")
OUT_DIR = pathlib.Path("extract/rp/")
RUN_PARALLEL = True
USE_DEV_DIRS = True


class UserExtraction:
    def __init__(self):
        self.collecting_utterances = False
        self.collecting_commands = False
        self.utterances = []
        self.commands = []

    def is_dirty(self):
        return self.utterances or self.commands

    def collect_utterance(self, utterance):
        if not self.collecting_utterances:
            return
        self.utterances.append(utterance)

    def collect_command(self, command):
        if not self.collecting_commands:
            return
        self.commands.append(command)

    def to_dict(self):
        return {"utterances": self.utterances, "commands": self.commands}


def extract_rp(combat_dir: pathlib.Path):
    previous_combat_state_update = {"data": None}
    out = []

    # user -> current buffer
    buffer = collections.defaultdict(lambda: UserExtraction())

    def flush(user_id: int):
        if user_id in buffer and buffer[user_id].is_dirty():
            out.append(buffer.pop(user_id).to_dict())

    # load all events into memory because we need to lookbehind
    # *mario long jump sound*
    events = list(utils.combat_dir_iterator(combat_dir))
    message_ids_that_are_commands = set(event["message_id"] for event in events if event["event_type"] == "command")
    messages_by_id = {event["message_id"]: event for event in events if event["event_type"] == "message"}

    # partition by round: start of player's turn to before next start of player's turn
    for event in events:
        # if the event is a 1-word utterance, skip it
        if event["event_type"] == "message" and len(event["content"].split()) < 2:
            continue

        # if the turn changed, start utterance recording whomever's turn it is
        if event["event_type"] == "combat_state_update":
            turn_changed = heuristics.utils.did_turn_change(previous_combat_state_update["data"], event["data"])
            previous_combat_state_update = event

            # mark all of the combatants on current turn's controllers to record utterances
            if turn_changed and event["data"]["current"] is not None:
                # this is gross, groups are weird
                current_combatant = event["data"]["combatants"][event["data"]["current"]]
                if current_combatant["type"] == "group":
                    for combatant in current_combatant["combatants"]:
                        whose_turn_is_it = combatant["controller_id"]
                        flush(whose_turn_is_it)
                        buffer[whose_turn_is_it].collecting_utterances = True
                else:
                    whose_turn_is_it = current_combatant["controller_id"]
                    flush(whose_turn_is_it)
                    buffer[whose_turn_is_it].collecting_utterances = True

        # collect all the commands until the next player utterance (or start of their next turn)
        if event["event_type"] in ("command", "automation_run", "combat_state_update"):
            # if the event was triggered by a message, find the message
            if event["event_type"] == "command":
                author_id = int(event["author_id"])
            elif event["event_type"] == "automation_run":
                triggering_message = messages_by_id.get(event["interaction_id"])
                if triggering_message is None:
                    continue
                author_id = int(triggering_message["author_id"])
            else:
                triggering_message = messages_by_id.get(event.get("probable_interaction_id"))
                if triggering_message is None:
                    continue
                author_id = int(triggering_message["author_id"])

            # and record the event for the triggering message's author
            entry = buffer[author_id]
            if entry.collecting_utterances:
                entry.collecting_utterances = False
                entry.collecting_commands = True
            entry.collect_command(previous_combat_state_update)
            entry.collect_command(event)

        # collect all player's utterances before the first command
        if event["event_type"] == "message" and event["message_id"] not in message_ids_that_are_commands:
            entry = buffer[int(event["author_id"])]
            entry.collecting_commands = False
            entry.collect_utterance(event)

    # discard any without prior utterances
    for event in reversed(out):
        if not (len(event["utterances"]) and len(event["commands"])):
            out.remove(event)
    # discard any without an !a|cast|i a|i cast|i aoo|i rc command
    # discard if we have no data at all
    if not out:
        return

    # see what we get
    utils.write_jsonl(OUT_DIR / f"{combat_dir.stem}.jsonl.gz", out)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dirs_to_distill = utils.get_combat_dirs(DATA_DIR) if not USE_DEV_DIRS else DEV_DIRS
    with tqdm.contrib.logging.logging_redirect_tqdm():
        if RUN_PARALLEL:
            tqdm.contrib.concurrent.process_map(extract_rp, dirs_to_distill, chunksize=10)
        else:
            for d in tqdm.tqdm(dirs_to_distill):
                extract_rp(d)
