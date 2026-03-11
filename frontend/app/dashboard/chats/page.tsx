"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { apiClient, Chat, Server } from "@/lib/api";

export default function ChatsNavigatorPage() {
  const [servers, setServers] = useState<Server[]>([]);
  const [chatsByServer, setChatsByServer] = useState<Record<string, Chat[]>>({});

  useEffect(() => {
    const load = async () => {
      const serverData = await apiClient.getServers();
      setServers(serverData);

      const entries = await Promise.all(
        serverData.map(async (server) => [server.id, await apiClient.getChats(server.id)] as const)
      );

      const grouped: Record<string, Chat[]> = {};
      entries.forEach(([id, chats]) => {
        grouped[id] = chats;
      });
      setChatsByServer(grouped);
    };

    load();
  }, []);

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
        <h1 className="text-2xl font-semibold text-white">Chatlar markazi</h1>
        <p className="mt-2 text-sm text-slate-400">
          Har bir chat server bilan bog&apos;langan. To&apos;g&apos;ridan-to&apos;g&apos;ri server sahifasidan chat yarating yoki oching.
        </p>
      </section>

      <section className="space-y-4">
        {servers.map((server) => (
          <article key={server.id} className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold text-white">{server.name}</h2>
                <p className="text-sm text-slate-400">{server.host}</p>
              </div>
              <Link
                href={`/dashboard/server/${server.id}`}
                className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:border-blue-400"
              >
                Server sahifasi
              </Link>
            </div>

            {(chatsByServer[server.id] ?? []).length > 0 && (
              <div className="mt-4 flex flex-wrap gap-2">
                {(chatsByServer[server.id] ?? []).map((chat) => (
                  <Link
                    key={chat.id}
                    href={`/dashboard/server/${server.id}/chat/${chat.id}`}
                    className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:border-cyan-400"
                  >
                    {chat.name}
                  </Link>
                ))}
              </div>
            )}
          </article>
        ))}
      </section>
    </div>
  );
}
