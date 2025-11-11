# Database Setup Instructions

This guide walks you through setting up the Supabase database for PersonaChat.

## Prerequisites

- A Supabase project created at [supabase.com](https://supabase.com)
- Your Supabase project URL and anon key configured in `.env`

## Step 1: Run the Database Schema

1. Log in to your Supabase dashboard at https://supabase.com/dashboard
2. Select your project (URL: https://jzinycxsxveexsghzcob.supabase.co)
3. Navigate to the **SQL Editor** in the left sidebar
4. Click **New Query**
5. Copy the entire contents of `schema.sql` from this repository
6. Paste it into the SQL Editor
7. Click **Run** to execute the schema

This will create:
- `user_profiles` table for extended user information
- `conversations` table for chat history
- Indexes for faster queries
- Row Level Security (RLS) policies to protect user data

## Step 2: Verify Table Creation

1. In your Supabase dashboard, navigate to **Table Editor**
2. You should see two new tables:
   - `user_profiles`
   - `conversations`
3. Click on each table to verify the columns are correct

### Expected Schema

**user_profiles:**
- `id` (UUID, primary key)
- `user_id` (UUID, references auth.users)
- `display_name` (TEXT)
- `preferences` (JSONB)
- `created_at` (TIMESTAMP)
- `updated_at` (TIMESTAMP)

**conversations:**
- `id` (UUID, primary key)
- `user_id` (UUID, references auth.users)
- `prompt` (TEXT)
- `response` (TEXT)
- `created_at` (TIMESTAMP)

## Step 3: Verify Row Level Security (RLS)

1. In the Table Editor, click on `user_profiles`
2. Click on the **Policies** tab at the top
3. You should see 4 policies:
   - "Users can view own profile"
   - "Users can insert own profile"
   - "Users can update own profile"
   - "Users can delete own profile"

4. Repeat for the `conversations` table, which should have 3 policies:
   - "Users can view own conversations"
   - "Users can insert own conversations"
   - "Users can delete own conversations"

**Important:** RLS ensures that users can only access their own data. Do not disable RLS in production.

## Step 4: Test Database Connectivity

1. Ensure your `.env` file has the correct values:
   ```
   SUPABASE_URL=https://jzinycxsxveexsghzcob.supabase.co
   SUPABASE_ANON_KEY=your-actual-anon-key-here
   ```

2. Start your Flask development server:
   ```bash
   python api/index.py
   ```

3. Register a new user or log in
4. Navigate to `/application`
5. Submit a prompt to Gemini
6. The conversation should be saved to the database

## Step 5: Verify Data in Supabase

1. Return to the Supabase dashboard
2. Navigate to **Table Editor** > `conversations`
3. You should see your test conversation stored with:
   - Your user ID
   - The prompt you submitted
   - The Gemini response
   - A timestamp

## Troubleshooting

### Error: "relation 'conversations' does not exist"
- Make sure you ran the `schema.sql` file completely
- Check the SQL Editor for any error messages during schema creation

### Error: "new row violates row-level security policy"
- Verify that RLS policies were created correctly
- Ensure you're logged in (user_id must match auth.uid())
- Check that `auth.users` table exists in Supabase Auth

### Conversations not appearing in the UI
- Check browser console for JavaScript errors
- Verify the `/application` route is returning `conversations` in the template context
- Test the database query manually in Supabase SQL Editor:
  ```sql
  SELECT * FROM conversations WHERE user_id = 'your-user-id';
  ```

### "Supabase is not configured" error
- Double-check `.env` file exists and has correct values
- Restart the Flask server after changing `.env`
- Verify environment variables are loading: add `print(os.environ.get("SUPABASE_URL"))` to `config.py`

## Optional: Create User Profile on Registration

If you want to automatically create a user profile when users register, you can set up a Supabase Database Trigger:

1. Go to **Database** > **Triggers** in Supabase dashboard
2. Create a new trigger on `auth.users` table
3. Set it to run after INSERT
4. Execute a function that inserts into `user_profiles`:

```sql
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.user_profiles (user_id, display_name)
  VALUES (new.id, new.email);
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
```

This automatically creates a profile for every new user.

## Next Steps

With the database set up, you can now:
- View conversation history that persists across sessions
- Extend `user_profiles` to store custom preferences
- Add features like conversation search or filtering
- Implement conversation deletion
- Add personas or custom AI configurations per user
