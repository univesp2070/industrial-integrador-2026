-- V003 - Pick events table
-- Records each product retrieval detected by weight sensor

CREATE TABLE IF NOT EXISTS pick_events (
    id              UUID NOT NULL DEFAULT gen_random_uuid(),
    time            TIMESTAMPTZ NOT NULL,
    device_id       UUID NOT NULL REFERENCES devices(id),
    product_name    TEXT NOT NULL,
    quantity        INT NOT NULL,
    weight_delta_kg FLOAT NOT NULL,
    confidence      FLOAT NOT NULL,
    PRIMARY KEY (id, time)
);

SELECT create_hypertable('pick_events', 'time', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS idx_pick_events_device ON pick_events (device_id, time DESC);
CREATE INDEX IF NOT EXISTS idx_pick_events_product ON pick_events (product_name, time DESC);
