import collections
import gzip
import json
import logging
import pathlib

import tqdm.contrib.concurrent
import tqdm.contrib.logging

import heuristics.utils
import utils

DATA_DIR = pathlib.Path("data/")
OUT_DIR = pathlib.Path("extract/rp/")
RUN_PARALLEL = True


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
    previous_combat_state = None
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

    # partition by round: start of player's turn to before next start of player's turn
    for event in events:
        # if the turn changed, start utterance recording whomever's turn it is
        if event["event_type"] == "combat_state_update":
            turn_changed = heuristics.utils.did_turn_change(previous_combat_state, event["data"])
            previous_combat_state = event["data"]

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

        # collect all player's utterances before the first command
        if event["event_type"] == "command":
            entry = buffer[int(event["author_id"])]
            if entry.collecting_utterances:
                entry.collecting_utterances = False
                entry.collecting_commands = True
            entry.collect_command(event)

        # collect all the commands until the next player utterance (or start of their next turn)
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
    with gzip.open(OUT_DIR / f"{combat_dir.stem}.jsonl.gz", "wt") as f:
        for line in out:
            f.write(json.dumps(line) + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tqdm.contrib.logging.logging_redirect_tqdm():
        if RUN_PARALLEL:
            tqdm.contrib.concurrent.process_map(extract_rp, utils.get_combat_dirs(DATA_DIR), chunksize=10)
        else:
            for d in tqdm.tqdm(utils.get_combat_dirs(DATA_DIR)):
                extract_rp(d)
