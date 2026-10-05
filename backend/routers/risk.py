"""POST /api/v1/risk — Volatility flag + congestion score."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()

class RiskRequest(BaseModel):
    route_id: str       = Field(..., example="AUS-PAR")
    destination_port: str = Field(..., example="Paradip")

class RiskResponse(BaseModel):
    route_id: str
    destination_port: str
    volatility_flag: str          # LOW / MEDIUM / HIGH
    volatility_score: float       # 0.0 – 1.0
    congestion_flag: str          # LOW / MEDIUM / HIGH
    congestion_score: float
    overall_risk: str
    advisory: str

@router.post("/risk", response_model=RiskResponse)
async def get_risk(req: RiskRequest):
    """
    Returns risk assessment: freight rate volatility + port congestion signals.
    Phase 4: Replace placeholders with real volatility model (rolling std / GARCH).
    """
    # TODO: real volatility + congestion model in Phase 4
    return RiskResponse(
        route_id=req.route_id,
        destination_port=req.destination_port,
        volatility_flag="MEDIUM",
        volatility_score=0.52,
        congestion_flag="LOW",
        congestion_score=0.18,
        overall_risk="MEDIUM",
        advisory="Monitor BDI movements weekly. Current congestion at destination is manageable.",
    )
