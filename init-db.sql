-- Table for server-level metrics (hardware & OS)
CREATE TABLE IF NOT EXISTS server_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    server_id VARCHAR(50) NOT NULL,
    -- Compute metrics
    cpu_usage_percent FLOAT CHECK (cpu_usage_percent >= 0 AND cpu_usage_percent <= 100),
    memory_usage_percent FLOAT CHECK (memory_usage_percent >= 0 AND memory_usage_percent <= 100),
    memory_available_gb FLOAT,
    -- Disk metrics
    disk_usage_percent FLOAT CHECK (disk_usage_percent >= 0 AND disk_usage_percent <= 100),
    disk_read_mbps FLOAT,
    disk_write_mbps FLOAT,
    -- Network metrics (per server)
    network_rx_mbps FLOAT,
    network_tx_mbps FLOAT,
    -- Hardware health
    cpu_temperature_celsius FLOAT,
    power_consumption_watts FLOAT,
    fan_speed_rpm INT,
    -- Metadata
    rack_id VARCHAR(20),
    datacenter_zone VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table for application-level metrics (service performance)
CREATE TABLE IF NOT EXISTS application_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    service_name VARCHAR(100) NOT NULL,
    -- Request metrics
    request_rate_per_sec FLOAT,
    -- Latency percentiles
    response_time_p50_ms FLOAT,
    response_time_p95_ms FLOAT,
    response_time_p99_ms FLOAT,
    -- Error tracking
    error_rate_percent FLOAT CHECK (error_rate_percent >= 0 AND error_rate_percent <= 100),
    error_count INT,
    -- Resource usage
    active_connections INT,
    queue_depth INT,
    -- Metadata
    server_id VARCHAR(50),
    endpoint VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table for model predictions (power consumption forecasting)
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    server_id VARCHAR(50) NOT NULL,
    predicted_power_watts FLOAT,
    actual_power_watts FLOAT,
    prediction_error_percent FLOAT,
    model_version VARCHAR(50),
    confidence_score FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Table for detected anomalies
CREATE TABLE IF NOT EXISTS anomalies (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    entity_type VARCHAR(50) NOT NULL, -- 'server' or 'application'
    entity_id VARCHAR(100) NOT NULL,  -- server_id or service_name
    anomaly_type VARCHAR(100) NOT NULL, -- 'cpu_spike', 'memory_leak', 'latency_spike', etc.
    severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    anomaly_score FLOAT,
    details JSONB,
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for server_metrics
CREATE INDEX idx_server_metrics_timestamp ON server_metrics(timestamp DESC);
CREATE INDEX idx_server_metrics_server_id ON server_metrics(server_id);
CREATE INDEX idx_server_metrics_server_time ON server_metrics(server_id, timestamp DESC);
CREATE INDEX idx_server_metrics_rack ON server_metrics(rack_id);

-- Indexes for application_metrics
CREATE INDEX idx_app_metrics_timestamp ON application_metrics(timestamp DESC);
CREATE INDEX idx_app_metrics_service ON application_metrics(service_name);
CREATE INDEX idx_app_metrics_service_time ON application_metrics(service_name, timestamp DESC);

-- Indexes for predictions
CREATE INDEX idx_predictions_timestamp ON predictions(timestamp DESC);
CREATE INDEX idx_predictions_server_id ON predictions(server_id);
CREATE INDEX idx_predictions_server_time ON predictions(server_id, timestamp DESC);

-- Indexes for anomalies
CREATE INDEX idx_anomalies_timestamp ON anomalies(timestamp DESC);
CREATE INDEX idx_anomalies_entity ON anomalies(entity_type, entity_id);
CREATE INDEX idx_anomalies_type ON anomalies(anomaly_type);
CREATE INDEX idx_anomalies_severity ON anomalies(severity);
CREATE INDEX idx_anomalies_unresolved ON anomalies(resolved) WHERE resolved = FALSE;

-- View for recent server health (last hour)
CREATE OR REPLACE VIEW recent_server_health AS
SELECT 
    server_id,
    timestamp,
    cpu_usage_percent,
    memory_usage_percent,
    cpu_temperature_celsius,
    power_consumption_watts,
    rack_id,
    datacenter_zone
FROM server_metrics
WHERE timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;

-- View for application performance summary (last 15 minutes)
CREATE OR REPLACE VIEW recent_application_performance AS
SELECT 
    service_name,
    AVG(request_rate_per_sec) as avg_request_rate,
    AVG(response_time_p95_ms) as avg_p95_latency,
    AVG(error_rate_percent) as avg_error_rate,
    MAX(timestamp) as last_updated
FROM application_metrics
WHERE timestamp > NOW() - INTERVAL '15 minutes'
GROUP BY service_name;

-- View for active anomalies
CREATE OR REPLACE VIEW active_anomalies AS
SELECT 
    entity_type,
    entity_id,
    anomaly_type,
    severity,
    anomaly_score,
    details,
    timestamp,
    created_at
FROM anomalies
WHERE resolved = FALSE
ORDER BY severity DESC, timestamp DESC;