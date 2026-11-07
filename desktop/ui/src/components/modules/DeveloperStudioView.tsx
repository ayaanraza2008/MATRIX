import React, { useState } from 'react';
import { Code2, Play, Terminal } from 'lucide-react';

export const DeveloperStudioView: React.FC = () => {
  const [code, setCode] = useState(
    '# MATRIX Python Sandbox\nimport sys\nimport platform\n\nprint(f"Python: {sys.version.split()[0]}")\nprint(f"Platform: {platform.system()} {platform.machine()}")\nprint("MATRIX Development Sandbox Operational!")\n'
  );
  const [output, setOutput] = useState<string | null>(null);
  const [statusText, setStatusText] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleValidate = async () => {
    setLoading(true);
    setStatusText(null);
    try {
      const res = await fetch('/api/v1/developer/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });
      const data = await res.json();
      if (data.valid) {
        setStatusText('✓ Syntax validated cleanly (Valid Python AST).');
      } else {
        setStatusText(`✗ ${data.error}`);
      }
    } catch {
      setStatusText('Validation request failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleExecute = async () => {
    setLoading(true);
    setOutput(null);
    try {
      const res = await fetch('/api/v1/developer/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code }),
      });
      const data = await res.json();
      setOutput(data.stdout || data.stderr || (data.success ? 'Program executed with no output.' : data.error));
      setStatusText(data.success ? `✓ Execution completed in ${data.latency_ms} ms` : '✗ Execution failed');
    } catch {
      setOutput('Execution connection failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleRunTests = async () => {
    setLoading(true);
    setOutput('Running pytest suite on tests/test_foundation.py...');
    try {
      const res = await fetch('/api/v1/developer/run-tests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ test_file: 'tests/test_foundation.py' }),
      });
      const data = await res.json();
      setOutput(data.stdout || data.stderr);
      setStatusText(data.success ? '✓ All Foundation Tests PASSED' : '✗ Tests had failures');
    } catch {
      setOutput('Failed to execute test runner.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <Code2 className="w-4 h-4 text-matrix-cyan" />
            DEVELOPER STUDIO & SANDBOX RUNNER
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Python 3.12 Subprocess Sandbox · AST Syntax Parsing · Live Pytest Harness
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Editor Area */}
        <div className="lg:col-span-7 matrix-glass rounded-xl p-5 space-y-3 flex flex-col">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-slate-200">
              PYTHON SCRIPT RUNNER
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={handleValidate}
                disabled={loading}
                className="px-3 py-1.5 rounded bg-slate-900 border border-slate-700 text-slate-300 hover:text-white font-mono text-xs transition-colors"
              >
                CHECK SYNTAX
              </button>
              <button
                onClick={handleExecute}
                disabled={loading}
                className="px-3 py-1.5 rounded bg-matrix-cyan text-slate-950 hover:bg-cyan-300 font-mono font-bold text-xs transition-colors flex items-center gap-1.5"
              >
                <Play className="w-3.5 h-3.5" />
                <span>EXECUTE</span>
              </button>
            </div>
          </div>

          <textarea
            value={code}
            onChange={(e) => setCode(e.target.value)}
            rows={12}
            className="w-full flex-1 p-3 rounded-lg bg-slate-950 font-mono text-xs text-slate-100 border border-matrix-border/60 focus:outline-none focus:border-matrix-cyan"
            spellCheck={false}
          />

          {statusText && (
            <p className="text-xs font-mono text-matrix-cyan mt-1">{statusText}</p>
          )}
        </div>

        {/* Output Console & Test Runner */}
        <div className="lg:col-span-5 matrix-glass rounded-xl p-5 space-y-4 flex flex-col">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-slate-200 flex items-center gap-1.5">
              <Terminal className="w-4 h-4 text-matrix-cyan" />
              TERMINAL OUTPUT
            </span>
            <button
              onClick={handleRunTests}
              disabled={loading}
              className="px-3 py-1 rounded bg-matrix-blue/20 border border-matrix-blue/40 text-matrix-blue hover:bg-matrix-blue hover:text-white font-mono font-bold text-[11px] transition-colors"
            >
              RUN PYTEST
            </button>
          </div>

          <div className="flex-1 min-h-[220px] p-3 rounded-lg bg-slate-950 font-mono text-xs text-slate-300 whitespace-pre-wrap overflow-y-auto border border-slate-900">
            {output ?? 'Subprocess terminal output will appear here after execution.'}
          </div>
        </div>
      </div>
    </div>
  );
};
