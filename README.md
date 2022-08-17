# avrae-dataset

Dataset exploration utilities for the Avrae NLP dataset

## Setup

### Python & Requirements

These utilities require Python 3.10+. I recommend creating a virtual environment to install the explorer's requirements:

```bash
$ python --version
Python 3.10.2
$ python -m venv venv
$ source venv/bin/activate
# If the venv is already set up, you can skip to this step
(venv) $ pip install -r requirements.txt
```

### Download the raw data

I recommend downloading the raw dataset into a directory at `data/` (relative to this repo's root). See the
avrae/penn-nlp-resources repo for instructions on downloading the dataset.

## Step 1: Heuristics

The first step of exploring the dataset is to define and apply heuristics to the dataset.

### Defining Heuristics

To define a heuristic, add it to the ``heuristics`` module - a function that takes an iterator of event dicts (a combat
session) and returns a single float (we'll use this later - the scale and meaning can be fairly arbitrary). Make sure to
import any added heuristics in ``heuristics/__init__.py``.

### Applying Heuristics

Next, you should compute each heuristic over the dataset - to do this efficiently, run `python heuristic_worker.py`.
This will compute each defined heuristic for each combat instance in parallel and save the results
to `heuristic_results/`.

If a heuristic has been computed for the dataset previously (based on heuristic name and dataset checksum), it will not
be recomputed. **Make sure to delete any prior result from your output directory or run with `--force-recompute` after
modifying heuristic code.**

The heuristic worker includes some additional arguments for more fine-grained control. You can view these arguments
with `python heuristic_worker.py --help`:

```text
usage: heuristic_worker.py [-d DATA_DIR] [-o OUTPUT_DIR] [-h HEURISTIC] [--force-recompute] [--help]

Applies defined heuristics to the Avrae NLP dataset.

options:
  -d DATA_DIR, --data-dir DATA_DIR
                        the directory containing the raw data (default: data/)
  -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                        the directory to save the heuristic results to (default: heuristic_results/)
  -h HEURISTIC, --heuristic HEURISTIC
                        the heuristic(s) to run (defaults to all)
  --force-recompute     forces the worker to recompute regardless of prior computation
  --help                displays CLI help
```

## Step 2: Exploration

After defining and computing some heuristics, the next step is to open up the dataset in the *dataset explorer* and
view each recording instance empirically alongside the computed heuristics.

This project provides a simple local web app to accomplish this. Run `python explorer_server.py` and the explorer will
be served at `http://127.0.0.1:31415/explorer`.
