"""
For each combat instance in the supplied input data dir, extract event subsets of the form
(command, automation_run, combat_state_update, rp utterances) such that the extracted utterances are the most likely
ones to be narrations of the recorded state changes
"""

import gzip
import json
import logging
import pathlib

import tqdm.contrib.concurrent
import tqdm.contrib.logging

import heuristics.utils
import utils

DATA_DIR = pathlib.Path("data/")
OUT_DIR = pathlib.Path("extract/narration/")
RUN_PARALLEL = True


class State:
    def __init__(self, message_groups):
        self.message_groups = message_groups
        self.last_seen_combat_state = None
        self.author_in_question = None
        self.current_combat_dm = None

        self.search_state = 1
        self.state_buffer = []
        self.utterance_buffer = []
        self.out = []

    # ==== helpers ====
    # def record automation:
    #   find group by automation id
    #   if group does not have (automation_run, combat_state_update, command) return False
    #   otherwise record the triple and return True
    def record_automation(self, run_event) -> bool:
        message_group = self.message_groups.get(run_event["interaction_id"])
        if message_group is None:
            return False
        event_types_in_group = {e["event_type"] for e in message_group}
        if not {"automation_run", "combat_state_update", "command"}.issubset(event_types_in_group):
            return False
        self.state_buffer.extend(
            [e for e in message_group if e["event_type"] in {"automation_run", "combat_state_update", "command"}]
        )
        return True

    def automation_event_author(self, event) -> str | None:
        """
        Returns the user ID that ran the command that caused this automation run. Can be None if automation was from
        a button_press.
        """
        message_group = self.message_groups.get(event["interaction_id"])
        if message_group is None:
            return None
        return message_group[0]["author_id"]

    def clear_buffer(self):
        self.state_buffer = []
        self.utterance_buffer = []
        self.author_in_question = None

    def flush(self):
        if self.state_buffer and self.utterance_buffer:
            self.out.append({"state": self.state_buffer.copy(), "utterances": self.utterance_buffer.copy()})
        self.clear_buffer()

    # ==== event handlers ====
    def on_event(self, event):
        if self.search_state == 1:
            self.on_event_searching(event)
        elif self.search_state == 2:
            self.on_event_recording_state(event)
        else:
            self.on_event_recording_narration(event)

        if event["event_type"] == "combat_state_update":
            self.last_seen_combat_state = event["data"]
            self.current_combat_dm = str(event["data"]["dm"])

    def on_event_searching(self, event):
        # state 1: searching
        # automation_run: record automation, -> state 2
        if event["event_type"] == "automation_run":
            if self.record_automation(event):
                self.search_state = 2
                self.author_in_question = self.automation_event_author(event)

    def on_event_recording_state(self, event):
        # state 2: recording state (from user)
        # automation_run
        if event["event_type"] == "automation_run":
            event_author = self.automation_event_author(event)
            if event_author is None:
                return
            # from user: record automation
            elif event_author == self.author_in_question:
                self.record_automation(event)
            # from different user: -> state 2 (other user)
            elif self.record_automation(event):
                self.clear_buffer()
                self.author_in_question = self.automation_event_author(event)
                self.record_automation(event)
        # turn changes: -> state 1
        elif event["event_type"] == "combat_state_update" and heuristics.utils.did_turn_change(
            self.last_seen_combat_state, event["data"]
        ):
            self.clear_buffer()
            self.search_state = 1
        # utterance from DM or user: record utterance, -> state 3
        elif (
            event["event_type"] == "message"
            and len(self.message_groups[event["message_id"]]) == 1
            and (event["author_id"] == self.current_combat_dm or event["author_id"] == self.author_in_question)
        ):
            self.utterance_buffer.append(event)
            self.search_state = 3

    def on_event_recording_narration(self, event):
        # state 3: recording narration
        # automation_run: flush, record automation, -> state 2
        if event["event_type"] == "automation_run":
            self.flush()
            if self.record_automation(event):
                self.author_in_question = self.automation_event_author(event)
                self.search_state = 2
        # turn changes: flush, -> state 1
        elif event["event_type"] == "combat_state_update" and heuristics.utils.did_turn_change(
            self.last_seen_combat_state, event["data"]
        ):
            self.flush()
            self.search_state = 1
        # utterance from DM or user: record utterance
        elif (
            event["event_type"] == "message"
            and len(self.message_groups[event["message_id"]]) == 1
            and (event["author_id"] == self.current_combat_dm or event["author_id"] == self.author_in_question)
        ):
            self.utterance_buffer.append(event)


def extract_narration(combat_dir: pathlib.Path):
    events = list(utils.combat_dir_iterator(combat_dir))

    # pass 1: group (message, automation_run, combat_state_update, command)s by message_id
    message_groups = {}
    for event in events:
        match event:
            case {"event_type": "message", "message_id": message_id}:
                message_groups[message_id] = [event]
            case {"event_type": "command", "message_id": message_id} if message_id in message_groups:
                message_groups[message_id].append(event)
            case {"event_type": "automation_run", "interaction_id": message_id} if message_id in message_groups:
                message_groups[message_id].append(event)
            case {
                "event_type": "combat_state_update",
                "probable_interaction_id": message_id,
            } if message_id in message_groups:
                message_groups[message_id].append(event)

    # do the thing
    state = State(message_groups)
    for event in events:
        state.on_event(event)
    state.flush()

    # discard if we have nothing
    if not state.out:
        return

    # see what we get
    with gzip.open(OUT_DIR / f"{combat_dir.stem}.jsonl.gz", "wt") as f:
        for line in state.out:
            f.write(json.dumps(line) + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with tqdm.contrib.logging.logging_redirect_tqdm():
        if RUN_PARALLEL:
            tqdm.contrib.concurrent.process_map(extract_narration, utils.get_combat_dirs(DATA_DIR), chunksize=10)
        else:
            for d in tqdm.tqdm(utils.get_combat_dirs(DATA_DIR)):
                extract_narration(d)
