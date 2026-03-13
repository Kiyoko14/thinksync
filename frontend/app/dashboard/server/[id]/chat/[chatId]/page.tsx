"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Home, Send, Shield, Trash2 } from "lucide-react";
import { apiClient, Chat, Message } from "@/lib/api";

export default function ChatPage() {
  const router = useRouter();
  const params = useParams<{ id: string; chatId: string }>();
  const serverId = params.id;
  const chatId = params.chatId;

  const [chat, setChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

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

  useEffect(() => {
    scrollToBottom();
  }, [messages, sending]);

  const handleSend = async (event: FormEvent) => {
    event.preventDefault();
    const content = input.trim();
    if (!content || sending) return;

    const optimisticUser: Message = {
      id: `optimistic-${Date.now()}`,
      chat_id: chatId,
      role: "user",
      content,
      created_at: new Date().toISOString(),
    };

    setSending(true);
    setInput("");
    setError("");
    setMessages((prev) => [...prev, optimisticUser]);

    try {
      const response = await apiClient.sendMessage(chatId, content);
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== optimisticUser.id),
        response.user_message,
        response.assistant_message,
      ]);
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== optimisticUser.id));
      setError(err instanceof Error ? err.message : "Xabar yuborilmadi");
    } finally {
      setSending(false);
    }
  };

  const handleDeleteChat = async () => {
    if (!confirm("Chat va unga bog'liq barcha ma'lumotlar o'chirilsinmi?")) return;
    try {
      setDeleting(true);
      await apiClient.deleteChat(chatId);
      router.push(`/dashboard/server/${serverId}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Chat o'chirilmadi");
      setDeleting(false);
    }
  };

  const sortedMessages = useMemo(
    () => [...messages].sort((a, b) => a.created_at.localeCompare(b.created_at)),
    [messages]
  );

  return (
    <div className="min-h-[calc(100vh-6rem)] space-y-4">
      <div className="flex items-center justify-between rounded-2xl border border-slate-800 bg-slate-900/70 px-4 py-3">
        <div className="flex items-center gap-2">
          <Link
            href="/dashboard"
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700 text-slate-200 transition hover:border-cyan-300/40"
            title="Dashboard"
          >
            <Home className="h-4 w-4" />
          </Link>
          <Link
            href={`/dashboard/server/${serverId}`}
            className="inline-flex h-9 w-9 items-center justify-center rounded-lg border border-slate-700 text-slate-200 transition hover:border-cyan-300/40"
            title="Back to server"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="ml-2">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-400">Agent Workspace</p>
            <p className="text-sm font-semibold text-white">{chat?.name ?? "Chat"}</p>
          </div>
        </div>

        <button
          onClick={() => void handleDeleteChat()}
          disabled={deleting}
          className="inline-flex items-center gap-2 rounded-lg border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-sm text-rose-200 disabled:opacity-60"
        >
          <Trash2 className="h-4 w-4" />
          {deleting ? "Deleting..." : "Delete Chat"}
        </button>
      </div>

      <section className="flex h-[calc(100vh-13rem)] flex-col overflow-hidden rounded-2xl border border-slate-800 bg-slate-900/70">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div>
            <h2 className="text-lg font-semibold text-white">AI DevOps Operator</h2>
            <p className="mt-0.5 text-xs text-slate-400">Server-aware assistant with command context and safe execution flow</p>
          </div>
          <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/40 bg-emerald-500/10 px-3 py-1 text-xs text-emerald-200">
            <Shield className="h-3.5 w-3.5" /> Guarded Mode
          </span>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5 min-h-0">
          {sortedMessages.length === 0 && !sending && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <div className="mb-3 rounded-2xl border border-cyan-400/30 bg-cyan-500/10 p-4">
                <Shield className="h-8 w-8 text-cyan-200" />
              </div>
              <p className="text-sm font-medium text-slate-300">Agent ishga tayyor</p>
              <p className="mt-1 text-xs text-slate-500">Bu chat nomi uchun alohida workspace konteksti yuritiladi</p>
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
              {error}
            </div>
          )}

          {sortedMessages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {message.role === "assistant" && (
                <span className="mr-2 mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-cyan-400/40 bg-cyan-500/10 text-xs text-cyan-100">
                  AI
                </span>
              )}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                  message.role === "user"
                    ? "bg-gradient-to-br from-blue-600 to-cyan-600 text-white"
                    : "border border-slate-700 bg-slate-800/80 text-slate-100"
                }`}
              >
                {message.content}
              </div>
            </div>
          ))}

          {sending && (
            <div className="flex justify-start">
              <span className="mr-2 mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-cyan-400/40 bg-cyan-500/10 text-xs text-cyan-100">
                AI
              </span>
              <div className="rounded-2xl border border-slate-700 bg-slate-800/80 px-4 py-3">
                <span className="flex gap-1">
                  <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
                  <span className="h-2 w-2 animate-bounce rounded-full bg-slate-400" />
                </span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <form onSubmit={handleSend} className="border-t border-slate-800 p-4">
          <div className="flex gap-3">
            <input
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Buyruq yoki savol yozing..."
              disabled={sending}
              className="flex-1 rounded-xl border border-slate-700 bg-slate-800 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-blue-500 disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={sending || !input.trim()}
              className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 to-cyan-500 px-5 py-3 text-sm font-semibold text-white transition hover:from-blue-500 hover:to-cyan-400 disabled:opacity-50"
            >
              <Send className="h-4 w-4" />
              {sending ? "..." : "Yuborish"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
