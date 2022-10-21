import csv
import functools
import logging
import pathlib

import pandas as pd

import heuristics
import utils

log = logging.getLogger(__name__)


class State:
    def __init__(self, data_dir_path: pathlib.Path, result_dir_path: pathlib.Path):
        self.data_dir_path = data_dir_path
        self.result_dir_path = result_dir_path
        self.dataset_checksum = None
        self.instance_ids = []
        self.heuristic_ids = []
        self.heuristics_by_instance = {}

    def init(self):
        log.info("Computing dataset checksum...")
        self.dataset_checksum = utils.dataset_checksum(self.data_dir_path)
        self.instance_ids = [instance_path.stem for instance_path in utils.get_combat_dirs(self.data_dir_path)]

        # load the computed heuristic results into memory, validating the checksum
        log.info("Loading heuristic results...")
        num_heuristics_attempted_loaded = 0
        self.heuristics_by_instance = {instance_id: {} for instance_id in self.instance_ids}
        for heuristic_result in self.result_dir_path.glob("*.csv"):
            num_heuristics_attempted_loaded += 1
            heuristic_name = heuristic_result.stem
            if heuristic_name not in heuristics.__all__:
                log.warning(
                    f"Heuristic {heuristic_name!r} has a result but is not defined in heuristics.__all__, skipping..."
                )
                continue
            log.debug(f"loading {heuristic_name=}")
            with open(heuristic_result, newline="") as f:
                reader = csv.reader(f)
                _, checksum = next(reader)
                if checksum != self.dataset_checksum:
                    log.warning(f"Heuristic {heuristic_name!r} has an invalid checksum, skipping...")
                    continue
                # consume the rest of the iterator of (instance id, score) pairs and construct a mapping
                for instance_id, score in reader:
                    self.heuristics_by_instance[instance_id][heuristic_name] = float(score)
            self.heuristic_ids.append(heuristic_name)
            log.debug(f"finished {heuristic_name=}")

        # log warnings if user needs to recompute heuristics
        if len(self.heuristic_ids) < num_heuristics_attempted_loaded:
            log.warning(
                f"{num_heuristics_attempted_loaded} heuristics found in results but only"
                f" {len(self.heuristic_ids)} loaded successfully!\n"
                "You may need to run `python heuristic_worker.py` to recompute heuristics after a dataset update."
            )
        elif num_heuristics_attempted_loaded == 0:
            log.warning(
                "No heuristics loaded! Make sure you have defined heuristics in `heuristics/__init__.py` and computed"
                " them by running `python heuristic_worker.py`."
            )

        log.info(f"State init complete ({len(self.heuristic_ids)} heuristics over {len(self.instance_ids)} instances)!")

    @functools.cached_property
    def instance_heuristics_df(self) -> pd.DataFrame:
        """Returns the mapping of instance IDs to heuristic values as a DataFrame."""
        return pd.DataFrame.from_dict(self.heuristics_by_instance, orient="index", columns=self.heuristic_ids)
