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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadData();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
    try {
      const msgs = await apiClient.getMessages(chat.id);
      setMessages(msgs);
    } catch (err) {
      console.error("Failed to load messages:", err);
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

      // Send message and process
      await apiClient.sendMessage(selectedChat.id, messageInput);

      // Simulate AI response (in real app, this would come from backend)
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        chat_id: selectedChat.id,
        role: "assistant",
        content: "Processing your request...",
        created_at: new Date().toISOString(),
      };
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
      <div className="flex items-center justify-center h-screen">
        <p className="text-slate-400">Loading chats...</p>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-120px)] flex space-x-6">
      {/* Chats Sidebar */}
      <div className="w-64 bg-slate-800 border border-slate-700 rounded-xl overflow-hidden flex flex-col">
        <div className="p-4 border-b border-slate-700">
          <button
            onClick={() => setShowNewChat(!showNewChat)}
            className="w-full px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg font-semibold hover:from-blue-600 hover:to-purple-700 transition text-sm"
          >
            {showNewChat ? "Cancel" : "+ New Chat"}
          </button>
        </div>

        {/* New Chat Form */}
        {showNewChat && (
          <form onSubmit={handleCreateChat} className="p-4 border-b border-slate-700 space-y-3">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Server
              </label>
              <select
                value={selectedServer}
                onChange={(e) => setSelectedServer(e.target.value)}
                className="w-full px-2 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                <option value="">Select a server</option>
                {servers.map((server) => (
                  <option key={server.id} value={server.id}>
                    {server.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Chat Name
              </label>
              <input
                type="text"
                value={newChatName}
                onChange={(e) => setNewChatName(e.target.value)}
                placeholder="e.g., Deploy App"
                className="w-full px-2 py-2 bg-slate-700 border border-slate-600 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <button
              type="submit"
              className="w-full px-2 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded text-sm font-medium transition"
            >
              Create
            </button>
          </form>
        )}

        {/* Chats List */}
        <div className="flex-1 overflow-y-auto">
          {chats.length === 0 ? (
            <div className="p-4 text-center text-slate-400 text-sm">No chats yet</div>
          ) : (
            <div className="space-y-2 p-4">
              {chats.map((chat) => (
                <button
                  key={chat.id}
                  onClick={() => selectChat(chat)}
                  className={`w-full text-left px-3 py-2 rounded-lg transition ${
                    selectedChat?.id === chat.id
                      ? "bg-blue-500/30 border border-blue-500/50 text-white"
                      : "hover:bg-slate-700 text-slate-300"
                  }`}
                >
                  <p className="font-medium text-sm truncate">{chat.name}</p>
                  <p className="text-xs opacity-70 mt-1">
                    {new Date(chat.created_at).toLocaleDateString()}
                  </p>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 bg-slate-800 border border-slate-700 rounded-xl flex flex-col">
        {selectedChat ? (
          <>
            {/* Chat Header */}
            <div className="p-4 border-b border-slate-700">
              <h2 className="text-xl font-bold text-white">{selectedChat.name}</h2>
              <p className="text-sm text-slate-400 mt-1">
                💬 AI-powered DevOps Chat
              </p>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {error && (
                <div className="p-3 bg-red-500/10 border border-red-500/50 rounded-lg">
                  <p className="text-red-400 text-sm">{error}</p>
                </div>
              )}
              {messages.length === 0 ? (
                <div className="flex items-center justify-center h-full">
                  <p className="text-slate-400">No messages yet. Start a conversation!</p>
                </div>
              ) : (
                messages.map((message) => (
                  <div
                    key={message.id}
                    className={`flex ${
                      message.role === "user" ? "justify-end" : "justify-start"
                    }`}
                  >
                    <div
                      className={`max-w-xs px-4 py-3 rounded-lg ${
                        message.role === "user"
                          ? "bg-blue-600 text-white rounded-br-none"
                          : "bg-slate-700 text-slate-100 rounded-bl-none"
                      }`}
                    >
                      <p className="text-sm">{message.content}</p>
                      <p
                        className={`text-xs mt-1 ${
                          message.role === "user"
                            ? "text-blue-100"
                            : "text-slate-400"
                        }`}
                      >
                        {new Date(message.created_at).toLocaleTimeString()}
                      </p>
                    </div>
                  </div>
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Message Input */}
            <form onSubmit={handleSendMessage} className="p-4 border-t border-slate-700">
              <div className="flex space-x-3">
                <input
                  type="text"
                  value={messageInput}
                  onChange={(e) => setMessageInput(e.target.value)}
                  placeholder="Ask me anything about DevOps..."
                  disabled={sending}
                  className="flex-1 px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder:text-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
                />
                <button
                  type="submit"
                  disabled={sending || !messageInput.trim()}
                  className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg font-semibold hover:from-blue-600 hover:to-purple-700 transition disabled:opacity-50"
                >
                  {sending ? "..." : "Send"}
                </button>
              </div>
            </form>
          </>
        ) : (
          <div className="flex items-center justify-center h-full">
            <p className="text-slate-400">Select a chat to begin</p>
          </div>
        )}
      </div>
    </div>
  );
}
