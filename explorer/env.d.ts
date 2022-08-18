/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_API_URL: string;  // the base endpoint for the explorer API
}

interface ImportMeta {
    readonly env: ImportMetaEnv;
}
