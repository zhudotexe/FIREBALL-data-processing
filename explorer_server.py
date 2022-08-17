import csv
import logging
import pathlib

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

import utils

log = logging.getLogger("explorer_server")

# ===== config =====
DATA_DIR = pathlib.Path("data/")
HEURISTIC_DIR = pathlib.Path("heuristic_results/")


class State:
    def __init__(self, data_dir_path: pathlib.Path, result_dir_path: pathlib.Path):
        self.data_dir_path = data_dir_path
        self.result_dir_path = result_dir_path
        self.dataset_checksum = None
        self.dataset_index = []
        self.heuristics_by_instance = {}

    def init(self):
        log.info("Computing dataset checksum...")
        self.dataset_checksum = utils.dataset_checksum(self.data_dir_path)
        self.dataset_index = [instance_path.stem for instance_path in utils.get_combat_dirs(self.data_dir_path)]

        # load the computed heuristic results into memory, validating the checksum
        log.info("Loading heuristic results...")
        self.heuristics_by_instance = {instance_id: {} for instance_id in self.dataset_index}
        for heuristic_result in self.result_dir_path.glob("*.csv"):
            heuristic_name = heuristic_result.stem
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
            log.debug(f"finished {heuristic_name=}")
        log.info("State init complete! Ready to serve explorer.")


# ===== app =====
app = FastAPI()
state = State(DATA_DIR, HEURISTIC_DIR)

app.mount("/explorer", StaticFiles(directory="explorer"), name="explorer")


@app.on_event("startup")
async def startup_event():
    state.init()


# ===== api routes =====
@app.get("/")
async def root():
    return RedirectResponse("/explorer")


@app.get("/index")
async def index():
    """Returns the dataset index (checksum + list of dir names)"""
    return {"checksum": state.dataset_checksum, "index": state.dataset_index}


@app.get("/heuristics")
async def heuristics() -> dict[str, dict[str, float]]:
    """Returns all of the computed heuristics. (instance id -> (heuristic id -> score))"""
    return state.heuristics_by_instance


@app.get("/events/{instance_id}")
def get_instance_events(instance_id: str):
    if instance_id not in state.dataset_index:
        raise HTTPException(status_code=404, detail="instance does not exist")
    # todo maybe we can do some caching here, this can take a bit of time
    # or like stream the response in event batches
    return list(utils.combat_dir_iterator(state.data_dir_path / instance_id))


# todo endpoints to save notes and -2 to +2 scores for each instance
# todo endpoints to retrieve those notes
# todo sqlite db to save those


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=31415)
