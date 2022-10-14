import csv
import logging
import os
import pathlib

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import utils
from state import State

log = logging.getLogger("explorer_server")

# ===== config =====
DATA_DIR = pathlib.Path(os.getenv("DATA_DIR", "data/"))
HEURISTIC_DIR = pathlib.Path(os.getenv("HEURISTIC_DIR", "heuristic_results/"))

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
async def heuristics() -> dict[str, dict[str, float]]:
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
