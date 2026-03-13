"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { apiClient, Secret, Server } from "@/lib/api";
import { KeyRound, Plus, Trash2, AlertTriangle } from "lucide-react";

export default function SecretsPage() {
  const router = useRouter();
  const { user, loading } = useAuth();

  const [servers, setServers] = useState<Server[]>([]);
  const [selectedServer, setSelectedServer] = useState("");
  const [secrets, setSecrets] = useState<Secret[]>([]);
  const [pageLoading, setPageLoading] = useState(true);
  const [secretsLoading, setSecretsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [newName, setNewName] = useState("");
  const [newValue, setNewValue] = useState("");
  const [saving, setSaving] = useState(false);

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

  const loadSecrets = useCallback(async (serverId: string) => {
    if (!serverId) return;
    setSecretsLoading(true);
    try {
      const data = await apiClient.secrets.list(serverId);
      setSecrets(data);
      setError("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load secrets");
    } finally {
      setSecretsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedServer) void loadSecrets(selectedServer);
  }, [selectedServer, loadSecrets]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedServer || !newName.trim() || !newValue) return;
    setSaving(true);
    setError("");
    try {
      await apiClient.secrets.upsert(selectedServer, newName.trim(), newValue);
      setSuccess(`Secret "${newName.trim()}" saved`);
      setNewName("");
      setNewValue("");
      await loadSecrets(selectedServer);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save secret");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete secret "${name}"? This cannot be undone.`)) return;
    try {
      await apiClient.secrets.delete(selectedServer, name);
      setSuccess(`Secret "${name}" deleted`);
      setSecrets((prev) => prev.filter((s) => s.name !== name));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete secret");
    }
  };

  if (loading || pageLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        Loading secrets...
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <KeyRound className="h-6 w-6 text-indigo-400" />
        <h1 className="text-xl font-semibold text-slate-100">Secrets</h1>
      </div>

      {/* Warning banner */}
      <div className="flex items-start gap-3 bg-yellow-500/10 border border-yellow-500/30 text-yellow-300 rounded-xl px-4 py-3">
        <AlertTriangle className="h-5 w-5 flex-shrink-0 mt-0.5" />
        <div className="text-sm">
          <p className="font-medium">Secrets are stored encrypted and never displayed after saving.</p>
          <p className="mt-0.5 text-yellow-400/80">
            Once a secret is created you can only overwrite or delete it. Values are never shown again.
          </p>
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

      {selectedServer && (
        <>
          {/* Add secret form */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
            <h2 className="text-base font-semibold text-slate-100 mb-4 flex items-center gap-2">
              <Plus className="h-4 w-4" />
              Add Secret
            </h2>
            <form onSubmit={(e) => void handleAdd(e)} className="flex items-end gap-3">
              <div className="flex-1">
                <label className="text-xs text-slate-500 block mb-1">Name</label>
                <input
                  required
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="MY_SECRET_KEY"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 font-mono text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <div className="flex-1">
                <label className="text-xs text-slate-500 block mb-1">Value</label>
                <input
                  required
                  type="password"
                  value={newValue}
                  onChange={(e) => setNewValue(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                />
              </div>
              <button
                type="submit"
                disabled={saving || !newName.trim() || !newValue}
                className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition disabled:opacity-60 whitespace-nowrap"
              >
                {saving ? "Saving…" : "Save Secret"}
              </button>
            </form>
          </div>

          {/* Secrets list */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6">
            <h2 className="text-base font-semibold text-slate-100 mb-4">
              Stored Secrets{" "}
              <span className="text-xs font-normal text-slate-500">({secrets.length})</span>
            </h2>
            {secretsLoading ? (
              <p className="text-sm text-slate-400">Loading…</p>
            ) : secrets.length === 0 ? (
              <p className="text-sm text-slate-500">No secrets for this server yet.</p>
            ) : (
              <div className="space-y-2">
                {secrets.map((s) => (
                  <div
                    key={s.name}
                    className="flex items-center justify-between bg-slate-900/60 rounded-lg px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-mono text-slate-100">{s.name}</p>
                      <p className="text-xs text-slate-500 mt-0.5">
                        Created {new Date(s.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <button
                      onClick={() => void handleDelete(s.name)}
                      className="bg-red-600/20 hover:bg-red-600/30 text-red-400 border border-red-500/30 px-3 py-1.5 rounded-lg text-sm transition inline-flex items-center gap-1.5"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                      Delete
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
