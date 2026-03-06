"use client";

import { useState, useEffect } from "react";
import { apiClient, Database, Server } from "@/lib/api";

export default function DatabasesPage() {
  const [databases, setDatabases] = useState<Database[]>([]);
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedServer, setSelectedServer] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [dbData, serverData] = await Promise.all([
        apiClient.getDatabases(),
        apiClient.getServers(),
      ]);
      setDatabases(dbData);
      setServers(serverData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDatabase = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError("");

    try {
      const newDb = await apiClient.createDatabase({
        server_id: selectedServer || undefined,
      });
      setDatabases([...databases, newDb]);
      setSuccess("Database created successfully");
      setShowForm(false);
      setSelectedServer("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create database");
    } finally {
      setCreating(false);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setSuccess("Copied to clipboard");
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-white">Databases</h1>
          <p className="text-slate-400 mt-2">Manage your database instances</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 transition"
        >
          {showForm ? "Cancel" : "+ New Database"}
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
          <h2 className="text-xl font-bold text-white mb-6">Create New Database</h2>
          <form onSubmit={handleCreateDatabase} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Associated Server (Optional)
              </label>
              <select
                value={selectedServer}
                onChange={(e) => setSelectedServer(e.target.value)}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Global Database</option>
                {servers.map((server) => (
                  <option key={server.id} value={server.id}>
                    {server.name} ({server.host})
                  </option>
                ))}
              </select>
              <p className="text-xs text-slate-400 mt-2">
                Select a server if this database is for a specific deployment
              </p>
            </div>
            <div className="flex space-x-4">
              <button
                type="submit"
                disabled={creating}
                className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 transition disabled:opacity-50"
              >
                {creating ? "Creating..." : "Create Database"}
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

      {/* Databases List */}
      {loading ? (
        <div className="text-center py-12">
          <p className="text-slate-400">Loading databases...</p>
        </div>
      ) : databases.length === 0 ? (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-12 text-center">
          <p className="text-slate-400 mb-4">No databases yet</p>
          <button
            onClick={() => setShowForm(true)}
            className="inline-block px-6 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg transition"
          >
            Create your first database
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6">
          {databases.map((db) => (
            <div
              key={db.id}
              className="bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition"
            >
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h3 className="text-lg font-bold text-white">
                    Database {db.project_id.substring(0, 8)}
                  </h3>
                  <p className="text-slate-400 text-sm mt-1">
                    Project ID: {db.project_id}
                  </p>
                </div>
                <span className="px-3 py-1 bg-green-500/20 border border-green-500/50 rounded-full text-green-400 text-xs font-medium">
                  Active
                </span>
              </div>

              <div className="space-y-3 mb-4">
                <div>
                  <p className="text-xs text-slate-400 mb-1">Database URL</p>
                  <div className="flex items-center space-x-2">
                    <code className="flex-1 px-3 py-2 bg-slate-700 rounded text-slate-300 text-xs overflow-x-auto">
                      {db.db_url}
                    </code>
                    <button
                      onClick={() => copyToClipboard(db.db_url)}
                      className="px-3 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded transition"
                      title="Copy to clipboard"
                    >
                      📋
                    </button>
                  </div>
                </div>
              </div>

              <div className="flex space-x-2 text-xs text-slate-400">
                <span>🔗 {db.server_id ? "Server-specific" : "Global"}</span>
                <span>•</span>
                <span>
                  Created {new Date(db.created_at).toLocaleDateString()}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
