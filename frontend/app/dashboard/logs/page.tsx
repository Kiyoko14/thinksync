"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiClient, Server, getToken } from "@/lib/api";
import { ScrollText, Copy, Trash2, Radio } from "lucide-react";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ??
  (process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:8000"
    : "https://api.thinksync.art");
const LINE_LIMITS = [50, 100, 200, 500];

export default function LogsPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  const [servers, setServers] = useState<Server[]>([]);
  const [selectedServer, setSelectedServer] = useState("");
  const [logFile, setLogFile] = useState("/var/log/syslog");
  const [lineLimit, setLineLimit] = useState(100);
  const [lines, setLines] = useState<string[]>([]);
  const [agentEvents, setAgentEvents] = useState<string[]>([]);
  const [liveStreaming, setLiveStreaming] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);
  const [error, setError] = useState("");

  const logBoxRef = useRef<HTMLDivElement>(null);
  const logEsRef = useRef<EventSource | null>(null);
  const agentEsRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  const loadServers = useCallback(async () => {
    try {
      const data = await apiClient.getServers();
      setServers(data);
      if (data.length > 0) setSelectedServer(data[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load servers");
    } finally {
      setPageLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) void loadServers();
  }, [user, loadServers]);

  // Auto-scroll log box
  useEffect(() => {
    if (logBoxRef.current) {
      logBoxRef.current.scrollTop = logBoxRef.current.scrollHeight;
    }
  }, [lines]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      logEsRef.current?.close();
      agentEsRef.current?.close();
    };
  }, []);

  const handleLoadHistory = async () => {
    if (!selectedServer) return;
    try {
      const data = await apiClient.logs.getHistory(selectedServer, lineLimit);
      setLines(data.lines ?? []);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load logs");
    }
  };

  const startLiveStream = () => {
    if (!selectedServer) return;
    const token = getToken();
    const url = `${API_BASE}/logs/stream/${selectedServer}?log_file=${encodeURIComponent(logFile)}&lines=${lineLimit}${token ? `&token=${encodeURIComponent(token)}` : ""}`;

    logEsRef.current?.close();
    const es = new EventSource(url);
    logEsRef.current = es;

    es.onmessage = (ev) => {
      setLines((prev) => [...prev, ev.data]);
    };
    es.onerror = () => {
      setError("Live stream disconnected");
      setLiveStreaming(false);
      es.close();
    };
    setLiveStreaming(true);
  };

  const stopLiveStream = () => {
    logEsRef.current?.close();
    logEsRef.current = null;
    setLiveStreaming(false);
  };

  const toggleLiveStream = () => {
    if (liveStreaming) {
      stopLiveStream();
    } else {
      startLiveStream();
    }
  };

  const startAgentEvents = () => {
    const token = getToken();
    const url = `${API_BASE}/logs/events${token ? `?token=${encodeURIComponent(token)}` : ""}`;
    agentEsRef.current?.close();
    const es = new EventSource(url);
    agentEsRef.current = es;
    es.onmessage = (ev) => {
      setAgentEvents((prev) => [...prev.slice(-199), ev.data]);
    };
    es.onerror = () => {
      es.close();
    };
  };

  useEffect(() => {
    if (user) startAgentEvents();
    return () => agentEsRef.current?.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  const handleCopy = () => {
    void navigator.clipboard.writeText(lines.join("\n"));
  };

  if (loading || pageLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        Loading logs...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <ScrollText className="h-6 w-6 text-indigo-400" />
        <h1 className="text-xl font-semibold text-slate-100">Log Viewer</h1>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Controls */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <div>
            <label className="text-xs text-slate-500 block mb-1">Server</label>
            <select
              value={selectedServer}
              onChange={(e) => setSelectedServer(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">Select server…</option>
              {servers.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-500 block mb-1">Log File</label>
            <input
              value={logFile}
              onChange={(e) => setLogFile(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
              placeholder="/var/log/syslog"
            />
          </div>
          <div>
            <label className="text-xs text-slate-500 block mb-1">Lines</label>
            <select
              value={lineLimit}
              onChange={(e) => setLineLimit(parseInt(e.target.value))}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              {LINE_LIMITS.map((l) => (
                <option key={l} value={l}>
                  {l} lines
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-end gap-2">
            <button
              onClick={() => void handleLoadHistory()}
              disabled={!selectedServer}
              className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60"
            >
              Load History
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={toggleLiveStream}
            disabled={!selectedServer}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60 ${
              liveStreaming
                ? "bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30"
                : "bg-green-600/20 hover:bg-green-600/30 text-green-400 border border-green-500/30"
            }`}
          >
            <Radio className="h-4 w-4" />
            {liveStreaming ? "Stop Stream" : "Live Stream"}
          </button>
          {liveStreaming && (
            <span className="flex items-center gap-1.5 text-xs text-green-400">
              <span className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
              Streaming
            </span>
          )}
        </div>
      </div>

      {/* Log output */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-slate-100">
            Output{" "}
            <span className="text-xs font-normal text-slate-500">({lines.length} lines)</span>
          </h2>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              disabled={lines.length === 0}
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 px-3 py-1.5 rounded-lg transition disabled:opacity-40"
            >
              <Copy className="h-3.5 w-3.5" />
              Copy All
            </button>
            <button
              onClick={() => setLines([])}
              disabled={lines.length === 0}
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 px-3 py-1.5 rounded-lg transition disabled:opacity-40"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Clear
            </button>
          </div>
        </div>
        <div
          ref={logBoxRef}
          className="bg-slate-950 border border-slate-700 rounded-lg p-4 h-96 overflow-y-auto font-mono text-xs text-slate-300 space-y-0.5"
        >
          {lines.length === 0 ? (
            <span className="text-slate-600">No log output. Load history or start live stream.</span>
          ) : (
            lines.map((line, i) => (
              <div key={i} className="flex gap-3">
                <span className="text-slate-600 select-none w-8 text-right flex-shrink-0">
                  {i + 1}
                </span>
                <span className="break-all">{line}</span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Agent events */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-slate-100">
            Agent Events{" "}
            <span className="text-xs font-normal text-slate-500">({agentEvents.length})</span>
          </h2>
          <button
            onClick={() => setAgentEvents([])}
            disabled={agentEvents.length === 0}
            className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white border border-slate-700 hover:border-slate-500 px-3 py-1.5 rounded-lg transition disabled:opacity-40"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Clear
          </button>
        </div>
        <div className="bg-slate-950 border border-slate-700 rounded-lg p-4 h-48 overflow-y-auto font-mono text-xs text-slate-300 space-y-0.5">
          {agentEvents.length === 0 ? (
            <span className="text-slate-600">Waiting for agent events…</span>
          ) : (
            agentEvents.map((ev, i) => (
              <div key={i} className="break-all text-cyan-300/80">
                {ev}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
