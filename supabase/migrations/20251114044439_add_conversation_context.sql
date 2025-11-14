-- Add context column to conversations table
-- This allows users to provide additional background information that informs persona responses

ALTER TABLE conversations
ADD COLUMN context TEXT;

-- Add comment for documentation
COMMENT ON COLUMN conversations.context IS 'User-provided background information that helps inform persona responses in the conversation';
