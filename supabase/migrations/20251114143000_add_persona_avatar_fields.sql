-- Add avatar fields to personas table
-- Migration: Add avatar_emoji and avatar_color columns

-- Add avatar_emoji column (stores single emoji like "👨‍💼")
ALTER TABLE personas
ADD COLUMN avatar_emoji TEXT;

-- Add avatar_color column (stores hex color like "#28A2AB")
ALTER TABLE personas
ADD COLUMN avatar_color TEXT;

-- Add comment for documentation
COMMENT ON COLUMN personas.avatar_emoji IS 'Emoji avatar for persona display (single emoji character)';
COMMENT ON COLUMN personas.avatar_color IS 'Custom avatar background color (hex format like #28A2AB)';
