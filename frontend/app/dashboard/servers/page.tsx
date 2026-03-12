"use client";

import { useState, useEffect } from "react";
import { apiClient, Server } from "@/lib/api";

type ServerFormData = {
  name: string;
  host: string;
  ssh_user: string;
  ssh_port: number;
  ssh_auth_method: "private_key" | "password";
  ssh_key: string;
  ssh_password: string;
};

export default function ServersPage() {
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<ServerFormData>({
    name: "",
    host: "",
    ssh_user: "",
    ssh_port: 22,
    ssh_auth_method: "private_key",
    ssh_key: "",
    ssh_password: "",
  });
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    try {
      const payload = {
        name: formData.name,
        host: formData.host,
        ssh_user: formData.ssh_user,
        ssh_port: formData.ssh_port,
        ssh_auth_method: formData.ssh_auth_method,
        ssh_key: formData.ssh_auth_method === "private_key" ? formData.ssh_key : undefined,
        ssh_password: formData.ssh_auth_method === "password" ? formData.ssh_password : undefined,
      };

      if (editingId) {
        await apiClient.updateServer(editingId, payload);
        setSuccess("Server updated successfully");
      } else {
        await apiClient.createServer(payload);
        setSuccess("Server created successfully");
      }

      setFormData({
        name: "",
        host: "",
        ssh_user: "",
        ssh_port: 22,
        ssh_auth_method: "private_key",
        ssh_key: "",
        ssh_password: "",
      });
      setShowForm(false);
      setEditingId(null);
      await loadServers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operation failed");
    }
  };

  const handleDelete = async (serverId: string) => {
    if (confirm("Are you sure you want to delete this server?")) {
      try {
        await apiClient.deleteServer(serverId);
        setSuccess("Server deleted successfully");
        await loadServers();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Delete failed");
      }
    }
  };

  const handleEdit = (server: Server) => {
    setFormData({
      name: server.name,
      host: server.host,
      ssh_user: server.ssh_user,
      ssh_port: server.ssh_port,
      ssh_auth_method: server.ssh_auth_method ?? "private_key",
      ssh_key: "",
      ssh_password: "",
    });
    setEditingId(server.id);
    setShowForm(true);
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingId(null);
    setFormData({
      name: "",
      host: "",
      ssh_user: "",
      ssh_port: 22,
      ssh_auth_method: "private_key",
      ssh_key: "",
      ssh_password: "",
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-white">Servers</h1>
          <p className="text-slate-400 mt-2">Manage your SSH servers</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 transition"
        >
          {showForm ? "Cancel" : "+ New Server"}
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

      {/* Form */}
      {showForm && (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <h2 className="text-xl font-bold text-white mb-6">
            {editingId ? "Edit Server" : "Add New Server"}
          </h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Server Name
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  required
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Host Address
                </label>
                <input
                  type="text"
                  value={formData.host}
                  onChange={(e) =>
                    setFormData({ ...formData, host: e.target.value })
                  }
                  placeholder="192.168.1.100"
                  required
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  SSH User
                </label>
                <input
                  type="text"
                  value={formData.ssh_user}
                  onChange={(e) =>
                    setFormData({ ...formData, ssh_user: e.target.value })
                  }
                  placeholder="ubuntu"
                  required
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  SSH Port
                </label>
                <input
                  type="number"
                  value={formData.ssh_port}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      ssh_port: parseInt(e.target.value),
                    })
                  }
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                SSH Authentication
              </label>
              <div className="grid grid-cols-2 gap-2 mb-4">
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, ssh_auth_method: "private_key", ssh_password: "" })}
                  className={`px-4 py-2 rounded-lg border text-sm transition ${
                    formData.ssh_auth_method === "private_key"
                      ? "border-blue-500 bg-blue-500/20 text-blue-300"
                      : "border-slate-600 bg-slate-700 text-slate-300"
                  }`}
                >
                  Private Key
                </button>
                <button
                  type="button"
                  onClick={() => setFormData({ ...formData, ssh_auth_method: "password", ssh_key: "" })}
                  className={`px-4 py-2 rounded-lg border text-sm transition ${
                    formData.ssh_auth_method === "password"
                      ? "border-blue-500 bg-blue-500/20 text-blue-300"
                      : "border-slate-600 bg-slate-700 text-slate-300"
                  }`}
                >
                  Password
                </button>
              </div>

              {formData.ssh_auth_method === "private_key" ? (
                <textarea
                  value={formData.ssh_key}
                  onChange={(e) => setFormData({ ...formData, ssh_key: e.target.value })}
                  placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
                  required
                  rows={6}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                />
              ) : (
                <input
                  type="password"
                  value={formData.ssh_password}
                  onChange={(e) => setFormData({ ...formData, ssh_password: e.target.value })}
                  placeholder="SSH password"
                  required
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              )}
            </div>
            <div className="flex space-x-4">
              <button
                type="submit"
                className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 transition"
              >
                {editingId ? "Update Server" : "Create Server"}
              </button>
              <button
                type="button"
                onClick={handleCancel}
                className="px-6 py-2 bg-slate-700 hover:bg-slate-600 text-white font-semibold rounded-lg transition"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Servers List */}
      {loading ? (
        <div className="text-center py-12">
          <p className="text-slate-400">Loading servers...</p>
        </div>
      ) : servers.length === 0 ? (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-12 text-center">
          <p className="text-slate-400 mb-4">No servers configured yet</p>
          <button
            onClick={() => setShowForm(true)}
            className="inline-block px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition"
          >
            Add your first server
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {servers.map((server) => (
            <div
              key={server.id}
              className="bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold text-white">{server.name}</h3>
                  <p className="text-slate-400 text-sm">{server.host}</p>
                </div>
                <span className="px-3 py-1 bg-green-500/20 border border-green-500/50 rounded-full text-green-400 text-xs font-medium">
                  Active
                </span>
              </div>
              <div className="space-y-2 mb-4 text-sm text-slate-400">
                <p>👤 User: {server.ssh_user}</p>
                <p>🔌 Port: {server.ssh_port}</p>
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => handleEdit(server)}
                  className="flex-1 px-3 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition text-sm font-medium"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(server.id)}
                  className="flex-1 px-3 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition text-sm font-medium border border-red-500/50"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
