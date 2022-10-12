import type {AnyEvent} from "@/events";
import {parseJSONStream, splitStreamOn} from "@/utils";

type HeuristicScoreMap = { [heuristicId: string]: number };
type InstanceHeuristicMap = { [instanceId: string]: HeuristicScoreMap };


const API_BASE = import.meta.env.VITE_API_URL;

// ===== api types =====
interface IndexModel {
    checksum: string;
    instances: string[];
    heuristics: string[];
}

// ===== client ====
export class DatasetClient {
    public indexLoaded: boolean = false;
    public heuristicsLoaded: boolean = false;
    public checksum: string = "";
    public instanceIds: string[] = [];
    public heuristicIds: string[] = [];
    public heuristicsByInstance: InstanceHeuristicMap = {};
    public apiBase = API_BASE;

    public async init() {
        await this.loadIndex();
        await this.loadHeuristicsByInstance();
    }

    async loadIndex() {
        const response = await fetch(`${API_BASE}/index`);
        if (response.ok) {
            const data = await response.json();
            this.checksum = data.checksum;
            this.instanceIds = data.instances;
            this.heuristicIds = data.heuristics;
            this.indexLoaded = true;
            console.debug(`Loaded dataset index: checksum=${this.checksum}`)
        } else {
            console.error(`Failed to load the dataset index: ${response.status} ${response.statusText}`);
        }
    }

    async loadHeuristicsByInstance() {
        const response = await fetch(`${API_BASE}/heuristics`);
        if (response.ok) {
            this.heuristicsByInstance = await response.json();
            this.heuristicsLoaded = true;
            console.debug(`Loaded heuristics: checksum=${this.checksum}`)
        } else {
            console.error(`Failed to load heuristics: ${response.status} ${response.statusText}`);
        }
    }

    async* loadEventsForInstance(instanceId: string): AsyncGenerator<AnyEvent> {
        const response = await fetch(`${API_BASE}/events/${instanceId}`);
        if (response.ok && response.body) {
            // stream transform code adapted from https://streams.spec.whatwg.org/demos/append-child.html
            // see "WHATWG Streams Standard" in licenses.txt
            const stream = response.body
                .pipeThrough(new TextDecoderStream())
                .pipeThrough(splitStreamOn('\n'))
                .pipeThrough(parseJSONStream<AnyEvent>())
                .getReader();

            // consume the readable stream and yield events
            while (true) {
                const {done, value} = await stream.read();
                if (done) break;
                yield value;
            }
        } else {
            console.error(`Failed to load instance events: ${response.status} ${response.statusText}`);
        }
    }
}
