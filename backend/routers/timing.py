"""POST /api/v1/timing — Optimal market entry window recommendation."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

class TimingRequest(BaseModel):
    route_id: str     = Field(..., example="AUS-PAR")
    vessel_class: str = Field(..., example="Panamax")
    contract_type: str = Field("short_term", description="short_term (30d) or mid_term (180d)")

class TimingResponse(BaseModel):
    route_id: str
    vessel_class: str
    contract_type: str
    recommendation: str           # FIX_NOW / WAIT / MONITOR
    suggested_window_start: str
    suggested_window_end: str
    expected_saving_pct: float    # vs fixing today
    rationale: str

@router.post("/timing", response_model=TimingResponse)
async def get_timing(req: TimingRequest):
    """
    Identifies optimal charter market entry window.
    Phase 4: Replace with real trough-detection from forecast series.
    """
    from datetime import datetime, timedelta
    today = datetime.today()
    return TimingResponse(
        route_id=req.route_id,
        vessel_class=req.vessel_class,
        contract_type=req.contract_type,
        recommendation="WAIT",
        suggested_window_start=(today + timedelta(days=14)).strftime("%Y-%m-%d"),
        suggested_window_end=(today + timedelta(days=28)).strftime("%Y-%m-%d"),
        expected_saving_pct=4.2,
        rationale="Forecast shows a rate trough in weeks 2–4. Waiting ~14 days is projected to save ~4.2% vs fixing today.",
    )
