-- SIH26006 — PostgreSQL Schema
-- Run: psql -U user -d freight_db -f database/schema.sql

-- ── Freight Rates (historical time series) ────────────────────────────────────
CREATE TABLE IF NOT EXISTS freight_rates (
    id              SERIAL PRIMARY KEY,
    date            DATE NOT NULL,
    route_id        VARCHAR(20) NOT NULL,        -- e.g. AUS-PAR
    vessel_class    VARCHAR(20) NOT NULL,        -- Handysize/Supramax/Panamax/Capesize
    rate            DECIMAL(10, 4) NOT NULL,     -- USD per tonne
    unit            VARCHAR(20) DEFAULT 'USD_per_tonne',
    source          VARCHAR(50),                 -- Baltic Exchange / Yahoo Proxy / Synthetic
    is_synthetic    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE (date, route_id, vessel_class)
);

CREATE INDEX idx_freight_rates_route_vessel ON freight_rates (route_id, vessel_class, date);

-- ── Port Constraints Reference Table ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS port_constraints (
    port_name           VARCHAR(50) PRIMARY KEY,
    country             VARCHAR(50) DEFAULT 'India',
    state               VARCHAR(50),
    port_type           VARCHAR(20) DEFAULT 'destination', -- 'destination' | 'origin'
    max_draft_m         DECIMAL(5, 2),
    max_loa_m           DECIMAL(7, 2),
    max_beam_m          DECIMAL(6, 2),
    berths              INTEGER,
    handling_rate_tpd   INTEGER,                -- tonnes per day
    notes               TEXT,
    updated_at          TIMESTAMP DEFAULT NOW()
);

-- ── Vessel Specifications ─────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS vessel_specs (
    vessel_class    VARCHAR(20) PRIMARY KEY,
    dwt_min         INTEGER,
    dwt_max         INTEGER,
    draft_m         DECIMAL(5, 2),
    loa_m           DECIMAL(7, 2),
    beam_m          DECIMAL(6, 2),
    min_cargo_t     INTEGER,
    max_cargo_t     INTEGER,
    description     TEXT
);

-- ── Commodity & Exogenous Indicators ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS market_indicators (
    id              SERIAL PRIMARY KEY,
    date            DATE NOT NULL,
    indicator_name  VARCHAR(50) NOT NULL,       -- BDI_ETF, COAL, BRENT, etc.
    value           DECIMAL(12, 4),
    source          VARCHAR(50),
    created_at      TIMESTAMP DEFAULT NOW(),
    UNIQUE (date, indicator_name)
);

-- ── Forecast Log (audit trail of all forecasts served) ───────────────────────
CREATE TABLE IF NOT EXISTS forecast_log (
    id              SERIAL PRIMARY KEY,
    requested_at    TIMESTAMP DEFAULT NOW(),
    route_id        VARCHAR(20),
    vessel_class    VARCHAR(20),
    horizon_days    INTEGER,
    cargo_volume_t  DECIMAL(12, 2),
    forecast_rate   DECIMAL(10, 4),
    lower_80_ci     DECIMAL(10, 4),
    upper_80_ci     DECIMAL(10, 4),
    model_used      VARCHAR(50),
    mape_backtest   DECIMAL(6, 2)
);

-- ── Risk Alerts Log ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS risk_alerts (
    id                  SERIAL PRIMARY KEY,
    created_at          TIMESTAMP DEFAULT NOW(),
    route_id            VARCHAR(20),
    destination_port    VARCHAR(50),
    volatility_flag     VARCHAR(10),
    volatility_score    DECIMAL(4, 3),
    congestion_flag     VARCHAR(10),
    congestion_score    DECIMAL(4, 3),
    overall_risk        VARCHAR(10),
    advisory            TEXT
);
