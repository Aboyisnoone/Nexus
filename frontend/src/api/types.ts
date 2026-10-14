export interface ErrorDetail {
    code: string;
    message: string;
}

export interface ErrorResponse {
    error: ErrorDetail;
}

export interface EvaluationAssertion {
    assertion: any;
    passed: boolean;
    actual: any;
    error: string | null;
}

export interface EvaluationReport {
    status: 'PASS' | 'FAIL' | 'ERROR';
    total: number;
    passed: number;
    failed: number;
    assertions: EvaluationAssertion[];
}

export interface RunResponse {
    run_id: string;
    scenario_id: string;
    mode: 'LIVE' | 'REPLAY';
    agent_version: string | null;
    status: 'RUNNING' | 'COMPLETED' | 'FAILED' | 'APPLIED';
    evaluation: EvaluationReport | null;
    error: string | null;
}

export interface TraceStep {
    step_index: number;
    step_type: string;
    simulated_time: string;
    recorded_at: string | null;
    [key: string]: any; // other payload fields depending on step_type
}

export interface DecisionTrace {
    trace_id: string;
    scenario_id: string;
    agent_version: string;
    steps: TraceStep[];
}

export interface TraceResponse {
    trace: DecisionTrace;
}

export interface MemoryItem {
    id: string;
    context_id: string;
    key: string;
    value: any;
    state: 'OBSERVED' | 'INFERRED' | 'CONFIRMED';
    version: number;
    previous_version_id: string | null;
    simulated_time_iso: string;
    evidence_json: string[];
    contradictions_json: string[];
    confirmation_event_json: any | null;
}

export interface MemoryResponse {
    memories: MemoryItem[];
}
