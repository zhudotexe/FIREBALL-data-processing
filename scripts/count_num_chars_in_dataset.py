"""
Counts the number of characters in message events in the dataset.
This is useful for estimating inference costs with GPT-3.
"""
import os.path
import pathlib
import sys
from collections import namedtuple, Counter

import tqdm.contrib.concurrent

sys.path.append("..")

from dataset import utils

DATA_DIR = pathlib.Path(os.path.dirname(__file__), "../data")
MODEL_COSTS = (
    ("Davinci", 0.02),
    ("Curie", 0.002),
    ("Babbage", 0.0005),
    ("Ada", 0.0004),
    ("FT Davinci", 0.12),
    ("FT Curie", 0.012),
    ("FT Babbage", 0.0024),
    ("FT Ada", 0.0016),
)

Count = namedtuple("Count", "n_chars n_events events commands authors")


def count(dname):
    events = Counter()  # event type -> occurrences
    commands = Counter()  # command name -> occurrences
    authors = Counter()  # author id -> number of characters
    n_chars = 0
    n_events = 0

    for event in utils.combat_dir_iterator(dname):
        n_events += 1
        events[event["event_type"]] += 1
        if event["event_type"] == "message":
            msg_len = len(event["content"])
            n_chars += msg_len
            authors[event["author_id"]] += msg_len
        elif event["event_type"] == "command":
            commands[event["command_name"]] += 1

    return Count(n_chars=n_chars, n_events=n_events, events=events, commands=commands, authors=authors)


def main():
    counts = tqdm.contrib.concurrent.process_map(count, utils.get_combat_dirs(DATA_DIR), chunksize=10)

    total_events = Counter()
    total_commands = Counter()
    total_authors = Counter()
    for c in counts:
        total_events.update(c.events)
        total_commands.update(c.commands)
        total_authors.update(c.authors)
    total_chars = sum(c.n_chars for c in counts)
    total_n_events = sum(c.n_events for c in counts)

    print(
        f"total number of characters: {total_chars}\n"
        f"total number of events: {total_n_events}\n"
        f"total events: {total_events}\n"
        f"total commands: {total_commands}\n"
        f"total authors: {total_authors}\n"
        f"unique authors: {len(total_authors)}"
    )

    token_count = total_chars / 4

    print(f"Total number of characters: {total_chars} (approx. {token_count} tokens)")
    for model_name, cost_per_1k in MODEL_COSTS:
        print(f"{model_name}: ${token_count / 1000 * cost_per_1k:.2f}")


if __name__ == "__main__":
    main()
