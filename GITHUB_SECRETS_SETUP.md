# GitHub Secrets Setup Guide

To enable automated database migrations, you need to configure GitHub repository secrets.

## Required Secrets

### 1. SUPABASE_ACCESS_TOKEN

**Purpose:** Authenticates the Supabase CLI in GitHub Actions to manage your database.

**Steps to get it:**
1. Go to https://supabase.com/dashboard/account/tokens
2. Click "Generate new token"
3. Give it a descriptive name (e.g., "PersonaChat GitHub Actions")
4. Copy the generated token
5. **Important:** Save it immediately - you won't be able to see it again!

**Add to GitHub:**
1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `SUPABASE_ACCESS_TOKEN`
5. Value: Paste the token you copied
6. Click "Add secret"

### 2. SUPABASE_PROJECT_REF

**Purpose:** Identifies which Supabase project to connect to.

**Value:** `jzinycxsxveexsghzcob`

**Add to GitHub:**
1. In Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Name: `SUPABASE_PROJECT_REF`
4. Value: `jzinycxsxveexsghzcob`
5. Click "Add secret"

## Verification

After adding both secrets:

1. Go to the "Actions" tab in your GitHub repository
2. You should see the "Run Supabase Migrations" workflow listed
3. You can manually trigger it by:
   - Clicking on the workflow
   - Clicking "Run workflow" button
   - Selecting "main" branch
   - Clicking "Run workflow"

If configured correctly, the workflow will:
- ✅ Link to your Supabase project
- ✅ Apply any pending migrations
- ✅ Show success message

## Troubleshooting

### "Access token not provided" error
- Double-check that `SUPABASE_ACCESS_TOKEN` is correctly spelled
- Regenerate the token if needed and update the secret

### "Project not found" error
- Verify `SUPABASE_PROJECT_REF` is set to `jzinycxsxveexsghzcob`
- Ensure your Supabase project is active

### Workflow doesn't trigger
- Make sure you're pushing to the `main` branch
- Check that you've modified files in `supabase/migrations/`
- You can always trigger manually via "Run workflow" button

## Security Notes

- Never commit these secrets to your repository
- Tokens give access to your database - keep them secure
- You can revoke and regenerate tokens anytime from the Supabase dashboard
- GitHub encrypts secrets and only exposes them during workflow runs
