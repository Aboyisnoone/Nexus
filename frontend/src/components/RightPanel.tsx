
import type { RunResponse } from '../api/types';

interface Props {
  run: RunResponse | null;
}

export function RightPanel({ run }: Props) {
  if (!run) {
    return (
      <div className="w-80 border-l border-gray-300 bg-white p-4 h-full flex flex-col justify-center items-center text-gray-400">
        <p className="text-sm">No run selected</p>
      </div>
    );
  }

  const { evaluation } = run;

  return (
    <div className="w-80 border-l border-gray-300 bg-white h-full overflow-y-auto flex flex-col">
      <div className="p-4 border-b border-gray-300 bg-gray-50">
        <h2 className="text-sm font-bold text-gray-700 uppercase">Evaluation</h2>
      </div>

      {run.status === 'FAILED' && !evaluation && (
        <div className="p-4">
            <div className="bg-red-50 border border-red-200 rounded p-3 text-sm">
                <span className="font-bold text-red-700">EXECUTION FAILED</span>
                {run.error && <pre className="mt-2 text-xs text-red-600 whitespace-pre-wrap">{run.error}</pre>}
            </div>
        </div>
      )}

      {evaluation && (
        <div className="p-4">
          <div className={"p-3 rounded border font-bold text-sm flex items-center justify-between mb-4 " + 
            (evaluation.status === 'PASS' ? 'bg-green-50 text-green-700 border-green-200' : 
             evaluation.status === 'FAIL' ? 'bg-red-50 text-red-700 border-red-200' : 
             'bg-yellow-50 text-yellow-700 border-yellow-200')}
          >
            <span>{evaluation.status}</span>
            <span className="text-xs opacity-75">{evaluation.passed} / {evaluation.total} PASSED</span>
          </div>

          <div className="space-y-3">
            {evaluation.assertions.map((a, i) => (
              <div key={i} className="border border-gray-200 rounded text-xs overflow-hidden">
                <div className={"px-2 py-1 font-semibold flex justify-between " + 
                    (a.passed ? 'bg-green-50 text-green-800 border-b border-green-100' : 'bg-red-50 text-red-800 border-b border-red-100')}
                >
                  <span className="font-mono">{a.assertion.type || 'Assertion'}</span>
                  <span>{a.passed ? '✓' : '✕'}</span>
                </div>
                <div className="p-2 bg-gray-50 font-mono text-[10px] space-y-1">
                  <div><span className="text-gray-500">Expected:</span> {JSON.stringify(a.assertion.expected ?? a.assertion)}</div>
                  <div><span className="text-gray-500">Actual:</span> {JSON.stringify(a.actual)}</div>
                  {a.error && <div className="text-red-600 mt-1">{a.error}</div>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
