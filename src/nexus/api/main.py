from fastapi import FastAPI, Depends, Query, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from typing import Optional, Literal

from nexus.api.models import RunResponse, TraceResponse, MemoryResponse, ErrorResponse, ErrorDetail
from nexus.api.dependencies import get_repository, get_pipeline
from nexus.core.persistence.repository import NexusRepository
from nexus.core.runner.pipeline import DecisionPipeline
from nexus.core.evaluation.suite import CoreSuiteRunner
from nexus.core.evaluation.evaluator import EvaluationReport

app = FastAPI(
    title="NEXUS v0.1 API",
    description="Autonomous agent evaluation and reliability laboratory.",
    version="0.1.0"
)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": {"code": "VALIDATION_ERROR", "message": str(exc)}}
    )

@app.get("/health", response_model=dict)
def health_check():
    return {"status": "ok", "service": "nexus"}

@app.post("/api/v1/scenarios/{id}/run", response_model=RunResponse, responses={404: {"model": ErrorResponse}, 400: {"model": ErrorResponse}})
def run_scenario(
    id: str,
    mode: Literal["LIVE", "REPLAY"] = Query(..., description="Execution mode: LIVE or REPLAY"),
    replay_of: Optional[str] = Query(None, description="Source run_id to replay (required if mode=REPLAY)"),
    agent_version: str = Query("v0.1", description="Agent version string"),
    repo: NexusRepository = Depends(get_repository),
    pipeline: DecisionPipeline = Depends(get_pipeline)
):
    scenario = repo.load_scenario(id)
    if not scenario:
        raise HTTPException(status_code=404, detail={"code": "SCENARIO_NOT_FOUND", "message": f"Scenario '{id}' not found."})
        
    if mode == "REPLAY" and not replay_of:
        raise HTTPException(status_code=400, detail={"code": "MISSING_REPLAY_SOURCE", "message": "replay_of is required for REPLAY mode."})

    try:
        if mode == "LIVE":
            run_result = pipeline.run_live(scenario, agent_version=agent_version)
        else:
            run_result = pipeline.run_replay(replay_of, override_agent_version=agent_version)
    except Exception as e:
        # In case of missing recording or mismatches, pipeline.run_replay usually returns a failed SimulationResult,
        # but if it raises, we catch it here and preserve the error.
        raise HTTPException(status_code=500, detail={"code": "ERR_SYSTEM", "message": str(e)})

    # Determine execution status mapping
    exec_status = run_result.simulation_result.status
    error_code = run_result.simulation_result.error

    # Check for specific replay errors that pipeline might encode as failed simulation
    if error_code in ("ERR_MISSING_RECORDING", "ERR_REPLAY_INPUT_MISMATCH"):
        pass # It's a domain error, not an HTTP 500

    # Get pre-evaluated report from the pipeline run
    evaluation = run_result.evaluation_report

    return RunResponse(
        run_id=run_result.run_id,
        scenario_id=id,
        mode=mode,
        agent_version=agent_version,
        status=exec_status,
        evaluation=evaluation,
        error=error_code
    )

@app.get("/api/v1/runs/{id}/trace", response_model=TraceResponse, responses={404: {"model": ErrorResponse}})
def get_trace(
    id: str,
    repo: NexusRepository = Depends(get_repository)
):
    trace = repo.load_decision_trace(id)
    if not trace:
        raise HTTPException(status_code=404, detail={"code": "TRACE_NOT_FOUND", "message": f"Trace for run '{id}' not found."})
    
    return TraceResponse(trace=trace)

@app.get("/api/v1/memory/{context_id}", response_model=MemoryResponse)
def get_memory(
    context_id: str,
    repo: NexusRepository = Depends(get_repository)
):
    memories = repo.load_memories(context_id)
    return MemoryResponse(memories=memories)

# Custom exception handler to format HTTPException to ErrorResponse
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request, exc):
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": detail}
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "HTTP_ERROR", "message": str(detail)}}
    )




@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"error": {"code": "ERR_SYSTEM", "message": str(exc)}}
    )

from fastapi.staticfiles import StaticFiles
import os

frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'frontend', 'dist'))
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
