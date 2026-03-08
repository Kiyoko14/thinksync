"use client";

import { useState, useEffect } from "react";
import { apiClient, Chat, Message, Server } from "@/lib/api";

export default function Dashboard() {
  const [stats, setStats] = useState({
    servers: 0,
    chats: 0,
    databases: 0,
  });
  const [loading, setLoading] = useState(true);
  const [recentChats, setRecentChats] = useState<Chat[]>([]);

  useEffect(() => {
    const loadStats = async () => {
      try {
        const [servers, chats] = await Promise.all([
          apiClient.getServers(),
          apiClient.getChats(),
        ]);

        setStats({
          servers: servers.length,
          chats: chats.length,
          databases: 0,
        });
        setRecentChats(chats.slice(0, 5));
      } catch (err) {
        console.error("Failed to load stats:", err);
      } finally {
        setLoading(false);
      }
    };

    loadStats();
  }, []);

  const StatCard = ({
    title,
    value,
    icon,
    color,
  }: {
    title: string;
    value: number;
    icon: string;
    color: string;
  }) => (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 hover:border-slate-600 transition">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-slate-400 text-sm font-medium">{title}</p>
          <p className="text-3xl font-bold text-white mt-2">{value}</p>
        </div>
        <div className={`text-4xl ${color} opacity-80`}>{icon}</div>
      </div>
    </div>
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-4xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-slate-400">Monitor your DevOps infrastructure</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <StatCard title="Servers" value={stats.servers} icon="🖥️" color="text-blue-500" />
        <StatCard title="AI Chats" value={stats.chats} icon="💬" color="text-purple-500" />
        <StatCard
          title="Databases"
          value={stats.databases}
          icon="🗄️"
          color="text-green-500"
        />
      </div>

      {/* Quick Actions */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
        <h2 className="text-xl font-bold text-white mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <a
            href="/dashboard/servers"
            className="px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition flex items-center space-x-2"
          >
            <span>➕</span>
            <span>Add Server</span>
          </a>
          <a
            href="/dashboard/chats"
            className="px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition flex items-center space-x-2"
          >
            <span>💬</span>
            <span>Start Chat</span>
          </a>
          <a
            href="/dashboard/deployments"
            className="px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition flex items-center space-x-2"
          >
            <span>🚀</span>
            <span>Create Deployment</span>
          </a>
          <a
            href="/dashboard/databases"
            className="px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white rounded-lg transition flex items-center space-x-2"
          >
            <span>🗄️</span>
            <span>Create Database</span>
          </a>
        </div>
      </div>

      {/* Recent Activity */}
      {recentChats.length > 0 && (
        <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
          <h2 className="text-xl font-bold text-white mb-4">Recent Chats</h2>
          <div className="space-y-3">
            {recentChats.map((chat) => (
              <a
                key={chat.id}
                href={`/dashboard/chats/${chat.id}`}
                className="block p-4 bg-slate-700 hover:bg-slate-600 rounded-lg transition group"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-white font-medium group-hover:text-blue-400 transition">
                      {chat.name}
                    </h3>
                    <p className="text-slate-500 text-sm mt-1">
                      Created {new Date(chat.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <span className="text-slate-400">→</span>
                </div>
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
