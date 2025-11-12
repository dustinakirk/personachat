# 🚀 Quick Start: Deploy Your First Migration

Follow these 3 simple steps to activate automated migrations.

## Step 1: Set Up GitHub Secrets (2 minutes)

### Get Your Supabase Access Token
1. Open https://supabase.com/dashboard/account/tokens
2. Click **"Generate new token"**
3. Name it: `PersonaChat GitHub Actions`
4. Copy the token (save it somewhere safe!)

### Add Secrets to GitHub
1. Go to your repository on GitHub
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **"New repository secret"** and add:

**First Secret:**
- Name: `SUPABASE_ACCESS_TOKEN`
- Value: [paste the token from above]
- Click "Add secret"

**Second Secret:**
- Name: `SUPABASE_PROJECT_REF`
- Value: `jzinycxsxveexsghzcob`
- Click "Add secret"

✅ Done! GitHub can now access your Supabase database.

---

## Step 2: Commit and Push (1 minute)

Run these commands in your terminal:

```bash
# Add all new files
git add .github/ supabase/ scripts/ *.md .gitignore README.md CLAUDE.md

# Commit with a descriptive message
git commit -m "Add automated Supabase migrations via GitHub Actions

- Initialize Supabase CLI project structure
- Create GitHub Actions workflow for auto-migrations
- Move legacy scripts to scripts/legacy/ as fallback
- Update documentation with CI/CD setup instructions

This enables push-to-deploy migrations: when changes are pushed
to supabase/migrations/ on main, GitHub Actions automatically
applies them to production database."

# Push to GitHub (this triggers the migration!)
git push origin main
```

---

## Step 3: Watch It Run (1 minute)

1. Go to your GitHub repository
2. Click the **"Actions"** tab at the top
3. You'll see **"Run Supabase Migrations"** running (yellow dot 🟡)
4. Click on it to see real-time logs
5. Wait for the green checkmark ✅

**Expected output in logs:**
```
✓ Checkout repository
✓ Setup Supabase CLI
✓ Link to Supabase project
✓ Run migrations
✓ Verify migration success
```

---

## 🎉 Success!

Your database now has:
- ✅ All V1 tables created
- ✅ Row Level Security enabled
- ✅ Indexes for performance
- ✅ Triggers for timestamps
- ✅ Old conversations backed up

## 🔄 Future Migrations (30 seconds each)

Whenever you need to change the database:

```bash
# 1. Create new migration
supabase migration new add_my_feature

# 2. Edit the file in supabase/migrations/
code supabase/migrations/[new_file].sql

# 3. Commit and push
git add supabase/migrations/
git commit -m "Add my feature to database"
git push origin main

# Done! GitHub Actions applies it automatically
```

---

## 🆘 If Something Goes Wrong

### Workflow doesn't appear in Actions tab
- Wait 30 seconds and refresh
- Check you pushed to `main` branch: `git branch`
- Verify files changed: `git diff origin/main`

### "Access token not provided" error
- Go back to Step 1, double-check token is set correctly
- Try regenerating the token and updating the secret

### Migration SQL fails
- Check the error in Actions logs
- Test locally first: `supabase link --project-ref jzinycxsxveexsghzcob && supabase db push`
- Fallback: Run manually from Supabase dashboard

### Need immediate help
```bash
# Manual migration (requires database password)
python scripts/legacy/run_migration_direct.py
```

---

## 📖 Learn More

- Full setup details: `MIGRATION_SETUP_COMPLETE.md`
- GitHub secrets guide: `GITHUB_SECRETS_SETUP.md`
- Legacy fallback options: `scripts/legacy/README.md`
- Development workflow: `README.md`

---

**Ready?** Start with Step 1 above! 👆
