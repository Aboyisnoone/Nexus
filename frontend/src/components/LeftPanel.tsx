import { useState } from 'react';
import { SCENARIOS } from '../manifest';

interface Props {
  selectedScenario: string;
  onSelectScenario: (id: string) => void;
  onRunLive: () => void;
  onRunReplay: (sourceRunId: string) => void;
  isRunning: boolean;
}

export function LeftPanel({ selectedScenario, onSelectScenario, onRunLive, onRunReplay, isRunning }: Props) {
  const [replayId, setReplayId] = useState('');

  return (
    <div className="w-80 border-r border-gray-300 bg-white flex flex-col h-full overflow-y-auto">
      <div className="p-4 border-b border-gray-300 bg-gray-50">
        <h1 className="text-xl font-bold tracking-tight text-gray-800">NEXUS v0.1</h1>
        <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider mt-1">Developer Debugger</p>
      </div>

      <div className="p-4 flex-1">
        <h2 className="text-sm font-bold text-gray-700 uppercase mb-2">Scenario</h2>
        <select 
          className="w-full border border-gray-300 rounded p-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 bg-white"
          value={selectedScenario}
          onChange={(e) => onSelectScenario(e.target.value)}
          disabled={isRunning}
        >
          {SCENARIOS.map(s => (
            <option key={s.id} value={s.id}>{s.label}</option>
          ))}
        </select>
        
        <p className="text-sm text-gray-600 mt-2 mb-6 h-12">
          {SCENARIOS.find(s => s.id === selectedScenario)?.description}
        </p>

        <h2 className="text-sm font-bold text-gray-700 uppercase mb-2 border-t border-gray-200 pt-4">Execution</h2>
        <button 
          onClick={onRunLive}
          disabled={isRunning}
          className="w-full bg-blue-600 text-white font-medium py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50 mb-6"
        >
          {isRunning ? 'RUNNING...' : 'RUN LIVE'}
        </button>

        <h2 className="text-sm font-bold text-gray-700 uppercase mb-2 border-t border-gray-200 pt-4">Replay</h2>
        <input 
          type="text" 
          placeholder="Source Run ID"
          className="w-full border border-gray-300 rounded p-2 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 mb-2 font-mono text-xs"
          value={replayId}
          onChange={(e) => setReplayId(e.target.value)}
          disabled={isRunning}
        />
        <button 
          onClick={() => onRunReplay(replayId)}
          disabled={isRunning || !replayId.trim()}
          className="w-full bg-gray-200 text-gray-800 font-medium py-2 rounded text-sm hover:bg-gray-300 disabled:opacity-50"
        >
          {isRunning ? 'RUNNING...' : 'REPLAY'}
        </button>
      </div>
    </div>
  );
}
