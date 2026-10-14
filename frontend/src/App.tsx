import { useState } from 'react';
import { LeftPanel } from './components/LeftPanel';
import { MiddlePanel } from './components/MiddlePanel';
import { RightPanel } from './components/RightPanel';
import { NexusApi, ApiError } from './api/client';
import type { RunResponse, DecisionTrace, MemoryResponse } from './api/types';
import { SCENARIOS } from './manifest';

function App() {
  const [selectedScenario, setSelectedScenario] = useState<string>(SCENARIOS[0].id);
  const [isRunning, setIsRunning] = useState(false);
  const [loadingTrace, setLoadingTrace] = useState(false);
  
  const [run, setRun] = useState<RunResponse | null>(null);
  const [trace, setTrace] = useState<DecisionTrace | null>(null);
  const [memory, setMemory] = useState<MemoryResponse | null>(null);
  
  const [error, setError] = useState<string | null>(null);

  const fetchTraceAndMemory = async (r: RunResponse) => {
    setLoadingTrace(true);
    try {
      const traceData = await NexusApi.getTrace(r.run_id);
      setTrace(traceData.trace);
      
      const memData = await NexusApi.getMemory(r.scenario_id);
      setMemory(memData);
    } catch (e) {
      if (e instanceof ApiError) {
        setError("Failed to load trace: " + e.message);
      } else {
        setError("Failed to load trace: " + String(e));
      }
    } finally {
      setLoadingTrace(false);
    }
  };

  const handleRunLive = async () => {
    setIsRunning(true);
    setError(null);
    setRun(null);
    setTrace(null);
    setMemory(null);
    
    try {
      const runData = await NexusApi.runLive(selectedScenario);
      setRun(runData);
      await fetchTraceAndMemory(runData);
    } catch (e) {
      if (e instanceof ApiError) {
        setError("API Error (" + e.code + "): " + e.message);
      } else {
        setError(String(e));
      }
    } finally {
      setIsRunning(false);
    }
  };

  const handleRunReplay = async (sourceRunId: string) => {
    setIsRunning(true);
    setError(null);
    setRun(null);
    setTrace(null);
    setMemory(null);
    
    try {
      const runData = await NexusApi.runReplay(selectedScenario, sourceRunId);
      setRun(runData);
      await fetchTraceAndMemory(runData);
    } catch (e) {
      if (e instanceof ApiError) {
        setError("API Error (" + e.code + "): " + e.message);
      } else {
        setError(String(e));
      }
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="flex h-screen w-screen bg-white text-gray-800 overflow-hidden font-sans">
      <LeftPanel 
        selectedScenario={selectedScenario}
        onSelectScenario={setSelectedScenario}
        onRunLive={handleRunLive}
        onRunReplay={handleRunReplay}
        isRunning={isRunning}
      />
      
      <MiddlePanel 
        run={run}
        trace={trace}
        memory={memory}
        loading={isRunning || loadingTrace}
        error={error}
      />
      
      <RightPanel 
        run={run}
      />
    </div>
  );
}

export default App;
