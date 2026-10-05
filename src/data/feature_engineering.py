"""
Phase 1–2 — Feature Engineering
Lag features, rolling statistics, calendar features, and exogenous indicators.
Reference: Freight-Prediction (Stef-creator) — feature engineering pipeline
"""

import pandas as pd
import numpy as np
from loguru import logger

from src.config import FEATURES_DIR


def add_lag_features(df: pd.DataFrame, target_col: str = "rate", lags: list[int] = [1, 2, 4, 8, 13, 26]) -> pd.DataFrame:
    """
    Add lagged versions of the target column (in weeks).
    Critical for freight rate time-series — rates are autocorrelated.
    """
    for lag in lags:
        df[f"{target_col}_lag_{lag}w"] = df.groupby(["route_id", "vessel_class"])[target_col].shift(lag)
    logger.debug(f"Added {len(lags)} lag features")
    return df


def add_rolling_features(df: pd.DataFrame, target_col: str = "rate", windows: list[int] = [4, 8, 13, 26]) -> pd.DataFrame:
    """
    Add rolling mean, std, min, max over the target column.
    Captures trend and volatility context for the model.
    """
    for w in windows:
        grp = df.groupby(["route_id", "vessel_class"])[target_col]
        df[f"{target_col}_roll_mean_{w}w"] = grp.transform(lambda x: x.shift(1).rolling(w).mean())
        df[f"{target_col}_roll_std_{w}w"]  = grp.transform(lambda x: x.shift(1).rolling(w).std())
        df[f"{target_col}_roll_min_{w}w"]  = grp.transform(lambda x: x.shift(1).rolling(w).min())
        df[f"{target_col}_roll_max_{w}w"]  = grp.transform(lambda x: x.shift(1).rolling(w).max())
    logger.debug(f"Added rolling features for windows {windows}")
    return df


def add_calendar_features(df: pd.DataFrame, date_col: str = "date") -> pd.DataFrame:
    """
    Add time-based features: month, quarter, week of year, year.
    Captures seasonal demand patterns (e.g., coal demand peaks in Q4).
    """
    dt = pd.to_datetime(df[date_col])
    df["month"]        = dt.dt.month
    df["quarter"]      = dt.dt.quarter
    df["week_of_year"] = dt.dt.isocalendar().week.astype(int)
    df["year"]         = dt.dt.year
    df["month_sin"]    = np.sin(2 * np.pi * df["month"] / 12)   # cyclical encoding
    df["month_cos"]    = np.cos(2 * np.pi * df["month"] / 12)
    logger.debug("Added calendar features (month, quarter, week, cyclical)")
    return df


def add_route_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add route metadata: sailing distance, origin/destination encodings.
    """
    from src.config import TRADE_ROUTES
    route_map = {r["route_id"]: r for r in TRADE_ROUTES}

    df["sailing_distance_nm"] = df["route_id"].map(
        lambda r: route_map.get(r, {}).get("sailing_distance_nm", np.nan)
    )
    df["origin"]      = df["route_id"].map(lambda r: route_map.get(r, {}).get("origin", "Unknown"))
    df["destination"] = df["route_id"].map(lambda r: route_map.get(r, {}).get("destination", "Unknown"))

    # Ordinal vessel class encoding (Handysize=0 → Capesize=3)
    vessel_order = {"Handysize": 0, "Supramax": 1, "Panamax": 2, "Capesize": 3}
    df["vessel_class_ord"] = df["vessel_class"].map(vessel_order)

    logger.debug("Added route and vessel class features")
    return df


def add_exogenous_features(df: pd.DataFrame, proxy_df: pd.DataFrame) -> pd.DataFrame:
    """
    Merge Yahoo Finance proxy data (BDI ETF, coal, grain, oil) as exogenous features.
    Proxy DataFrame must be weekly-indexed.
    """
    if proxy_df is None or proxy_df.empty:
        logger.warning("No exogenous proxy data provided — skipping")
        return df

    proxy_df = proxy_df.copy()
    proxy_df.index = pd.to_datetime(proxy_df.index)

    # Resample to weekly Monday frequency to align with rate data
    proxy_weekly = proxy_df.resample("W-MON").last().ffill()
    proxy_weekly.index.name = "date"
    proxy_weekly = proxy_weekly.reset_index()

    df = df.merge(proxy_weekly, on="date", how="left")
    logger.debug(f"Merged {proxy_weekly.columns.tolist()} exogenous features")
    return df


def add_rate_change_features(df: pd.DataFrame, target_col: str = "rate") -> pd.DataFrame:
    """
    Add rate-of-change and momentum features.
    Useful for capturing trend direction signals.
    """
    grp = df.groupby(["route_id", "vessel_class"])[target_col]
    df[f"{target_col}_pct_change_1w"] = grp.pct_change(1)
    df[f"{target_col}_pct_change_4w"] = grp.pct_change(4)

    # Momentum: current rate vs 8-week average
    roll8 = grp.transform(lambda x: x.shift(1).rolling(8).mean())
    df[f"{target_col}_momentum_8w"]   = df[target_col] / roll8 - 1
    logger.debug("Added rate change and momentum features")
    return df


# ── Master Feature Pipeline ───────────────────────────────────────────────────

def build_feature_set(
    rates_df: pd.DataFrame,
    proxy_df: pd.DataFrame | None = None,
    save: bool = True,
) -> pd.DataFrame:
    """
    Full feature engineering pipeline.
    Input: raw rate DataFrame
    Output: ML-ready feature DataFrame

    Pipeline:
      raw rates → lags → rolling → calendar → route info → exogenous → momentum → drop NaN
    """
    logger.info("Building feature set...")
    df = rates_df.copy()
    df = df.sort_values(["route_id", "vessel_class", "date"]).reset_index(drop=True)

    df = add_lag_features(df)
    df = add_rolling_features(df)
    df = add_calendar_features(df)
    df = add_route_features(df)
    df = add_rate_change_features(df)
    if proxy_df is not None:
        df = add_exogenous_features(df, proxy_df)

    before = len(df)
    df = df.dropna()
    logger.info(f"Dropped {before - len(df)} rows with NaN | Final: {len(df)} rows")

    if save:
        FEATURES_DIR.mkdir(parents=True, exist_ok=True)
        out = FEATURES_DIR / "features_all_routes.parquet"
        df.to_parquet(out, index=False)
        logger.success(f"Saved feature set → {out}")

    return df
