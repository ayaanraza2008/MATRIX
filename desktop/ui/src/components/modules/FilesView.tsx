import React, { useState, useEffect } from 'react';
import { FolderGit2, FileText, Folder, RefreshCw, Eye } from 'lucide-react';

interface FileItem {
  name: string;
  path: string;
  is_dir: boolean;
  size_bytes: number;
  modified_at: number;
}

export const FilesView: React.FC = () => {
  const [files, setFiles] = useState<FileItem[]>([]);
  const [selectedContent, setSelectedContent] = useState<string | null>(null);
  const [selectedName, setSelectedName] = useState<string | null>(null);
  const [newFilename, setNewFilename] = useState('');
  const [newContent, setNewContent] = useState('');
  const [loading, setLoading] = useState(false);

  const fetchFiles = async () => {
    try {
      const res = await fetch('/api/v1/files');
      if (res.ok) {
        const data = await res.json();
        setFiles(data);
      }
    } catch {}
  };

  useEffect(() => {
    fetchFiles();
  }, []);

  const handleReadFile = async (filename: string) => {
    try {
      const res = await fetch('/api/v1/files/read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ relative_path: filename }),
      });
      if (res.ok) {
        const data = await res.json();
        setSelectedContent(data.content);
        setSelectedName(data.filename);
      }
    } catch {}
  };

  const handleCreateFile = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFilename.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/v1/files/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: newFilename, content: newContent }),
      });
      if (res.ok) {
        setNewFilename('');
        setNewContent('');
        fetchFiles();
      }
    } catch {}
    finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-6 matrix-grid-bg">
      <div className="flex items-center justify-between border-b border-matrix-border/50 pb-4">
        <div>
          <h1 className="text-sm font-mono uppercase font-bold text-slate-100 flex items-center gap-2">
            <FolderGit2 className="w-4 h-4 text-matrix-cyan" />
            FILE & DOCUMENT INTELLIGENCE
          </h1>
          <p className="text-xs font-mono text-matrix-textMuted mt-0.5">
            Protected Storage: D:\matrix_data · PDF/DOCX/XLSX/CSV/TXT reader & safe file organization
          </p>
        </div>
        <button
          onClick={fetchFiles}
          className="p-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-300 hover:text-matrix-cyan transition-colors"
          title="Refresh partition"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: File Explorer */}
        <div className="lg:col-span-5 matrix-glass rounded-xl p-4 space-y-3">
          <h2 className="text-xs font-mono uppercase font-bold text-slate-200">
            D:\matrix_data\ DIRECTORY
          </h2>

          <div className="space-y-1 max-h-96 overflow-y-auto">
            {files.map((file) => (
              <div
                key={file.name}
                onClick={() => !file.is_dir && handleReadFile(file.name)}
                className={`p-2 rounded-lg flex items-center justify-between font-mono text-xs cursor-pointer transition-colors ${
                  file.name === selectedName
                    ? 'bg-matrix-cyan/20 border border-matrix-cyan/40 text-matrix-cyan'
                    : 'hover:bg-slate-900/60 text-slate-300'
                }`}
              >
                <div className="flex items-center gap-2 truncate">
                  {file.is_dir ? (
                    <Folder className="w-4 h-4 text-matrix-amber flex-shrink-0" />
                  ) : (
                    <FileText className="w-4 h-4 text-matrix-cyan flex-shrink-0" />
                  )}
                  <span className="truncate">{file.name}</span>
                </div>
                <span className="text-[10px] text-slate-500 flex-shrink-0">
                  {file.is_dir ? 'DIR' : `${(file.size_bytes / 1024).toFixed(1)} KB`}
                </span>
              </div>
            ))}
          </div>

          {/* Quick Create File Form */}
          <form onSubmit={handleCreateFile} className="pt-3 border-t border-slate-800 space-y-2">
            <span className="text-[11px] font-mono text-slate-400">Create Document in D:\matrix_data</span>
            <input
              type="text"
              value={newFilename}
              onChange={(e) => setNewFilename(e.target.value)}
              placeholder="e.g. mission_log.txt"
              className="w-full h-8 px-2.5 rounded bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 focus:outline-none focus:border-matrix-cyan"
            />
            <textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              placeholder="Content..."
              rows={2}
              className="w-full p-2 rounded bg-slate-950 border border-slate-800 text-xs font-mono text-slate-200 focus:outline-none focus:border-matrix-cyan"
            />
            <button
              type="submit"
              disabled={!newFilename.trim() || loading}
              className="w-full py-1.5 rounded bg-matrix-cyan text-slate-950 font-mono font-bold text-xs hover:bg-cyan-300 disabled:opacity-40 transition-colors"
            >
              SAVE DOCUMENT
            </button>
          </form>
        </div>

        {/* Right: Document Viewer */}
        <div className="lg:col-span-7 matrix-glass rounded-xl p-5 flex flex-col">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 mb-3">
            <span className="text-xs font-mono font-bold text-slate-200 flex items-center gap-2">
              <Eye className="w-4 h-4 text-matrix-cyan" />
              {selectedName ? `PREVIEW: ${selectedName}` : 'DOCUMENT VIEWER'}
            </span>
          </div>

          <div className="flex-1 min-h-[300px] p-4 rounded-lg bg-slate-950/80 border border-slate-900 font-mono text-xs text-slate-300 whitespace-pre-wrap overflow-y-auto">
            {selectedContent ?? 'Select a file from the left explorer to view its contents.'}
          </div>
        </div>
      </div>
    </div>
  );
};
