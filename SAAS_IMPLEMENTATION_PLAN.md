# SaaS Implementation Plan - Receipt Checker
**Date**: February 11, 2026
**Goal**: Transform Receipt Checker into a subscription-based SaaS product

---

## 🎯 Overview

Transform the current Receipt Checker into a multi-tenant SaaS application with:
1. Secure user authentication
2. Encrypted metadata database
3. Stripe subscription (19€/month)

---

## 📋 Requirements Analysis

### 1. User Authentication
**Options**:
- **Supabase** (Recommended)
  - ✅ Auth + Database in one
  - ✅ PostgreSQL built-in
  - ✅ Row-level security (RLS)
  - ✅ Free tier: 50,000 monthly active users
  - ✅ Built-in encryption
  - ✅ Real-time subscriptions
  - ❌ Learning curve for Python integration
  
- **Clerk**
  - ✅ Easy to integrate
  - ✅ Beautiful pre-built UI
  - ✅ User management dashboard
  - ✅ Free tier: 10,000 monthly active users
  - ❌ Need separate database
  - ❌ More expensive at scale
  - ❌ Less control over data

**Recommendation**: **Supabase** - Better for SaaS, includes database, better scaling

### 2. Encrypted Metadata Database
**Requirements**:
- Store OCR text (encrypted)
- Store tags/categories
- Store file paths (relative, not actual files)
- User isolation (each user sees only their data)
- Fast search capabilities

**Schema Design**:
```sql
-- Users (handled by Supabase Auth)

-- Receipts metadata
CREATE TABLE receipts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users NOT NULL,
  filename TEXT NOT NULL,
  file_path TEXT NOT NULL, -- Encrypted relative path
  ocr_text TEXT, -- Encrypted OCR text
  amount DECIMAL(10,2),
  currency TEXT DEFAULT 'EUR',
  date DATE,
  vendor TEXT,
  tags TEXT[], -- Array of tags
  category TEXT,
  statement_id UUID REFERENCES statements(id),
  matched BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Statements metadata
CREATE TABLE statements (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users NOT NULL,
  filename TEXT NOT NULL,
  file_path TEXT NOT NULL,
  total_transactions INTEGER,
  matched_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Subscriptions (synced with Stripe)
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users NOT NULL,
  stripe_customer_id TEXT UNIQUE NOT NULL,
  stripe_subscription_id TEXT UNIQUE,
  status TEXT NOT NULL, -- active, canceled, past_due, etc.
  current_period_end TIMESTAMPTZ,
  cancel_at_period_end BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable Row Level Security
ALTER TABLE receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE statements ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Users can only access their own receipts"
  ON receipts FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY "Users can only access their own statements"
  ON statements FOR ALL
  USING (auth.uid() = user_id);

CREATE POLICY "Users can only access their own subscription"
  ON subscriptions FOR ALL
  USING (auth.uid() = user_id);
```

### 3. Stripe Integration
**Plan**:
- **Price**: 19€/month
- **Product**: "Receipt Checker Pro"
- **Features**: Unlimited receipts, statements, OCR processing

**Stripe Setup**:
```python
# Product: Receipt Checker Pro
# Price: 19.00 EUR/month (recurring)
# Payment methods: Card, SEPA Direct Debit (for EU)
```

---

## 🏗️ Architecture Changes

### Current Architecture
```
User → Flask App → Local File System
                 → SQLite/CSV files
```

### New Architecture
```
User → Flask App → Supabase Auth (authentication)
                 → Supabase DB (encrypted metadata)
                 → Railway Storage (actual receipt files)
                 → Stripe (subscriptions)
```

### File Storage Strategy
**Option 1: Railway Volumes** (Recommended for now)
- ✅ Already using Railway
- ✅ Simple implementation
- ✅ User folders: `/app/statements/{user_id}/`
- ❌ Limited by Railway volume size
- ❌ Not easily scalable

**Option 2: S3/Supabase Storage** (Future upgrade)
- ✅ Unlimited storage
- ✅ Better for scaling
- ✅ Built-in encryption
- ❌ Additional costs
- ❌ More complex implementation

**Recommendation**: Start with Railway volumes, migrate to S3/Supabase Storage later

---

## 📐 Implementation Phases

### Phase 1: Setup & Configuration (Day 1)
1. Create Supabase project
2. Set up Stripe account (test mode)
3. Create database schema
4. Install required packages

**New Dependencies**:
```txt
supabase==2.3.0
stripe==7.9.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
```

### Phase 2: Authentication (Day 2-3)
1. Implement Supabase authentication
2. Create login/register pages
3. Add protected routes
4. Session management
5. User profile page

**Files to Create/Modify**:
- `web/auth_routes.py` - Auth endpoints (EXPAND)
- `web/templates/auth/login.html` - Login page (EXPAND)
- `web/templates/auth/register.html` - Register page (NEW)
- `src/supabase_client.py` - Supabase integration (NEW)
- `src/middleware.py` - Auth middleware (NEW)

### Phase 3: Database Migration (Day 4-5)
1. Create encrypted metadata tables
2. Implement data encryption/decryption
3. Migrate existing logic to use Supabase
4. Add user-based file isolation

**Files to Modify**:
- `src/database.py` - Add Supabase queries
- `src/models.py` - Update models
- `web/app.py` - Update all routes to use user context

### Phase 4: Stripe Integration (Day 6-7)
1. Create Stripe product and price
2. Implement checkout flow
3. Add webhook handlers
4. Create subscription management UI
5. Add subscription checks to all endpoints

**Files to Create**:
- `src/stripe_client.py` - Stripe integration
- `web/subscription_routes.py` - Subscription endpoints
- `web/templates/subscription/checkout.html` - Checkout page
- `web/templates/subscription/manage.html` - Manage subscription

### Phase 5: Testing & Deployment (Day 8-9)
1. End-to-end testing
2. Security audit
3. Performance testing
4. Production deployment
5. Documentation

---

## 🔐 Security Considerations

### Data Encryption
```python
from cryptography.fernet import Fernet
import os

# Generate encryption key (store in environment variable)
ENCRYPTION_KEY = os.getenv('ENCRYPTION_KEY')
cipher_suite = Fernet(ENCRYPTION_KEY)

def encrypt_text(text: str) -> str:
    """Encrypt sensitive text before storing in database"""
    return cipher_suite.encrypt(text.encode()).decode()

def decrypt_text(encrypted_text: str) -> str:
    """Decrypt text when retrieving from database"""
    return cipher_suite.decrypt(encrypted_text.encode()).decode()
```

### User Data Isolation
- Each user gets their own folder: `statements/{user_id}/`
- All database queries filtered by `user_id`
- Row-level security enforced by Supabase
- File access validated on every request

### Environment Variables
```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Stripe
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRICE_ID=price_... # 19€/month plan

# Encryption
ENCRYPTION_KEY=your-fernet-key

# App
SECRET_KEY=your-flask-secret-key
```

---

## 💰 Cost Estimates

### Monthly Costs
| Service | Plan | Cost |
|---------|------|------|
| Supabase | Free tier | €0 (up to 500MB, 50k users) |
| Railway | Hobby | $5/month (€4.70) |
| Stripe | Standard | 1.4% + €0.25 per transaction |
| Domain (optional) | - | €10/year |

**Revenue Model**:
- Price: €19/month
- Target: 100 users
- Monthly Revenue: €1,900
- Monthly Costs: ~€5 + Stripe fees (~€250) = €255
- **Profit Margin**: ~87%

---

## 📊 User Flow

### New User Journey
1. Land on homepage → Click "Sign Up"
2. Register with email/password
3. Verify email (optional)
4. Redirect to checkout (Stripe)
5. Subscribe to €19/month plan
6. Redirect to app dashboard
7. Upload first statement & receipts
8. Start matching!

### Existing Features (Enhanced)
- Upload statements → Now stored per user
- Upload receipts → Encrypted metadata saved
- OCR processing → Results encrypted in database
- Matching → Works with user's data only
- Pool management → User-specific pool

---

## 🚀 Go-Live Checklist

### Pre-Launch
- [ ] Supabase production database created
- [ ] Stripe production mode enabled
- [ ] All environment variables set
- [ ] SSL certificate configured
- [ ] Terms of Service & Privacy Policy pages
- [ ] GDPR compliance check
- [ ] Backup strategy implemented

### Launch
- [ ] Deploy to Railway production
- [ ] Test complete user flow
- [ ] Monitor error logs
- [ ] Set up Stripe webhook monitoring
- [ ] Create support email/system

### Post-Launch
- [ ] Monitor user registrations
- [ ] Track subscription metrics
- [ ] Gather user feedback
- [ ] Plan feature roadmap

---

## 📈 Success Metrics

### Week 1
- 10 signups
- 5 paying subscribers
- €95 MRR

### Month 1
- 50 signups
- 25 paying subscribers
- €475 MRR

### Month 3
- 200 signups
- 100 paying subscribers
- €1,900 MRR

---

## 🛠️ Next Steps

**Immediate Actions**:
1. Choose: Supabase vs Clerk (Recommendation: Supabase)
2. Set up Supabase project
3. Set up Stripe account
4. Start Phase 1 implementation

**Questions to Answer**:
1. Do you want to start with Supabase or Clerk?
2. Should we support SEPA payments (EU) or card-only?
3. Free trial period? (e.g., 14 days)
4. What should we name the product? (Currently "I FUCKING HATE COUNTS")
5. Need invoice generation for B2B customers?

---

**Estimated Timeline**: 9-14 days for full implementation
**Complexity**: Medium-High
**Risk Level**: Low (all services proven and stable)

