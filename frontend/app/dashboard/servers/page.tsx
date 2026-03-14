"use client";

import Link from "next/link";
import { type ComponentType, useEffect, useMemo, useState } from "react";
import { Activity, Pencil, Plus, Server, ShieldCheck, Trash2 } from "lucide-react";
import { apiClient, Server as ServerType } from "@/lib/api";

type ServerFormData = {
  name: string;
  host: string;
  ssh_user: string;
  ssh_port: number;
  ssh_auth_method: "private_key" | "password";
  ssh_key: string;
  ssh_password: string;
};

const emptyForm: ServerFormData = {
  name: "",
  host: "",
  ssh_user: "ubuntu",
  ssh_port: 22,
  ssh_auth_method: "private_key",
  ssh_key: "",
  ssh_password: "",
};

export default function ServersPage() {
  const [servers, setServers] = useState<ServerType[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [checkingId, setCheckingId] = useState<string | null>(null);
  const [formData, setFormData] = useState<ServerFormData>(emptyForm);
  const [statusMap, setStatusMap] = useState<Record<string, "online" | "offline" | "unknown">>({});
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    void loadServers();
  }, []);

  async function loadServers() {
    try {
      const data = await apiClient.getServers();
      setServers(data);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load servers");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSuccess("");

    const payload = {
      name: formData.name,
      host: formData.host,
      ssh_user: formData.ssh_user,
      ssh_port: formData.ssh_port,
      ssh_auth_method: formData.ssh_auth_method,
      ssh_key: formData.ssh_auth_method === "private_key" ? formData.ssh_key : undefined,
      ssh_password: formData.ssh_auth_method === "password" ? formData.ssh_password : undefined,
    };

    try {
      if (editingId) {
        await apiClient.updateServer(editingId, payload);
        setSuccess("Server updated successfully");
      } else {
        await apiClient.createServer(payload);
        setSuccess("Server created successfully");
      }

      setShowForm(false);
      setEditingId(null);
      setFormData(emptyForm);
      await loadServers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Operation failed");
    }
  }

  async function handleDelete(serverId: string) {
    if (!confirm("Delete this server and related chats?")) return;
    try {
      await apiClient.deleteServer(serverId);
      setServers((prev) => prev.filter((s) => s.id !== serverId));
      setSuccess("Server deleted");
      setStatusMap((prev) => {
        const copy = { ...prev };
        delete copy[serverId];
        return copy;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  function startEdit(server: ServerType) {
    setEditingId(server.id);
    setFormData({
      name: server.name,
      host: server.host,
      ssh_user: server.ssh_user,
      ssh_port: server.ssh_port,
      ssh_auth_method: server.ssh_auth_method ?? "private_key",
      ssh_key: "",
      ssh_password: "",
    });
    setShowForm(true);
  }

  function resetForm() {
    setShowForm(false);
    setEditingId(null);
    setFormData(emptyForm);
  }

  async function checkStatus(serverId: string) {
    setCheckingId(serverId);
    try {
      const response = await apiClient.getServerStatus(serverId);
      const status = String((response as { status?: string }).status ?? "unknown");
      setStatusMap((prev) => ({
        ...prev,
        [serverId]: status === "online" ? "online" : status === "offline" ? "offline" : "unknown",
      }));
    } catch {
      setStatusMap((prev) => ({ ...prev, [serverId]: "offline" }));
    } finally {
      setCheckingId(null);
    }
  }

  const metrics = useMemo(() => {
    const keyAuth = servers.filter((s) => (s.ssh_auth_method ?? "private_key") === "private_key").length;
    const passwordAuth = servers.length - keyAuth;
    const online = Object.values(statusMap).filter((v) => v === "online").length;
    return { total: servers.length, keyAuth, passwordAuth, online };
  }, [servers, statusMap]);

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/75 p-6 sm:p-8">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Infrastructure</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Servers</h1>
            <p className="mt-3 text-sm text-slate-300">SSH server inventory, authentication setup, and health checks in one place.</p>
          </div>
          {!showForm && (
            <button
              onClick={() => setShowForm(true)}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:from-cyan-400 hover:to-blue-500"
            >
              <Plus className="h-4 w-4" />
              Add Server
            </button>
          )}
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard title="Total" value={metrics.total} icon={Server} />
        <StatCard title="Online Checked" value={metrics.online} icon={Activity} />
        <StatCard title="Private Key" value={metrics.keyAuth} icon={ShieldCheck} />
        <StatCard title="Password" value={metrics.passwordAuth} icon={ShieldCheck} />
      </section>

      {error && <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</div>}
      {success && <div className="rounded-xl border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">{success}</div>}

      {showForm && (
        <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
          <h2 className="text-lg font-semibold text-white">{editingId ? "Edit Server" : "Create Server"}</h2>
          <form onSubmit={handleSubmit} className="mt-4 space-y-4">
            <div className="grid gap-4 md:grid-cols-2">
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="Server name"
                required
                className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-cyan-400"
              />
              <input
                type="text"
                value={formData.host}
                onChange={(e) => setFormData((prev) => ({ ...prev, host: e.target.value }))}
                placeholder="Host (IP or DNS)"
                required
                className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-cyan-400"
              />
              <input
                type="text"
                value={formData.ssh_user}
                onChange={(e) => setFormData((prev) => ({ ...prev, ssh_user: e.target.value }))}
                placeholder="SSH user"
                required
                className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-cyan-400"
              />
              <input
                type="number"
                min={1}
                max={65535}
                value={formData.ssh_port}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    ssh_port: Number(e.target.value) || 22,
                  }))
                }
                placeholder="SSH port"
                required
                className="rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-cyan-400"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() =>
                  setFormData((prev) => ({
                    ...prev,
                    ssh_auth_method: "private_key",
                    ssh_password: "",
                  }))
                }
                className={`rounded-xl border px-4 py-2 text-sm ${
                  formData.ssh_auth_method === "private_key"
                    ? "border-cyan-400 bg-cyan-500/15 text-cyan-100"
                    : "border-slate-700 bg-slate-800 text-slate-300"
                }`}
              >
                Private Key
              </button>
              <button
                type="button"
                onClick={() =>
                  setFormData((prev) => ({
                    ...prev,
                    ssh_auth_method: "password",
                    ssh_key: "",
                  }))
                }
                className={`rounded-xl border px-4 py-2 text-sm ${
                  formData.ssh_auth_method === "password"
                    ? "border-cyan-400 bg-cyan-500/15 text-cyan-100"
                    : "border-slate-700 bg-slate-800 text-slate-300"
                }`}
              >
                Password
              </button>
            </div>

            {formData.ssh_auth_method === "private_key" ? (
              <textarea
                value={formData.ssh_key}
                onChange={(e) => setFormData((prev) => ({ ...prev, ssh_key: e.target.value }))}
                placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
                rows={6}
                required
                className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 font-mono text-sm text-white outline-none focus:border-cyan-400"
              />
            ) : (
              <input
                type="password"
                value={formData.ssh_password}
                onChange={(e) => setFormData((prev) => ({ ...prev, ssh_password: e.target.value }))}
                placeholder="SSH password"
                required
                className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-cyan-400"
              />
            )}

            <div className="flex gap-3">
              <button
                type="submit"
                className="rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-3 text-sm font-semibold text-white"
              >
                {editingId ? "Update Server" : "Create Server"}
              </button>
              <button
                type="button"
                onClick={resetForm}
                className="rounded-xl border border-slate-700 px-5 py-3 text-sm text-slate-200"
              >
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
        {loading ? (
          <p className="text-slate-400">Loading servers...</p>
        ) : servers.length === 0 ? (
          <p className="text-slate-400">No servers configured yet.</p>
        ) : (
          <div className="space-y-3">
            {servers.map((server) => {
              const status = statusMap[server.id] ?? "unknown";
              return (
                <div
                  key={server.id}
                  className="flex flex-col gap-3 rounded-xl border border-slate-800 bg-slate-950/45 p-4 md:flex-row md:items-center md:justify-between"
                >
                  <div>
                    <p className="font-semibold text-white">{server.name}</p>
                    <p className="mt-1 text-sm text-slate-400">{server.host}:{server.ssh_port} as {server.ssh_user}</p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`rounded-full border px-3 py-1 text-xs font-medium ${
                        status === "online"
                          ? "border-emerald-400/40 bg-emerald-500/15 text-emerald-200"
                          : status === "offline"
                            ? "border-rose-400/40 bg-rose-500/15 text-rose-200"
                            : "border-slate-500/40 bg-slate-500/15 text-slate-300"
                      }`}
                    >
                      {status}
                    </span>
                    <button
                      onClick={() => void checkStatus(server.id)}
                      disabled={checkingId === server.id}
                      className="rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200 transition hover:border-cyan-300/40 disabled:opacity-50"
                    >
                      {checkingId === server.id ? "Checking..." : "Check Status"}
                    </button>
                    <Link
                      href={`/dashboard/server/${server.id}`}
                      className="inline-flex items-center gap-1 rounded-lg border border-cyan-400/40 bg-cyan-500/10 px-3 py-1.5 text-xs text-cyan-100"
                    >
                      Open
                    </Link>
                    <button
                      onClick={() => startEdit(server)}
                      className="inline-flex items-center gap-1 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-200"
                    >
                      <Pencil className="h-3.5 w-3.5" /> Edit
                    </button>
                    <button
                      onClick={() => void handleDelete(server.id)}
                      className="inline-flex items-center gap-1 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-1.5 text-xs text-rose-200"
                    >
                      <Trash2 className="h-3.5 w-3.5" /> Delete
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

function StatCard({
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
