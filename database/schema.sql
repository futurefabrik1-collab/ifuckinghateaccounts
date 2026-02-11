-- Receipt Checker SaaS Database Schema
-- For Supabase PostgreSQL

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- RECEIPTS TABLE
-- ============================================================================
CREATE TABLE receipts (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  
  -- File information
  filename TEXT NOT NULL,
  file_path TEXT NOT NULL,  -- Encrypted relative path
  file_size INTEGER,
  file_type TEXT,
  
  -- OCR and extracted data (encrypted)
  ocr_text TEXT,  -- Encrypted full OCR text
  
  -- Parsed receipt data
  amount DECIMAL(10,2),
  currency TEXT DEFAULT 'EUR',
  date DATE,
  vendor TEXT,
  
  -- Categorization
  tags TEXT[],
  category TEXT,
  
  -- Statement matching
  statement_id UUID REFERENCES statements(id) ON DELETE SET NULL,
  transaction_row INTEGER,  -- Which row in the statement CSV
  matched BOOLEAN DEFAULT FALSE,
  match_confidence INTEGER DEFAULT 0,
  manually_matched BOOLEAN DEFAULT FALSE,
  manually_unmatched BOOLEAN DEFAULT FALSE,
  
  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  -- Indexes for performance
  CONSTRAINT receipts_user_id_idx UNIQUE (user_id, filename)
);

-- ============================================================================
-- STATEMENTS TABLE
-- ============================================================================
CREATE TABLE statements (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  
  -- File information
  filename TEXT NOT NULL,
  file_path TEXT NOT NULL,  -- Encrypted relative path
  file_size INTEGER,
  
  -- Statement metadata
  total_transactions INTEGER DEFAULT 0,
  matched_count INTEGER DEFAULT 0,
  unmatched_count INTEGER DEFAULT 0,
  
  -- Date range
  start_date DATE,
  end_date DATE,
  
  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  CONSTRAINT statements_user_id_idx UNIQUE (user_id, filename)
);

-- ============================================================================
-- SUBSCRIPTIONS TABLE
-- ============================================================================
CREATE TABLE subscriptions (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
  
  -- Stripe data
  stripe_customer_id TEXT UNIQUE NOT NULL,
  stripe_subscription_id TEXT UNIQUE,
  stripe_price_id TEXT NOT NULL,
  
  -- Subscription status
  status TEXT NOT NULL DEFAULT 'trialing',  -- trialing, active, past_due, canceled, incomplete
  
  -- Billing
  current_period_start TIMESTAMPTZ,
  current_period_end TIMESTAMPTZ,
  cancel_at_period_end BOOLEAN DEFAULT FALSE,
  canceled_at TIMESTAMPTZ,
  
  -- Trial
  trial_start TIMESTAMPTZ,
  trial_end TIMESTAMPTZ,
  
  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  
  CONSTRAINT subscriptions_user_id_unique UNIQUE (user_id)
);

-- ============================================================================
-- USER PROFILES TABLE (extended auth.users)
-- ============================================================================
CREATE TABLE user_profiles (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  
  -- Profile data
  full_name TEXT,
  company_name TEXT,
  
  -- Preferences
  currency TEXT DEFAULT 'EUR',
  language TEXT DEFAULT 'de',
  
  -- Usage stats
  total_receipts INTEGER DEFAULT 0,
  total_statements INTEGER DEFAULT 0,
  storage_used_bytes BIGINT DEFAULT 0,
  
  -- Metadata
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- AUDIT LOG TABLE (optional, for tracking important actions)
-- ============================================================================
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
  
  -- Action details
  action TEXT NOT NULL,  -- 'upload_receipt', 'delete_receipt', 'match', 'subscribe', etc.
  table_name TEXT,
  record_id UUID,
  
  -- Changes (JSON)
  old_values JSONB,
  new_values JSONB,
  
  -- Metadata
  ip_address INET,
  user_agent TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================================================

-- Enable RLS on all tables
ALTER TABLE receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE statements ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Receipts policies
CREATE POLICY "Users can view their own receipts"
  ON receipts FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own receipts"
  ON receipts FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own receipts"
  ON receipts FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own receipts"
  ON receipts FOR DELETE
  USING (auth.uid() = user_id);

-- Statements policies
CREATE POLICY "Users can view their own statements"
  ON statements FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own statements"
  ON statements FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own statements"
  ON statements FOR UPDATE
  USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own statements"
  ON statements FOR DELETE
  USING (auth.uid() = user_id);

-- Subscriptions policies
CREATE POLICY "Users can view their own subscription"
  ON subscriptions FOR SELECT
  USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own subscription"
  ON subscriptions FOR INSERT
  WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own subscription"
  ON subscriptions FOR UPDATE
  USING (auth.uid() = user_id);

-- User profiles policies
CREATE POLICY "Users can view their own profile"
  ON user_profiles FOR SELECT
  USING (auth.uid() = id);

CREATE POLICY "Users can update their own profile"
  ON user_profiles FOR UPDATE
  USING (auth.uid() = id);

-- Audit logs policies (read-only for users)
CREATE POLICY "Users can view their own audit logs"
  ON audit_logs FOR SELECT
  USING (auth.uid() = user_id);

-- ============================================================================
-- FUNCTIONS AND TRIGGERS
-- ============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply updated_at triggers
CREATE TRIGGER update_receipts_updated_at
  BEFORE UPDATE ON receipts
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_statements_updated_at
  BEFORE UPDATE ON statements
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at
  BEFORE UPDATE ON subscriptions
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_profiles_updated_at
  BEFORE UPDATE ON user_profiles
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- Function to create user profile automatically on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.user_profiles (id, full_name)
  VALUES (NEW.id, NEW.raw_user_meta_data->>'full_name');
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to create profile on user signup
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW
  EXECUTE FUNCTION public.handle_new_user();

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

-- Receipts indexes
CREATE INDEX idx_receipts_user_id ON receipts(user_id);
CREATE INDEX idx_receipts_statement_id ON receipts(statement_id);
CREATE INDEX idx_receipts_date ON receipts(date);
CREATE INDEX idx_receipts_matched ON receipts(matched);
CREATE INDEX idx_receipts_created_at ON receipts(created_at DESC);

-- Statements indexes
CREATE INDEX idx_statements_user_id ON statements(user_id);
CREATE INDEX idx_statements_created_at ON statements(created_at DESC);

-- Subscriptions indexes
CREATE INDEX idx_subscriptions_user_id ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_stripe_customer_id ON subscriptions(stripe_customer_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);

-- Audit logs indexes
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- ============================================================================
-- GRANTS (if needed for service role)
-- ============================================================================

-- Grant necessary permissions
-- (Supabase handles most of this automatically with RLS)

-- ============================================================================
-- SEED DATA (optional, for testing)
-- ============================================================================

-- You can add test data here for development
-- Example:
-- INSERT INTO user_profiles (id, full_name) VALUES (...);

COMMENT ON TABLE receipts IS 'Stores receipt metadata with encrypted OCR text';
COMMENT ON TABLE statements IS 'Stores bank statement metadata';
COMMENT ON TABLE subscriptions IS 'Tracks Stripe subscriptions for billing';
COMMENT ON TABLE user_profiles IS 'Extended user profile information';
COMMENT ON TABLE audit_logs IS 'Audit trail of important user actions';
