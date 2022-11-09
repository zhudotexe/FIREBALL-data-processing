"""
Counts the number of characters in message events in the dataset.
This is useful for estimating inference costs with GPT-3.
"""
import os.path
import pathlib
import sys

import tqdm.contrib.concurrent

sys.path.append("..")

import dataset.utils

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


def count_tokens_in_dir(dname):
    return sum(len(event["content"]) for event in utils.combat_dir_iterator(dname) if event["event_type"] == "message")


def main():
    counts = tqdm.contrib.concurrent.process_map(count_tokens_in_dir, utils.get_combat_dirs(DATA_DIR), chunksize=10)

    count = sum(counts)
    token_count = count / 4

    print(f"Total number of characters: {count} (approx. {token_count} tokens)")
    for model_name, cost_per_1k in MODEL_COSTS:
        print(f"{model_name}: ${token_count / 1000 * cost_per_1k:.2f}")


if __name__ == "__main__":
    main()

