-- Database initialization script for Reflex Executive Assistant
-- This script runs when the PostgreSQL container starts for the first time

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create additional databases for different environments
CREATE DATABASE reflex_test;
CREATE DATABASE reflex_staging;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE reflex TO reflex_user;
GRANT ALL PRIVILEGES ON DATABASE reflex_test TO reflex_user;
GRANT ALL PRIVILEGES ON DATABASE reflex_staging TO reflex_user;

-- Set default privileges for future tables
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO reflex_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO reflex_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON FUNCTIONS TO reflex_user;

-- Create indexes for better performance
-- (These will be created by SQLAlchemy, but we can add custom ones here)

-- Create a function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create a function to generate UUIDs
CREATE OR REPLACE FUNCTION generate_uuid()
RETURNS UUID AS $$
BEGIN
    RETURN uuid_generate_v4();
END;
$$ language 'plpgsql';

-- Create a function to clean old data
CREATE OR REPLACE FUNCTION cleanup_old_data(days_old INTEGER DEFAULT 90)
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER := 0;
BEGIN
    -- Clean up old conversations and messages
    DELETE FROM messages 
    WHERE conversation_id IN (
        SELECT id FROM conversations 
        WHERE started_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old
    );
    
    DELETE FROM conversations 
    WHERE started_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old;
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    -- Clean up old workflow executions
    DELETE FROM workflow_executions 
    WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old
    AND status IN ('completed', 'failed', 'timeout');
    
    -- Clean up old Slack messages
    DELETE FROM slack_messages 
    WHERE timestamp < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old;
    
    -- Clean up old emails
    DELETE FROM emails 
    WHERE received_at < CURRENT_TIMESTAMP - INTERVAL '1 day' * days_old;
    
    RETURN deleted_count;
END;
$$ language 'plpgsql';

-- Create a function to get system statistics
CREATE OR REPLACE FUNCTION get_system_stats()
RETURNS TABLE (
    table_name TEXT,
    record_count BIGINT,
    last_updated TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        'conversations'::TEXT as table_name,
        COUNT(*)::BIGINT as record_count,
        MAX(updated_at) as last_updated
    FROM conversations
    UNION ALL
    SELECT 
        'messages'::TEXT,
        COUNT(*)::BIGINT,
        MAX(created_at)
    FROM messages
    UNION ALL
    SELECT 
        'workflow_executions'::TEXT,
        COUNT(*)::BIGINT,
        MAX(updated_at)
    FROM workflow_executions
    UNION ALL
    SELECT 
        'slack_messages'::TEXT,
        COUNT(*)::BIGINT,
        MAX(timestamp)
    FROM slack_messages
    UNION ALL
    SELECT 
        'emails'::TEXT,
        COUNT(*)::BIGINT,
        MAX(received_at)
    FROM emails;
END;
$$ language 'plpgsql';

-- Create a function to monitor database health
CREATE OR REPLACE FUNCTION check_database_health()
RETURNS TABLE (
    check_name TEXT,
    status TEXT,
    details TEXT
) AS $$
BEGIN
    -- Check if tables exist
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversations') THEN
        RETURN QUERY SELECT 'tables_exist'::TEXT, 'healthy'::TEXT, 'All required tables exist'::TEXT;
    ELSE
        RETURN QUERY SELECT 'tables_exist'::TEXT, 'unhealthy'::TEXT, 'Required tables missing'::TEXT;
    END IF;
    
    -- Check database size
    RETURN QUERY 
    SELECT 
        'database_size'::TEXT,
        CASE 
            WHEN pg_database_size('reflex') < 1073741824 THEN 'healthy'::TEXT  -- Less than 1GB
            ELSE 'warning'::TEXT
        END,
        'Database size: ' || pg_size_pretty(pg_database_size('reflex'))::TEXT;
    
    -- Check active connections
    RETURN QUERY 
    SELECT 
        'active_connections'::TEXT,
        CASE 
            WHEN (SELECT count(*) FROM pg_stat_activity WHERE datname = 'reflex') < 50 THEN 'healthy'::TEXT
            ELSE 'warning'::TEXT
        END,
        'Active connections: ' || (SELECT count(*) FROM pg_stat_activity WHERE datname = 'reflex')::TEXT;
END;
$$ language 'plpgsql';

-- Grant execute permissions on functions
GRANT EXECUTE ON FUNCTION update_updated_at_column() TO reflex_user;
GRANT EXECUTE ON FUNCTION generate_uuid() TO reflex_user;
GRANT EXECUTE ON FUNCTION cleanup_old_data(INTEGER) TO reflex_user;
GRANT EXECUTE ON FUNCTION get_system_stats() TO reflex_user;
GRANT EXECUTE ON FUNCTION check_database_health() TO reflex_user;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Reflex Executive Assistant database initialized successfully';
    RAISE NOTICE 'Database: reflex';
    RAISE NOTICE 'User: reflex_user';
    RAISE NOTICE 'Extensions: uuid-ossp, pg_trgm';
    RAISE NOTICE 'Functions: update_updated_at_column, generate_uuid, cleanup_old_data, get_system_stats, check_database_health';
END $$; 