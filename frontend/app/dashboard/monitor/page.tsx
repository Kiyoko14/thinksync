"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiClient, ServerMetrics, Alert, Server } from "@/lib/api";
import { Activity, RefreshCw } from "lucide-react";

function MetricBar({ label, value }: { label: string; value: number }) {
  const pct = Math.min(100, Math.max(0, value));
  const color =
    pct >= 80 ? "bg-red-500" : pct >= 60 ? "bg-yellow-500" : "bg-green-500";
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm text-slate-400">{label}</span>
        <span
          className={`text-sm font-semibold ${
            pct >= 80 ? "text-red-400" : pct >= 60 ? "text-yellow-400" : "text-green-400"
          }`}
        >
          {pct.toFixed(1)}%
        </span>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

const METRIC_OPTIONS = ["cpu_percent", "mem_percent", "disk_percent"];
const TIME_OPTIONS = [15, 30, 60, 120, 360];

export default function MonitorPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  const [servers, setServers] = useState<Server[]>([]);
  const [selectedServer, setSelectedServer] = useState("");
  const [metrics, setMetrics] = useState<ServerMetrics | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [history, setHistory] = useState<ServerMetrics[]>([]);
  const [historyMetric, setHistoryMetric] = useState("cpu_percent");
  const [historyMinutes, setHistoryMinutes] = useState(30);

  const [collecting, setCollecting] = useState(false);
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [pageLoading, setPageLoading] = useState(true);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  const loadServers = useCallback(async () => {
    try {
      const data = await apiClient.getServers();
      setServers(data);
      if (data.length > 0 && !selectedServer) setSelectedServer(data[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load servers");
    } finally {
      setPageLoading(false);
    }
  }, [selectedServer]);

  useEffect(() => {
    if (user) void loadServers();
  }, [user, loadServers]);

  const fetchMetrics = useCallback(async (serverId: string) => {
    if (!serverId) return;
    try {
      const [m, a] = await Promise.all([
        apiClient.monitor.getLatest(serverId),
        apiClient.monitor.getAlerts(serverId),
      ]);
      setMetrics(m);
      setAlerts(a);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch metrics");
    }
  }, []);

  useEffect(() => {
    if (selectedServer) void fetchMetrics(selectedServer);
  }, [selectedServer, fetchMetrics]);

  useEffect(() => {
    if (autoRefresh && selectedServer) {
      intervalRef.current = setInterval(() => {
        void fetchMetrics(selectedServer);
      }, 30000);
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [autoRefresh, selectedServer, fetchMetrics]);

  const handleCollect = async () => {
    if (!selectedServer) return;
    setCollecting(true);
    try {
      const m = await apiClient.monitor.collectMetrics(selectedServer);
      setMetrics(m);
      setSuccess("Metrics collected");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Collection failed");
    } finally {
      setCollecting(false);
    }
  };

  const handleLoadHistory = async () => {
    if (!selectedServer) return;
    try {
      const data = await apiClient.monitor.getHistory(selectedServer, historyMetric, historyMinutes);
      setHistory(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load history");
    }
  };

  const formatUptime = (seconds?: number) => {
    if (!seconds) return "—";
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${d}d ${h}h ${m}m`;
  };

  if (loading || pageLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        Loading monitor...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Activity className="h-6 w-6 text-indigo-400" />
          <h1 className="text-xl font-semibold text-slate-100">Server Monitor</h1>
        </div>
        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
              className="accent-indigo-500"
            />
            Auto-refresh (30s)
          </label>
          <button
            onClick={() => void handleCollect()}
            disabled={!selectedServer || collecting}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60 inline-flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${collecting ? "animate-spin" : ""}`} />
            Collect Metrics
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-500/10 border border-green-500/30 text-green-400 px-4 py-3 rounded-lg text-sm">
          {success}
        </div>
      )}

      {/* Server selector */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
        <label className="text-sm text-slate-400 block mb-2">Select Server</label>
        <select
          value={selectedServer}
          onChange={(e) => setSelectedServer(e.target.value)}
          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full max-w-sm"
        >
          <option value="">Choose a server…</option>
          {servers.map((s) => (
            <option key={s.id} value={s.id}>
              {s.name}
            </option>
          ))}
        </select>
      </div>

      {metrics && (
        <>
          {/* Current metrics */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-semibold text-slate-100">Current Metrics</h2>
              <span className="text-xs text-slate-500">
                {new Date(metrics.collected_at).toLocaleString()}
              </span>
            </div>
            <div className="space-y-4">
              <MetricBar label="CPU Usage" value={metrics.cpu_percent} />
              <MetricBar label="Memory Usage" value={metrics.mem_percent} />
              <MetricBar label="Disk Usage" value={metrics.disk_percent} />
            </div>
            <div className="mt-4 grid grid-cols-2 gap-4 pt-4 border-t border-slate-700/50">
              <div>
                <p className="text-xs text-slate-500 mb-0.5">Load (1m)</p>
                <p className="text-sm text-slate-100">{metrics.load_1m?.toFixed(2) ?? "—"}</p>
              </div>
              <div>
                <p className="text-xs text-slate-500 mb-0.5">Uptime</p>
                <p className="text-sm text-slate-100">{formatUptime(metrics.uptime_seconds)}</p>
              </div>
            </div>
          </div>

          {/* Alerts */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
            <h2 className="text-base font-semibold text-slate-100 mb-4">Alerts</h2>
            {alerts.length === 0 ? (
              <p className="text-sm text-slate-500">No active alerts.</p>
            ) : (
              <div className="space-y-2">
                {alerts.map((a, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3"
                  >
                    <div>
                      <span className="text-sm font-medium text-red-400">{a.metric}</span>
                      <span className="text-xs text-slate-400 ml-2">
                        value: {a.value.toFixed(1)} / threshold: {a.threshold}
                      </span>
                    </div>
                    <span className="text-xs text-slate-500">
                      {new Date(a.ts * 1000).toLocaleString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* History */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
            <h2 className="text-base font-semibold text-slate-100 mb-4">Metric History</h2>
            <div className="flex items-center gap-3 mb-4">
              <select
                value={historyMetric}
                onChange={(e) => setHistoryMetric(e.target.value)}
                className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {METRIC_OPTIONS.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
              <select
                value={historyMinutes}
                onChange={(e) => setHistoryMinutes(parseInt(e.target.value))}
                className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                {TIME_OPTIONS.map((t) => (
                  <option key={t} value={t}>
                    Last {t}m
                  </option>
                ))}
              </select>
              <button
                onClick={() => void handleLoadHistory()}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
              >
                Load
              </button>
            </div>
            {history.length === 0 ? (
              <p className="text-sm text-slate-500">No history data. Click Load to fetch.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-slate-500 border-b border-slate-700">
                      <th className="pb-2 pr-4">Timestamp</th>
                      <th className="pb-2 pr-4">CPU%</th>
                      <th className="pb-2 pr-4">Mem%</th>
                      <th className="pb-2">Disk%</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-700/50">
                    {history.map((h, i) => (
                      <tr key={i} className="text-slate-300">
                        <td className="py-2 pr-4 text-xs text-slate-400">
                          {new Date(h.collected_at).toLocaleString()}
                        </td>
                        <td className="py-2 pr-4">{h.cpu_percent.toFixed(1)}</td>
                        <td className="py-2 pr-4">{h.mem_percent.toFixed(1)}</td>
                        <td className="py-2">{h.disk_percent.toFixed(1)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {!metrics && selectedServer && (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center">
          <Activity className="h-10 w-10 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">No metrics yet. Click &ldquo;Collect Metrics&rdquo; to start.</p>
        </div>
      )}
    </div>
  );
}
