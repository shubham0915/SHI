"""Forecasting metrics: MAPE, RMSE, MAE."""
import numpy as np


def compute_metrics(actuals: np.ndarray, predictions: np.ndarray) -> dict:
    actuals = np.array(actuals, dtype=float)
    predictions = np.array(predictions, dtype=float)

    mape = float(np.mean(np.abs((actuals - predictions) / np.where(actuals == 0, 1e-9, actuals))) * 100)
    rmse = float(np.sqrt(np.mean((actuals - predictions) ** 2)))
    mae  = float(np.mean(np.abs(actuals - predictions)))

    return {"mape": round(mape, 4), "rmse": round(rmse, 4), "mae": round(mae, 4)}
