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

  const copyToClipboard = (text?: string) => {
    if (!text) return;
    navigator.clipboard.writeText(text);
    setSuccess("Copied to clipboard");
  };

  return (
    <div className="space-y-6">

      {/* Header */}

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-white">Databases</h1>
          <p className="text-slate-400 mt-2">
            Manage your database instances
          </p>
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
          <h2 className="text-xl font-bold text-white mb-6">
            Create New Database
          </h2>

          <form onSubmit={handleCreateDatabase} className="space-y-4">

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Associated Server (Optional)
              </label>

              <select
                value={selectedServer}
                onChange={(e) => setSelectedServer(e.target.value)}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
              >
                <option value="">Global Database</option>

                {servers.map((server) => (
                  <option key={server.id} value={server.id}>
                    {server.name} ({server.host ?? "unknown"})
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={creating}
              className="px-6 py-2 bg-blue-600 text-white rounded-lg"
            >
              {creating ? "Creating..." : "Create Database"}
            </button>

          </form>
        </div>
      )}

      {/* Databases */}

      {loading ? (
        <p className="text-slate-400">Loading databases...</p>
      ) : databases.length === 0 ? (
        <p className="text-slate-400">No databases yet</p>
      ) : (
        <div className="grid gap-6">

          {databases.map((db) => (

            <div
              key={db.id}
              className="bg-slate-800 border border-slate-700 rounded-xl p-6"
            >

              <h3 className="text-lg font-bold text-white">
                Database {(db.project_id ?? "unknown").substring(0, 8)}
              </h3>

              <p className="text-slate-400 text-sm mt-1">
                Project ID: {db.project_id ?? "unknown"}
              </p>

              <div className="mt-3 flex items-center gap-2">

                <code className="px-3 py-2 bg-slate-700 rounded text-xs text-slate-300">
                  {db.db_url ?? "Not available"}
                </code>

                <button
                  onClick={() => copyToClipboard(db.db_url)}
                  className="px-3 py-2 bg-slate-700 rounded"
                >
                  📋
                </button>

              </div>

              <p className="text-xs text-slate-400 mt-3">
                Created{" "}
                {db.created_at
                  ? new Date(db.created_at).toLocaleDateString()
                  : "Unknown"}
              </p>

            </div>

          ))}

        </div>
      )}

    </div>
  );
}
