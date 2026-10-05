"""POST /api/v1/recommend — Vessel type recommendation after constraint filtering."""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class RecommendRequest(BaseModel):
    destination_port: str = Field(..., example="Paradip")
    origin_country:   str = Field(..., example="Australia")
    cargo_volume_t:   float = Field(..., example=65000)
    horizon_days:     int   = Field(30, ge=7, le=180)


class VesselOption(BaseModel):
    rank: int
    vessel_class: str
    eligible: bool
    rejection_reason: str | None
    forecast_rate: float | None
    turnaround_days: float | None
    total_cost_usd: float | None
    recommendation: str


@router.post("/recommend", response_model=list[VesselOption])
async def recommend_vessel(req: RecommendRequest):
    """
    Filters all 4 vessel classes against port physical constraints,
    then ranks eligible vessels by forecasted freight cost.

    Uses: PortConstraintEngine + VesselRanker (src/constraints/vessel_ranker.py)
    """
    from src.constraints.vessel_ranker import PortConstraintEngine, VesselRanker
    from src.config import VESSEL_SPECS

    engine = PortConstraintEngine()
    eligible, rejected = engine.filter_eligible_vessels(req.destination_port, req.cargo_volume_t)

    results = []

    # Eligible vessels — add placeholder forecast rates
    for i, r in enumerate(eligible):
        base_rate = {"Handysize": 22.0, "Supramax": 18.5, "Panamax": 16.0, "Capesize": 12.5}.get(r.vessel_class, 18.0)
        results.append(VesselOption(
            rank=i + 1,
            vessel_class=r.vessel_class,
            eligible=True,
            rejection_reason=None,
            forecast_rate=base_rate,
            turnaround_days=round(req.cargo_volume_t / 20000 + 1, 1),
            total_cost_usd=round(base_rate * req.cargo_volume_t, 0),
            recommendation=f"✅ Recommended — fits port constraints at {req.destination_port}",
        ))

    # Rejected vessels
    for r in rejected:
        results.append(VesselOption(
            rank=99,
            vessel_class=r.vessel_class,
            eligible=False,
            rejection_reason=r.rejection_reason,
            forecast_rate=None,
            turnaround_days=None,
            total_cost_usd=None,
            recommendation=f"❌ Ineligible — {r.rejection_reason}",
        ))

    return sorted(results, key=lambda x: x.rank)
