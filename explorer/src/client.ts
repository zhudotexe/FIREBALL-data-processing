import type {RPToCommandDistill, StateToNarrationDistill, TimeBasedDistill} from "@/avrae/distill";
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

    private async* eventsFromStream<T>(stream: ReadableStream<Uint8Array>): AsyncGenerator<T> {
        // stream transform code adapted from https://streams.spec.whatwg.org/demos/append-child.html
        // see "WHATWG Streams Standard" in licenses.txt
        const reader = stream
            .pipeThrough(new TextDecoderStream())
            .pipeThrough(splitStreamOn('\n'))
            .pipeThrough(parseJSONStream<T>())
            .getReader();

        // consume the readable stream and yield events
        while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            yield value;
        }
    }

    async* loadEventsForInstance(instanceId: string): AsyncGenerator<AnyEvent> {
        const response = await fetch(`${API_BASE}/events/${instanceId}`);
        if (response.ok && response.body) {
            yield* await this.eventsFromStream<AnyEvent>(response.body);
        } else {
            console.error(`Failed to load instance events: ${response.status} ${response.statusText}`);
        }
    }

    async* loadRPCommandDistill(instanceId: string): AsyncGenerator<RPToCommandDistill> {
        const response = await fetch(`${API_BASE}/distill/rp/${instanceId}`);
        if (response.ok && response.body) {
            yield* await this.eventsFromStream<RPToCommandDistill>(response.body);
        } else {
            console.error(`Failed to load RP distill: ${response.status} ${response.statusText}`);
        }
    }

    async* loadStateNarrationDistill(instanceId: string): AsyncGenerator<StateToNarrationDistill> {
        const response = await fetch(`${API_BASE}/distill/narration/${instanceId}`);
        if (response.ok && response.body) {
            yield* await this.eventsFromStream<StateToNarrationDistill>(response.body);
        } else {
            console.error(`Failed to load narration distill: ${response.status} ${response.statusText}`);
        }
    }

    async* loadTimeBasedDistill(instanceId: string): AsyncGenerator<TimeBasedDistill> {
        const response = await fetch(`${API_BASE}/distill/experiment1/${instanceId}`);
        if (response.ok && response.body) {
            yield* await this.eventsFromStream<TimeBasedDistill>(response.body);
        } else {
            console.error(`Failed to load time based distill: ${response.status} ${response.statusText}`);
        }
    }
}
