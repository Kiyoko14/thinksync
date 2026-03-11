"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import { apiClient, Chat, Message } from "@/lib/api";

export default function ChatPage() {
  const params = useParams<{ id: string; chatId: string }>();
  const serverId = params.id;
  const chatId = params.chatId;

  const [chat, setChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const loadData = useCallback(async () => {
    try {
      const [chatData, messagesData] = await Promise.all([
        apiClient.getChat(chatId),
        apiClient.getMessages(chatId),
      ]);
      setChat(chatData);
      setMessages(messagesData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat yuklanmadi");
    }
  }, [chatId]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleSend = async (event: FormEvent) => {
    event.preventDefault();
    const content = input.trim();
    if (!content) return;

    setSending(true);
    setInput("");

    try {
      const response = await apiClient.sendMessage(chatId, content);
      setMessages((prev) => [...prev, response.user_message, response.assistant_message]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Xabar yuborilmadi");
    } finally {
      setSending(false);
    }
  };

  const sortedMessages = useMemo(
    () => [...messages].sort((a, b) => a.created_at.localeCompare(b.created_at)),
    [messages]
  );

  return (
    <div className="grid min-h-[75vh] gap-4 lg:grid-cols-[260px_1fr]">
      <aside className="rounded-2xl border border-slate-800 bg-slate-900/75 p-4">
        <Link
          href={`/dashboard/server/${serverId}`}
          className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 transition hover:border-blue-400"
        >
          Chatdan chiqish
        </Link>
        <div className="mt-6 space-y-2">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Aktiv chat</p>
          <h1 className="text-lg font-semibold text-white">{chat?.name ?? "Chat"}</h1>
        </div>
      </aside>

      <section className="flex min-h-[75vh] flex-col rounded-2xl border border-slate-800 bg-slate-900/70">
        <div className="border-b border-slate-800 px-5 py-4">
          <h2 className="text-xl font-semibold text-white">AI chat oynasi</h2>
          <p className="mt-1 text-sm text-slate-400">Message history va server-aware command execution</p>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-4">
          {error && <p className="rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-200">{error}</p>}

          {sortedMessages.map((message) => (
            <div key={message.id} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm ${
                  message.role === "user"
                    ? "bg-blue-600 text-white"
                    : "border border-slate-700 bg-slate-800 text-slate-100"
                }`}
              >
                <p>{message.content}</p>
              </div>
            </div>
          ))}
        </div>

        <form onSubmit={handleSend} className="border-t border-slate-800 p-4">
          <div className="flex gap-3">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Buyruq yoki savol yozing..."
              className="flex-1 rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none focus:border-blue-500"
            />
            <button
              disabled={sending}
              className="rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-5 py-3 text-sm font-semibold text-white disabled:opacity-60"
            >
              Send
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
