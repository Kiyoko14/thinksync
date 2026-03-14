```sql
BEGIN;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS public.servers (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  host VARCHAR(255) NOT NULL,
  ssh_user VARCHAR(100) NOT NULL,
  ssh_port INT NOT NULL DEFAULT 22,
  ssh_auth_method VARCHAR(20) NOT NULL DEFAULT 'private_key',
  ssh_key TEXT,
  ssh_password TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT servers_ssh_auth_method_chk CHECK (ssh_auth_method IN ('private_key', 'password')),
  CONSTRAINT servers_name_not_empty_chk CHECK (length(trim(name)) > 0),
  CONSTRAINT servers_host_not_empty_chk CHECK (length(trim(host)) > 0)
);

CREATE TABLE IF NOT EXISTS public.chats (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  server_id UUID NOT NULL REFERENCES public.servers(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name VARCHAR(255) NOT NULL,
  workspace_path TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chats_name_not_empty_chk CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS public.messages (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  chat_id UUID NOT NULL REFERENCES public.chats(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT messages_role_chk CHECK (role IN ('user', 'assistant', 'system'))
);

CREATE TABLE IF NOT EXISTS public.deployments (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  server_id UUID REFERENCES public.servers(id) ON DELETE SET NULL,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  code TEXT,
  language VARCHAR(50),
  deployment_type VARCHAR(50),
  deployment_script TEXT,
  status VARCHAR(50) NOT NULL DEFAULT 'pending',
  run_id UUID,
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.tasks (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  chat_id UUID NOT NULL REFERENCES public.chats(id) ON DELETE CASCADE,
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
  state VARCHAR(50),
  step VARCHAR(100),
  attempts INT NOT NULL DEFAULT 0,
  result JSONB DEFAULT '{}'::jsonb,
  error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.databases (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  server_id UUID REFERENCES public.servers(id) ON DELETE SET NULL,
  project_id VARCHAR(255),
  db_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.actions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  chat_id UUID NOT NULL REFERENCES public.chats(id) ON DELETE CASCADE,
  action_json JSONB,
  result TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.server_secrets (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  server_id UUID NOT NULL REFERENCES public.servers(id) ON DELETE CASCADE,
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  name VARCHAR(120) NOT NULL,
  value TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT server_secrets_name_not_empty_chk CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS public.pipelines (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  server_id UUID REFERENCES public.servers(id) ON DELETE SET NULL,
  name VARCHAR(120) NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  stages JSONB NOT NULL DEFAULT '[]'::jsonb,
  stage_count INT NOT NULL DEFAULT 0,
  environment_variables JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT pipelines_name_not_empty_chk CHECK (length(trim(name)) > 0)
);

CREATE TABLE IF NOT EXISTS public.pipeline_runs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  pipeline_id UUID REFERENCES public.pipelines(id) ON DELETE CASCADE,
  pipeline_name VARCHAR(120),
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  chat_id UUID REFERENCES public.chats(id) ON DELETE SET NULL,
  triggered_by VARCHAR(50) NOT NULL DEFAULT 'manual',
  status VARCHAR(50) NOT NULL DEFAULT 'pending',
  stage_count INT NOT NULL DEFAULT 0,
  stage_results JSONB NOT NULL DEFAULT '[]'::jsonb,
  duration_seconds DOUBLE PRECISION,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.server_alerts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  server_id UUID NOT NULL REFERENCES public.servers(id) ON DELETE CASCADE,
  metric VARCHAR(50) NOT NULL,
  value DOUBLE PRECISION NOT NULL,
  threshold DOUBLE PRECISION NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.server_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  server_id UUID NOT NULL REFERENCES public.servers(id) ON DELETE CASCADE,
  line TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.agent_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  agent VARCHAR(100) NOT NULL,
  input_hash VARCHAR(64),
  result JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.agent_experiences (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  chat_id UUID REFERENCES public.chats(id) ON DELETE SET NULL,
  task_id VARCHAR(255),
  agent VARCHAR(100) NOT NULL,
  request_pattern TEXT,
  outcome VARCHAR(20) NOT NULL,
  payload JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT agent_experiences_outcome_chk CHECK (outcome IN ('success', 'failure', 'partial'))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_servers_user_name_ci
  ON public.servers (user_id, lower(name));

DROP INDEX IF EXISTS ux_chats_user_server_name_ci;
CREATE UNIQUE INDEX IF NOT EXISTS ux_chats_user_name_ci
  ON public.chats (user_id, lower(name));

CREATE UNIQUE INDEX IF NOT EXISTS ux_server_secrets_server_name_ci
  ON public.server_secrets (server_id, lower(name));

CREATE INDEX IF NOT EXISTS idx_servers_user_id ON public.servers(user_id);
CREATE INDEX IF NOT EXISTS idx_chats_user_id ON public.chats(user_id);
CREATE INDEX IF NOT EXISTS idx_chats_server_id ON public.chats(server_id);
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON public.messages(chat_id);
CREATE INDEX IF NOT EXISTS idx_deployments_user_id ON public.deployments(user_id);
CREATE INDEX IF NOT EXISTS idx_deployments_server_id ON public.deployments(server_id);
CREATE INDEX IF NOT EXISTS idx_deployments_run_id ON public.deployments(run_id);
CREATE INDEX IF NOT EXISTS idx_tasks_chat_id ON public.tasks(chat_id);
CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON public.tasks(user_id);
CREATE INDEX IF NOT EXISTS idx_databases_user_id ON public.databases(user_id);
CREATE INDEX IF NOT EXISTS idx_actions_chat_id ON public.actions(chat_id);
CREATE INDEX IF NOT EXISTS idx_server_secrets_server_id ON public.server_secrets(server_id);
CREATE INDEX IF NOT EXISTS idx_server_secrets_user_id ON public.server_secrets(user_id);
CREATE INDEX IF NOT EXISTS idx_pipelines_user_id ON public.pipelines(user_id);
CREATE INDEX IF NOT EXISTS idx_pipelines_server_id ON public.pipelines(server_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_pipeline_id ON public.pipeline_runs(pipeline_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_user_id ON public.pipeline_runs(user_id);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_chat_id ON public.pipeline_runs(chat_id);
CREATE INDEX IF NOT EXISTS idx_server_alerts_server_id ON public.server_alerts(server_id);
CREATE INDEX IF NOT EXISTS idx_server_logs_server_id ON public.server_logs(server_id);
CREATE INDEX IF NOT EXISTS idx_agent_logs_agent ON public.agent_logs(agent);
CREATE INDEX IF NOT EXISTS idx_agent_experiences_agent ON public.agent_experiences(agent);
CREATE INDEX IF NOT EXISTS idx_agent_experiences_chat_id ON public.agent_experiences(chat_id);

DROP TRIGGER IF EXISTS trg_servers_updated_at ON public.servers;
CREATE TRIGGER trg_servers_updated_at
BEFORE UPDATE ON public.servers
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_chats_updated_at ON public.chats;
CREATE TRIGGER trg_chats_updated_at
BEFORE UPDATE ON public.chats
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_deployments_updated_at ON public.deployments;
CREATE TRIGGER trg_deployments_updated_at
BEFORE UPDATE ON public.deployments
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_tasks_updated_at ON public.tasks;
CREATE TRIGGER trg_tasks_updated_at
BEFORE UPDATE ON public.tasks
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_server_secrets_updated_at ON public.server_secrets;
CREATE TRIGGER trg_server_secrets_updated_at
BEFORE UPDATE ON public.server_secrets
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_pipelines_updated_at ON public.pipelines;
CREATE TRIGGER trg_pipelines_updated_at
BEFORE UPDATE ON public.pipelines
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS trg_pipeline_runs_updated_at ON public.pipeline_runs;
CREATE TRIGGER trg_pipeline_runs_updated_at
BEFORE UPDATE ON public.pipeline_runs
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

ALTER TABLE public.servers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.deployments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.databases ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.server_secrets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipelines ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pipeline_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.server_alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.server_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.agent_experiences ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS servers_select_own ON public.servers;
DROP POLICY IF EXISTS servers_insert_own ON public.servers;
DROP POLICY IF EXISTS servers_update_own ON public.servers;
DROP POLICY IF EXISTS servers_delete_own ON public.servers;

CREATE POLICY servers_select_own ON public.servers
FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY servers_insert_own ON public.servers
FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY servers_update_own ON public.servers
FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY servers_delete_own ON public.servers
FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS chats_select_own ON public.chats;
DROP POLICY IF EXISTS chats_insert_own ON public.chats;
DROP POLICY IF EXISTS chats_update_own ON public.chats;
DROP POLICY IF EXISTS chats_delete_own ON public.chats;

CREATE POLICY chats_select_own ON public.chats
FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY chats_insert_own ON public.chats
FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY chats_update_own ON public.chats
FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY chats_delete_own ON public.chats
FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS messages_select_own ON public.messages;
DROP POLICY IF EXISTS messages_insert_own ON public.messages;

CREATE POLICY messages_select_own ON public.messages
FOR SELECT USING (
  EXISTS (
    SELECT 1 FROM public.chats c
    WHERE c.id = messages.chat_id AND c.user_id = auth.uid()
  )
);
CREATE POLICY messages_insert_own ON public.messages
FOR INSERT WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.chats c
    WHERE c.id = messages.chat_id AND c.user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS deployments_select_own ON public.deployments;
DROP POLICY IF EXISTS deployments_insert_own ON public.deployments;
DROP POLICY IF EXISTS deployments_update_own ON public.deployments;
DROP POLICY IF EXISTS deployments_delete_own ON public.deployments;

CREATE POLICY deployments_select_own ON public.deployments
FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY deployments_insert_own ON public.deployments
FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY deployments_update_own ON public.deployments
FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY deployments_delete_own ON public.deployments
FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS tasks_select_own ON public.tasks;
DROP POLICY IF EXISTS tasks_insert_own ON public.tasks;
DROP POLICY IF EXISTS tasks_update_own ON public.tasks;
DROP POLICY IF EXISTS tasks_delete_own ON public.tasks;

CREATE POLICY tasks_select_own ON public.tasks
FOR SELECT USING (
  user_id = auth.uid()
  OR EXISTS (
    SELECT 1 FROM public.chats c
    WHERE c.id = tasks.chat_id AND c.user_id = auth.uid()
  )
);
CREATE POLICY tasks_insert_own ON public.tasks
FOR INSERT WITH CHECK (
  user_id = auth.uid()
  OR user_id IS NULL
);
CREATE POLICY tasks_update_own ON public.tasks
FOR UPDATE USING (
  user_id = auth.uid()
  OR EXISTS (
    SELECT 1 FROM public.chats c
    WHERE c.id = tasks.chat_id AND c.user_id = auth.uid()
  )
+) WITH CHECK (
  user_id = auth.uid()
  OR user_id IS NULL
);
CREATE POLICY tasks_delete_own ON public.tasks
FOR DELETE USING (
  user_id = auth.uid()
  OR EXISTS (
    SELECT 1 FROM public.chats c
    WHERE c.id = tasks.chat_id AND c.user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS databases_select_own ON public.databases;
DROP POLICY IF EXISTS databases_insert_own ON public.databases;
DROP POLICY IF EXISTS databases_update_own ON public.databases;
DROP POLICY IF EXISTS databases_delete_own ON public.databases;

CREATE POLICY databases_select_own ON public.databases
FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY databases_insert_own ON public.databases
FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY databases_update_own ON public.databases
FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY databases_delete_own ON public.databases
FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS actions_select_own ON public.actions;
DROP POLICY IF EXISTS actions_insert_own ON public.actions;
DROP POLICY IF EXISTS actions_update_own ON public.actions;
DROP POLICY IF EXISTS actions_delete_own ON public.actions;

CREATE POLICY actions_select_own ON public.actions
FOR SELECT USING (
  EXISTS (
    SELECT 1 FROM public.chats c
    WHERE c.id = actions.chat_id AND c.user_id = auth.uid()
  )
);
CREATE POLICY actions_insert_own ON public.actions
FOR INSERT WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.chats c
    WHERE c.id = actions.chat_id AND c.user_id = auth.uid()
  )
);
CREATE POLICY actions_update_own ON public.actions
FOR UPDATE USING (
  EXISTS (
    SELECT 1 FROM public.chats c
    WHERE c.id = actions.chat_id AND c.user_id = auth.uid()
  )
+) WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.chats c
    WHERE c.id = actions.chat_id AND c.user_id = auth.uid()
  )
);
CREATE POLICY actions_delete_own ON public.actions
FOR DELETE USING (
  EXISTS (
    SELECT 1 FROM public.chats c
    WHERE c.id = actions.chat_id AND c.user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS server_secrets_select_own ON public.server_secrets;
DROP POLICY IF EXISTS server_secrets_insert_own ON public.server_secrets;
DROP POLICY IF EXISTS server_secrets_update_own ON public.server_secrets;
DROP POLICY IF EXISTS server_secrets_delete_own ON public.server_secrets;

CREATE POLICY server_secrets_select_own ON public.server_secrets
FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY server_secrets_insert_own ON public.server_secrets
FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY server_secrets_update_own ON public.server_secrets
FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY server_secrets_delete_own ON public.server_secrets
FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS pipelines_select_own ON public.pipelines;
DROP POLICY IF EXISTS pipelines_insert_own ON public.pipelines;
DROP POLICY IF EXISTS pipelines_update_own ON public.pipelines;
DROP POLICY IF EXISTS pipelines_delete_own ON public.pipelines;

CREATE POLICY pipelines_select_own ON public.pipelines
FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY pipelines_insert_own ON public.pipelines
FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY pipelines_update_own ON public.pipelines
FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY pipelines_delete_own ON public.pipelines
FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS pipeline_runs_select_own ON public.pipeline_runs;
DROP POLICY IF EXISTS pipeline_runs_insert_own ON public.pipeline_runs;
DROP POLICY IF EXISTS pipeline_runs_update_own ON public.pipeline_runs;
DROP POLICY IF EXISTS pipeline_runs_delete_own ON public.pipeline_runs;

CREATE POLICY pipeline_runs_select_own ON public.pipeline_runs
FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY pipeline_runs_insert_own ON public.pipeline_runs
FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY pipeline_runs_update_own ON public.pipeline_runs
FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
CREATE POLICY pipeline_runs_delete_own ON public.pipeline_runs
FOR DELETE USING (auth.uid() = user_id);

DROP POLICY IF EXISTS server_alerts_select_own ON public.server_alerts;
DROP POLICY IF EXISTS server_alerts_insert_own ON public.server_alerts;

CREATE POLICY server_alerts_select_own ON public.server_alerts
FOR SELECT USING (
  EXISTS (
    SELECT 1 FROM public.servers s
    WHERE s.id = server_alerts.server_id AND s.user_id = auth.uid()
  )
);
CREATE POLICY server_alerts_insert_own ON public.server_alerts
FOR INSERT WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.servers s
    WHERE s.id = server_alerts.server_id AND s.user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS server_logs_select_own ON public.server_logs;
DROP POLICY IF EXISTS server_logs_insert_own ON public.server_logs;
DROP POLICY IF EXISTS server_logs_delete_own ON public.server_logs;

CREATE POLICY server_logs_select_own ON public.server_logs
FOR SELECT USING (
  EXISTS (
    SELECT 1 FROM public.servers s
    WHERE s.id = server_logs.server_id AND s.user_id = auth.uid()
  )
);
CREATE POLICY server_logs_insert_own ON public.server_logs
FOR INSERT WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.servers s
    WHERE s.id = server_logs.server_id AND s.user_id = auth.uid()
  )
);
CREATE POLICY server_logs_delete_own ON public.server_logs
FOR DELETE USING (
  EXISTS (
    SELECT 1 FROM public.servers s
    WHERE s.id = server_logs.server_id AND s.user_id = auth.uid()
  )
);

DROP POLICY IF EXISTS agent_logs_select_all_auth ON public.agent_logs;
DROP POLICY IF EXISTS agent_logs_insert_all_auth ON public.agent_logs;
DROP POLICY IF EXISTS agent_logs_update_all_auth ON public.agent_logs;
DROP POLICY IF EXISTS agent_logs_delete_all_auth ON public.agent_logs;

CREATE POLICY agent_logs_select_all_auth ON public.agent_logs
FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY agent_logs_insert_all_auth ON public.agent_logs
FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY agent_logs_update_all_auth ON public.agent_logs
FOR UPDATE USING (auth.uid() IS NOT NULL) WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY agent_logs_delete_all_auth ON public.agent_logs
FOR DELETE USING (auth.uid() IS NOT NULL);

DROP POLICY IF EXISTS agent_experiences_select_auth ON public.agent_experiences;
DROP POLICY IF EXISTS agent_experiences_insert_auth ON public.agent_experiences;
DROP POLICY IF EXISTS agent_experiences_update_auth ON public.agent_experiences;
DROP POLICY IF EXISTS agent_experiences_delete_auth ON public.agent_experiences;

CREATE POLICY agent_experiences_select_auth ON public.agent_experiences
FOR SELECT USING (auth.uid() IS NOT NULL);
CREATE POLICY agent_experiences_insert_auth ON public.agent_experiences
FOR INSERT WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY agent_experiences_update_auth ON public.agent_experiences
FOR UPDATE USING (auth.uid() IS NOT NULL) WITH CHECK (auth.uid() IS NOT NULL);
CREATE POLICY agent_experiences_delete_auth ON public.agent_experiences
FOR DELETE USING (auth.uid() IS NOT NULL);

COMMIT;
```