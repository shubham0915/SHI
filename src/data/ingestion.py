"""
Phase 1 — Data Ingestion Layer
Handles: BDI/BPI proxy download (Yahoo Finance), CSV loading, and DB persistence.
Reference: Freight-Prediction (Stef-creator) — data/raw pipeline pattern
"""

import pandas as pd
import yfinance as yf
from pathlib import Path
from loguru import logger
from datetime import datetime, timedelta

from src.config import YAHOO_PROXIES, RAW_DIR, TRADE_ROUTES


# ── Yahoo Finance Proxy Ingestion ─────────────────────────────────────────────

def fetch_yahoo_proxy_data(
    start: str = "2015-01-01",
    end: str | None = None,
    save: bool = True,
) -> pd.DataFrame:
    """
    Download free Baltic/commodity proxies from Yahoo Finance.
    Use when paid Baltic Exchange data is unavailable (development phase).

    Proxies:
      BDRY  → Breakwave Dry Bulk ETF (tracks BDI movements)
      BTU   → Peabody Energy (coal price proxy)
      VALE  → Vale (iron ore / dry-bulk demand proxy)
      WEAT  → Wheat (grain trade proxy)
      BZ=F  → Brent crude (fuel cost)

    Returns: DataFrame indexed by date, columns = ticker symbols
    """
    if end is None:
        end = datetime.today().strftime("%Y-%m-%d")

    logger.info(f"Fetching Yahoo Finance proxies: {list(YAHOO_PROXIES.values())} | {start} → {end}")

    frames = {}
    for name, ticker in YAHOO_PROXIES.items():
        try:
            df = yf.download(ticker, start=start, end=end, progress=False)
            frames[name] = df["Close"].rename(name)
            logger.success(f"  ✓ {ticker} ({name}): {len(df)} rows")
        except Exception as e:
            logger.warning(f"  ✗ {ticker} ({name}): {e}")

    combined = pd.concat(frames, axis=1)
    combined.index = pd.to_datetime(combined.index)
    combined = combined.sort_index().ffill()

    if save:
        out_path = RAW_DIR / "commodity" / "yahoo_proxies.csv"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        combined.to_csv(out_path)
        logger.info(f"Saved to {out_path}")

    return combined


# ── CSV Loaders ───────────────────────────────────────────────────────────────

def load_freight_rate_csv(filepath: str | Path) -> pd.DataFrame:
    """
    Load a freight rate CSV (BPI, BDI, route-specific).
    Expected columns: date, rate (USD/tonne or $/day), vessel_class, route_id
    """
    df = pd.read_csv(filepath, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df.columns = df.columns.str.lower().str.strip().str.replace(" ", "_")

    # Validate required columns
    required = {"date", "rate"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    logger.info(f"Loaded freight rates: {len(df)} rows | {df['date'].min()} → {df['date'].max()}")
    return df


def load_bdi_csv(filepath: str | Path | None = None) -> pd.DataFrame:
    """
    Load Baltic Dry Index (BDI) historical series.
    Falls back to BDRY ETF proxy if not provided.
    Source: tloosley/BDI-Prediction-Model — bdi.csv pattern
    """
    if filepath is None:
        bdi_path = RAW_DIR / "freight_rates" / "bdi.csv"
        if not bdi_path.exists():
            logger.warning("bdi.csv not found — fetching BDRY proxy from Yahoo Finance")
            proxy = fetch_yahoo_proxy_data(save=True)
            return proxy[["BDI_ETF"]].rename(columns={"BDI_ETF": "bdi"})
        filepath = bdi_path

    df = pd.read_csv(filepath, parse_dates=["date"])
    df.columns = df.columns.str.lower().str.strip()
    df = df.sort_values("date").reset_index(drop=True)
    logger.info(f"Loaded BDI: {len(df)} rows")
    return df


def load_port_constraints_csv(filepath: str | Path | None = None) -> pd.DataFrame:
    """
    Load port infrastructure constraints.
    Falls back to built-in config if no CSV provided.
    """
    if filepath is None:
        # Use built-in config
        from src.config import PORT_CONSTRAINTS
        df = pd.DataFrame(PORT_CONSTRAINTS).T.reset_index()
        df.columns = ["port_name"] + list(df.columns[1:])
        logger.info(f"Using built-in port constraints: {len(df)} ports")
        return df

    df = pd.read_csv(filepath)
    df.columns = df.columns.str.lower().str.strip()
    logger.info(f"Loaded port constraints from CSV: {len(df)} ports")
    return df


# ── Synthetic Data Generator (Phase 1 fallback) ──────────────────────────────

def generate_synthetic_freight_rates(
    route_id: str = "AUS-PAR",
    vessel_class: str = "Panamax",
    start: str = "2018-01-01",
    end: str = "2024-12-31",
    base_rate: float = 18.0,
    seed: int = 42,
    save: bool = True,
) -> pd.DataFrame:
    """
    Generate realistic synthetic freight rates for a route × vessel class pair.
    Uses random walk + seasonal component to mimic BDI behavior.
    Use ONLY during development when real data is unavailable.
    """
    import numpy as np

    np.random.seed(seed)
    dates = pd.date_range(start, end, freq="W-MON")
    n = len(dates)

    # Trend + seasonal + noise (mimics dry-bulk rate volatility)
    trend = np.linspace(0, 5, n)
    seasonal = 3.0 * np.sin(2 * np.pi * np.arange(n) / 52)  # annual cycle
    noise = np.random.normal(0, 2.5, n).cumsum() * 0.1
    rates = base_rate + trend + seasonal + noise
    rates = np.clip(rates, 5.0, 80.0)  # realistic $/tonne bounds

    df = pd.DataFrame({
        "date": dates,
        "rate": rates.round(2),
        "vessel_class": vessel_class,
        "route_id": route_id,
        "unit": "USD_per_tonne",
        "is_synthetic": True,
    })

    if save:
        fname = f"synthetic_{route_id}_{vessel_class}.csv".replace("/", "-")
        out = RAW_DIR / "freight_rates" / fname
        out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(out, index=False)
        logger.info(f"Saved synthetic rates to {out}")

    return df


# ── Master Loader ─────────────────────────────────────────────────────────────

def load_all_routes_data(use_synthetic: bool = False) -> pd.DataFrame:
    """
    Load freight rate data for all configured routes.
    Tries real CSVs first; falls back to synthetic if use_synthetic=True.
    """
    frames = []
    for route in TRADE_ROUTES:
        route_id = route["route_id"]
        for vessel_class in ["Handysize", "Supramax", "Panamax", "Capesize"]:
            fname = RAW_DIR / "freight_rates" / f"{route_id}_{vessel_class}.csv"
            if fname.exists():
                df = load_freight_rate_csv(fname)
                df["route_id"] = route_id
                df["vessel_class"] = vessel_class
                frames.append(df)
            elif use_synthetic:
                df = generate_synthetic_freight_rates(route_id, vessel_class, save=True)
                frames.append(df)

    if not frames:
        raise FileNotFoundError(
            "No freight rate data found. Run with use_synthetic=True to generate placeholder data."
        )

    combined = pd.concat(frames, ignore_index=True)
    logger.success(f"Loaded {len(combined)} total rows across {combined['route_id'].nunique()} routes")
    return combined
