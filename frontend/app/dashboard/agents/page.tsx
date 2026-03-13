"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiClient, AgentStats, Task } from "@/lib/api";
import { Bot, RefreshCw, Search } from "lucide-react";

const KNOWN_AGENTS = ["planner", "action_agent", "debugger", "auditor", "autonomous"];

export default function AgentsPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  const [stats, setStats] = useState<AgentStats>({});
  const [tasks, setTasks] = useState<Task[]>([]);
  const [memory, setMemory] = useState<Record<string, unknown> | null>(null);
  const [taskIdInput, setTaskIdInput] = useState("");
  const [inspecting, setInspecting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [pageLoading, setPageLoading] = useState(true);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  const loadAll = useCallback(async () => {
    try {
      const [s, t] = await Promise.all([
        apiClient.agents.getStats(),
        apiClient.tasks.list(),
      ]);
      setStats(s);
      setTasks(t);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load agent data");
    } finally {
      setPageLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (user) void loadAll();
  }, [user, loadAll]);

  // Auto-refresh every 60s
  useEffect(() => {
    intervalRef.current = setInterval(() => {
      void loadAll();
    }, 60000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [loadAll]);

  const handleRefresh = () => {
    setRefreshing(true);
    void loadAll();
  };

  const handleInspect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!taskIdInput.trim()) return;
    setInspecting(true);
    setMemory(null);
    try {
      const data = await apiClient.agents.getMemory(taskIdInput.trim());
      setMemory(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fetch memory");
    } finally {
      setInspecting(false);
    }
  };

  const agentKeys = Object.keys(stats).length > 0 ? Object.keys(stats) : KNOWN_AGENTS;

  const taskStateColor = (state: string) => {
    const map: Record<string, string> = {
      pending: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
      running: "bg-blue-500/20 text-blue-400 border-blue-500/40",
      done: "bg-green-500/20 text-green-400 border-green-500/40",
      failed: "bg-red-500/20 text-red-400 border-red-500/40",
    };
    return map[state] ?? "bg-slate-500/20 text-slate-400 border-slate-500/40";
  };

  if (loading || pageLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        Loading agents...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Bot className="h-6 w-6 text-indigo-400" />
          <h1 className="text-xl font-semibold text-slate-100">AI Agents</h1>
        </div>
        <button
          onClick={handleRefresh}
          disabled={refreshing}
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60 inline-flex items-center gap-2"
        >
          <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
          Refresh Stats
        </button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 text-red-400 px-4 py-3 rounded-lg text-sm">
          {error}
        </div>
      )}

      {/* Agent stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {agentKeys.map((agent) => {
          const counters = stats[agent] ?? {};
          return (
            <div
              key={agent}
              className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6"
            >
              <div className="flex items-center gap-2 mb-3">
                <Bot className="h-4 w-4 text-indigo-400" />
                <h3 className="font-semibold text-slate-100 capitalize">{agent.replace(/_/g, " ")}</h3>
              </div>
              {Object.keys(counters).length === 0 ? (
                <p className="text-xs text-slate-500">No data</p>
              ) : (
                <dl className="space-y-1.5">
                  {Object.entries(counters).map(([key, val]) => (
                    <div key={key} className="flex items-center justify-between">
                      <dt className="text-xs text-slate-400 capitalize">{key.replace(/_/g, " ")}</dt>
                      <dd className="text-xs font-semibold text-slate-100">{val}</dd>
                    </div>
                  ))}
                </dl>
              )}
            </div>
          );
        })}
      </div>

      {/* Working memory inspector */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
        <h2 className="text-base font-semibold text-slate-100 mb-4">Working Memory Inspector</h2>
        <form onSubmit={(e) => void handleInspect(e)} className="flex items-center gap-3 mb-4">
          <input
            value={taskIdInput}
            onChange={(e) => setTaskIdInput(e.target.value)}
            placeholder="Task ID…"
            className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            type="submit"
            disabled={inspecting || !taskIdInput.trim()}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60 inline-flex items-center gap-2"
          >
            <Search className="h-4 w-4" />
            {inspecting ? "Inspecting…" : "Inspect"}
          </button>
        </form>
        {memory !== null && (
          <div className="bg-slate-950 border border-slate-700 rounded-lg p-4 overflow-x-auto">
            <pre className="text-xs text-green-300 font-mono whitespace-pre-wrap">
              {JSON.stringify(memory, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Tasks table */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
        <h2 className="text-base font-semibold text-slate-100 mb-4">
          Tasks{" "}
          <span className="text-xs font-normal text-slate-500">({tasks.length})</span>
        </h2>
        {tasks.length === 0 ? (
          <p className="text-sm text-slate-500">No tasks found.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-slate-500 border-b border-slate-700">
                  <th className="pb-2 pr-4">ID</th>
                  <th className="pb-2 pr-4">Chat</th>
                  <th className="pb-2 pr-4">State</th>
                  <th className="pb-2 pr-4">Step</th>
                  <th className="pb-2 pr-4">Attempts</th>
                  <th className="pb-2">Created</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                {tasks.map((t) => (
                  <tr key={t.id} className="text-slate-300">
                    <td className="py-2.5 pr-4 font-mono text-xs text-slate-400">{t.id.slice(0, 12)}…</td>
                    <td className="py-2.5 pr-4 font-mono text-xs text-slate-400">{t.chat_id.slice(0, 12)}…</td>
                    <td className="py-2.5 pr-4">
                      <span
                        className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium border ${taskStateColor(t.state)}`}
                      >
                        {t.state}
                      </span>
                    </td>
                    <td className="py-2.5 pr-4 text-xs text-slate-400">{t.step ?? "—"}</td>
                    <td className="py-2.5 pr-4 text-xs text-slate-400">{t.attempts ?? 0}</td>
                    <td className="py-2.5 text-xs text-slate-400">
                      {new Date(t.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
