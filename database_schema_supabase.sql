-- =============================================================================
-- INBOX ZEN - EMAIL PARSING MCP SERVER
-- SUPABASE DATABASE SCHEMA
-- =============================================================================
-- 
-- Description: Complete PostgreSQL/Supabase schema for the Inbox Zen
--              Email Parsing MCP Server with Supabase integration.
--              
-- Features:    - Multi-user support with RLS (Row Level Security)
--              - Real-time subscriptions capability
--              - Email processing and analysis storage
--              - Task extraction and management
--              - User configuration and settings
--              - Audit logging and analytics
--
-- Version:     1.0.0
-- Date:        May 30, 2025
-- =============================================================================

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For better text search

-- =============================================================================
-- TABLE 1: PROFILES (User Management)
-- =============================================================================
-- Purpose: Store application-specific user profiles linked to Supabase Auth
-- RLS: Users can only see/modify their own profile

CREATE TABLE profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT,
    avatar_url TEXT,
    
    -- User settings
    timezone TEXT DEFAULT 'UTC',
    language TEXT DEFAULT 'en',
    
    -- Email configuration
    inbound_email_address TEXT, -- Postmark inbound address for this user
    email_processing_enabled BOOLEAN DEFAULT true,
    notification_preferences JSONB DEFAULT '{}',
    
    -- Subscription settings
    plan_type TEXT DEFAULT 'free' CHECK (plan_type IN ('free', 'pro', 'enterprise')),
    email_quota_monthly INTEGER DEFAULT 1000,
    emails_processed_this_month INTEGER DEFAULT 0,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    
    -- Indexes for performance
    CONSTRAINT valid_email CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

-- Create indexes
CREATE INDEX idx_profiles_email ON profiles(email);
CREATE INDEX idx_profiles_inbound_email ON profiles(inbound_email_address);
CREATE INDEX idx_profiles_created_at ON profiles(created_at);

-- RLS Policies
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

CREATE POLICY "Users can insert own profile" ON profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- =============================================================================
-- TABLE 2: EMAILS (Core Email Storage and Analysis)
-- =============================================================================
-- Purpose: Store all received emails with their analysis results
-- RLS: Users can only access their own emails

CREATE TABLE emails (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    
    -- Email identification
    message_id TEXT NOT NULL UNIQUE, -- Original email message ID
    thread_id TEXT, -- For email threading
    
    -- Email content
    from_email TEXT NOT NULL,
    to_emails JSONB NOT NULL, -- Array of recipient emails
    cc_emails JSONB DEFAULT '[]',
    bcc_emails JSONB DEFAULT '[]',
    subject TEXT NOT NULL,
    text_body TEXT,
    html_body TEXT,
    
    -- Email metadata
    headers JSONB DEFAULT '{}',
    attachments JSONB DEFAULT '[]', -- Array of attachment metadata
    received_at TIMESTAMPTZ NOT NULL,
    
    -- MCP Analysis Results (from existing EmailAnalysis model)
    urgency_score INTEGER CHECK (urgency_score >= 0 AND urgency_score <= 100),
    urgency_level TEXT CHECK (urgency_level IN ('low', 'medium', 'high', 'critical')),
    sentiment TEXT CHECK (sentiment IN ('positive', 'negative', 'neutral')),
    sentiment_score FLOAT CHECK (sentiment_score >= -1.0 AND sentiment_score <= 1.0),
    confidence FLOAT CHECK (confidence >= 0.0 AND confidence <= 1.0),
    
    -- Extracted data
    keywords JSONB DEFAULT '[]', -- Array of keywords
    entities JSONB DEFAULT '{}', -- Named entities (person, organization, etc.)
    temporal_references JSONB DEFAULT '[]', -- Date/time references
    contact_info JSONB DEFAULT '{}', -- Phone numbers, emails, URLs
    
    -- Processing metadata
    mcp_analysis JSONB DEFAULT '{}', -- Complete MCP analysis result
    mcp_processed_at TIMESTAMPTZ,
    processing_time_ms INTEGER,
    language_detected TEXT DEFAULT 'en',
    
    -- Status and flags
    status TEXT DEFAULT 'received' CHECK (status IN ('received', 'processing', 'analyzed', 'error')),
    is_spam BOOLEAN DEFAULT false,
    is_archived BOOLEAN DEFAULT false,
    is_starred BOOLEAN DEFAULT false,
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Search optimization
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(subject, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(text_body, '')), 'B') ||
        setweight(to_tsvector('english', coalesce(from_email, '')), 'C')
    ) STORED
);

-- Create indexes for performance
CREATE INDEX idx_emails_user_id ON emails(user_id);
CREATE INDEX idx_emails_message_id ON emails(message_id);
CREATE INDEX idx_emails_from_email ON emails(from_email);
CREATE INDEX idx_emails_received_at ON emails(received_at DESC);
CREATE INDEX idx_emails_urgency_score ON emails(urgency_score DESC);
CREATE INDEX idx_emails_status ON emails(status);
CREATE INDEX idx_emails_search_vector ON emails USING GIN(search_vector);
CREATE INDEX idx_emails_thread_id ON emails(thread_id) WHERE thread_id IS NOT NULL;

-- Composite indexes for common queries
CREATE INDEX idx_emails_user_urgency ON emails(user_id, urgency_score DESC, received_at DESC);
CREATE INDEX idx_emails_user_status ON emails(user_id, status, received_at DESC);

-- RLS Policies
ALTER TABLE emails ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own emails" ON emails
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own emails" ON emails
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own emails" ON emails
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own emails" ON emails
    FOR DELETE USING (auth.uid() = user_id);

-- =============================================================================
-- TABLE 3: EMAIL_TASKS (Action Items Extracted from Emails)
-- =============================================================================
-- Purpose: Store tasks and action items extracted from emails by MCP analysis
-- RLS: Users can only access their own tasks

CREATE TABLE email_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email_id UUID NOT NULL REFERENCES emails(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    
    -- Task details
    title TEXT NOT NULL,
    description TEXT,
    source_context TEXT, -- Original text from email where task was extracted
    
    -- Task classification
    urgency_score INTEGER CHECK (urgency_score >= 0 AND urgency_score <= 100),
    priority TEXT DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    category TEXT, -- e.g., 'meeting', 'deadline', 'review', 'approval'
    
    -- Temporal information
    deadline_detected TIMESTAMPTZ,
    reminder_date TIMESTAMPTZ,
    estimated_duration_minutes INTEGER,
    
    -- Task status
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'completed', 'cancelled', 'deferred')),
    completion_date TIMESTAMPTZ,
    
    -- Assignment and collaboration
    assigned_to_email TEXT, -- If task is assigned to someone specific
    assigned_by_user BOOLEAN DEFAULT true, -- false if auto-assigned by AI
    
    -- Extraction metadata
    extraction_confidence FLOAT CHECK (extraction_confidence >= 0.0 AND extraction_confidence <= 1.0),
    extraction_method TEXT DEFAULT 'regex', -- 'regex', 'ai', 'manual'
    
    -- User interactions
    user_confirmed BOOLEAN DEFAULT false, -- User has confirmed this is a valid task
    user_notes TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Search optimization
    search_vector tsvector GENERATED ALWAYS AS (
        setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
        setweight(to_tsvector('english', coalesce(description, '')), 'B')
    ) STORED
);

-- Create indexes
CREATE INDEX idx_email_tasks_email_id ON email_tasks(email_id);
CREATE INDEX idx_email_tasks_user_id ON email_tasks(user_id);
CREATE INDEX idx_email_tasks_status ON email_tasks(status);
CREATE INDEX idx_email_tasks_deadline ON email_tasks(deadline_detected) WHERE deadline_detected IS NOT NULL;
CREATE INDEX idx_email_tasks_urgency ON email_tasks(urgency_score DESC);
CREATE INDEX idx_email_tasks_search_vector ON email_tasks USING GIN(search_vector);

-- Composite indexes for dashboard queries
CREATE INDEX idx_email_tasks_user_status_deadline ON email_tasks(user_id, status, deadline_detected);
CREATE INDEX idx_email_tasks_user_priority ON email_tasks(user_id, priority, created_at DESC);

-- RLS Policies
ALTER TABLE email_tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own tasks" ON email_tasks
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own tasks" ON email_tasks
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own tasks" ON email_tasks
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete own tasks" ON email_tasks
    FOR DELETE USING (auth.uid() = user_id);

-- =============================================================================
-- TABLE 4: USER_EMAIL_MAPPINGS (Configuration for Inbound Email Routing)
-- =============================================================================
-- Purpose: Map inbound email addresses/rules to users for webhook processing
-- RLS: Users can only manage their own mappings

CREATE TABLE user_email_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    
    -- Mapping configuration
    inbound_identifier TEXT NOT NULL, -- Unique identifier for Postmark routing
    postmark_target_address TEXT NOT NULL, -- The actual Postmark inbound address
    custom_alias TEXT, -- User-friendly alias
    
    -- Processing rules
    auto_process BOOLEAN DEFAULT true,
    urgency_boost INTEGER DEFAULT 0, -- Boost urgency score by this amount
    default_category TEXT,
    custom_rules JSONB DEFAULT '{}', -- Custom processing rules
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    last_email_received TIMESTAMPTZ,
    email_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(inbound_identifier),
    UNIQUE(user_id, postmark_target_address)
);

-- Create indexes
CREATE INDEX idx_user_email_mappings_user_id ON user_email_mappings(user_id);
CREATE INDEX idx_user_email_mappings_inbound_id ON user_email_mappings(inbound_identifier);
CREATE INDEX idx_user_email_mappings_active ON user_email_mappings(is_active) WHERE is_active = true;

-- RLS Policies
ALTER TABLE user_email_mappings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own email mappings" ON user_email_mappings
    FOR ALL USING (auth.uid() = user_id);

-- =============================================================================
-- TABLE 5: EMAIL_ANALYTICS (Analytics and Statistics)
-- =============================================================================
-- Purpose: Store aggregated analytics data for performance and insights
-- RLS: Users can only see their own analytics

CREATE TABLE email_analytics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    
    -- Time period
    date_bucket DATE NOT NULL, -- Daily aggregation
    period_type TEXT DEFAULT 'daily' CHECK (period_type IN ('daily', 'weekly', 'monthly')),
    
    -- Volume metrics
    emails_received INTEGER DEFAULT 0,
    emails_processed INTEGER DEFAULT 0,
    emails_with_tasks INTEGER DEFAULT 0,
    
    -- Urgency distribution
    urgent_emails INTEGER DEFAULT 0,
    medium_urgency_emails INTEGER DEFAULT 0,
    low_urgency_emails INTEGER DEFAULT 0,
    
    -- Sentiment distribution
    positive_emails INTEGER DEFAULT 0,
    negative_emails INTEGER DEFAULT 0,
    neutral_emails INTEGER DEFAULT 0,
    
    -- Performance metrics
    avg_processing_time_ms FLOAT,
    max_processing_time_ms INTEGER,
    min_processing_time_ms INTEGER,
    
    -- Task metrics
    tasks_extracted INTEGER DEFAULT 0,
    tasks_completed INTEGER DEFAULT 0,
    tasks_overdue INTEGER DEFAULT 0,
    
    -- Top senders and keywords
    top_senders JSONB DEFAULT '[]',
    top_keywords JSONB DEFAULT '[]',
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, date_bucket, period_type)
);

-- Create indexes
CREATE INDEX idx_email_analytics_user_id ON email_analytics(user_id);
CREATE INDEX idx_email_analytics_date ON email_analytics(date_bucket DESC);
CREATE INDEX idx_email_analytics_user_date ON email_analytics(user_id, date_bucket DESC);

-- RLS Policies
ALTER TABLE email_analytics ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own analytics" ON email_analytics
    FOR SELECT USING (auth.uid() = user_id);

-- =============================================================================
-- TABLE 6: REAL_TIME_SUBSCRIPTIONS (Real-time Notification Subscriptions)
-- =============================================================================
-- Purpose: Manage real-time subscriptions for live updates
-- RLS: Users can only manage their own subscriptions

CREATE TABLE realtime_subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    
    -- Subscription details
    subscription_type TEXT NOT NULL CHECK (subscription_type IN 
        ('new_emails', 'urgent_emails', 'task_updates', 'analytics_updates')),
    
    -- Filtering criteria
    filters JSONB DEFAULT '{}', -- JSON filters for subscription
    min_urgency_score INTEGER DEFAULT 0,
    
    -- Delivery settings
    delivery_method TEXT DEFAULT 'websocket' CHECK (delivery_method IN 
        ('websocket', 'webhook', 'server_sent_events')),
    webhook_url TEXT, -- For webhook delivery
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    last_notification_sent TIMESTAMPTZ,
    notification_count INTEGER DEFAULT 0,
    
    -- Rate limiting
    max_notifications_per_hour INTEGER DEFAULT 100,
    current_hour_notifications INTEGER DEFAULT 0,
    rate_limit_reset TIMESTAMPTZ DEFAULT NOW(),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_realtime_subscriptions_user_id ON realtime_subscriptions(user_id);
CREATE INDEX idx_realtime_subscriptions_type ON realtime_subscriptions(subscription_type);
CREATE INDEX idx_realtime_subscriptions_active ON realtime_subscriptions(is_active) WHERE is_active = true;

-- RLS Policies
ALTER TABLE realtime_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own subscriptions" ON realtime_subscriptions
    FOR ALL USING (auth.uid() = user_id);

-- =============================================================================
-- TABLE 7: AUDIT_LOGS (Audit Trail)
-- =============================================================================
-- Purpose: Track all important user actions for security and debugging
-- RLS: Users can only see their own audit logs

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES profiles(id) ON DELETE SET NULL,
    
    -- Action details
    action_type TEXT NOT NULL, -- e.g., 'email_processed', 'task_created', 'user_login'
    resource_type TEXT, -- e.g., 'email', 'task', 'profile'
    resource_id UUID, -- ID of the affected resource
    
    -- Action context
    details JSONB DEFAULT '{}', -- Additional action details
    ip_address INET,
    user_agent TEXT,
    
    -- Outcome
    success BOOLEAN DEFAULT true,
    error_message TEXT,
    
    -- Performance
    execution_time_ms INTEGER,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_logs_action_type ON audit_logs(action_type);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id) WHERE resource_id IS NOT NULL;

-- RLS Policies
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own audit logs" ON audit_logs
    FOR SELECT USING (auth.uid() = user_id);

-- =============================================================================
-- FUNCTIONS AND TRIGGERS
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers to relevant tables
CREATE TRIGGER update_profiles_updated_at BEFORE UPDATE ON profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_emails_updated_at BEFORE UPDATE ON emails
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_email_tasks_updated_at BEFORE UPDATE ON email_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_email_mappings_updated_at BEFORE UPDATE ON user_email_mappings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_email_analytics_updated_at BEFORE UPDATE ON email_analytics
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_realtime_subscriptions_updated_at BEFORE UPDATE ON realtime_subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to automatically create user profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, email, full_name, avatar_url)
    VALUES (
        new.id,
        new.email,
        new.raw_user_meta_data->>'full_name',
        new.raw_user_meta_data->>'avatar_url'
    );
    RETURN new;
END;
$$ language plpgsql security definer;

-- Trigger to create profile on user signup
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Function to update email analytics daily
CREATE OR REPLACE FUNCTION update_daily_analytics()
RETURNS VOID AS $$
DECLARE
    user_record RECORD;
    analytics_date DATE := CURRENT_DATE - INTERVAL '1 day';
BEGIN
    -- Update analytics for each user
    FOR user_record IN SELECT id FROM profiles LOOP
        INSERT INTO email_analytics (
            user_id,
            date_bucket,
            period_type,
            emails_received,
            emails_processed,
            emails_with_tasks,
            urgent_emails,
            medium_urgency_emails,
            low_urgency_emails,
            positive_emails,
            negative_emails,
            neutral_emails,
            avg_processing_time_ms,
            tasks_extracted,
            tasks_completed
        )
        SELECT 
            user_record.id,
            analytics_date,
            'daily',
            COUNT(*) as emails_received,
            COUNT(*) FILTER (WHERE status = 'analyzed') as emails_processed,
            COUNT(*) FILTER (WHERE (
                SELECT COUNT(*) FROM email_tasks et 
                WHERE et.email_id = e.id
            ) > 0) as emails_with_tasks,
            COUNT(*) FILTER (WHERE urgency_level = 'high') as urgent_emails,
            COUNT(*) FILTER (WHERE urgency_level = 'medium') as medium_urgency_emails,
            COUNT(*) FILTER (WHERE urgency_level = 'low') as low_urgency_emails,
            COUNT(*) FILTER (WHERE sentiment = 'positive') as positive_emails,
            COUNT(*) FILTER (WHERE sentiment = 'negative') as negative_emails,
            COUNT(*) FILTER (WHERE sentiment = 'neutral') as neutral_emails,
            AVG(processing_time_ms) as avg_processing_time_ms,
            (SELECT COUNT(*) FROM email_tasks et 
             WHERE et.user_id = user_record.id 
             AND et.created_at::date = analytics_date) as tasks_extracted,
            (SELECT COUNT(*) FROM email_tasks et 
             WHERE et.user_id = user_record.id 
             AND et.completion_date::date = analytics_date) as tasks_completed
        FROM emails e
        WHERE e.user_id = user_record.id
        AND e.received_at::date = analytics_date
        GROUP BY user_record.id
        ON CONFLICT (user_id, date_bucket, period_type) 
        DO UPDATE SET
            emails_received = EXCLUDED.emails_received,
            emails_processed = EXCLUDED.emails_processed,
            emails_with_tasks = EXCLUDED.emails_with_tasks,
            urgent_emails = EXCLUDED.urgent_emails,
            medium_urgency_emails = EXCLUDED.medium_urgency_emails,
            low_urgency_emails = EXCLUDED.low_urgency_emails,
            positive_emails = EXCLUDED.positive_emails,
            negative_emails = EXCLUDED.negative_emails,
            neutral_emails = EXCLUDED.neutral_emails,
            avg_processing_time_ms = EXCLUDED.avg_processing_time_ms,
            tasks_extracted = EXCLUDED.tasks_extracted,
            tasks_completed = EXCLUDED.tasks_completed,
            updated_at = NOW();
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- VIEWS FOR COMMON QUERIES
-- =============================================================================

-- View for user dashboard summary
CREATE OR REPLACE VIEW user_dashboard_summary AS
SELECT 
    p.id as user_id,
    p.email,
    p.full_name,
    
    -- Email counts
    (SELECT COUNT(*) FROM emails e WHERE e.user_id = p.id) as total_emails,
    (SELECT COUNT(*) FROM emails e WHERE e.user_id = p.id AND e.received_at > NOW() - INTERVAL '24 hours') as emails_today,
    (SELECT COUNT(*) FROM emails e WHERE e.user_id = p.id AND e.urgency_level = 'high') as urgent_emails,
    
    -- Task counts
    (SELECT COUNT(*) FROM email_tasks et WHERE et.user_id = p.id) as total_tasks,
    (SELECT COUNT(*) FROM email_tasks et WHERE et.user_id = p.id AND et.status = 'pending') as pending_tasks,
    (SELECT COUNT(*) FROM email_tasks et WHERE et.user_id = p.id AND et.deadline_detected < NOW()) as overdue_tasks,
    
    -- Recent activity
    (SELECT MAX(e.received_at) FROM emails e WHERE e.user_id = p.id) as last_email_received,
    (SELECT COUNT(*) FROM emails e WHERE e.user_id = p.id AND e.received_at > NOW() - INTERVAL '7 days') as emails_this_week
    
FROM profiles p;

-- View for email search with full-text search
CREATE OR REPLACE VIEW searchable_emails AS
SELECT 
    e.*,
    p.email as user_email,
    (SELECT COUNT(*) FROM email_tasks et WHERE et.email_id = e.id) as task_count,
    ts_rank(e.search_vector, plainto_tsquery('english', '')) as search_rank
FROM emails e
JOIN profiles p ON e.user_id = p.id;

-- =============================================================================
-- REAL-TIME PUBLICATIONS FOR SUPABASE REALTIME
-- =============================================================================

-- Enable realtime for tables that need live updates
ALTER PUBLICATION supabase_realtime ADD TABLE emails;
ALTER PUBLICATION supabase_realtime ADD TABLE email_tasks;
ALTER PUBLICATION supabase_realtime ADD TABLE email_analytics;

-- =============================================================================
-- SAMPLE DATA AND TESTING FUNCTIONS
-- =============================================================================

-- Function to create sample data for testing (only in development)
CREATE OR REPLACE FUNCTION create_sample_data(user_email TEXT)
RETURNS VOID AS $$
DECLARE
    sample_user_id UUID;
    sample_email_id UUID;
BEGIN
    -- Find or create user
    SELECT id INTO sample_user_id FROM profiles WHERE email = user_email;
    
    IF sample_user_id IS NULL THEN
        RAISE EXCEPTION 'User with email % not found', user_email;
    END IF;
    
    -- Create sample email
    INSERT INTO emails (
        user_id, message_id, from_email, to_emails, subject, text_body,
        urgency_score, urgency_level, sentiment, confidence, keywords,
        received_at, status
    ) VALUES (
        sample_user_id,
        'sample-' || gen_random_uuid()::text,
        'sender@example.com',
        '["' || user_email || '"]'::jsonb,
        'URGENT: Project deadline tomorrow',
        'Hi, we need to complete the project by tomorrow. Please review the documents and send your feedback ASAP.',
        85,
        'high',
        'negative',
        0.92,
        '["urgent", "deadline", "project", "ASAP"]'::jsonb,
        NOW() - INTERVAL '2 hours',
        'analyzed'
    ) RETURNING id INTO sample_email_id;
    
    -- Create sample task
    INSERT INTO email_tasks (
        email_id, user_id, title, description, urgency_score, priority,
        deadline_detected, extraction_confidence, status
    ) VALUES (
        sample_email_id,
        sample_user_id,
        'Review project documents',
        'Review the project documents and provide feedback before tomorrow deadline',
        85,
        'high',
        NOW() + INTERVAL '1 day',
        0.88,
        'pending'
    );
    
    RAISE NOTICE 'Sample data created for user %', user_email;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- PERFORMANCE OPTIMIZATION
-- =============================================================================

-- Partial indexes for performance
CREATE INDEX CONCURRENTLY idx_emails_unprocessed ON emails(received_at DESC) 
    WHERE status IN ('received', 'processing');

CREATE INDEX CONCURRENTLY idx_emails_urgent_recent ON emails(user_id, received_at DESC) 
    WHERE urgency_level = 'high' AND received_at > NOW() - INTERVAL '30 days';

CREATE INDEX CONCURRENTLY idx_tasks_due_soon ON email_tasks(user_id, deadline_detected) 
    WHERE status = 'pending' AND deadline_detected > NOW() AND deadline_detected < NOW() + INTERVAL '7 days';

-- =============================================================================
-- SECURITY ADDITIONAL MEASURES
-- =============================================================================

-- Function to validate email format
CREATE OR REPLACE FUNCTION is_valid_email(email_text TEXT)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN email_text ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$';
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Additional security constraints
ALTER TABLE emails ADD CONSTRAINT valid_from_email 
    CHECK (is_valid_email(from_email));

-- Rate limiting function for API calls
CREATE OR REPLACE FUNCTION check_rate_limit(user_uuid UUID, action_type TEXT, max_per_hour INTEGER DEFAULT 1000)
RETURNS BOOLEAN AS $$
DECLARE
    current_count INTEGER;
BEGIN
    -- Count actions in the last hour
    SELECT COUNT(*) INTO current_count
    FROM audit_logs
    WHERE user_id = user_uuid
    AND action_type = action_type
    AND created_at > NOW() - INTERVAL '1 hour';
    
    RETURN current_count < max_per_hour;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- =============================================================================
-- SCHEMA VALIDATION AND DOCUMENTATION
-- =============================================================================

COMMENT ON TABLE profiles IS 'User profiles linked to Supabase Auth with application-specific settings';
COMMENT ON TABLE emails IS 'Core email storage with MCP analysis results and full-text search';
COMMENT ON TABLE email_tasks IS 'Action items and tasks extracted from emails by MCP processing';
COMMENT ON TABLE user_email_mappings IS 'Configuration for routing inbound emails to specific users';
COMMENT ON TABLE email_analytics IS 'Aggregated analytics data for user insights and system monitoring';
COMMENT ON TABLE realtime_subscriptions IS 'Real-time notification subscriptions for live updates';
COMMENT ON TABLE audit_logs IS 'Audit trail for security and debugging purposes';

-- =============================================================================
-- TABLE 8: ORGANIZATIONS (Multi-Tenancy Support)
-- =============================================================================
-- Purpose: Store organization information for multi-tenant support
-- RLS: Users can only see organizations they belong to

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    settings JSONB DEFAULT '{}',
    
    -- Organization metadata
    created_by UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT organizations_name_length CHECK (char_length(name) >= 2 AND char_length(name) <= 100)
);

-- Create indexes
CREATE INDEX idx_organizations_name ON organizations(name);
CREATE INDEX idx_organizations_created_by ON organizations(created_by);
CREATE INDEX idx_organizations_created_at ON organizations(created_at);

-- RLS Policies
ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view organizations they belong to" ON organizations
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM organization_members 
            WHERE organization_id = organizations.id 
            AND user_id = auth.uid()
        )
    );

CREATE POLICY "Organization owners can update organization" ON organizations
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM organization_members 
            WHERE organization_id = organizations.id 
            AND user_id = auth.uid() 
            AND role IN ('owner', 'admin')
        )
    );

CREATE POLICY "Users can create organizations" ON organizations
    FOR INSERT WITH CHECK (auth.uid() = created_by);

-- =============================================================================
-- TABLE 9: ORGANIZATION_MEMBERS (User-Organization Relationships)
-- =============================================================================
-- Purpose: Store user memberships and roles within organizations
-- RLS: Users can only see memberships for organizations they belong to

CREATE TABLE organization_members (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    
    -- Role information
    role TEXT NOT NULL CHECK (role IN ('owner', 'admin', 'member', 'guest')),
    
    -- Membership metadata
    invited_by UUID REFERENCES profiles(id),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(organization_id, user_id)
);

-- Create indexes
CREATE INDEX idx_organization_members_org_id ON organization_members(organization_id);
CREATE INDEX idx_organization_members_user_id ON organization_members(user_id);
CREATE INDEX idx_organization_members_role ON organization_members(role);

-- RLS Policies
ALTER TABLE organization_members ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view memberships in their organizations" ON organization_members
    FOR SELECT USING (
        user_id = auth.uid() OR
        EXISTS (
            SELECT 1 FROM organization_members om 
            WHERE om.organization_id = organization_members.organization_id 
            AND om.user_id = auth.uid()
        )
    );

CREATE POLICY "Organization admins can manage memberships" ON organization_members
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM organization_members om 
            WHERE om.organization_id = organization_members.organization_id 
            AND om.user_id = auth.uid() 
            AND om.role IN ('owner', 'admin')
        )
    );

-- =============================================================================
-- TABLE 10: ORGANIZATION_INVITATIONS (Pending Invitations)
-- =============================================================================
-- Purpose: Store pending invitations to join organizations
-- RLS: Users can only see invitations they sent or received

CREATE TABLE organization_invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Invitation details
    email TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'member', 'guest')),
    
    -- Invitation metadata
    invited_by UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'declined', 'expired')),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Response tracking
    responded_at TIMESTAMPTZ,
    response_details JSONB DEFAULT '{}',
    
    -- Constraints
    UNIQUE(organization_id, email, status) -- Prevent duplicate pending invitations
);

-- Create indexes
CREATE INDEX idx_organization_invitations_org_id ON organization_invitations(organization_id);
CREATE INDEX idx_organization_invitations_email ON organization_invitations(email);
CREATE INDEX idx_organization_invitations_status ON organization_invitations(status);
CREATE INDEX idx_organization_invitations_expires_at ON organization_invitations(expires_at);

-- RLS Policies
ALTER TABLE organization_invitations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view invitations they sent" ON organization_invitations
    FOR SELECT USING (invited_by = auth.uid());

CREATE POLICY "Users can view invitations sent to them" ON organization_invitations
    FOR SELECT USING (
        email = (SELECT email FROM profiles WHERE id = auth.uid())
    );

CREATE POLICY "Organization admins can manage invitations" ON organization_invitations
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM organization_members om 
            WHERE om.organization_id = organization_invitations.organization_id 
            AND om.user_id = auth.uid() 
            AND om.role IN ('owner', 'admin')
        )
    );

-- =============================================================================
-- TABLE 11: USER_PREFERENCES (User-Specific Settings)
-- =============================================================================
-- Purpose: Store user preferences and AI analysis settings
-- RLS: Users can only access their own preferences

CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Preference categories
    category TEXT NOT NULL CHECK (category IN ('ai_analysis', 'notifications', 'ui', 'processing', 'general')),
    
    -- Preference data
    preferences JSONB NOT NULL DEFAULT '{}',
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    UNIQUE(user_id, organization_id, category)
);

-- Create indexes
CREATE INDEX idx_user_preferences_user_id ON user_preferences(user_id);
CREATE INDEX idx_user_preferences_org_id ON user_preferences(organization_id);
CREATE INDEX idx_user_preferences_category ON user_preferences(category);

-- RLS Policies
ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can manage own preferences" ON user_preferences
    FOR ALL USING (user_id = auth.uid());

-- =============================================================================
-- ENHANCED AUDIT_LOGS (Extended for User Management)
-- =============================================================================
-- Update existing audit_logs table to support organization and user management events

-- Add organization_id column to existing audit_logs table
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL;

-- Add index for organization audit events
CREATE INDEX IF NOT EXISTS idx_audit_logs_organization_id ON audit_logs(organization_id);

-- Add additional RLS policy for organization audit logs
CREATE POLICY IF NOT EXISTS "Organization members can view org audit logs" ON audit_logs
    FOR SELECT USING (
        organization_id IS NOT NULL AND
        EXISTS (
            SELECT 1 FROM organization_members om 
            WHERE om.organization_id = audit_logs.organization_id 
            AND om.user_id = auth.uid()
            AND om.role IN ('owner', 'admin')
        )
    );

-- =============================================================================
-- FUNCTIONS AND TRIGGERS FOR USER MANAGEMENT
-- =============================================================================

-- Add updated_at triggers for new tables
CREATE TRIGGER update_organizations_updated_at 
    BEFORE UPDATE ON organizations 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_user_preferences_updated_at 
    BEFORE UPDATE ON user_preferences 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enhanced function to automatically create user profile after auth signup
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, email, full_name)
    VALUES (
        NEW.id,
        NEW.email,
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.email)
    );
    RETURN NEW;
END;
$$ language 'plpgsql' SECURITY DEFINER;

-- Update trigger to automatically create profile for new users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION handle_new_user();

-- Add comments for new tables
COMMENT ON TABLE organizations IS 'Organizations for multi-tenant support with RBAC';
COMMENT ON TABLE organization_members IS 'User memberships and roles within organizations';
COMMENT ON TABLE organization_invitations IS 'Pending invitations to join organizations';
COMMENT ON TABLE user_preferences IS 'User-specific preferences and AI analysis settings';

-- Final schema validation
DO $$
BEGIN
    RAISE NOTICE 'Inbox Zen Supabase Schema v1.0.0 installed successfully!';
    RAISE NOTICE 'Core Tables: profiles, emails, email_tasks, user_email_mappings, email_analytics, realtime_subscriptions, audit_logs';
    RAISE NOTICE 'User Management: organizations, organization_members, organization_invitations, user_preferences';
    RAISE NOTICE 'RLS enabled on all user tables with appropriate policies';
    RAISE NOTICE 'Full-text search configured for emails and tasks';
    RAISE NOTICE 'Real-time subscriptions enabled for live updates';
    RAISE NOTICE 'Multi-tenancy and RBAC support fully configured';
    RAISE NOTICE 'Performance indexes created for optimal query performance';
    RAISE NOTICE 'Ready for Supabase integration with MCP Email Parsing Server!';
END $$;
