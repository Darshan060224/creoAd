-- Initial database schema for CreoAd
-- Run automatically when PostgreSQL container starts

CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(36) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255),
    full_name VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaigns (
    id VARCHAR(36) PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    job_id VARCHAR(255),
    business_url TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'queued',
    brand_data JSONB,
    script_data JSONB,
    scenes_data JSONB,
    video_url TEXT,
    video_duration INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS job_logs (
    id VARCHAR(36) PRIMARY KEY,
    campaign_id VARCHAR(36) NOT NULL,
    job_id VARCHAR(255),
    stage VARCHAR(50),
    status VARCHAR(50),
    message TEXT,
    duration_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
);

-- Indices for faster queries
CREATE INDEX IF NOT EXISTS idx_campaigns_user_id ON campaigns(user_id);
CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns(status);
CREATE INDEX IF NOT EXISTS idx_campaigns_job_id ON campaigns(job_id);
CREATE INDEX IF NOT EXISTS idx_job_logs_campaign_id ON job_logs(campaign_id);
CREATE INDEX IF NOT EXISTS idx_job_logs_stage ON job_logs(stage);
