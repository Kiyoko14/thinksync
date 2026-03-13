"use client";

import { type ComponentType, useEffect, useMemo, useState } from "react";
import { Copy, Database, Plus, Server } from "lucide-react";
import { apiClient, Database as DatabaseType, Server as ServerType } from "@/lib/api";

export default function DatabasesPage() {
  const [databases, setDatabases] = useState<DatabaseType[]>([]);
  const [servers, setServers] = useState<ServerType[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [selectedServer, setSelectedServer] = useState("");
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    void loadData();
  }, []);

  async function loadData() {
    try {
      const [dbData, serverData] = await Promise.all([
        apiClient.getDatabases(),
        apiClient.getServers(),
      ]);
      setDatabases(dbData);
      setServers(serverData);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  }

  async function handleCreateDatabase(e: React.FormEvent) {
    e.preventDefault();
    setCreating(true);
    setError("");
    setSuccess("");
    try {
      const created = await apiClient.createDatabase({
        server_id: selectedServer || undefined,
      });
      setDatabases((prev) => [created, ...prev]);
      setSuccess("Database created successfully");
      setSelectedServer("");
      setShowForm(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create database");
    } finally {
      setCreating(false);
    }
  }

  async function copyToClipboard(text?: string) {
    if (!text) return;
    await navigator.clipboard.writeText(text);
    setSuccess("Connection URL copied");
  }

  const metrics = useMemo(() => {
    const attached = databases.filter((d) => Boolean(d.server_id)).length;
    const global = databases.length - attached;
    return { total: databases.length, attached, global };
  }, [databases]);

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/75 p-6 sm:p-8">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Data Layer</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Databases</h1>
            <p className="mt-3 text-sm text-slate-300">Manage provisioned database projects and attach them to specific servers.</p>
          </div>
          <button
            onClick={() => setShowForm((prev) => !prev)}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:from-cyan-400 hover:to-blue-500"
          >
            <Plus className="h-4 w-4" />
            {showForm ? "Close Form" : "New Database"}
          </button>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-3">
        <MetricCard title="Total" value={metrics.total} icon={Database} />
        <MetricCard title="Attached" value={metrics.attached} icon={Server} />
        <MetricCard title="Global" value={metrics.global} icon={Database} />
      </section>

      {error && <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
      {success && <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">{success}</div>}

      {showForm && (
        <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <h2 className="text-lg font-semibold text-white">Create Database</h2>
          <form onSubmit={handleCreateDatabase} className="mt-4 flex flex-col gap-4 md:flex-row md:items-end">
            <div className="flex-1">
              <label className="mb-2 block text-sm text-slate-400">Attach to server (optional)</label>
              <select
                value={selectedServer}
                onChange={(e) => setSelectedServer(e.target.value)}
                className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-cyan-400"
              >
                <option value="">Global database</option>
                {servers.map((server) => (
                  <option key={server.id} value={server.id}>
                    {server.name} ({server.host})
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              disabled={creating}
              className="rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-3 text-sm font-semibold text-white disabled:opacity-60"
            >
              {creating ? "Creating..." : "Create"}
            </button>
          </form>
        </section>
      )}

      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
        {loading ? (
          <p className="text-slate-400">Loading databases...</p>
        ) : databases.length === 0 ? (
          <p className="text-slate-400">No databases created yet.</p>
        ) : (
          <div className="space-y-3">
            {databases.map((db) => {
              const serverName = db.server_id
                ? servers.find((s) => s.id === db.server_id)?.name ?? "Unknown server"
                : "Global";

              return (
                <div
                  key={db.id}
                  className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-950/45 p-4 md:flex-row md:items-center md:justify-between"
                >
                  <div className="min-w-0">
                    <p className="font-semibold text-white">Project {String(db.project_id ?? "unknown").slice(0, 8)}</p>
                    <p className="mt-1 text-sm text-slate-400">Attached: {serverName}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Created {db.created_at ? new Date(db.created_at).toLocaleString() : "-"}
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <code className="max-w-[460px] truncate rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-xs text-slate-200">
                      {db.db_url ?? "No URL"}
                    </code>
                    <button
                      onClick={() => void copyToClipboard(db.db_url)}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-200"
                    >
                      <Copy className="h-3.5 w-3.5" /> Copy
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}

function MetricCard({
  title,
  value,
  icon: Icon,
}: {
  title: string;
  value: number;
  icon: ComponentType<{ className?: string }>;
}) {
  return (
    <article className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
      <div className="mb-3 inline-flex rounded-lg border border-cyan-400/30 bg-cyan-500/10 p-2">
        <Icon className="h-4 w-4 text-cyan-200" />
      </div>
      <p className="text-xs uppercase tracking-[0.14em] text-slate-400">{title}</p>
      <p className="mt-2 text-3xl font-semibold text-white">{value}</p>
    </article>
  );
}
