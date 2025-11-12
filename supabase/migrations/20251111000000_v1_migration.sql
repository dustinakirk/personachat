-- ============================================================================
-- PersonaChat V1 Migration Script
-- ============================================================================
-- This script migrates your database from the legacy schema to V1
--
-- IMPORTANT: This will DROP the old 'conversations' table and its data
-- The old table structure (user_id, prompt, response) is incompatible with V1
--
-- Run this in your Supabase SQL Editor
-- ============================================================================

-- Step 1: Drop old conversations table (DESTRUCTIVE - backs up data first)
-- Create a backup of old conversations before dropping
DO $$
BEGIN
    -- Only create backup if old table exists and has the old structure
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'conversations'
    ) AND EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name = 'conversations'
        AND column_name = 'prompt'  -- Old schema had 'prompt' column
    ) THEN
        -- Backup old conversations
        CREATE TABLE IF NOT EXISTS conversations_backup_old AS
        SELECT * FROM conversations;

        -- Drop old table
        DROP TABLE IF EXISTS conversations CASCADE;

        RAISE NOTICE 'Old conversations table backed up to conversations_backup_old and dropped';
    END IF;
END $$;

-- Step 2: No extension needed - using built-in gen_random_uuid()
-- Note: gen_random_uuid() is built into PostgreSQL 13+ and Supabase

-- Step 3: Create new tables (using IF NOT EXISTS for safety)

-- User profiles (may already exist)
CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    display_name TEXT,
    preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id)
);

-- Persona groups for organizing personas
CREATE TABLE IF NOT EXISTS persona_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Personas table for storing persona profiles
CREATE TABLE IF NOT EXISTS personas (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    group_id UUID REFERENCES persona_groups(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    role TEXT,
    company TEXT,
    age_stage TEXT,
    goals JSONB DEFAULT '[]'::jsonb,
    pains JSONB DEFAULT '[]'::jsonb,
    behaviors TEXT,
    tools TEXT,
    stakeholders JSONB DEFAULT '[]'::jsonb,
    quotes JSONB DEFAULT '[]'::jsonb,
    tags JSONB DEFAULT '[]'::jsonb,
    notes TEXT,
    archived BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Persona relationships for network visualization
CREATE TABLE IF NOT EXISTS persona_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    from_persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    to_persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,
    label TEXT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(from_persona_id, to_persona_id)
);

-- NEW Conversations table for multi-persona chat sessions
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Many-to-many relationship between conversations and personas
CREATE TABLE IF NOT EXISTS conversation_participants (
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (conversation_id, persona_id)
);

-- Messages within conversations
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    persona_id UUID REFERENCES personas(id) ON DELETE SET NULL,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Step 4: Create indexes
CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX IF NOT EXISTS idx_persona_groups_user_id ON persona_groups(user_id);
CREATE INDEX IF NOT EXISTS idx_personas_user_id ON personas(user_id);
CREATE INDEX IF NOT EXISTS idx_personas_group_id ON personas(group_id);
CREATE INDEX IF NOT EXISTS idx_personas_archived ON personas(archived);
CREATE INDEX IF NOT EXISTS idx_persona_relationships_user_id ON persona_relationships(user_id);
CREATE INDEX IF NOT EXISTS idx_persona_relationships_from ON persona_relationships(from_persona_id);
CREATE INDEX IF NOT EXISTS idx_persona_relationships_to ON persona_relationships(to_persona_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_participants_conversation ON conversation_participants(conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversation_participants_persona ON conversation_participants(persona_id);
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

-- Step 5: Enable Row Level Security
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE persona_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE personas ENABLE ROW LEVEL SECURITY;
ALTER TABLE persona_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;

-- Step 6: Drop existing policies if they exist (to avoid conflicts)
DROP POLICY IF EXISTS "Users can view own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can insert own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can update own profile" ON user_profiles;
DROP POLICY IF EXISTS "Users can delete own profile" ON user_profiles;

DROP POLICY IF EXISTS "Users can view own persona groups" ON persona_groups;
DROP POLICY IF EXISTS "Users can insert own persona groups" ON persona_groups;
DROP POLICY IF EXISTS "Users can update own persona groups" ON persona_groups;
DROP POLICY IF EXISTS "Users can delete own persona groups" ON persona_groups;

DROP POLICY IF EXISTS "Users can view own personas" ON personas;
DROP POLICY IF EXISTS "Users can insert own personas" ON personas;
DROP POLICY IF EXISTS "Users can update own personas" ON personas;
DROP POLICY IF EXISTS "Users can delete own personas" ON personas;

DROP POLICY IF EXISTS "Users can view own persona relationships" ON persona_relationships;
DROP POLICY IF EXISTS "Users can insert own persona relationships" ON persona_relationships;
DROP POLICY IF EXISTS "Users can update own persona relationships" ON persona_relationships;
DROP POLICY IF EXISTS "Users can delete own persona relationships" ON persona_relationships;

DROP POLICY IF EXISTS "Users can view own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can insert own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can update own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can delete own conversations" ON conversations;

DROP POLICY IF EXISTS "Users can view participants of own conversations" ON conversation_participants;
DROP POLICY IF EXISTS "Users can manage participants of own conversations" ON conversation_participants;

DROP POLICY IF EXISTS "Users can view messages in own conversations" ON messages;
DROP POLICY IF EXISTS "Users can insert messages in own conversations" ON messages;
DROP POLICY IF EXISTS "Users can delete messages in own conversations" ON messages;

-- Step 7: Create RLS Policies

-- User Profiles
CREATE POLICY "Users can view own profile"
    ON user_profiles FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own profile"
    ON user_profiles FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own profile"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own profile"
    ON user_profiles FOR DELETE
    USING (auth.uid() = user_id);

-- Persona Groups
CREATE POLICY "Users can view own persona groups"
    ON persona_groups FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own persona groups"
    ON persona_groups FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own persona groups"
    ON persona_groups FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own persona groups"
    ON persona_groups FOR DELETE
    USING (auth.uid() = user_id);

-- Personas
CREATE POLICY "Users can view own personas"
    ON personas FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own personas"
    ON personas FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own personas"
    ON personas FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own personas"
    ON personas FOR DELETE
    USING (auth.uid() = user_id);

-- Persona Relationships
CREATE POLICY "Users can view own persona relationships"
    ON persona_relationships FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own persona relationships"
    ON persona_relationships FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own persona relationships"
    ON persona_relationships FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own persona relationships"
    ON persona_relationships FOR DELETE
    USING (auth.uid() = user_id);

-- Conversations
CREATE POLICY "Users can view own conversations"
    ON conversations FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own conversations"
    ON conversations FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own conversations"
    ON conversations FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own conversations"
    ON conversations FOR DELETE
    USING (auth.uid() = user_id);

-- Conversation Participants
CREATE POLICY "Users can view participants of own conversations"
    ON conversation_participants FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM conversations
        WHERE conversations.id = conversation_participants.conversation_id
        AND conversations.user_id = auth.uid()
    ));

CREATE POLICY "Users can manage participants of own conversations"
    ON conversation_participants FOR ALL
    USING (EXISTS (
        SELECT 1 FROM conversations
        WHERE conversations.id = conversation_participants.conversation_id
        AND conversations.user_id = auth.uid()
    ))
    WITH CHECK (EXISTS (
        SELECT 1 FROM conversations
        WHERE conversations.id = conversation_participants.conversation_id
        AND conversations.user_id = auth.uid()
    ));

-- Messages
CREATE POLICY "Users can view messages in own conversations"
    ON messages FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM conversations
        WHERE conversations.id = messages.conversation_id
        AND conversations.user_id = auth.uid()
    ));

CREATE POLICY "Users can insert messages in own conversations"
    ON messages FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM conversations
        WHERE conversations.id = messages.conversation_id
        AND conversations.user_id = auth.uid()
    ));

CREATE POLICY "Users can delete messages in own conversations"
    ON messages FOR DELETE
    USING (EXISTS (
        SELECT 1 FROM conversations
        WHERE conversations.id = messages.conversation_id
        AND conversations.user_id = auth.uid()
    ));

-- Step 8: Create triggers

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop existing triggers if they exist
DROP TRIGGER IF EXISTS update_user_profiles_updated_at ON user_profiles;
DROP TRIGGER IF EXISTS update_persona_groups_updated_at ON persona_groups;
DROP TRIGGER IF EXISTS update_personas_updated_at ON personas;
DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;

-- Create triggers
CREATE TRIGGER update_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_persona_groups_updated_at
    BEFORE UPDATE ON persona_groups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_personas_updated_at
    BEFORE UPDATE ON personas
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Migration complete!
-- Your old conversations are backed up in 'conversations_backup_old' table
SELECT 'Migration complete! All V1 tables created successfully.' AS status;
