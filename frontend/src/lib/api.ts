const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "https://api.thinksync.art";

const TOKEN_KEY = "thinksync_token";

// ─── Token helpers ────────────────────────────────────────────────────────────

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

// ─── Types ────────────────────────────────────────────────────────────────────

export type User = {
  id: string;
  email: string;
  created_at: string;
};

export type Server = {
  id: string;
  user_id: string;
  name: string;
  host: string;
  ssh_user: string;
  ssh_port: number;
  ssh_auth_method?: "private_key" | "password";
  ssh_key?: string;
  ssh_password?: string;
  created_at?: string;
};

export type Chat = {
  id: string;
  user_id: string;
  server_id: string;
  name: string;
  created_at?: string;
};

export type Message = {
  id: string;
  chat_id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export type Database = {
  id: string;
  user_id: string;
  server_id?: string;
  project_id?: string;
  db_url?: string;
  created_at?: string;
};

export type Deployment = {
  id: string;
  server_id: string;
  code: string;
  language: string;
  deployment_type: string;
  status: "pending" | "success" | "failed";
  created_at: string;
};

export type SendMessageResponse = {
  user_message: Message;
  assistant_message: Message;
  inspection?: Record<string, unknown>;
};

// ─── HTTP helper ──────────────────────────────────────────────────────────────

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let message = `Request failed: ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // ignore JSON parse errors
    }
    throw new Error(message);
  }

  // Return null for 204 No Content
  if (response.status === 204) {
    return null as T;
  }

  return response.json() as Promise<T>;
}

// ─── API client ───────────────────────────────────────────────────────────────

export const apiClient = {
  // Auth
  async login(email: string, password: string): Promise<User> {
    const data = await request<{ token: string; user: User }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(data.token);
    return data.user;
  },

  async logout(): Promise<void> {
    try {
      await request<void>("/auth/logout", { method: "POST" });
    } finally {
      clearToken();
    }
  },

  async getSession(): Promise<User | null> {
    try {
      const data = await request<{
        user_id: string;
        email: string;
        created_at: string;
      }>("/auth/session");
      return { id: data.user_id, email: data.email, created_at: data.created_at };
    } catch {
      return null;
    }
  },

  // Servers
  async getServers(): Promise<Server[]> {
    return request<Server[]>("/servers/");
  },

  async getServer(id: string): Promise<Server> {
    return request<Server>(`/servers/${id}`);
  },

  async createServer(
    data: Omit<Server, "id" | "user_id" | "created_at">
  ): Promise<Server> {
    return request<Server>("/servers/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateServer(
    id: string,
    data: Partial<Omit<Server, "id" | "user_id">>
  ): Promise<Server> {
    return request<Server>(`/servers/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  async deleteServer(id: string): Promise<void> {
    return request<void>(`/servers/${id}`, { method: "DELETE" });
  },

  async deployCode(
    serverId: string,
    data: { code: string; language: string; deployment_type: string }
  ): Promise<{ deployment_id?: string; message?: string }> {
    return request<{ deployment_id?: string; message?: string }>(`/servers/${serverId}/deploy`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Chats
  async getChats(serverId?: string): Promise<Chat[]> {
    const query = serverId ? `?server_id=${encodeURIComponent(serverId)}` : "";
    return request<Chat[]>(`/chats/${query}`);
  },

  async getChat(id: string): Promise<Chat> {
    return request<Chat>(`/chats/${id}`);
  },

  async createChat(data: { server_id: string; name: string }): Promise<Chat> {
    return request<Chat>("/chats/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  // Messages
  async getMessages(chatId: string): Promise<Message[]> {
    return request<Message[]>(`/chats/${chatId}/messages`);
  },

  async sendMessage(
    chatId: string,
    content: string
  ): Promise<SendMessageResponse> {
    return request<SendMessageResponse>(`/chats/${chatId}/messages`, {
      method: "POST",
      body: JSON.stringify({ content }),
    });
  },

  // Deployments
  async getDeployments(): Promise<Deployment[]> {
    return request<Deployment[]>("/deployments/");
  },

  // Databases
  async getDatabases(): Promise<Database[]> {
    return request<Database[]>("/database/");
  },

  async createDatabase(data: { server_id?: string }): Promise<Database> {
    return request<Database>("/database/", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },
};
