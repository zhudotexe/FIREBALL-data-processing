import csv
import logging
import os
import pathlib

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import heuristics
import utils

log = logging.getLogger("explorer_server")

# ===== config =====
DATA_DIR = pathlib.Path(os.getenv("DATA_DIR", "data/"))
HEURISTIC_DIR = pathlib.Path(os.getenv("HEURISTIC_DIR", "heuristic_results/"))


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


# ===== app =====
app = FastAPI()
state = State(DATA_DIR, HEURISTIC_DIR)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/explorer", StaticFiles(directory="explorer/dist", html=True), name="explorer")


@app.on_event("startup")
async def startup_event():
    state.init()


# ===== api routes =====
@app.get("/")
async def root():
    return RedirectResponse("/explorer")


@app.get("/index")
async def index():
    """Returns the dataset index (checksum, list of instance ids, list of heuristic ids)"""
    return {"checksum": state.dataset_checksum, "instances": state.instance_ids, "heuristics": state.heuristic_ids}


@app.get("/heuristics")
async def instance_heuristics() -> dict[str, dict[str, float]]:
    """Returns all of the computed heuristics. (instance id -> (heuristic id -> score))"""
    return state.heuristics_by_instance


@app.get("/events/{instance_id}")
def get_instance_events(instance_id: str):
    """Returns a streaming response of events, with each chunk being a list of events."""
    if instance_id not in state.instance_ids:
        raise HTTPException(status_code=404, detail="instance does not exist")
    # stream the response in order to reduce memory usage (big instances can be 250MB+, don't consume entire iterator)
    return StreamingResponse(
        utils.combat_dir_iterator_raw(state.data_dir_path / instance_id), media_type="application/jsonl+json"
    )


# todo endpoints to save notes and -2 to +2 scores for each instance
# todo endpoints to retrieve those notes
# todo sqlite db to save those


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    uvicorn.run(app, host="127.0.0.1", port=31415, log_config=None)
