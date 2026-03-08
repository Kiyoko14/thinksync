# Supabase Setup Guide

This guide walks you through setting up Supabase for ThinkSync.

## 1. Create Supabase Project

### Step 1: Sign Up / Log In
1. Go to [supabase.com](https://supabase.com)
2. Click "Start your project" or sign in
3. Click "New Project"

### Step 2: Create Project
- **Project Name**: `thinksync` (or your preferred name)
- **Database Password**: Create a strong password (save it!)
- **Region**: Choose closest to your servers
- Click "Create new project"

*Wait 2-3 minutes for project to initialize*

### Step 3: Get API Keys
1. Go to Project Settings → API
2. Copy the following:
   - **Project URL** → `SUPABASE_URL`
   - **anon (public) key** → `SUPABASE_ANON_KEY`
   - **service_role (secret) key** → Keep safe, use for admin operations

## 2. Enable Authentication

### Step 1: Configure Providers
1. Go to Authentication → Providers
2. Enable "Email" (already enabled by default)
3. Configure Email settings:
   - Go to Authentication → Email Templates
   - Customize if needed (optional)

### Step 2: Configure Magic Link
1. Go to Authentication → Email
2. Under "Email Link", set:
   - Redirect URL: `http://localhost:3000/auth/callback` (for dev)
   - Or: `https://yourdomain.com/auth/callback` (for prod)

## 3. Create Database Tables

### Step 1: Access SQL Editor
1. Go to the SQL Editor in Supabase dashboard
2. Click "New Query"

### Step 2: Copy and Run These Queries

```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table (managed by Supabase Auth)
-- (Created automatically)

-- Servers table
CREATE TABLE IF NOT EXISTS servers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    ssh_user VARCHAR(100),
    ssh_port INT DEFAULT 22,
    ssh_key TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, name)
);

-- Chats table
CREATE TABLE IF NOT EXISTS chats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_id UUID REFERENCES servers(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name VARCHAR(255),
    workspace_path TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Messages table
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    role VARCHAR(20),
    content TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Deployments table
CREATE TABLE IF NOT EXISTS deployments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    server_id UUID REFERENCES servers(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    code TEXT,
    language VARCHAR(50),
    deployment_type VARCHAR(50),
    deployment_script TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Tasks table
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    state VARCHAR(50),
    step VARCHAR(100),
    attempts INT DEFAULT 0,
    error TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Databases table
CREATE TABLE IF NOT EXISTS databases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    server_id UUID REFERENCES servers(id) ON DELETE SET NULL,
    project_id VARCHAR(255),
    db_url TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Actions table
CREATE TABLE IF NOT EXISTS actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    chat_id UUID NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
    action_json JSONB,
    result TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Step 3: Create Indexes (for performance)

```sql
-- Indexes for common queries
CREATE INDEX idx_servers_user_id ON servers(user_id);
CREATE INDEX idx_chats_user_id ON chats(user_id);
CREATE INDEX idx_chats_server_id ON chats(server_id);
CREATE INDEX idx_messages_chat_id ON messages(chat_id);
CREATE INDEX idx_deployments_user_id ON deployments(user_id);
CREATE INDEX idx_tasks_chat_id ON tasks(chat_id);
CREATE INDEX idx_databases_user_id ON databases(user_id);
```

## 4. Enable Row-Level Security

### Step 1: Create RLS Policies

```sql
-- Enable RLS
ALTER TABLE servers ENABLE ROW LEVEL SECURITY;
ALTER TABLE chats ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE deployments ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE databases ENABLE ROW LEVEL SECURITY;
ALTER TABLE actions ENABLE ROW LEVEL SECURITY;

-- Servers: Users can only see/modify their own
CREATE POLICY "Users can select their own servers"
    ON servers FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert servers"
    ON servers FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own servers"
    ON servers FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own servers"
    ON servers FOR DELETE
    USING (auth.uid() = user_id);

-- Chats: Users can only see/modify their own
CREATE POLICY "Users can select their own chats"
    ON chats FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert chats"
    ON chats FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own chats"
    ON chats FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete their own chats"
    ON chats FOR DELETE
    USING (auth.uid() = user_id);

-- Messages: Users can see messages from their chats
CREATE POLICY "Users can select messages from their chats"
    ON messages FOR SELECT
    USING (
        chat_id IN (
            SELECT id FROM chats WHERE user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert messages in their chats"
    ON messages FOR INSERT
    WITH CHECK (
        chat_id IN (
            SELECT id FROM chats WHERE user_id = auth.uid()
        )
    );

-- Similar policies for other tables...
-- (Copy the pattern above for deployments, tasks, databases, actions)
```

## 5. Configure API Access

### Step 1: Get Access Token
1. Go to Settings → API Tokens
2. Under "Service Role Secret", copy the token
3. Add to `.env.local` as `SUPABASE_ACCESS_TOKEN`

### Step 2: Get Organization ID
1. Go to Account Settings → Organizations
2. Copy the Organization ID
3. Add to `.env.local` as `SUPABASE_ORG_ID` (if creating databases)

## 6. Update Environment Variables

Add to `.env.local`:
```bash
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_ACCESS_TOKEN=your-access-token
SUPABASE_ORG_ID=your-org-id

# Frontend
NEXT_PUBLIC_SUPABASE_URL=https://your-project-id.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

## 7. Test Connection

### Option 1: Using cURL
```bash
curl -H "apikey: $SUPABASE_ANON_KEY" \
  https://your-project-id.supabase.co/rest/v1/servers
```

### Option 2: Using ThinkSync
```bash
# Start the application
docker-compose up --build

# Check health
curl http://localhost:8000/health
```

## 8. Configure Storage (Optional)

### For uploading SSH keys, code files, etc.
1. Go to Storage in Supabase dashboard
2. Create new bucket: `ssh-keys` (private)
3. Create new bucket: `deployments` (private)

### Update storage policies:
```sql
-- SSH Keys bucket policy
CREATE POLICY "Users can upload SSH keys"
    ON storage.objects FOR INSERT
    WITH CHECK (bucket_id = 'ssh-keys' AND auth.uid() = owner);

CREATE POLICY "Users can read SSH keys"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'ssh-keys' AND auth.uid() = owner);
```

## 9. Realtime Configuration (Optional)

To enable realtime updates:

1. Go to Realtime → Database in Supabase dashboard
2. Enable for tables you want realtime:
   - ✓ chats
   - ✓ messages
   - ✓ tasks
   - ✓ deployments

## 10. Backup Configuration

### Enable automatic backups:
1. Go to Settings → Backups
2. Automatic backups are enabled by default
3. Retention is based on your plan

### Manual backup:
1. Go to Settings → Backups
2. Click "Create new backup"

## Troubleshooting

### Connection Error: "Failed to initialize Supabase"
- Verify `SUPABASE_URL` and `SUPABASE_ANON_KEY` are correct
- Check network connectivity
- Ensure project is not in sleep mode

### Authentication Error: "Not authenticated"
- Make sure magic link is being sent to the correct email
- Check email spam folder
- Verify redirect URL in Email configuration

### Query Error: "401 Unauthorized"
- Check RLS policies are correctly configured
- Verify user is authenticated with valid JWT token

### Performance Issues:
- Check indexes are created
- Consider upgrading Supabase plan
- Monitor query performance in Supabase dashboard

## Next Steps

1. ✅ Verify all tables are created
2. ✅ Test authentication flow
3. ✅ Test API endpoints
4. ✅ Configure your app with credentials
5. ✅ Start development!

## Resources

- [Supabase Docs](https://supabase.com/docs)
- [Supabase Auth](https://supabase.com/docs/guides/auth)
- [Supabase RLS](https://supabase.com/docs/guides/auth/row-level-security)
- [Supabase API](https://supabase.com/docs/reference/javascript)

## Support

For Supabase issues:
- Check [Supabase Status](https://status.supabase.com/)
- Visit [Supabase Discord](https://discord.supabase.com)
- Review [Supabase Docs](https://supabase.com/docs)
