-- Migration: Remove Persona Groups and Persona Relationships
-- This migration removes the persona_groups and persona_relationships tables
-- and their associated columns from the personas table.

-- Drop foreign key constraints first
ALTER TABLE personas DROP CONSTRAINT IF EXISTS personas_group_id_fkey;

-- Remove columns from personas table
ALTER TABLE personas DROP COLUMN IF EXISTS group_id;
ALTER TABLE personas DROP COLUMN IF EXISTS stakeholders;

-- Drop indexes related to groups and relationships
DROP INDEX IF EXISTS idx_persona_groups_user_id;
DROP INDEX IF EXISTS idx_personas_group_id;
DROP INDEX IF EXISTS idx_persona_relationships_from_persona;
DROP INDEX IF EXISTS idx_persona_relationships_to_persona;
DROP INDEX IF EXISTS idx_persona_relationships_type;

-- Drop tables (CASCADE will remove associated policies and triggers)
DROP TABLE IF EXISTS persona_relationships CASCADE;
DROP TABLE IF EXISTS persona_groups CASCADE;
