import type { RunResponse, TraceResponse, MemoryResponse } from "./types";

export class ApiError extends Error {
    code: string;
    status: number;
    constructor(code: string, message: string, status: number) {
        super(message);
        this.code = code;
        this.status = status;
        this.name = "ApiError";
    }
}

async function fetchWithHandle<T>(url: string, options?: RequestInit): Promise<T> {
    const res = await fetch(url, options);
    if (!res.ok) {
        let errBody;
        try {
            errBody = await res.json();
        } catch {
            throw new ApiError("HTTP_ERROR", res.statusText, res.status);
        }
        if (errBody && errBody.error) {
            throw new ApiError(errBody.error.code, errBody.error.message, res.status);
        }
        throw new ApiError("HTTP_ERROR", res.statusText, res.status);
    }
    return res.json() as Promise<T>;
}

export const NexusApi = {
    runLive: (scenarioId: string, agentVersion: string = "v0.1") => 
        fetchWithHandle<RunResponse>("/api/v1/scenarios/" + scenarioId + "/run?mode=LIVE&agent_version=" + agentVersion, { method: "POST" }),
    
    runReplay: (scenarioId: string, replayOf: string, agentVersion: string = "v0.1") =>
        fetchWithHandle<RunResponse>("/api/v1/scenarios/" + scenarioId + "/run?mode=REPLAY&replay_of=" + replayOf + "&agent_version=" + agentVersion, { method: "POST" }),
        
    getTrace: (runId: string) =>
        fetchWithHandle<TraceResponse>("/api/v1/runs/" + runId + "/trace"),
        
    getMemory: (contextId: string) =>
        fetchWithHandle<MemoryResponse>("/api/v1/memory/" + contextId)
};
