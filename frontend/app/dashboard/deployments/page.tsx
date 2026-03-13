"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiClient, Server, Deployment } from "@/lib/api";
import { Rocket, Plus, Play, Info, X } from "lucide-react";

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending: "bg-yellow-500/20 text-yellow-400 border-yellow-500/50",
    success: "bg-green-500/20 text-green-400 border-green-500/50",
    failed: "bg-red-500/20 text-red-400 border-red-500/50",
    running: "bg-blue-500/20 text-blue-400 border-blue-500/50",
  };
  const cls = map[status] ?? "bg-slate-500/20 text-slate-400 border-slate-500/50";
  return (
    <span className={`inline-flex px-2.5 py-0.5 border rounded-full text-xs font-medium capitalize ${cls}`}>
      {status}
    </span>
  );
}

export default function DeploymentsPage() {
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  const [servers, setServers] = useState<Server[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [statusModal, setStatusModal] = useState<Deployment | null>(null);
  const [statusLoading, setStatusLoading] = useState(false);

  const [formData, setFormData] = useState({
    server_id: "",
    code: "",
    language: "python",
    deployment_type: "docker",
  });

  const pollRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [authLoading, user, router]);

  const loadAll = useCallback(async () => {
    try {
      const [srv, deps] = await Promise.all([
        apiClient.getServers(),
        apiClient.deployments.list(),
      ]);
      setServers(srv);
      setDeployments(deps);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (user) void loadAll();
  }, [user, loadAll]);

  // Poll running/pending deployments every 5s
  useEffect(() => {
    const hasActive = deployments.some(
      (d) => d.status === "pending" || d.status === "running"
    );
    if (hasActive) {
      pollRef.current = setInterval(async () => {
        try {
          const updated = await apiClient.deployments.list();
          setDeployments(updated);
        } catch {
          // silent
        }
      }, 5000);
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [deployments]);

  const handleDeploy = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.server_id || !formData.code) {
      setError("Please fill in all required fields");
      return;
    }
    setDeploying(true);
    setError("");
    try {
      const result = await apiClient.deployCode(formData.server_id, {
        code: formData.code,
        language: formData.language,
        deployment_type: formData.deployment_type,
      });
      const newDeployment: Deployment = {
        id: result.deployment_id || Date.now().toString(),
        server_id: formData.server_id,
        code: formData.code,
        language: formData.language,
        deployment_type: formData.deployment_type,
        status: "pending",
        created_at: new Date().toISOString(),
      };
      setDeployments((prev) => [newDeployment, ...prev]);
      setSuccess(result.message || "Deployment created successfully");
      setFormData({ server_id: "", code: "", language: "python", deployment_type: "docker" });
      setShowForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deployment failed");
    } finally {
      setDeploying(false);
    }
  };

  const handleExecute = async (id: string) => {
    try {
      const result = await apiClient.deployments.execute(id);
      setSuccess(result.message || "Execution triggered");
      const updated = await apiClient.deployments.list();
      setDeployments(updated);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Execute failed");
    }
  };

  const handleViewStatus = async (id: string) => {
    setStatusLoading(true);
    try {
      const dep = await apiClient.deployments.getStatus(id);
      setStatusModal(dep);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch status");
    } finally {
      setStatusLoading(false);
    }
  };

  const getServerName = (serverId: string) =>
    servers.find((s) => s.id === serverId)?.name || "Unknown";

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        Loading deployments...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Rocket className="h-6 w-6 text-indigo-400" />
          <div>
            <h1 className="text-xl font-semibold text-slate-100">Deployments</h1>
            <p className="text-sm text-slate-400">Deploy and manage your applications</p>
          </div>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition inline-flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          {showForm ? "Cancel" : "New Deployment"}
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

      {/* Deployment Form */}
      {showForm && (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
          <h2 className="text-base font-semibold text-slate-100 mb-4">Create New Deployment</h2>
          <form onSubmit={(e) => void handleDeploy(e)} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="text-sm text-slate-400 block mb-1">Target Server *</label>
                <select
                  value={formData.server_id}
                  onChange={(e) => setFormData({ ...formData, server_id: e.target.value })}
                  required
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="">Select a server</option>
                  {servers.map((server) => (
                    <option key={server.id} value={server.id}>
                      {server.name} ({server.host})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm text-slate-400 block mb-1">Language</label>
                <select
                  value={formData.language}
                  onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="python">Python</option>
                  <option value="nodejs">Node.js</option>
                  <option value="go">Go</option>
                  <option value="rust">Rust</option>
                </select>
              </div>
              <div>
                <label className="text-sm text-slate-400 block mb-1">Deployment Type</label>
                <select
                  value={formData.deployment_type}
                  onChange={(e) => setFormData({ ...formData, deployment_type: e.target.value })}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="docker">Docker</option>
                  <option value="kubernetes">Kubernetes</option>
                  <option value="bare-metal">Bare Metal</option>
                </select>
              </div>
            </div>
            <div>
              <label className="text-sm text-slate-400 block mb-1">Code / Configuration *</label>
              <textarea
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
                placeholder="Paste your application code or docker configuration..."
                required
                rows={10}
                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-indigo-500 font-mono text-sm"
              />
            </div>
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={deploying}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60"
              >
                {deploying ? "Deploying…" : "Deploy Code"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="border border-slate-600 text-slate-300 hover:text-white px-6 py-2 rounded-lg text-sm transition"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Deployments List */}
      {deployments.length === 0 ? (
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center">
          <Rocket className="h-10 w-10 text-slate-600 mx-auto mb-3" />
          <p className="text-slate-400 mb-4">No deployments yet</p>
          <button
            onClick={() => setShowForm(true)}
            className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition"
          >
            Create your first deployment
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {deployments.map((deployment) => (
            <div
              key={deployment.id}
              className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="font-semibold text-slate-100">
                      {getServerName(deployment.server_id)} Deployment
                    </h3>
                    <StatusBadge status={deployment.status} />
                  </div>
                  <p className="text-sm text-slate-400">
                    {deployment.language} · {deployment.deployment_type}
                  </p>
                  <div className="mt-2 bg-slate-900/60 rounded-lg p-3 max-h-24 overflow-y-auto">
                    <p className="text-xs font-mono text-slate-400 whitespace-pre-wrap break-words">
                      {deployment.code.substring(0, 200)}
                      {deployment.code.length > 200 ? "…" : ""}
                    </p>
                  </div>
                  <p className="text-xs text-slate-500 mt-2">
                    {new Date(deployment.created_at).toLocaleString()}
                  </p>
                </div>
                <div className="flex flex-col gap-2 flex-shrink-0">
                  {deployment.status === "pending" && (
                    <button
                      onClick={() => void handleExecute(deployment.id)}
                      className="bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg text-sm font-medium transition inline-flex items-center gap-1.5"
                    >
                      <Play className="h-3.5 w-3.5" />
                      Execute
                    </button>
                  )}
                  <button
                    onClick={() => void handleViewStatus(deployment.id)}
                    disabled={statusLoading}
                    className="bg-slate-700 hover:bg-slate-600 text-slate-200 px-3 py-1.5 rounded-lg text-sm transition inline-flex items-center gap-1.5 disabled:opacity-60"
                  >
                    <Info className="h-3.5 w-3.5" />
                    Status
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Status modal */}
      {statusModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-lg">
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700">
              <h2 className="text-base font-semibold text-slate-100">Deployment Status</h2>
              <button onClick={() => setStatusModal(null)} className="text-slate-400 hover:text-white">
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="p-6 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Status</span>
                <StatusBadge status={statusModal.status} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">ID</span>
                <span className="text-sm font-mono text-slate-300">{statusModal.id}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Server</span>
                <span className="text-sm text-slate-300">{getServerName(statusModal.server_id)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Language</span>
                <span className="text-sm text-slate-300">{statusModal.language}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Type</span>
                <span className="text-sm text-slate-300">{statusModal.deployment_type}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-400">Created</span>
                <span className="text-sm text-slate-300">
                  {new Date(statusModal.created_at).toLocaleString()}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

