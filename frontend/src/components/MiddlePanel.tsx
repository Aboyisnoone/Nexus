import { useState } from 'react';
import type { RunResponse, DecisionTrace, TraceStep, MemoryResponse } from '../api/types';

interface Props {
  run: RunResponse | null;
  trace: DecisionTrace | null;
  memory: MemoryResponse | null;
  loading: boolean;
  error: string | null;
}

export function MiddlePanel({ run, trace, memory, loading, error }: Props) {
  if (loading) {
    return <div className="flex-1 flex items-center justify-center text-gray-500 font-mono text-sm">LOADING...</div>;
  }
  
  if (error) {
    return (
      <div className="flex-1 p-8">
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded font-mono text-sm">
          <h3 className="font-bold mb-2">ERROR</h3>
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (!run) {
    return <div className="flex-1 flex items-center justify-center text-gray-400 font-mono text-sm">Select a scenario to inspect</div>;
  }

  return (
    <div className="flex-1 flex flex-col h-full bg-gray-50 overflow-hidden">
      <div className="bg-white border-b border-gray-200 p-3 flex justify-between items-center shrink-0">
        <div className="text-sm font-mono text-gray-600">
          <span className="font-bold text-gray-800">RUN: </span>{run.run_id}
        </div>
        <div className="text-xs font-mono bg-gray-100 px-2 py-1 rounded border border-gray-200 text-gray-600">
          MODE: {run.mode} {run.agent_version ? ' | AGENT: ' + run.agent_version : ''}
        </div>
      </div>
      
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {trace?.steps.map((step, idx) => (
          <TraceStepCard key={idx} step={step} memory={memory} />
        ))}
        {run.status === 'FAILED' && (
          <div className="border border-red-300 bg-red-50 p-3 rounded font-mono text-sm flex justify-between text-red-700">
             <span className="font-bold">EXECUTION TERMINATED</span>
             <span>✕</span>
          </div>
        )}
      </div>
    </div>
  );
}

function TraceStepCard({ step, memory }: { step: TraceStep, memory: MemoryResponse | null }) {
  const [expanded, setExpanded] = useState(false);
  
  const isFailedValidation = step.step_type === 'VALIDATION' && step.validation_result?.valid === false;
  
  return (
    <div className={"border rounded bg-white shadow-sm overflow-hidden " + (isFailedValidation ? 'border-red-300' : 'border-gray-200')}>
      <div 
        className={"px-3 py-2 flex items-center justify-between cursor-pointer hover:bg-gray-50 " + (isFailedValidation ? 'bg-red-50' : '')}
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center space-x-3">
          <span className="text-gray-400 font-mono text-xs">{String(step.step_index).padStart(2, '0')}</span>
          <span className={"font-bold text-sm tracking-wide " + (isFailedValidation ? 'text-red-700' : 'text-gray-800')}>
            {step.step_type.replace(/_/g, ' ')}
          </span>
        </div>
        <div className="flex items-center space-x-3">
          {isFailedValidation && <span className="text-xs font-mono text-red-600">ERR_INVALID_ACTION</span>}
          <span className={isFailedValidation ? 'text-red-500 font-bold' : 'text-green-500 font-bold'}>
            {isFailedValidation ? '✕' : '✓'}
          </span>
        </div>
      </div>
      
      {expanded && (
        <div className="border-t border-gray-100 p-3 bg-gray-50 overflow-x-auto text-xs font-mono">
          {step.step_type === 'MEMORY' && memory ? (
            <MemoryViewer memory={memory} />
          ) : step.step_type === 'LLM_ACTION' ? (
            <ActionViewer action={step.action} />
          ) : (
            <pre className="text-gray-700">{JSON.stringify(step, null, 2)}</pre>
          )}
        </div>
      )}
    </div>
  );
}

function MemoryViewer({ memory }: { memory: MemoryResponse }) {
  if (memory.memories.length === 0) return <div className="text-gray-500">No memory retrieved.</div>;
  return (
    <div className="space-y-2">
      {memory.memories.map(m => (
        <div key={m.id} className="border border-gray-200 bg-white p-2 rounded">
          <div className="flex justify-between items-center mb-1">
            <span className="font-bold text-blue-700">{m.key}</span>
            <span className={"px-1 py-0.5 rounded text-[10px] " + 
              (m.state === 'CONFIRMED' ? 'bg-green-100 text-green-800' : 
               m.state === 'OBSERVED' ? 'bg-blue-100 text-blue-800' : 'bg-yellow-100 text-yellow-800')}
            >
              {m.state}
            </span>
          </div>
          <div className="text-gray-800 break-all">{JSON.stringify(m.value)}</div>
          {m.contradictions_json && m.contradictions_json.length > 0 && (
            <div className="mt-1 text-[10px] text-red-600 bg-red-50 p-1 rounded">
              Contradictions: {m.contradictions_json.length}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}

function ActionViewer({ action }: { action: any }) {
  if (!action) return null;
  return (
    <div className="space-y-2">
      <div className="bg-yellow-50 border border-yellow-200 p-2 rounded text-yellow-800">
        <span className="font-bold text-[10px] uppercase block mb-1">Internal Provenance (Preference Basis)</span>
        {action.preference_basis ? JSON.stringify(action.preference_basis, null, 2) : 'None'}
      </div>
      <div className="bg-white border border-gray-200 p-2 rounded">
        <pre className="text-gray-700">{JSON.stringify({...action, preference_basis: undefined}, null, 2)}</pre>
      </div>
    </div>
  );
}
