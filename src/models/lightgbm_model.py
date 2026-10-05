"""
Phase 3 — LightGBM Forecasting Model with Optuna Hyperparameter Tuning
Reference: boa-forecaster (TomCardeLo) — LightGBM + Optuna pattern
           RSL-times-series-forecasting — SHAP explainability pattern
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import lightgbm as lgb
import optuna
import shap
from loguru import logger
from pathlib import Path
import joblib

from src.config import MODEL_DIR
from src.utils.metrics import compute_metrics

optuna.logging.set_verbosity(optuna.logging.WARNING)


class LightGBMFreightModel:
    """
    LightGBM gradient-boosted regression model for freight rate forecasting.
    Trained per route × vessel class pair.

    Features:
    - Optuna hyperparameter optimization with walk-forward objective
    - SHAP-based explainability (why is rate going up/down?)
    - Confidence interval estimation via quantile regression
    - Serializable — save/load for production API serving
    """

    name = "LightGBM"

    def __init__(
        self,
        n_trials: int = 50,
        horizon_weeks: int = 4,
        quantiles: list[float] = [0.1, 0.5, 0.9],
    ):
        self.n_trials = n_trials
        self.horizon_weeks = horizon_weeks
        self.quantiles = quantiles
        self.model_median: lgb.Booster | None = None
        self.model_lower:  lgb.Booster | None = None
        self.model_upper:  lgb.Booster | None = None
        self.best_params: dict = {}
        self.feature_names: list[str] = []

    # ── Training ──────────────────────────────────────────────────────────────

    def _objective(self, trial: optuna.Trial, X: pd.DataFrame, y: pd.Series) -> float:
        """Optuna objective: minimize MAPE via walk-forward inner-loop."""
        params = {
            "objective":        "regression",
            "metric":           "mape",
            "verbosity":        -1,
            "boosting_type":    "gbdt",
            "num_leaves":       trial.suggest_int("num_leaves", 20, 150),
            "learning_rate":    trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
            "n_estimators":     trial.suggest_int("n_estimators", 100, 1000),
            "min_child_samples":trial.suggest_int("min_child_samples", 5, 50),
            "subsample":        trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "reg_alpha":        trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda":       trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        }

        # Simple time-based split for tuning (avoid data leakage)
        split = int(len(X) * 0.8)
        X_tr, X_val = X.iloc[:split], X.iloc[split:]
        y_tr, y_val = y.iloc[:split], y.iloc[split:]

        model = lgb.LGBMRegressor(**params)
        model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], callbacks=[lgb.early_stopping(50, verbose=False)])
        preds = model.predict(X_val)
        metrics = compute_metrics(y_val.values, preds)
        return metrics["mape"]

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series) -> None:
        """
        1. Tune hyperparameters with Optuna
        2. Train median model (point forecast)
        3. Train lower/upper quantile models (confidence band)
        """
        self.feature_names = list(X_train.columns)
        logger.info(f"LightGBM: tuning {self.n_trials} Optuna trials...")

        study = optuna.create_study(direction="minimize")
        study.optimize(
            lambda trial: self._objective(trial, X_train, y_train),
            n_trials=self.n_trials,
            show_progress_bar=False,
        )
        self.best_params = study.best_params
        logger.success(f"Best MAPE: {study.best_value:.2f}% | params: {self.best_params}")

        # Train median (point forecast)
        self.model_median = lgb.LGBMRegressor(**self.best_params, objective="regression")
        self.model_median.fit(X_train, y_train)

        # Train quantile models for confidence intervals
        self.model_lower = lgb.LGBMRegressor(**{**self.best_params, "objective": "quantile", "alpha": 0.1})
        self.model_upper = lgb.LGBMRegressor(**{**self.best_params, "objective": "quantile", "alpha": 0.9})
        self.model_lower.fit(X_train, y_train)
        self.model_upper.fit(X_train, y_train)

        logger.success("LightGBM models (median + 10th/90th quantile) trained")

    def predict(self, X_test: pd.DataFrame) -> np.ndarray:
        """Point forecast (median model)."""
        return self.model_median.predict(X_test)

    def predict_with_intervals(self, X_test: pd.DataFrame) -> dict:
        """
        Returns forecast with 80% confidence interval.
        {forecast, lower_80, upper_80}
        """
        return {
            "forecast":   self.model_median.predict(X_test),
            "lower_80":   self.model_lower.predict(X_test),
            "upper_80":   self.model_upper.predict(X_test),
        }

    # ── Explainability (SHAP) ─────────────────────────────────────────────────

    def get_shap_values(self, X: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
        """
        Compute SHAP values for feature importance & 'Why this forecast?' panel.
        Returns: (shap_values array, feature_names list)
        """
        explainer = shap.TreeExplainer(self.model_median)
        shap_values = explainer.shap_values(X)
        return shap_values, self.feature_names

    def get_top_drivers(self, X_row: pd.DataFrame, n: int = 5) -> list[dict]:
        """
        Return top-N feature drivers for a single prediction row.
        Used in dashboard 'Why this forecast?' panel.
        """
        shap_vals, feat_names = self.get_shap_values(X_row)
        drivers = sorted(
            zip(feat_names, shap_vals[0]),
            key=lambda x: abs(x[1]),
            reverse=True,
        )[:n]
        return [{"feature": f, "shap_value": float(v), "direction": "↑" if v > 0 else "↓"} for f, v in drivers]

    # ── Persistence ───────────────────────────────────────────────────────────

    def save(self, route_id: str, vessel_class: str) -> Path:
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        path = MODEL_DIR / f"lgbm_{route_id}_{vessel_class}.pkl"
        joblib.dump(self, path)
        logger.info(f"Model saved → {path}")
        return path

    @classmethod
    def load(cls, route_id: str, vessel_class: str) -> "LightGBMFreightModel":
        path = MODEL_DIR / f"lgbm_{route_id}_{vessel_class}.pkl"
        if not path.exists():
            raise FileNotFoundError(f"No saved model at {path} — run training first")
        return joblib.load(path)
