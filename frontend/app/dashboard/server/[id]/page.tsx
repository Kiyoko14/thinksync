"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { apiClient, Chat, Server } from "@/lib/api";

export default function ServerDetailPage() {
  const params = useParams<{ id: string }>();
  const serverId = params.id;

  const [server, setServer] = useState<Server | null>(null);
  const [chats, setChats] = useState<Chat[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [chatName, setChatName] = useState("");
  const [error, setError] = useState("");

  const loadData = useCallback(async () => {
    if (!serverId) return;
    try {
      const [serverData, chatsData] = await Promise.all([
        apiClient.getServer(serverId),
        apiClient.getChats(serverId),
      ]);
      setServer(serverData);
      setChats(chatsData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ma'lumot yuklanmadi");
    }
  }, [serverId]);

  useEffect(() => {
    const timer = setTimeout(() => {
      void loadData();
    }, 0);

    return () => clearTimeout(timer);
  }, [loadData]);

  const handleCreateChat = async (event: FormEvent) => {
    event.preventDefault();
    if (!serverId) return;

    try {
      await apiClient.createChat({ server_id: serverId, name: chatName });
      setChatName("");
      setShowModal(false);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat yaratilmadi");
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Server Workspace</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">{server?.name ?? "Server"}</h1>
            <p className="mt-2 text-sm text-slate-400">{server?.host}</p>
          </div>
          <button
            onClick={() => setShowModal(true)}
            className="rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-5 py-3 text-sm font-semibold text-white"
          >
            + Chat qo&apos;shish
          </button>
        </div>
      </section>

      {error && <p className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">{error}</p>}

      <section className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
        <h2 className="text-xl font-semibold text-white">Chatlar ro&apos;yxati</h2>
        {chats.length === 0 ? (
          <p className="mt-3 text-sm text-slate-400">Hozircha chat mavjud emas.</p>
        ) : (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            {chats.map((chat) => (
              <Link
                key={chat.id}
                href={`/dashboard/server/${serverId}/chat/${chat.id}`}
                className="rounded-xl border border-slate-700 bg-slate-800/70 p-4 transition hover:border-blue-400"
              >
                <p className="font-semibold text-white">{chat.name}</p>
                <p className="mt-2 line-clamp-2 text-sm text-slate-400">Oxirgi xabarni chat ichida ko&apos;rasiz.</p>
              </Link>
            ))}
          </div>
        )}
      </section>

      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
          <div className="w-full max-w-md rounded-2xl border border-slate-700 bg-slate-900 p-6">
            <h3 className="text-xl font-semibold text-white">Chat yaratish</h3>
            <form onSubmit={handleCreateChat} className="mt-5 space-y-4">
              <input
                required
                value={chatName}
                onChange={(event) => setChatName(event.target.value)}
                placeholder="Chat nomi"
                className="w-full rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-blue-500"
              />
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
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
