import axios from "axios";

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
        try {
            const response = await axios.get<IndexModel>(`${API_BASE}/index`);
            this.checksum = response.data.checksum;
            this.instanceIds = response.data.instances;
            this.heuristicIds = response.data.heuristics;
            this.indexLoaded = true;
            console.debug(`Loaded dataset index: checksum=${this.checksum}`)
        } catch (error) {
            console.error("Failed to load the dataset index:", error);
        }
    }

    async loadHeuristicsByInstance() {
        try {
            const response = await axios.get<InstanceHeuristicMap>(`${API_BASE}/heuristics`);
            this.heuristicsByInstance = response.data;
            this.heuristicsLoaded = true;
            console.debug(`Loaded heuristics: checksum=${this.checksum}`)
        } catch (error) {
            console.error("Failed to load heuristics:", error);
        }
    }
}