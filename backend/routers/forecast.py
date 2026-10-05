"""POST /api/v1/forecast — Freight rate forecast with confidence intervals."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from loguru import logger

router = APIRouter()


class ForecastRequest(BaseModel):
    route_id: str         = Field(..., example="AUS-PAR",   description="Trade route ID")
    vessel_class: str     = Field(..., example="Panamax",    description="Handysize/Supramax/Panamax/Capesize")
    horizon_days: int     = Field(30,  ge=7, le=180,         description="Forecast horizon in days")
    cargo_volume_t: float = Field(..., example=65000,        description="Cargo parcel size in tonnes")

    class Config:
        json_schema_extra = {
            "example": {
                "route_id": "AUS-PAR",
                "vessel_class": "Panamax",
                "horizon_days": 30,
                "cargo_volume_t": 65000,
            }
        }


class ForecastResponse(BaseModel):
    route_id: str
    vessel_class: str
    horizon_days: int
    forecast_rate_usd_per_tonne: float
    lower_80_ci: float
    upper_80_ci: float
    forecast_series: list[dict]   # [{date, rate, lower, upper}]
    model_used: str
    mape_backtest: float | None


@router.post("/forecast", response_model=ForecastResponse)
async def get_forecast(req: ForecastRequest):
    """
    Returns freight rate forecast with 80% confidence interval for a given
    route × vessel class × horizon.

    Steps:
    1. Load best trained model for (route_id, vessel_class) pair
    2. Build feature input for forecast horizon
    3. Return point forecast + lower/upper quantile bands
    """
    logger.info(f"Forecast request: {req.route_id} | {req.vessel_class} | {req.horizon_days}d")

    # TODO: Replace with real model inference in Phase 4
    # Placeholder response for scaffold validation
    import random, math
    from datetime import datetime, timedelta

    base_rate = 18.0
    series = []
    for i in range(req.horizon_days // 7):
        date = (datetime.today() + timedelta(weeks=i)).strftime("%Y-%m-%d")
        rate = base_rate + random.gauss(0, 1.5) + math.sin(i * 0.5)
        series.append({
            "date": date,
            "rate": round(rate, 2),
            "lower": round(rate * 0.88, 2),
            "upper": round(rate * 1.12, 2),
        })

    return ForecastResponse(
        route_id=req.route_id,
        vessel_class=req.vessel_class,
        horizon_days=req.horizon_days,
        forecast_rate_usd_per_tonne=round(base_rate + random.gauss(0, 1), 2),
        lower_80_ci=round((base_rate - 2.5), 2),
        upper_80_ci=round((base_rate + 3.0), 2),
        forecast_series=series,
        model_used="LightGBM (placeholder)",
        mape_backtest=None,
    )
