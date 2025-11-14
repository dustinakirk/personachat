-- Add custom_fields column to personas table for flexible, domain-specific attributes
-- This allows personas to store arbitrary structured data beyond the predefined schema

ALTER TABLE personas
ADD COLUMN custom_fields JSONB DEFAULT '{}'::jsonb;

-- Create index on custom_fields for better query performance on JSONB operations
CREATE INDEX idx_personas_custom_fields ON personas USING GIN (custom_fields);

-- Add comment to document the column purpose
COMMENT ON COLUMN personas.custom_fields IS 'Flexible JSONB storage for domain-specific persona attributes (e.g., coaching_domains, education_credentials, capabilities, accomplishments)';
