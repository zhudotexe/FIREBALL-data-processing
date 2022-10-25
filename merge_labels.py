"""
Merge labelled instances with their labels.

Labels should be a csv file with columns (instance_id, label).
"""
import os
import pathlib

import pandas as pd

from dataset import Dataset

DATA_DIR = pathlib.Path(os.getenv("DATA_DIR", "data/"))
HEURISTIC_DIR = pathlib.Path(os.getenv("HEURISTIC_DIR", "heuristic_results/"))
HUMAN_LABEL_FILE = pathlib.Path(os.getenv("HUMAN_LABEL_FILE", "regression_data/bootstrap_labels.csv"))

DEBUG = True

state = Dataset(DATA_DIR, HEURISTIC_DIR)


def load_labels() -> pd.DataFrame:
    """
    Loads human-annotated labels for instances.
    The labels should be present at the file in HUMAN_LABEL_FILE (regression_data/bootstrap_labels.csv by default).
    Download the CSV from https://docs.google.com/spreadsheets/d/1UNbF9tqca3pR1cig5e7HJyqZFJlEX-juOg2C9Ft0EEI/edit#gid=0
    """
    label_csv = pd.read_csv(HUMAN_LABEL_FILE)
    return label_csv[["Instance ID", "Label"]]


def main():
    state.init()
    instance_heuristics_df = state.instance_heuristics_df
    labels_df = load_labels()

    if DEBUG:
        print(instance_heuristics_df.head())
        print(labels_df.head())


if __name__ == "__main__":
    main()
