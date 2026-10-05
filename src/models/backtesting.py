"""
Phase 2–3 — Walk-Forward Backtesting Framework
Reference: boa-forecaster (TomCardeLo) — walk-forward CV + model leaderboard pattern

This is the core validation engine used to compare ARIMA, Prophet, and LightGBM
across routes and vessel classes. Uses rolling-window folds to avoid data leakage.
"""

from __future__ import annotations

import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from loguru import logger
from typing import Protocol, Any

from src.utils.metrics import compute_metrics


# ── Model Protocol ────────────────────────────────────────────────────────────

class FreightModel(Protocol):
    """Interface that all forecasting models must implement."""

    name: str

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> None: ...
    def predict(self, X_test: pd.DataFrame) -> np.ndarray: ...


# ── Fold Result ───────────────────────────────────────────────────────────────

@dataclass
class FoldResult:
    fold_idx: int
    model_name: str
    route_id: str
    vessel_class: str
    train_end: pd.Timestamp
    test_start: pd.Timestamp
    test_end: pd.Timestamp
    mape: float
    rmse: float
    mae: float
    predictions: np.ndarray = field(repr=False)
    actuals: np.ndarray = field(repr=False)


# ── Walk-Forward Backtester ───────────────────────────────────────────────────

class WalkForwardBacktester:
    """
    Rolling-window walk-forward cross-validator for freight rate forecasting.

    Splits time series into expanding training windows with fixed test horizons.
    Each fold: train on [0:t], test on [t:t+horizon], advance by step_weeks.

    Reference: boa-forecaster backtesting.py — adapted for multi-route freight context
    """

    def __init__(
        self,
        n_folds: int = 8,
        horizon_weeks: int = 4,
        min_train_weeks: int = 52,
        step_weeks: int = 4,
    ):
        self.n_folds = n_folds
        self.horizon_weeks = horizon_weeks
        self.min_train_weeks = min_train_weeks
        self.step_weeks = step_weeks

    def _build_folds(self, df: pd.DataFrame, date_col: str = "date") -> list[tuple]:
        """Generate (train_idx, test_idx) pairs for walk-forward CV."""
        dates = sorted(df[date_col].unique())
        n = len(dates)

        if n < self.min_train_weeks + self.horizon_weeks:
            raise ValueError(
                f"Not enough data: need {self.min_train_weeks + self.horizon_weeks} weeks, got {n}"
            )

        folds = []
        # Start from min_train_weeks, advance by step_weeks, collect n_folds
        start = self.min_train_weeks
        for _ in range(self.n_folds):
            if start + self.horizon_weeks > n:
                break
            train_dates = dates[:start]
            test_dates = dates[start: start + self.horizon_weeks]
            folds.append((train_dates, test_dates))
            start += self.step_weeks

        logger.debug(f"Generated {len(folds)} walk-forward folds (horizon={self.horizon_weeks}w)")
        return folds

    def evaluate(
        self,
        model: FreightModel,
        df: pd.DataFrame,
        feature_cols: list[str],
        target_col: str = "rate",
        date_col: str = "date",
        route_id: str = "ALL",
        vessel_class: str = "ALL",
    ) -> list[FoldResult]:
        """
        Run walk-forward backtesting for a single model on a single route × vessel segment.
        Returns a list of FoldResult objects for aggregation.
        """
        folds = self._build_folds(df, date_col)
        results = []

        for i, (train_dates, test_dates) as enumerate(folds):
            train = df[df[date_col].isin(train_dates)]
            test  = df[df[date_col].isin(test_dates)]

            X_train, y_train = train[feature_cols], train[target_col]
            X_test,  y_test  = test[feature_cols],  test[target_col]

            try:
                model.fit(X_train, y_train)
                preds = model.predict(X_test)
                metrics = compute_metrics(y_test.values, preds)

                results.append(FoldResult(
                    fold_idx=i,
                    model_name=model.name,
                    route_id=route_id,
                    vessel_class=vessel_class,
                    train_end=max(train_dates),
                    test_start=min(test_dates),
                    test_end=max(test_dates),
                    mape=metrics["mape"],
                    rmse=metrics["rmse"],
                    mae=metrics["mae"],
                    predictions=preds,
                    actuals=y_test.values,
                ))

                logger.debug(
                    f"Fold {i+1}/{len(folds)} | {model.name} | "
                    f"MAPE={metrics['mape']:.2f}% RMSE={metrics['rmse']:.2f}"
                )

            except Exception as e:
                logger.error(f"Fold {i+1} failed for {model.name}: {e}")

        return results


# ── Leaderboard Builder ───────────────────────────────────────────────────────

def build_leaderboard(all_results: list[FoldResult]) -> pd.DataFrame:
    """
    Aggregate fold results into a model leaderboard.
    Groups by model × route × vessel class, computes mean metrics across folds.
    Returns DataFrame sorted by MAPE (ascending — lower is better).
    """
    records = [
        {
            "model":        r.model_name,
            "route_id":     r.route_id,
            "vessel_class": r.vessel_class,
            "mape":         r.mape,
            "rmse":         r.rmse,
            "mae":          r.mae,
        }
        for r in all_results
    ]
    df = pd.DataFrame(records)
    leaderboard = (
        df.groupby(["model", "route_id", "vessel_class"])
          .agg(
              mean_mape=("mape", "mean"),
              mean_rmse=("rmse", "mean"),
              mean_mae=("mae",  "mean"),
              n_folds=("mape",  "count"),
          )
          .reset_index()
          .sort_values("mean_mape")
    )
    logger.info(f"Leaderboard built: {len(leaderboard)} model-route-class combinations")
    return leaderboard


def select_best_model_per_route(leaderboard: pd.DataFrame) -> dict[tuple, str]:
    """
    Returns dict: {(route_id, vessel_class): best_model_name}
    Used to determine which model to use for live forecasting.
    """
    idx = leaderboard.groupby(["route_id", "vessel_class"])["mean_mape"].idxmin()
    best = leaderboard.loc[idx][["route_id", "vessel_class", "model"]]
    return {
        (row.route_id, row.vessel_class): row.model
        for row in best.itertuples()
    }
