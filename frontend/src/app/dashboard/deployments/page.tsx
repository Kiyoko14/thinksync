"use client";

import { useState, useEffect } from "react";
import { apiClient, Server } from "@/lib/api";

interface Deployment {
  id: string;
  server_id: string;
  code: string;
  language: string;
  deployment_type: string;
  status: string;
  created_at: string;
}

export default function DeploymentsPage() {
  const [servers, setServers] = useState<Server[]>([]);
  const [deployments, setDeployments] = useState<Deployment[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [deploying, setDeploying] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [formData, setFormData] = useState({
    server_id: "",
    code: "",
    language: "python",
    deployment_type: "docker",
  });

  useEffect(() => {
    loadServers();
  }, []);

  const loadServers = async () => {
    try {
      const data = await apiClient.getServers();
      setServers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load servers");
    } finally {
      setLoading(false);
    }
  };

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

      // Add to deployments list
      const newDeployment: Deployment = {
        id: result.deployment_id || Date.now().toString(),
        server_id: formData.server_id,
        code: formData.code,
        language: formData.language,
        deployment_type: formData.deployment_type,
        status: "pending",
        created_at: new Date().toISOString(),
      };

      setDeployments([newDeployment, ...deployments]);
      setSuccess(result.message || "Deployment created successfully");
      setFormData({
        server_id: "",
        code: "",
        language: "python",
        deployment_type: "docker",
      });
      setShowForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Deployment failed");
    } finally {
      setDeploying(false);
    }
  };

  const getServerName = (serverId: string) => {
    return servers.find((s) => s.id === serverId)?.name || "Unknown";
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "pending":
        return "bg-yellow-500/20 text-yellow-400 border-yellow-500/50";
      case "success":
        return "bg-green-500/20 text-green-400 border-green-500/50";
      case "failed":
        return "bg-red-500/20 text-red-400 border-red-500/50";
      default:
        return "bg-slate-500/20 text-slate-400 border-slate-500/50";
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-white">Deployments</h1>
          <p className="text-slate-400 mt-2">Deploy and manage your applications</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 transition"
        >
          {showForm ? "Cancel" : "🚀 New Deployment"}
        </button>
      </div>

      {/* Messages */}
      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg">
          <p className="text-red-400">{error}</p>
        </div>
      )}
      {success && (
        <div className="p-4 bg-green-500/10 border border-green-500/50 rounded-lg">
          <p className="text-green-400">{success}</p>
        </div>
      )}

      {/* Deployment Form */}
      {showForm && (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <h2 className="text-xl font-bold text-white mb-6">Create New Deployment</h2>
          <form onSubmit={handleDeploy} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Target Server *
                </label>
                <select
                  value={formData.server_id}
                  onChange={(e) =>
                    setFormData({ ...formData, server_id: e.target.value })
                  }
                  required
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
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
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Language
                </label>
                <select
                  value={formData.language}
                  onChange={(e) =>
                    setFormData({ ...formData, language: e.target.value })
                  }
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="python">Python</option>
                  <option value="nodejs">Node.js</option>
                  <option value="go">Go</option>
                  <option value="rust">Rust</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Deployment Type
                </label>
                <select
                  value={formData.deployment_type}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      deployment_type: e.target.value,
                    })
                  }
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="docker">Docker</option>
                  <option value="kubernetes">Kubernetes</option>
                  <option value="bare-metal">Bare Metal</option>
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Code / Configuration *
              </label>
              <textarea
                value={formData.code}
                onChange={(e) =>
                  setFormData({ ...formData, code: e.target.value })
                }
                placeholder="Paste your application code or docker configuration..."
                required
                rows={10}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
              />
            </div>
            <div className="flex space-x-4">
              <button
                type="submit"
                disabled={deploying}
                className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 transition disabled:opacity-50"
              >
                {deploying ? "Deploying..." : "Deploy Code"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white font-semibold rounded-lg transition"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Deployments List */}
      {loading ? (
        <div className="text-center py-12">
          <p className="text-slate-400">Loading...</p>
        </div>
      ) : deployments.length === 0 ? (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-12 text-center">
          <p className="text-slate-400 mb-4">No deployments yet</p>
          <button
            onClick={() => setShowForm(true)}
            className="inline-block px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition"
          >
            Create your first deployment
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {deployments.map((deployment) => (
            <div
              key={deployment.id}
              className="bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-lg font-bold text-white">
                    {getServerName(deployment.server_id)} Deployment
                  </h3>
                  <p className="text-slate-400 text-sm mt-1">
                    {deployment.language} • {deployment.deployment_type}
                  </p>
                </div>
                <span
                  className={`px-3 py-1 border rounded-full text-xs font-medium capitalize ${getStatusColor(
                    deployment.status
                  )}`}
                >
                  {deployment.status}
                </span>
              </div>

              <div className="bg-slate-700/50 rounded p-3 mb-4 max-h-32 overflow-y-auto">
                <p className="text-slate-300 text-xs font-mono whitespace-pre-wrap break-words">
                  {deployment.code.substring(0, 200)}
                  {deployment.code.length > 200 ? "..." : ""}
                </p>
              </div>

              <div className="flex space-x-2 text-xs text-slate-400">
                <span>🕐 {new Date(deployment.created_at).toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
