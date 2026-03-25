-- VibeFinder PostgreSQL Initialization Script
-- This script runs automatically when the container is first created

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant privileges (the database is already created by POSTGRES_DB env var)
-- Additional setup can be added here

-- Example: Create a read-only user for reporting (optional)
-- CREATE USER readonly_user WITH PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE vibefinder TO readonly_user;
-- GRANT USAGE ON SCHEMA public TO readonly_user;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly_user;

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'VibeFinder database initialized successfully';
END $$;
