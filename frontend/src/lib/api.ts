const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  (process.env.NODE_ENV === "development"
    ? "http://127.0.0.1:8000"
    : "https://api.thinksync.art");

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
  status: "pending" | "running" | "success" | "failed";
  created_at: string;
};

export interface DeploymentStatus {
  deployment_id: string;
  status: string;
  run?: {
    run_id?: string;
    status?: string;
    current_stage?: string;
    duration_seconds?: number;
    stage_results?: Array<{ name?: string; status?: string }>;
  } | null;
}

export type SendMessageResponse = {
  user_message: Message;
  assistant_message: Message;
  inspection?: Record<string, unknown>;
};

export interface Stage {
  name: string;
  commands: string[];
  on_failure: string;
  timeout: number;
}

export interface Pipeline {
  id: string;
  name: string;
  description?: string;
  server_id: string;
  stages: Stage[];
  environment_variables?: Record<string, string>;
  created_at: string;
}

export interface StageResult {
  name: string;
  status: string;
  output?: string;
}

export interface PipelineRun {
  id: string;
  pipeline_id: string;
  status: string;
  current_stage?: string;
  duration_seconds?: number;
  stage_results?: StageResult[];
  created_at: string;
}

export interface ServerMetrics {
  server_id: string;
  cpu_percent: number;
  mem_percent: number;
  disk_percent: number;
  load_1m?: number;
  uptime_seconds?: number;
  collected_at: string;
}

export interface Alert {
  server_id: string;
  metric: string;
  value: number;
  threshold: number;
  ts: number;
}

export interface Secret {
  name: string;
  server_id: string;
  created_at: string;
}

export interface LogHistoryEntry {
  line: string;
  ts?: number | string;
}

export interface AgentStats {
  [agent: string]: Record<string, number>;
}

export interface Task {
  id: string;
  chat_id: string;
  state: string;
  step?: string;
  attempts?: number;
  created_at: string;
}

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

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers,
    });
  } catch {
    throw new Error(
      `Backend bilan ulanish amalga oshmadi. API URL: ${API_URL}. Frontend .env faylida NEXT_PUBLIC_API_URL ni tekshiring.`
    );
  }

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

  async executeCommand(
    serverId: string,
    command: string,
    timeout?: number
  ): Promise<{ output: string; exit_code: number }> {
    return request<{ output: string; exit_code: number }>(
      `/servers/${serverId}/execute`,
      {
        method: "POST",
        body: JSON.stringify({ command, timeout }),
      }
    );
  },

  async getServerStatus(serverId: string): Promise<Record<string, unknown>> {
    return request<Record<string, unknown>>(`/servers/${serverId}/status`);
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

  async deleteChat(chatId: string): Promise<{ message: string; chat_id: string; server_id: string }> {
    return request<{ message: string; chat_id: string; server_id: string }>(`/chats/${chatId}`, {
      method: "DELETE",
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

  // Deployments (flat - kept for backwards compat)
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

  // ─── Namespaced sub-clients ───────────────────────────────────────────────

  agents: {
    async getStats(): Promise<AgentStats> {
      return request<AgentStats>("/agents/stats");
    },
    async getMemory(taskId: string): Promise<Record<string, unknown>> {
      return request<Record<string, unknown>>(`/agents/memory/${taskId}`);
    },
    async processMessage(
      chatId: string,
      data: Record<string, unknown>
    ): Promise<Record<string, unknown>> {
      return request<Record<string, unknown>>(`/agents/process/${chatId}`, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
  },

  monitor: {
    async collectMetrics(serverId: string): Promise<ServerMetrics> {
      return request<ServerMetrics>(`/monitor/${serverId}/collect`, {
        method: "POST",
      });
    },
    async getLatest(serverId: string): Promise<ServerMetrics> {
      return request<ServerMetrics>(`/monitor/${serverId}/latest`);
    },
    async getHistory(
      serverId: string,
      metric: string,
      minutes: number
    ): Promise<ServerMetrics[]> {
      return request<ServerMetrics[]>(
        `/monitor/${serverId}/history?metric=${encodeURIComponent(metric)}&minutes=${minutes}`
      );
    },
    async getAlerts(serverId: string): Promise<Alert[]> {
      return request<Alert[]>(`/monitor/${serverId}/alerts`);
    },
  },

  pipelines: {
    async list(): Promise<Pipeline[]> {
      return request<Pipeline[]>("/pipelines/");
    },
    async create(
      data: Omit<Pipeline, "id" | "created_at">
    ): Promise<Pipeline> {
      return request<Pipeline>("/pipelines/", {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    async get(id: string): Promise<Pipeline> {
      return request<Pipeline>(`/pipelines/${id}`);
    },
    async update(
      id: string,
      data: Partial<Omit<Pipeline, "id" | "created_at">>
    ): Promise<Pipeline> {
      return request<Pipeline>(`/pipelines/${id}`, {
        method: "PUT",
        body: JSON.stringify(data),
      });
    },
    async delete(id: string): Promise<void> {
      return request<void>(`/pipelines/${id}`, { method: "DELETE" });
    },
    async triggerRun(
      id: string,
      data?: Record<string, unknown>
    ): Promise<PipelineRun> {
      return request<PipelineRun>(`/pipelines/${id}/run`, {
        method: "POST",
        body: JSON.stringify(data ?? {}),
      });
    },
    async getRun(runId: string): Promise<PipelineRun> {
      return request<PipelineRun>(`/pipelines/runs/${runId}`);
    },
    async cancelRun(runId: string): Promise<PipelineRun> {
      return request<PipelineRun>(`/pipelines/runs/${runId}/cancel`, {
        method: "POST",
      });
    },
    async listRuns(pipelineId: string): Promise<PipelineRun[]> {
      return request<PipelineRun[]>(`/pipelines/${pipelineId}/runs`);
    },
  },

  logs: {
    async getHistory(
      serverId: string,
      limit?: number
    ): Promise<{ lines: string[] }> {
      const q = limit !== undefined ? `?limit=${limit}` : "";
      const payload = await request<{ lines?: Array<string | LogHistoryEntry> }>(
        `/logs/history/${serverId}${q}`
      );
      const normalized = (payload.lines ?? []).map((entry) =>
        typeof entry === "string" ? entry : String(entry?.line ?? "")
      );
      return { lines: normalized.filter((line) => line.length > 0) };
    },
  },

  secrets: {
    async list(serverId: string): Promise<Secret[]> {
      return request<Secret[]>(`/secrets/${serverId}`);
    },
    async upsert(
      serverId: string,
      name: string,
      value: string
    ): Promise<Secret> {
      return request<Secret>(`/secrets/${serverId}`, {
        method: "POST",
        body: JSON.stringify({ name, value }),
      });
    },
    async delete(serverId: string, name: string): Promise<void> {
      return request<void>(`/secrets/${serverId}/${encodeURIComponent(name)}`, {
        method: "DELETE",
      });
    },
  },

  tasks: {
    async list(): Promise<Task[]> {
      return request<Task[]>("/tasks/");
    },
    async get(id: string): Promise<Task> {
      return request<Task>(`/tasks/${id}`);
    },
  },

  deployments: {
    async list(): Promise<Deployment[]> {
      return request<Deployment[]>("/deployments/");
    },
    async get(id: string): Promise<Deployment> {
      return request<Deployment>(`/deployments/${id}`);
    },
    async execute(
      id: string
    ): Promise<{ message?: string; run_id?: string; status?: string }> {
      return request<{ message?: string; run_id?: string; status?: string }>(
        `/deployments/${id}/execute`,
        {
        method: "POST",
        }
      );
    },
    async getStatus(id: string): Promise<DeploymentStatus> {
      return request<DeploymentStatus>(`/deployments/${id}/status`);
    },
  },
};
