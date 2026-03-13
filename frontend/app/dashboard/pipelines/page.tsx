"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import {
  apiClient,
  Pipeline,
  PipelineRun,
  Server,
  Stage,
} from "@/lib/api";
import { GitBranch, Plus, Play, Trash2, Edit2, ChevronDown, ChevronUp, X } from "lucide-react";

type EnvVar = { key: string; value: string };

interface StageForm {
  name: string;
  commands: string;
  on_failure: string;
  timeout: number;
}

interface PipelineForm {
  name: string;
  description: string;
  server_id: string;
  stages: StageForm[];
  env_vars: EnvVar[];
}

const emptyStage = (): StageForm => ({
  name: "",
  commands: "",
  on_failure: "stop",
  timeout: 300,
});

const emptyForm = (): PipelineForm => ({
  name: "",
  description: "",
  server_id: "",
  stages: [emptyStage()],
  env_vars: [],
});

function statusBadge(status: string) {
  const map: Record<string, string> = {
    pending: "bg-yellow-500/20 text-yellow-400 border-yellow-500/40",
    running: "bg-blue-500/20 text-blue-400 border-blue-500/40",
    success: "bg-green-500/20 text-green-400 border-green-500/40",
    failed: "bg-red-500/20 text-red-400 border-red-500/40",
    cancelled: "bg-slate-500/20 text-slate-400 border-slate-500/40",
  };
  const cls = map[status] ?? "bg-slate-500/20 text-slate-400 border-slate-500/40";
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium border ${cls}`}>
      {status}
    </span>
  );
}

export default function PipelinesPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  const [servers, setServers] = useState<Server[]>([]);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [pageLoading, setPageLoading] = useState(true);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<PipelineForm>(emptyForm());
  const [saving, setSaving] = useState(false);

  const [expandedRuns, setExpandedRuns] = useState<Record<string, boolean>>({});
  const [runsMap, setRunsMap] = useState<Record<string, PipelineRun[]>>({});
  const [runsLoading, setRunsLoading] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  const loadData = useCallback(async () => {
    try {
      const [srv, pip] = await Promise.all([
        apiClient.getServers(),
        apiClient.pipelines.list(),
      ]);
      setServers(srv);
      setPipelines(pip);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load data");
    } finally {
      setPageLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) void loadData();
  }, [user, loadData]);

  const openCreate = () => {
    setEditingId(null);
    setForm(emptyForm());
    setShowModal(true);
  };

  const openEdit = (p: Pipeline) => {
    setEditingId(p.id);
    setForm({
      name: p.name,
      description: p.description ?? "",
      server_id: p.server_id,
      stages: p.stages.map((s) => ({
        name: s.name,
        commands: s.commands.join("\n"),
        on_failure: s.on_failure,
        timeout: s.timeout,
      })),
      env_vars: Object.entries(p.environment_variables ?? {}).map(([key, value]) => ({
        key,
        value,
      })),
    });
    setShowModal(true);
  };

  const buildPayload = (): Omit<Pipeline, "id" | "created_at"> => {
    const stages: Stage[] = form.stages.map((s) => ({
      name: s.name,
      commands: s.commands.split("\n").map((c) => c.trim()).filter(Boolean),
      on_failure: s.on_failure,
      timeout: s.timeout,
    }));
    const environment_variables: Record<string, string> = {};
    form.env_vars.forEach(({ key, value }) => {
      if (key.trim()) environment_variables[key.trim()] = value;
    });
    return {
      name: form.name,
      description: form.description || undefined,
      server_id: form.server_id,
      stages,
      environment_variables,
    };
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      if (editingId) {
        const updated = await apiClient.pipelines.update(editingId, buildPayload());
        setPipelines((prev) => prev.map((p) => (p.id === editingId ? updated : p)));
        setSuccess("Pipeline updated");
      } else {
        const created = await apiClient.pipelines.create(buildPayload());
        setPipelines((prev) => [created, ...prev]);
        setSuccess("Pipeline created");
      }
      setShowModal(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm("Delete this pipeline?")) return;
    try {
      await apiClient.pipelines.delete(id);
      setPipelines((prev) => prev.filter((p) => p.id !== id));
      setSuccess("Pipeline deleted");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  };

  const handleRun = async (id: string) => {
    try {
      const run = await apiClient.pipelines.triggerRun(id);
      setSuccess(`Run triggered: ${run.id}`);
      const updated = await apiClient.pipelines.listRuns(id);
      setRunsMap((prev) => ({ ...prev, [id]: updated }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Run failed");
    }
  };

  const toggleRuns = async (pipelineId: string) => {
    const expanded = !expandedRuns[pipelineId];
    setExpandedRuns((prev) => ({ ...prev, [pipelineId]: expanded }));
    if (expanded && !runsMap[pipelineId]) {
      setRunsLoading((prev) => ({ ...prev, [pipelineId]: true }));
      try {
        const runs = await apiClient.pipelines.listRuns(pipelineId);
        setRunsMap((prev) => ({ ...prev, [pipelineId]: runs }));
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load runs");
      } finally {
        setRunsLoading((prev) => ({ ...prev, [pipelineId]: false }));
      }
    }
  };

  const handleCancelRun = async (runId: string, pipelineId: string) => {
    try {
      await apiClient.pipelines.cancelRun(runId);
      const updated = await apiClient.pipelines.listRuns(pipelineId);
      setRunsMap((prev) => ({ ...prev, [pipelineId]: updated }));
      setSuccess("Run cancelled");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Cancel failed");
    }
  };

  const updateStage = (i: number, field: keyof StageForm, value: string | number) => {
    setForm((prev) => {
      const stages = [...prev.stages];
      stages[i] = { ...stages[i], [field]: value };
      return { ...prev, stages };
    });
  };

  const addStage = () => setForm((prev) => ({ ...prev, stages: [...prev.stages, emptyStage()] }));
  const removeStage = (i: number) =>
    setForm((prev) => ({ ...prev, stages: prev.stages.filter((_, idx) => idx !== i) }));

  const addEnvVar = () =>
    setForm((prev) => ({ ...prev, env_vars: [...prev.env_vars, { key: "", value: "" }] }));
  const removeEnvVar = (i: number) =>
    setForm((prev) => ({ ...prev, env_vars: prev.env_vars.filter((_, idx) => idx !== i) }));
  const updateEnvVar = (i: number, field: "key" | "value", val: string) => {
    setForm((prev) => {
      const env_vars = [...prev.env_vars];
      env_vars[i] = { ...env_vars[i], [field]: val };
      return { ...prev, env_vars };
    });
  };

  if (loading || pageLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        Loading pipelines...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <GitBranch className="h-6 w-6 text-indigo-400" />
          <h1 className="text-xl font-semibold text-slate-100">CI/CD Pipelines</h1>
        </div>
        <button
          onClick={openCreate}
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition inline-flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          New Pipeline
        </button>
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

      {/* Pipeline list */}
      {pipelines.length === 0 ? (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center">
          <GitBranch className="h-10 w-10 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400">No pipelines yet. Create your first CI/CD pipeline.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {pipelines.map((p) => (
            <div key={p.id} className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-slate-100">{p.name}</p>
                  {p.description && <p className="text-sm text-slate-400 mt-0.5">{p.description}</p>}
                  <p className="text-xs text-slate-500 mt-1">
                    {p.stages.length} stage{p.stages.length !== 1 ? "s" : ""} ·{" "}
                    {servers.find((s) => s.id === p.server_id)?.name ?? p.server_id} ·{" "}
                    {new Date(p.created_at).toLocaleDateString()}
                  </p>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={() => void handleRun(p.id)}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg text-sm font-medium transition inline-flex items-center gap-1"
                  >
                    <Play className="h-3.5 w-3.5" />
                    Run
                  </button>
                  <button
                    onClick={() => void toggleRuns(p.id)}
                    className="bg-slate-700 hover:bg-slate-600 text-slate-200 px-3 py-1.5 rounded-lg text-sm transition inline-flex items-center gap-1"
                  >
                    {expandedRuns[p.id] ? (
                      <ChevronUp className="h-3.5 w-3.5" />
                    ) : (
                      <ChevronDown className="h-3.5 w-3.5" />
                    )}
                    Runs
                  </button>
                  <button
                    onClick={() => openEdit(p)}
                    className="bg-slate-700 hover:bg-slate-600 text-slate-200 px-3 py-1.5 rounded-lg text-sm transition"
                  >
                    <Edit2 className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => void handleDelete(p.id)}
                    className="bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30 px-3 py-1.5 rounded-lg text-sm transition"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              {/* Runs section */}
              {expandedRuns[p.id] && (
                <div className="mt-4 border-t border-slate-700/50 pt-4">
                  {runsLoading[p.id] ? (
                    <p className="text-sm text-slate-400">Loading runs...</p>
                  ) : !runsMap[p.id] || runsMap[p.id].length === 0 ? (
                    <p className="text-sm text-slate-500">No runs yet.</p>
                  ) : (
                    <div className="space-y-2">
                      {runsMap[p.id].map((run) => (
                        <div
                          key={run.id}
                          className="flex items-center justify-between bg-slate-900/60 rounded-lg px-4 py-2.5"
                        >
                          <div className="flex items-center gap-3">
                            {statusBadge(run.status)}
                            <span className="text-xs font-mono text-slate-300">{run.id.slice(0, 12)}…</span>
                            {run.current_stage && (
                              <span className="text-xs text-slate-500">Stage: {run.current_stage}</span>
                            )}
                            {run.duration_seconds !== undefined && (
                              <span className="text-xs text-slate-500">{run.duration_seconds}s</span>
                            )}
                          </div>
                          <div className="flex items-center gap-2">
                            <span className="text-xs text-slate-500">
                              {new Date(run.created_at).toLocaleString()}
                            </span>
                            {run.status === "running" && (
                              <button
                                onClick={() => void handleCancelRun(run.id, p.id)}
                                className="text-xs text-red-400 hover:text-red-300 border border-red-500/30 px-2 py-0.5 rounded"
                              >
                                Cancel
                              </button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
              <h2 className="text-lg font-semibold text-slate-100">
                {editingId ? "Edit Pipeline" : "New Pipeline"}
              </h2>
              <button onClick={() => setShowModal(false)} className="text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>
            <form onSubmit={(e) => void handleSave(e)} className="p-6 space-y-5">
              {/* Basic info */}
              <div className="space-y-3">
                <div>
                  <label className="text-sm text-slate-400 block mb-1">Name *</label>
                  <input
                    required
                    value={form.name}
                    onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="my-pipeline"
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-400 block mb-1">Description</label>
                  <input
                    value={form.description}
                    onChange={(e) => setForm((p) => ({ ...p, description: e.target.value }))}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    placeholder="Optional description"
                  />
                </div>
                <div>
                  <label className="text-sm text-slate-400 block mb-1">Server *</label>
                  <select
                    required
                    value={form.server_id}
                    onChange={(e) => setForm((p) => ({ ...p, server_id: e.target.value }))}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  >
                    <option value="">Select server…</option>
                    {servers.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Stages */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-300">Stages</label>
                  <button
                    type="button"
                    onClick={addStage}
                    className="text-xs text-indigo-400 hover:text-indigo-300"
                  >
                    + Add stage
                  </button>
                </div>
                <div className="space-y-3">
                  {form.stages.map((stage, i) => (
                    <div key={i} className="bg-slate-800 rounded-lg p-4 space-y-3">
                      <div className="flex items-center gap-2">
                        <input
                          required
                          value={stage.name}
                          onChange={(e) => updateStage(i, "name", e.target.value)}
                          placeholder={`Stage ${i + 1} name`}
                          className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        />
                        {form.stages.length > 1 && (
                          <button
                            type="button"
                            onClick={() => removeStage(i)}
                            className="text-red-400 hover:text-red-300"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                      <textarea
                        value={stage.commands}
                        onChange={(e) => updateStage(i, "commands", e.target.value)}
                        placeholder="Commands (one per line)"
                        rows={3}
                        className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                      <div className="flex items-center gap-3">
                        <div className="flex-1">
                          <label className="text-xs text-slate-500 block mb-1">On failure</label>
                          <select
                            value={stage.on_failure}
                            onChange={(e) => updateStage(i, "on_failure", e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          >
                            <option value="stop">Stop</option>
                            <option value="continue">Continue</option>
                            <option value="retry">Retry</option>
                          </select>
                        </div>
                        <div className="flex-1">
                          <label className="text-xs text-slate-500 block mb-1">Timeout (s)</label>
                          <input
                            type="number"
                            min={1}
                            value={stage.timeout}
                            onChange={(e) => updateStage(i, "timeout", parseInt(e.target.value) || 300)}
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Env vars */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-slate-300">Environment Variables</label>
                  <button
                    type="button"
                    onClick={addEnvVar}
                    className="text-xs text-indigo-400 hover:text-indigo-300"
                  >
                    + Add variable
                  </button>
                </div>
                <div className="space-y-2">
                  {form.env_vars.map((ev, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <input
                        value={ev.key}
                        onChange={(e) => updateEnvVar(i, "key", e.target.value)}
                        placeholder="KEY"
                        className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                      <input
                        value={ev.value}
                        onChange={(e) => updateEnvVar(i, "value", e.target.value)}
                        placeholder="value"
                        className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm font-mono focus:outline-none focus:ring-2 focus:ring-indigo-500"
                      />
                      <button
                        type="button"
                        onClick={() => removeEnvVar(i)}
                        className="text-red-400 hover:text-red-300"
                      >
                        <X className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 border border-slate-600 text-slate-300 hover:text-white px-4 py-2 rounded-lg text-sm transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={saving}
                  className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60"
                >
                  {saving ? "Saving…" : editingId ? "Update" : "Create"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
