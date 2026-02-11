# Supabase Setup Guide

## Step 1: Create Supabase Project (10 minutes)

1. **Go to Supabase**: https://supabase.com
2. **Sign Up/Login** with GitHub or email
3. **Create New Project**:
   - Organization: Create new or use existing
   - Name: `receipt-checker` (or your choice)
   - Database Password: Generate strong password (save it!)
   - Region: Choose closest to your users (e.g., `eu-central-1` for Europe)
   - Pricing Plan: Free (sufficient for MVP)
   - Click "Create new project"

4. **Wait 2-3 minutes** for project to provision

## Step 2: Get API Keys (2 minutes)

Once project is ready:

1. Go to **Settings** (gear icon) → **API**
2. Copy the following values:

```bash
Project URL: https://xxxxxxxxxxxxx.supabase.co
anon public key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
service_role key: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (keep secret!)
```

3. Save these to your `.env` file

## Step 3: Run Database Schema (5 minutes)

1. In Supabase dashboard, go to **SQL Editor**
2. Click **New query**
3. Copy the entire contents of `database/schema.sql`
4. Paste into the SQL editor
5. Click **Run** (bottom right)
6. ✅ You should see "Success. No rows returned"

## Step 4: Configure Email Templates (Optional, 5 minutes)

1. Go to **Authentication** → **Email Templates**
2. Customize the templates:
   - Confirm signup
   - Magic Link
   - Change Email Address
   - Reset Password

3. Update sender name: "Receipt Checker" or your app name

## Step 5: Set Environment Variables

Create `.env` file in project root:

```bash
# Copy from .env.saas.example
cp .env.saas.example .env
```

Edit `.env` and fill in:

```bash
# Supabase (from Step 2)
SUPABASE_URL=https://xxxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Generate encryption key
# Run: python src/encryption.py
ENCRYPTION_KEY=your-generated-key-here

# Flask
SECRET_KEY=your-flask-secret-key-here

# Stripe (we'll add these next)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_...
```

## Step 6: Generate Encryption Key

```bash
cd "/Users/markburnett/DevPro/Receipt Checker"
python3 src/encryption.py
```

Copy the output and add to `.env` as `ENCRYPTION_KEY`

## Step 7: Install Dependencies

```bash
cd "/Users/markburnett/DevPro/Receipt Checker"
source venv/bin/activate
pip install -r requirements_saas.txt
```

## Step 8: Test Connection

Create a test script:

```python
# test_supabase.py
from src.supabase_client import supabase_client

# Test connection
result = supabase_client.select('user_profiles')
print(f"Connection test: {result}")
```

Run:
```bash
python test_supabase.py
```

Should output: `Connection test: {'success': True, 'data': []}`

## ✅ Supabase Setup Complete!

Your Supabase project is ready with:
- ✅ Database schema created
- ✅ Row-level security enabled
- ✅ API keys configured
- ✅ Encryption key generated
- ✅ Connection tested

---

## Next Steps

1. Set up Stripe account → See `SETUP_STRIPE.md`
2. Implement authentication routes
3. Test complete flow

---

## Troubleshooting

**Problem**: "relation 'user_profiles' does not exist"
- **Solution**: Run the schema.sql again in SQL Editor

**Problem**: "ENCRYPTION_KEY not set"
- **Solution**: Run `python src/encryption.py` and add key to `.env`

**Problem**: "Invalid API key"
- **Solution**: Check you're using the anon key, not the service role key for client

**Problem**: RLS blocks all queries
- **Solution**: Make sure you're authenticated first (sign in with test user)

---

## Database Access

**View Tables**:
1. Go to **Table Editor** in Supabase dashboard
2. You'll see: `receipts`, `statements`, `subscriptions`, `user_profiles`, `audit_logs`

**View Logs**:
1. Go to **Logs** → **Postgres Logs**
2. See all database queries and errors

**Reset Database** (if needed):
```sql
-- Drop all tables
DROP TABLE IF EXISTS audit_logs CASCADE;
DROP TABLE IF EXISTS receipts CASCADE;
DROP TABLE IF EXISTS statements CASCADE;
DROP TABLE IF EXISTS subscriptions CASCADE;
DROP TABLE IF EXISTS user_profiles CASCADE;

-- Then re-run schema.sql
```
