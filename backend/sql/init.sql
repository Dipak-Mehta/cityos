CREATE TABLE IF NOT EXISTS intersections (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS telemetry (
    id BIGSERIAL PRIMARY KEY,
    intersection_id VARCHAR(64) NOT NULL REFERENCES intersections(id),
    timestamp TIMESTAMPTZ NOT NULL,
    traffic_volume INTEGER NOT NULL,
    signal_latency DOUBLE PRECISION NOT NULL,
    power_voltage DOUBLE PRECISION NOT NULL,
    error_count INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_telemetry_intersection_time ON telemetry(intersection_id, timestamp DESC);

INSERT INTO intersections (id, name, latitude, longitude) VALUES
('PUN-001', 'Pilot Intersection 001', 18.5204, 73.8567),
('PUN-002', 'Pilot Intersection 002', 18.5314, 73.8446),
('PUN-003', 'Pilot Intersection 003', 18.5074, 73.8077)
ON CONFLICT (id) DO NOTHING;
