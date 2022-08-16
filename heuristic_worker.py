import argparse
import csv
import functools
import logging
import os
import pathlib

import dirhash
import tqdm
import tqdm.contrib.concurrent
import tqdm.contrib.logging

import heuristics
from utils import combat_dir_iterator, get_combat_dirs

# ===== argparsing =====
parser = argparse.ArgumentParser(description="Applies defined heuristics to the Avrae NLP dataset.", add_help=False)
parser.add_argument(
    "-d",
    "--data-dir",
    help="the directory containing the raw data (default: data/)",
    default="data/",
    type=pathlib.Path,
)
parser.add_argument(
    "-o",
    "--output-dir",
    help="the directory to save the heuristic results to (default: heuristic_results/)",
    default="heuristic_results/",
    type=pathlib.Path,
)
parser.add_argument(
    "-h",
    "--heuristic",
    help="the heuristic(s) to run (defaults to all)",
    action="append",
)
parser.add_argument(
    "--force-recompute",
    help="forces the worker to recompute regardless of prior computation",
    action="store_true",
)
parser.add_argument("--help", help="displays CLI help", action="help")

# ===== main =====
log = logging.getLogger(__name__)


def get_heuristic(name: str) -> heuristics.Heuristic:
    """Returns the heuristic with the given name (utility method for CLI)"""
    return getattr(heuristics, name)


def worker_entrypoint(heuristic: heuristics.Heuristic, combat_dir: str) -> tuple[str, int | float]:
    """Multiprocessing worker entrypoint, applies the given heuristic to one dir"""
    return os.path.basename(combat_dir), heuristic(combat_dir_iterator(combat_dir))


class Runner:
    def __init__(
        self,
        data_dir_path: pathlib.Path,
        result_dir_path: pathlib.Path,
        compute_heuristics: list[str] | None = None,
        force_recompute: bool = False,
    ):
        self.data_dir_path = data_dir_path
        self.result_dir_path = result_dir_path
        self.heuristics = compute_heuristics
        self.force_recompute = force_recompute
        self.dataset_checksum = None

    @classmethod
    def from_args(cls, args: argparse.Namespace):
        return cls(
            data_dir_path=args.data_dir,
            result_dir_path=args.output_dir,
            compute_heuristics=args.heuristic,
            force_recompute=args.force_recompute,
        )

    def init(self):
        num_cores = os.cpu_count() or 1
        log.info(f"Hashing dataset (with parallelization={num_cores})...")
        self.dataset_checksum = dirhash.dirhash(self.data_dir_path, "md5", match=("*.gz",), jobs=num_cores)
        log.info(f"checksum={self.dataset_checksum}")
        os.makedirs(self.result_dir_path, exist_ok=True)

    def run_one(self, heuristic_name: str):
        log.info(f"Applying heuristic {heuristic_name!r}...")
        result_file_path = self.result_dir_path / f"{heuristic_name}.csv"
        heuristic = get_heuristic(heuristic_name)
        entrypoint = functools.partial(worker_entrypoint, heuristic)

        # if the results already exist for this dataset and heuristic, we can skip everything
        try:
            with open(result_file_path, newline="") as f:
                reader = csv.reader(f)
                _, existing_checksum = next(reader)
            if self.force_recompute:
                log.info(
                    f"A result for this dataset already exists at {os.path.relpath(result_file_path)} but recompute is"
                    " forced, overwriting..."
                )
            elif existing_checksum == self.dataset_checksum:
                log.info(f"A result for this dataset already exists at {os.path.relpath(result_file_path)}!")
                return
            else:
                log.info("An existing result was found but the checksum does not match, overwriting...")
        except FileNotFoundError:
            pass

        # execution
        results = tqdm.contrib.concurrent.process_map(entrypoint, get_combat_dirs(self.data_dir_path), chunksize=10)
        results.sort(key=lambda pair: pair[1])
        log.info(f"Application of {heuristic_name} complete, saving results...")

        # save results
        with open(result_file_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(("checksum", self.dataset_checksum))
            writer.writerows(results)

    def run_heuristics(self, heuristic_names: list[str]):
        if not all(hasattr(heuristics, name) for name in heuristic_names):
            raise RuntimeError(
                f"Heuristic(s) were passed but not defined: {set(heuristic_names).difference(heuristics.__all__)}"
            )

        with tqdm.contrib.logging.logging_redirect_tqdm():
            for heuristic_name in tqdm.tqdm(heuristic_names):
                self.run_one(heuristic_name)

    def run_all(self):
        self.run_heuristics(heuristics.__all__)

    def run_cli(self):
        self.init()

        if self.heuristics is None:
            self.run_all()
        elif not self.heuristics:
            raise RuntimeError(
                "At least one heuristic should be passed, or the argument should be omitted to run all heuristics."
            )
        else:
            self.run_heuristics(self.heuristics)
        log.info("Done!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    Runner.from_args(parser.parse_args()).run_cli()
