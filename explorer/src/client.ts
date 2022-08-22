
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
}
