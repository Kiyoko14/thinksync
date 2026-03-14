"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { KeyRound, Lock, Network, ServerIcon } from "lucide-react";
import { apiClient, Server } from "@/lib/api";

export default function DashboardPage() {
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

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
          <Link
            href="/dashboard/servers"
            className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:from-cyan-400 hover:to-blue-500"
          >
            Manage Servers
          </Link>
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
    </div>
  );
}
