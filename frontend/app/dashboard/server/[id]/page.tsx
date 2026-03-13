"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { MessageSquare, Plus, Trash2 } from "lucide-react";
import { apiClient, Chat, Server } from "@/lib/api";

export default function ServerDetailPage() {
  const params = useParams<{ id: string }>();
  const serverId = params.id;

  const [server, setServer] = useState<Server | null>(null);
  const [chats, setChats] = useState<Chat[]>([]);
  const [showModal, setShowModal] = useState(false);
  const [chatName, setChatName] = useState("");
  const [creating, setCreating] = useState(false);
  const [deletingChatId, setDeletingChatId] = useState<string | null>(null);
  const [error, setError] = useState("");

  const normalizeName = (name: string) =>
    name
      .trim()
      .replace(/\s+/g, " ")
      .toLowerCase();

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

    const normalized = normalizeName(chatName);
    if (normalized.length < 2) {
      setError("Chat nomi kamida 2 ta belgi bo'lishi kerak");
      return;
    }

    const duplicateExists = chats.some((chat) => normalizeName(chat.name) === normalized);
    if (duplicateExists) {
      setError("Bir xil nomdagi chat ochish mumkin emas");
      return;
    }

    try {
      setCreating(true);
      await apiClient.createChat({ server_id: serverId, name: normalized });
      setChatName("");
      setShowModal(false);
      setError("");
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat yaratilmadi");
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteChat = async (chatId: string) => {
    if (!confirm("Ushbu chat va unga bog'liq barcha ma'lumotlar o'chirilsinmi?")) return;
    try {
      setDeletingChatId(chatId);
      await apiClient.deleteChat(chatId);
      setChats((prev) => prev.filter((chat) => chat.id !== chatId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat o'chirilmadi");
    } finally {
      setDeletingChatId(null);
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
            <span className="inline-flex items-center gap-2">
              <Plus className="h-4 w-4" /> Chat qo&apos;shish
            </span>
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
              <div
                key={chat.id}
                className="rounded-xl border border-slate-700 bg-slate-800/70 p-4 transition hover:border-blue-400"
              >
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-white">{chat.name}</p>
                    <p className="mt-2 line-clamp-2 text-sm text-slate-400">Agent suhbatini oching va shu chat kontekstida ishlang.</p>
                  </div>
                  <button
                    onClick={() => void handleDeleteChat(chat.id)}
                    disabled={deletingChatId === chat.id}
                    className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-rose-500/40 bg-rose-500/10 text-rose-200 disabled:opacity-50"
                    title="Delete chat"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                <Link
                  href={`/dashboard/server/${serverId}/chat/${chat.id}`}
                  className="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-100 transition hover:border-cyan-300/40"
                >
                  <MessageSquare className="h-4 w-4" /> Chatni ochish
                </Link>
              </div>
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
              <p className="text-xs text-slate-400">
                Muhim: bitta server ichida bir xil nomdagi chat ochish qat&apos;iyan taqiqlangan.
              </p>
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
                  disabled={creating}
                  className="flex-1 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-4 py-3 text-sm font-semibold text-white"
                >
                  {creating ? "Saqlanmoqda..." : "Saqlash"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
