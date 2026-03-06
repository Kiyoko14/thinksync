"use client";

import { useState, useEffect, useRef } from "react";
import { apiClient, Chat, Message, Server } from "@/lib/api";

export default function ChatsPage() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [servers, setServers] = useState<Server[]>([]);
  const [selectedChat, setSelectedChat] = useState<Chat | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNewChat, setShowNewChat] = useState(false);
  const [newChatName, setNewChatName] = useState("");
  const [selectedServer, setSelectedServer] = useState("");
  const [messageInput, setMessageInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [loadingChat, setLoadingChat] = useState(false);
  // mobile sidebar toggle
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // close mobile sidebar when a chat is selected
  useEffect(() => {
    if (selectedChat && sidebarOpen) {
      setSidebarOpen(false);
    }
  }, [selectedChat, sidebarOpen]);

  // clear success message after a few seconds
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(""), 3000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  // clear error after a while
  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(""), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  const loadData = async () => {
    try {
      const [chatsData, serversData] = await Promise.all([
        apiClient.getChats(),
        apiClient.getServers(),
      ]);
      setChats(chatsData);
      setServers(serversData);
      if (chatsData.length > 0) {
        selectChat(chatsData[0]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const selectChat = async (chat: Chat) => {
    setSelectedChat(chat);
    setSearchQuery("");
    setLoadingChat(true);
    try {
      const msgs = await apiClient.getMessages(chat.id);
      setMessages(msgs);
    } catch (err) {
      console.error("Failed to load messages:", err);
      setError(err instanceof Error ? err.message : "Failed to load messages");
    } finally {
      setLoadingChat(false);
    }
  };

  const handleCreateChat = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedServer || !newChatName) {
      setError("Please select a server and enter a chat name");
      return;
    }

    try {
      const chat = await apiClient.createChat({
        server_id: selectedServer,
        name: newChatName,
      });
      setChats([...chats, chat]);
      setNewChatName("");
      setSelectedServer("");
      setShowNewChat(false);
      setSuccess("Chat created successfully");
      selectChat(chat);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create chat");
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedChat || !messageInput.trim()) return;

    setSending(true);
    setError("");

    try {
      // Add user message immediately
      const userMessage: Message = {
        id: Date.now().toString(),
        chat_id: selectedChat.id,
        role: "user",
        content: messageInput,
        created_at: new Date().toISOString(),
      };
      setMessages([...messages, userMessage]);
      setMessageInput("");

      // Send message and wait for AI response from backend
      const aiMessage = await apiClient.sendMessage(selectedChat.id, messageInput);
      setMessages((prev) => [...prev, aiMessage]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send message");
      setMessages((prev) => prev.slice(0, -1)); // Remove last message on error
    } finally {
      setSending(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
          <p className="text-slate-300">Loading your chats...</p>
        </div>
      </div>
    );
  }

  const filteredChats = chats.filter((chat) =>
    chat.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getServerName = (serverId: string) => {
    return servers.find((s) => s.id === serverId)?.name || "Unknown Server";
  };

  return (
    <div className="relative min-h-[calc(100vh-120px)] flex bg-slate-900">
      {/* Sidebar (conversations) */}
      <div className={`fixed inset-y-0 left-0 w-80 bg-gradient-to-b from-slate-800 to-slate-900 border-r border-slate-700 flex flex-col transform transition-transform duration-200 z-30 lg:relative lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        {/* Header */}
        <div className="p-4 border-b border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-white">💬 Conversations</h2>
            <button
              onClick={() => setShowNewChat(!showNewChat)}
              className="p-2 hover:bg-slate-700 rounded-lg transition"
              title="New Chat"
            >
              <svg
                className="w-5 h-5 text-blue-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 4v16m8-8H4"
                />
              </svg>
            </button>
          </div>

          {/* Search Input */}
          <div className="relative">
            <svg
              className="absolute left-3 top-3 w-4 h-4 text-slate-500"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <input
              type="text"
              placeholder="Search conversations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            />
          </div>
        </div>

        {/* New Chat Form */}
        {showNewChat && (
          <form onSubmit={handleCreateChat} className="p-4 border-b border-slate-700 space-y-3 bg-slate-700/50">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">
                Select Server
              </label>
              <select
                value={selectedServer}
                onChange={(e) => setSelectedServer(e.target.value)}
                className="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
                disabled={servers.length === 0}
              >
                <option value="">Choose a server...</option>
                {servers.map((server) => (
                  <option key={server.id} value={server.id}>
                    {server.name}
                  </option>
                ))}
              </select>
              {servers.length === 0 && (
                <p className="text-xs text-slate-400 mt-1">
                  No servers available. Add a server first.
                </p>
              )}
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wider">
                Chat Name
              </label>
              <input
                type="text"
                value={newChatName}
                onChange={(e) => setNewChatName(e.target.value)}
                placeholder="e.g., Deploy to Production"
                maxLength={50}
                className="w-full px-3 py-2 bg-slate-600 border border-slate-500 rounded-lg text-white placeholder:text-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
              />
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={servers.length === 0}
                className="flex-1 px-3 py-2 bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 text-white rounded-lg font-semibold text-sm transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Create
              </button>
              <button
                type="button"
                onClick={() => setShowNewChat(false)}
                className="flex-1 px-3 py-2 bg-slate-600 hover:bg-slate-700 text-white rounded-lg font-semibold text-sm transition"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Chats List */}
        <div className="flex-1 overflow-y-auto">
          {filteredChats.length === 0 ? (
            <div className="p-6 text-center text-slate-400">
              <svg
                className="w-12 h-12 mx-auto mb-3 opacity-50"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 8v4m0 4v.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                />
              </svg>
              {searchQuery ? (
                <p className="text-sm">No conversations match your search</p>
              ) : (
                <div>
                  <p className="text-sm mb-2">No conversations yet</p>
                  <button
                    onClick={() => setShowNewChat(true)}
                    className="text-blue-400 hover:text-blue-300 text-sm font-semibold"
                  >
                    Start a new conversation
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-2 p-4">
              {filteredChats.map((chat) => (
                <button
                  key={chat.id}
                  onClick={() => selectChat(chat)}
                  className={`w-full text-left px-4 py-3 rounded-lg transition duration-200 border ${
                    selectedChat?.id === chat.id
                      ? "bg-blue-500/20 border-blue-500/50 shadow-lg"
                      : "border-transparent hover:bg-slate-700/50"
                  }`}
                >
                  <p className="font-semibold text-sm text-white truncate">{chat.name}</p>
                  <p className="text-xs text-slate-400 mt-1">
                    📍 {getServerName(chat.server_id)}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">
                    {new Date(chat.created_at).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: chat.created_at.includes(new Date().getFullYear().toString()) ? undefined : "numeric",
                    })}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* overlay for mobile when sidebar is open */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Chat Area */}
      <div className="flex-1 flex flex-col bg-slate-900">
        {selectedChat ? (
          <>
            {/* Chat Header */}
            <div className="px-6 py-4 border-b border-slate-700 bg-gradient-to-r from-slate-800 to-slate-900">
              <div className="flex items-center justify-between">
              <div className="flex items-center">
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="lg:hidden mr-4 text-slate-400 hover:text-white transition"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>
                <div>
                  <h2 className="text-2xl font-bold text-white">{selectedChat.name}</h2>
                  <p className="text-sm text-slate-400 mt-1">
                    🤖 AI-Powered DevOps Assistant • {getServerName(selectedChat.server_id)}
                  </p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                  <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                  <p className="text-sm text-slate-400">Connected</p>
                </div>
              </div>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {error && (
                <div className="sticky top-0 p-4 bg-red-500/15 border border-red-500/50 rounded-lg backdrop-blur">
                  <div className="flex items-start">
                    <svg
                      className="w-5 h-5 text-red-400 mr-3 flex-shrink-0 mt-0.5"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span className="text-red-300 text-sm">{error}</span>
                  </div>
                </div>
              )}

              {success && (
                <div className="sticky top-0 p-4 bg-green-500/15 border border-green-500/50 rounded-lg backdrop-blur animate-in fade-in">
                  <div className="flex items-start">
                    <svg
                      className="w-5 h-5 text-green-400 mr-3 flex-shrink-0 mt-0.5"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span className="text-green-300 text-sm">{success}</span>
                  </div>
                </div>
              )}

              {loadingChat ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto mb-3"></div>
                    <p className="text-slate-400">Loading messages...</p>
                  </div>
                </div>
              ) : messages.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <div className="text-center">
                    <svg
                      className="w-16 h-16 text-slate-600 mx-auto mb-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={1.5}
                        d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                      />
                    </svg>
                    <p className="text-slate-400 text-lg mb-2">Start a conversation</p>
                    <p className="text-slate-500 text-sm max-w-sm">
                      Ask me anything about your DevOps tasks. I'm here to help!
                    </p>
                  </div>
                </div>
              ) : (
                messages.map((message, index) => (
                  <div
                    key={message.id}
                    className={`flex ${message.role === "user" ? "justify-end" : "justify-start"} animate-in fade-in slide-in-from-bottom-2`}
                  >
                    <div
                      className={`flex items-end space-x-3 max-w-[85%] ${
                        message.role === "user" ? "flex-row-reverse space-x-reverse" : ""
                      }`}
                    >
                      {/* Avatar */}
                      <div
                        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center font-semibold text-white text-xs ${
                          message.role === "user"
                            ? "bg-blue-600"
                            : "bg-gradient-to-br from-purple-500 to-purple-600"
                        }`}
                      >
                        {message.role === "user" ? "U" : "AI"}
                      </div>

                      {/* Message Bubble */}
                      <div
                        className={`px-4 py-3 rounded-2xl shadow-sm ${
                          message.role === "user"
                            ? "bg-blue-600 text-white rounded-br-none"
                            : "bg-slate-700 text-slate-100 rounded-bl-none border border-slate-600"
                        }`}
                      >
                        <p className="text-sm leading-relaxed">{message.content}</p>
                        <p
                          className={`text-xs mt-2 ${
                            message.role === "user" ? "text-blue-100" : "text-slate-400"
                          }`}
                        >
                          {new Date(message.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input */}
            <form onSubmit={handleSendMessage} className="p-6 border-t border-slate-700 bg-gradient-to-t from-slate-800 to-transparent sticky bottom-0">
              <div className="flex gap-3">
                <input
                  type="text"
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  placeholder="Ask me about deployments, logs, configs..."
                  disabled={sending || loadingChat}
                  className="flex-1 px-4 py-3 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 transition disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <button
                  type="submit"
                  disabled={sending || !messageInput.trim() || loadingChat}
                  className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-lg font-semibold transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                  {sending ? (
                    <>
                      <span className="animate-spin">⟳</span>
                      <span>Sending</span>
                    </>
                  ) : (
                    <>
                      <span>Send</span>
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                      </svg>
                    </>
                  )}
                </button>
              </div>
            </form>
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <svg
                className="w-20 h-20 text-slate-700 mx-auto mb-4"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={1.5}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
              <h3 className="text-xl font-semibold text-white mb-2">No Chat Selected</h3>
              <p className="text-slate-400 max-w-md mx-auto mb-6">
                Select a conversation from the list or create a new one to get started with your AI DevOps assistant.
              </p>
              <button
                onClick={() => setShowNewChat(true)}
                className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white rounded-lg font-semibold transition"
              >
                + New Conversation
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
