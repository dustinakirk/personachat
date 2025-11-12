-- Add Persona Relationships Table
-- This migration creates the persona_relationships table to enable AI-driven
-- relationship detection and rich contextual awareness between personas.

-- Create persona_relationships table
CREATE TABLE IF NOT EXISTS persona_relationships (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    from_persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    to_persona_id UUID NOT NULL REFERENCES personas(id) ON DELETE CASCADE,
    relationship_type TEXT NOT NULL,  -- e.g., colleague, supervisor, friend, rival, etc.
    label TEXT,  -- Brief label for the relationship
    shared_context TEXT,  -- Shared history, common location, background, etc.
    interaction_style TEXT,  -- How these personas typically interact
    notes TEXT,  -- User's additional notes
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(from_persona_id, to_persona_id),
    -- Prevent self-relationships
    CHECK (from_persona_id != to_persona_id)
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_persona_relationships_user_id ON persona_relationships(user_id);
CREATE INDEX IF NOT EXISTS idx_persona_relationships_from ON persona_relationships(from_persona_id);
CREATE INDEX IF NOT EXISTS idx_persona_relationships_to ON persona_relationships(to_persona_id);
CREATE INDEX IF NOT EXISTS idx_persona_relationships_type ON persona_relationships(relationship_type);

-- Enable Row Level Security
ALTER TABLE persona_relationships ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Users can view own persona relationships" ON persona_relationships;
DROP POLICY IF EXISTS "Users can insert own persona relationships" ON persona_relationships;
DROP POLICY IF EXISTS "Users can update own persona relationships" ON persona_relationships;
DROP POLICY IF EXISTS "Users can delete own persona relationships" ON persona_relationships;

-- Create RLS Policies
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

-- Create trigger for updated_at
DROP TRIGGER IF EXISTS update_persona_relationships_updated_at ON persona_relationships;

CREATE TRIGGER update_persona_relationships_updated_at
    BEFORE UPDATE ON persona_relationships
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Migration complete
SELECT 'Persona relationships table created successfully.' AS status;
