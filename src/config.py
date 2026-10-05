"""
SIH26006 — Central configuration.
All constants, route definitions, vessel specs, and port constraints live here.
"""

from pydantic_settings import BaseSettings
from pathlib import Path

# ── Project Paths ─────────────────────────────────────────────────────────────
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
FEATURES_DIR = DATA_DIR / "features"
SEED_DIR = DATA_DIR / "seed"
MODEL_DIR = ROOT_DIR / "models" / "artifacts"
REPORTS_DIR = ROOT_DIR / "reports"


# ── App Settings (loaded from .env) ──────────────────────────────────────────
class Settings(BaseSettings):
    database_url: str = "postgresql://user:password@localhost:5432/freight_db"
    api_secret_key: str = "dev-secret"
    environment: str = "development"
    backend_url: str = "http://localhost:8000"
    optuna_n_trials: int = 50
    forecast_horizon_days: int = 30
    log_level: str = "INFO"
    use_yahoo_proxy: bool = True

    class Config:
        env_file = ".env"


settings = Settings()


# ── Vessel Class Specifications ───────────────────────────────────────────────
# Source: industry standard DWT ranges; draft/LOA/beam are typical maximums
VESSEL_SPECS: dict[str, dict] = {
    "Handysize": {
        "dwt_min": 20_000,
        "dwt_max": 39_999,
        "draft_m": 10.0,
        "loa_m": 185.0,
        "beam_m": 28.0,
        "min_cargo_t": 15_000,
        "max_cargo_t": 35_000,
        "description": "Small geared vessel, can access most East Coast ports",
    },
    "Supramax": {
        "dwt_min": 50_000,
        "dwt_max": 60_000,
        "draft_m": 12.5,
        "loa_m": 200.0,
        "beam_m": 32.0,
        "min_cargo_t": 40_000,
        "max_cargo_t": 58_000,
        "description": "Workhorse of dry-bulk; flexible geared vessels",
    },
    "Panamax": {
        "dwt_min": 65_000,
        "dwt_max": 82_000,
        "draft_m": 14.0,
        "loa_m": 229.0,
        "beam_m": 32.2,
        "min_cargo_t": 60_000,
        "max_cargo_t": 80_000,
        "description": "High volume; draft-limited at some East Coast ports",
    },
    "Capesize": {
        "dwt_min": 100_000,
        "dwt_max": 180_000,
        "draft_m": 17.5,
        "loa_m": 290.0,
        "beam_m": 45.0,
        "min_cargo_t": 90_000,
        "max_cargo_t": 170_000,
        "description": "Lowest $/tonne; only Vizag/Paradip can handle",
    },
}


# ── East Coast India Port Constraints ─────────────────────────────────────────
# Source: port authority publications + industry references
# NOTE: These are reference values — verify against latest port circulars
PORT_CONSTRAINTS: dict[str, dict] = {
    "Paradip": {
        "max_draft_m": 16.5,
        "max_loa_m": 275.0,
        "max_beam_m": 43.0,
        "berths": 4,
        "handling_rate_tpd": 25_000,
        "state": "Odisha",
        "notes": "Major coal import hub; deep-draft capable",
    },
    "Visakhapatnam": {
        "max_draft_m": 16.5,
        "max_loa_m": 275.0,
        "max_beam_m": 43.0,
        "berths": 5,
        "handling_rate_tpd": 30_000,
        "state": "Andhra Pradesh",
        "notes": "Deep draft; can handle Capesize",
    },
    "Gangavaram": {
        "max_draft_m": 16.5,
        "max_loa_m": 270.0,
        "max_beam_m": 43.0,
        "berths": 3,
        "handling_rate_tpd": 20_000,
        "state": "Andhra Pradesh",
        "notes": "Private port; excellent handling rate",
    },
    "Gopalpur": {
        "max_draft_m": 12.5,
        "max_loa_m": 200.0,
        "max_beam_m": 32.0,
        "berths": 2,
        "handling_rate_tpd": 10_000,
        "state": "Odisha",
        "notes": "Smaller port; Supramax max",
    },
    "Dhamra": {
        "max_draft_m": 14.5,
        "max_loa_m": 250.0,
        "max_beam_m": 40.0,
        "berths": 3,
        "handling_rate_tpd": 20_000,
        "state": "Odisha",
        "notes": "Adani-operated; growing capacity",
    },
    "Sagar-Sandheads": {
        "max_draft_m": 8.5,
        "max_loa_m": 170.0,
        "max_beam_m": 27.0,
        "berths": 2,
        "handling_rate_tpd": 6_000,
        "state": "West Bengal",
        "notes": "River mouth anchorage; tide-dependent; Handysize only",
    },
    "Haldia": {
        "max_draft_m": 8.0,
        "max_loa_m": 175.0,
        "max_beam_m": 27.0,
        "berths": 3,
        "handling_rate_tpd": 8_000,
        "state": "West Bengal",
        "notes": "Tidal river port (Hooghly); strict draft — Handysize/small Supramax",
    },
}


# ── Origin Countries & Key Loading Ports ─────────────────────────────────────
ORIGIN_PORTS: dict[str, list[str]] = {
    "Australia": ["Newcastle", "Hay Point", "Abbot Point", "Dalrymple Bay"],
    "USA": ["Hampton Roads", "Baltimore", "New Orleans"],
    "Mozambique": ["Nacala", "Beira"],
    "Russia": ["Murmansk", "Vostochny", "Vanino"],
    "Indonesia": ["Banjarmasin", "Samarinda", "Tarahan", "Bontang"],
}


# ── Standard Trade Routes (Origin → Destination) ─────────────────────────────
# sailing_distance_nm: approximate nautical miles
TRADE_ROUTES: list[dict] = [
    {"route_id": "AUS-PAR", "origin": "Australia", "destination": "Paradip",        "sailing_distance_nm": 4_500},
    {"route_id": "AUS-VIZ", "origin": "Australia", "destination": "Visakhapatnam",  "sailing_distance_nm": 4_300},
    {"route_id": "IDN-PAR", "origin": "Indonesia", "destination": "Paradip",        "sailing_distance_nm": 2_200},
    {"route_id": "IDN-VIZ", "origin": "Indonesia", "destination": "Visakhapatnam",  "sailing_distance_nm": 2_000},
    {"route_id": "IDN-HAL", "origin": "Indonesia", "destination": "Haldia",         "sailing_distance_nm": 1_900},
    {"route_id": "USA-PAR", "origin": "USA",        "destination": "Paradip",        "sailing_distance_nm": 9_500},
    {"route_id": "MOZ-VIZ", "origin": "Mozambique", "destination": "Visakhapatnam", "sailing_distance_nm": 4_100},
    {"route_id": "MOZ-PAR", "origin": "Mozambique", "destination": "Paradip",       "sailing_distance_nm": 4_200},
    {"route_id": "RUS-VIZ", "origin": "Russia",     "destination": "Visakhapatnam", "sailing_distance_nm": 6_500},
]

# ── Baltic Index Proxies (Yahoo Finance tickers — free alternative) ───────────
YAHOO_PROXIES: dict[str, str] = {
    "BDI_ETF":   "BDRY",    # Breakwave Dry Bulk Shipping ETF (tracks BDI)
    "COAL_MINER":"BTU",     # Peabody Energy (coal price proxy)
    "IRON_ORE":  "VALE",    # Vale (iron ore / dry bulk demand proxy)
    "GRAIN":     "WEAT",    # Teucrium Wheat Fund
    "OIL_BRENT": "BZ=F",    # Brent crude (fuel cost proxy)
}

# ── Forecast Horizons ─────────────────────────────────────────────────────────
HORIZONS: dict[str, int] = {
    "short_term":  30,   # days — single voyage / spot reference
    "mid_term":   180,   # days — 3–6 month charter
}
