"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { apiClient, Server } from "@/lib/api";

type NewServerForm = {
  name: string;
  host: string;
  ssh_user: string;
  ssh_port: number;
};

const initialForm: NewServerForm = {
  name: "",
  host: "",
  ssh_user: "ubuntu",
  ssh_port: 22,
};

export default function DashboardPage() {
  const [servers, setServers] = useState<Server[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState<NewServerForm>(initialForm);
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

  const handleCreateServer = async (event: FormEvent) => {
    event.preventDefault();
    setError("");

    try {
      await apiClient.createServer({ ...form, ssh_key: "local-managed-key" });
      setForm(initialForm);
      setModalOpen(false);
      await loadServers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Server yaratilmadi");
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/75 p-6 sm:p-8">
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-center">
          <div>
            <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Control Center</p>
            <h1 className="mt-2 text-3xl font-semibold">Servers Dashboard</h1>
            <p className="mt-3 max-w-2xl text-sm text-slate-300">
              Barcha serverlaringiz shu yerda. Har bir server ichida chatlar bo'ladi va AI real filesystem holatini
              tekshirgan holda buyruq bajaradi.
            </p>
          </div>
          <button
            onClick={() => setModalOpen(true)}
            className="rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-5 py-3 text-sm font-semibold text-white transition hover:from-blue-500 hover:to-cyan-400"
          >
            + Server qo'shish
          </button>
        </div>
      </section>

      {error && <p className="rounded-xl border border-rose-400/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</p>}

      <section>
        {loading ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-10 text-center text-slate-300">Yuklanmoqda...</div>
        ) : servers.length === 0 ? (
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-10 text-center">
            <h2 className="text-xl font-semibold text-white">Server topilmadi</h2>
            <p className="mt-2 text-sm text-slate-400">Birinci serverni qo'shing va AI chatni boshlang.</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {servers.map((server) => (
              <article key={server.id} className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="text-lg font-semibold text-white">{server.name}</h3>
                    <p className="mt-1 text-sm text-slate-400">{server.host}</p>
                  </div>
                  <span className="rounded-full border border-emerald-400/40 bg-emerald-500/15 px-3 py-1 text-xs text-emerald-300">Online</span>
                </div>

                <div className="mt-5 space-y-1 text-sm text-slate-300">
                  <p>SSH User: {server.ssh_user}</p>
                  <p>SSH Port: {server.ssh_port}</p>
                </div>

                <Link
                  href={`/dashboard/server/${server.id}`}
                  className="mt-5 inline-flex w-full items-center justify-center rounded-xl border border-slate-700 px-4 py-2 text-sm text-slate-100 transition hover:border-blue-400 hover:bg-slate-800"
                >
                  Serverga kirish
                </Link>
              </article>
            ))}
          </div>
        )}
      </section>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-900 p-6">
            <h2 className="text-xl font-semibold">Yangi server qo'shish</h2>
            <form onSubmit={handleCreateServer} className="mt-5 space-y-4">
              <input
                required
                value={form.name}
                onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
                placeholder="Server nomi"
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

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="flex-1 rounded-xl border border-slate-700 px-4 py-3 text-sm text-slate-200"
                >
                  Bekor qilish
                </button>
                <button
                  type="submit"
                  className="flex-1 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-4 py-3 text-sm font-semibold text-white"
                >
                  Saqlash
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
