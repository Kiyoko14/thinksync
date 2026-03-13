"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { KeyRound, Lock, Network, Plus, ServerIcon } from "lucide-react";
import { apiClient, Server } from "@/lib/api";

type NewServerForm = {
  name: string;
  host: string;
  ssh_user: string;
  ssh_port: number;
  ssh_auth_method: "private_key" | "password";
  ssh_key: string;
  ssh_password: string;
};

const initialForm: NewServerForm = {
  name: "",
  host: "",
  ssh_user: "ubuntu",
  ssh_port: 22,
  ssh_auth_method: "private_key",
  ssh_key: "",
  ssh_password: "",
};

export default function DashboardPage() {
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<NewServerForm>(initialForm);
  const [error, setError] = useState("");
  const [creatingServer, setCreatingServer] = useState(false);

  const loadServers = async () => {
    try {
      const data = await apiClient.getServers();
      setServers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Serverlar yuklanmadi");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadServers();
  }, []);

  const handleCreateServer = async (event: FormEvent) => {
    event.preventDefault();
    setError("");
    setCreatingServer(true);

    try {
      await apiClient.createServer({
        name: form.name,
        host: form.host,
        ssh_user: form.ssh_user,
        ssh_port: form.ssh_port,
        ssh_auth_method: form.ssh_auth_method,
        ssh_key: form.ssh_auth_method === "private_key" ? form.ssh_key : undefined,
        ssh_password: form.ssh_auth_method === "password" ? form.ssh_password : undefined,
      });
      setForm(initialForm);
      setModalOpen(false);
      await loadServers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Server yaratilmadi");
    } finally {
      setCreatingServer(false);
    }
  };

  const keyAuthCount = servers.filter((server) => {
    if (server.ssh_auth_method) {
      return server.ssh_auth_method === "private_key";
    }
    return Boolean(server.ssh_key);
  }).length;

  const passwordAuthCount = servers.filter((server) => {
    if (server.ssh_auth_method) {
      return server.ssh_auth_method === "password";
    }
    return false;
  }).length;

  const uniqueHosts = new Set(servers.map((server) => server.host)).size;

  const metrics = [
    {
      label: "Total Servers",
      value: servers.length,
      icon: ServerIcon,
      description: "Configured infrastructure endpoints",
    },
    {
      label: "Private Key Auth",
      value: keyAuthCount,
      icon: KeyRound,
      description: "Servers using private key login",
    },
    {
      label: "Password Auth",
      value: passwordAuthCount,
      icon: Lock,
      description: "Servers using password login",
    },
    {
      label: "Unique Hosts",
      value: uniqueHosts,
      icon: Network,
      description: "Distinct host targets in inventory",
    },
  ];

  const renderSkeleton = () => (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {[1, 2, 3].map((item) => (
        <div key={item} className="animate-pulse rounded-2xl border border-slate-800 bg-slate-900/65 p-5">
          <div className="h-5 w-1/2 rounded bg-slate-800" />
          <div className="mt-3 h-4 w-2/3 rounded bg-slate-800" />
          <div className="mt-7 space-y-2">
            <div className="h-3 w-1/2 rounded bg-slate-800" />
            <div className="h-3 w-1/3 rounded bg-slate-800" />
          </div>
          <div className="mt-5 h-9 w-full rounded bg-slate-800" />
        </div>
      ))}
    </div>
  );

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/75 p-6 sm:p-8">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Control Center</p>
            <h1 className="mt-2 text-3xl font-semibold">Infrastructure Dashboard</h1>
            <p className="mt-3 max-w-2xl text-sm text-slate-300">
              Manage your servers, run AI-driven operations, and keep every deployment path visible from a single workspace.
            </p>
          </div>
          <button
            onClick={() => setModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:from-cyan-400 hover:to-blue-500"
          >
            <Plus className="h-4 w-4" />
            Add Server
          </button>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {metrics.map((metric) => {
          const Icon = metric.icon;
          return (
            <article key={metric.label} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
              <div className="mb-4 inline-flex rounded-lg border border-cyan-400/30 bg-cyan-500/10 p-2">
                <Icon className="h-4 w-4 text-cyan-200" />
              </div>
              <p className="text-xs uppercase tracking-[0.14em] text-slate-400">{metric.label}</p>
              <p className="mt-2 text-3xl font-semibold text-white">{metric.value}</p>
              <p className="mt-2 text-sm text-slate-400">{metric.description}</p>
            </article>
          );
        })}
      </section>

      {error && <p className="rounded-xl border border-rose-400/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</p>}

      <section>
        {loading ? (
          renderSkeleton()
        ) : servers.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-10 text-center">
            <h2 className="text-xl font-semibold text-white">No servers yet</h2>
            <p className="mt-2 text-sm text-slate-400">Create your first server to start infrastructure automation.</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {servers.map((server) => (
              <article
                key={server.id}
                className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 transition duration-300 hover:-translate-y-0.5 hover:border-cyan-300/40"
              >
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-lg font-semibold text-white">{server.name}</h3>
                    <p className="mt-1 text-sm text-slate-400">{server.host}</p>
                  </div>
                  <span className="rounded-full border border-slate-600 bg-slate-800 px-3 py-1 text-xs text-slate-300">Configured</span>
                </div>

                <div className="mt-5 space-y-1 text-sm text-slate-300">
                  <p>SSH User: {server.ssh_user}</p>
                  <p>SSH Port: {server.ssh_port}</p>
                </div>

                <Link
                  href={`/dashboard/server/${server.id}`}
                  className="mt-5 inline-flex w-full items-center justify-center rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-100 transition hover:border-blue-400 hover:bg-slate-800"
                >
                  Open Server
                </Link>
              </article>
            ))}
          </div>
        )}
      </section>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Create New Server</h2>
            <form onSubmit={handleCreateServer} className="mt-5 space-y-4">
              <input
                required
                value={form.name}
                onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
                placeholder="Server name"
                className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm outline-none focus:border-blue-500"
              />
              <input
                required
                value={form.host}
                onChange={(event) => setForm((prev) => ({ ...prev, host: event.target.value }))}
                placeholder="SSH host"
                className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm outline-none focus:border-blue-500"
              />
              <div className="grid gap-3 sm:grid-cols-2">
                <input
                  required
                  value={form.ssh_user}
                  onChange={(event) => setForm((prev) => ({ ...prev, ssh_user: event.target.value }))}
                  placeholder="SSH user"
                  className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm outline-none focus:border-blue-500"
                />
                <input
                  required
                  type="number"
                  value={form.ssh_port}
                  onChange={(event) => setForm((prev) => ({ ...prev, ssh_port: Number(event.target.value) || 22 }))}
                  placeholder="SSH port"
                  className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <p className="mb-2 text-sm text-slate-300">SSH Authentication</p>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setForm((prev) => ({ ...prev, ssh_auth_method: "private_key", ssh_password: "" }))}
                    className={`rounded-xl border px-4 py-2 text-sm transition ${
                      form.ssh_auth_method === "private_key"
                        ? "border-blue-500 bg-blue-500/20 text-blue-300"
                        : "border-slate-700 bg-slate-800 text-slate-300"
                    }`}
                  >
                    Private Key
                  </button>
                  <button
                    type="button"
                    onClick={() => setForm((prev) => ({ ...prev, ssh_auth_method: "password", ssh_key: "" }))}
                    className={`rounded-xl border px-4 py-2 text-sm transition ${
                      form.ssh_auth_method === "password"
                        ? "border-blue-500 bg-blue-500/20 text-blue-300"
                        : "border-slate-700 bg-slate-800 text-slate-300"
                    }`}
                  >
                    Password
                  </button>
                </div>
              </div>

              {form.ssh_auth_method === "private_key" ? (
                <textarea
                  required
                  rows={5}
                  value={form.ssh_key}
                  onChange={(event) => setForm((prev) => ({ ...prev, ssh_key: event.target.value }))}
                  placeholder="-----BEGIN OPENSSH PRIVATE KEY-----"
                  className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 font-mono text-sm outline-none focus:border-blue-500"
                />
              ) : (
                <input
                  required
                  type="password"
                  value={form.ssh_password}
                  onChange={(event) => setForm((prev) => ({ ...prev, ssh_password: event.target.value }))}
                  placeholder="SSH password"
                  className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm outline-none focus:border-blue-500"
                />
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="flex-1 rounded-xl border border-slate-700 px-4 py-3 text-sm text-slate-200"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingServer}
                  className="flex-1 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-4 py-3 text-sm font-semibold text-white"
                >
                  {creatingServer ? "Creating..." : "Save"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
