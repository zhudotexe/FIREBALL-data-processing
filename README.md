# AWS Kinesis Dataset Exploration Tool

This repo contains a set of tools in order to explore datasets collected via AWS Kinesis Firehose quickly and
intuitively, while providing the framework to quickly iterate on heuristics and visualize raw data.

- Operates directly on gzipped JSONL files output by AWS Kinesis Firehose, no extraction needed
- Memory efficient (streaming heuristic applicator)
- High-throughput and horizontally scalable (multiprocessing out of the box)
- Low-latency (streaming API & client)

I built this tool for the Avrae NLP project (https://www.cis.upenn.edu/~ccb/language-to-avrae.html) and this is the
dataset this repo is implemented for, but the tool is designed with some degree of dataset-agnosticism in mind.

For help using this tool in your own data science project, contact me at andrz@seas.upenn.edu or view "Customizing the
Explorer" below.

## Downloading raw data

I recommend downloading the raw dataset into a directory at `data/` (relative to this repo's root). Usually this is done
with `aws s3 sync`.

For the Avrae NLP project, see the avrae/penn-nlp-resources repo for instructions on downloading the dataset.

## Step 1: Heuristics

The first step of exploring the dataset is to define and apply heuristics to the dataset.

### Requirements

The heuristic worker requires Python 3.10+.

I recommend creating a virtual environment to install the Python requirements:

```bash
# installing Python requirements
$ python --version
Python 3.10.2
$ python -m venv venv
$ source venv/bin/activate
# If the venv is already set up, you can skip to this step
(venv) $ pip install -r requirements.txt
```

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

Applies defined heuristics to a dataset.

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

### Requirements

Building the explorer app locally is optional - the prebuilt files can be downloaded from TODO.

To build the explorer web app locally, Node.js 16+ is required.

The explorer app uses some [modern web technologies](https://caniuse.com/mdn-api_textdecoderstream) that are not yet
supported by all browsers; Chrome 71+, Edge 79+, Safari 14.1+, or Opera 58+ is required (Firefox and IE are not
supported).

```bash
# installing Node requirements (optional)
$ node --version
v16.17.0
$ npm --version
8.17.0
$ cd explorer
$ npm install
```

### Build Explorer App

The explorer app is a Vue app that lives in `explorer/`. To build it, run `npm run build` from the explorer directory.

Alternatively, you can download a prebuilt distribution from TODO. To use the prebuilt distribution, create
the `explorer/dist` directory and extract it to that directory. The project file structure should look like this:

```text
aws-kinesis-dataset-exploration-tool/
    explorer/
        dist/
            assets/
                index.***.css
                index.***.js
            index.html
```

### Run Explorer App

This project provides a simple local web app to accomplish this. Run `python explorer_server.py` and the explorer will
be served at `http://127.0.0.1:31415/explorer`.

Similarly to the heuristic worker, you can point the explorer to an alternate dataset directory and heuristic results
directory by setting the `DATA_DIR` and `HEURISTIC_DIR` environment variables, respectively.

### Customizing the Explorer

The implementation of the explorer in this repo is built for the Avrae NLP project. To use this tool for your own
project, you will need to change your event visualizer and models.

#### Define Custom Event Models (Optional)

This step provides typed interfaces in order to make building the custom event visualizer easier. You can skip this step
by setting `type AnyEvent = any` in `explorer/src/events.ts` if you do not need static typing.

Otherwise, create a directory in `explorer/src` for your own dataset, and define your event type(s) as a TypeScript
interface. Once you've done that, set the `AnyType` type to your newly defined type(s) in `explorer/src/events.ts`.

#### Define Event Key

In order to use this tool's event annotation features, each event should have a unique ID. To define how to extract this
ID from an event, implement `getEventId(event: AnyEvent): string | null` in `explorer/src/events.ts`.

If the function returns `null`, the event for which it did will not support annotations.

#### Custom Event Visualizer

To visualize an event, define a Vue component in your dataset-specific directory that takes your event as a prop. Use
this template:

```vue
<!-- explorer/src/(dataset)/EventComponent.vue -->
<script setup lang="ts">
// don't change this!
import type {AnyEvent} from "@/events";
defineProps<{event: AnyEvent}>();
// any custom JS logic goes here
</script>

<template>
<!-- by default, this displays the event as JSON - update the template to your liking -->
<pre>
    {{ event }}
</pre>
</template>

<style scoped>
/* css goes here */
</style>
```

Then, update the import in `explorer/src/views/InstanceViewer.vue` to use your dataset-specific component:

```vue
<!-- explorer/src/views/InstanceViewer.vue -->
<script setup lang="ts">
[...]
import EventComponent from "@/(dataset)/EventComponent.vue";  // change this line!
[...]
</script>
```

### Gotchas

As JavaScript's `number` type loses precision for integers greater than 2^53, the explorer will automatically parse
any integer that would otherwise cause rounding as a `BigInt`.
