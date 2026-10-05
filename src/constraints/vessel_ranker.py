"""
Phase 3 — Vessel-Port Constraint Engine + Vessel Ranker
Reference: AryanB26/FreightIQ — vessel-port compatibility + charter decision module
           SIH26006 (Abhishekinthegrid) — route constraint integration

This is the core differentiator of the SIH26006 system:
  1. Filter vessel classes that CANNOT physically call at the destination port
  2. Rank remaining eligible vessels by forecast cost + turnaround efficiency
  3. Return a ranked recommendation list with reasons
"""

from __future__ import annotations

import pandas as pd
from dataclasses import dataclass
from loguru import logger

from src.config import PORT_CONSTRAINTS, VESSEL_SPECS


# ── Data Classes ──────────────────────────────────────────────────────────────

@dataclass
class PortConstraintResult:
    vessel_class: str
    is_eligible: bool
    rejection_reason: str | None
    # Port vs vessel comparison
    port_max_draft: float
    vessel_draft: float
    port_max_loa: float
    vessel_loa: float
    port_max_beam: float
    vessel_beam: float


@dataclass
class VesselRecommendation:
    rank: int
    vessel_class: str
    forecast_rate_usd_per_tonne: float
    forecast_lower: float
    forecast_upper: float
    estimated_turnaround_days: float
    total_voyage_cost_usd: float        # rate × cargo_volume
    cost_per_tonne: float
    constraint_check: PortConstraintResult
    recommendation_reason: str


# ── Constraint Filter ─────────────────────────────────────────────────────────

class PortConstraintEngine:
    """
    Cross-references vessel physical specs against port infrastructure limits.
    Eliminates vessel classes that CANNOT physically call at the port.

    Checks:
      - Draft (vessel vs port max allowable draft)
      - LOA (vessel length vs port maximum berth length)
      - Beam (vessel width vs port channel/berth width)
      - Cargo capacity (cargo_volume fits within vessel min/max DWT range)
    """

    def check_vessel(
        self,
        vessel_class: str,
        port_name: str,
        cargo_volume_t: float,
    ) -> PortConstraintResult:
        """Check if a vessel class is physically eligible for a port + cargo."""
        port = PORT_CONSTRAINTS.get(port_name)
        vessel = VESSEL_SPECS.get(vessel_class)

        if port is None:
            raise ValueError(f"Unknown port: {port_name}. Valid: {list(PORT_CONSTRAINTS.keys())}")
        if vessel is None:
            raise ValueError(f"Unknown vessel class: {vessel_class}. Valid: {list(VESSEL_SPECS.keys())}")

        rejection_reason = None

        # Check 1: Draft
        if vessel["draft_m"] > port["max_draft_m"]:
            rejection_reason = (
                f"Draft exceeded: vessel {vessel['draft_m']}m > port max {port['max_draft_m']}m"
            )

        # Check 2: LOA
        elif vessel["loa_m"] > port["max_loa_m"]:
            rejection_reason = (
                f"LOA exceeded: vessel {vessel['loa_m']}m > port max {port['max_loa_m']}m"
            )

        # Check 3: Beam
        elif vessel["beam_m"] > port["max_beam_m"]:
            rejection_reason = (
                f"Beam exceeded: vessel {vessel['beam_m']}m > port max {port['max_beam_m']}m"
            )

        # Check 4: Cargo volume within vessel capacity
        elif cargo_volume_t < vessel["min_cargo_t"]:
            rejection_reason = (
                f"Cargo too small: {cargo_volume_t:,.0f}t < vessel min {vessel['min_cargo_t']:,.0f}t"
            )
        elif cargo_volume_t > vessel["max_cargo_t"]:
            rejection_reason = (
                f"Cargo too large: {cargo_volume_t:,.0f}t > vessel max {vessel['max_cargo_t']:,.0f}t"
            )

        return PortConstraintResult(
            vessel_class=vessel_class,
            is_eligible=(rejection_reason is None),
            rejection_reason=rejection_reason,
            port_max_draft=port["max_draft_m"],
            vessel_draft=vessel["draft_m"],
            port_max_loa=port["max_loa_m"],
            vessel_loa=vessel["loa_m"],
            port_max_beam=port["max_beam_m"],
            vessel_beam=vessel["beam_m"],
        )

    def filter_eligible_vessels(
        self,
        port_name: str,
        cargo_volume_t: float,
    ) -> tuple[list[PortConstraintResult], list[PortConstraintResult]]:
        """
        Check all 4 vessel classes. Return (eligible_list, rejected_list).
        """
        eligible, rejected = [], []
        for vessel_class in VESSEL_SPECS:
            result = self.check_vessel(vessel_class, port_name, cargo_volume_t)
            if result.is_eligible:
                eligible.append(result)
            else:
                rejected.append(result)

        logger.info(
            f"Port '{port_name}' | Cargo {cargo_volume_t:,.0f}t → "
            f"{len(eligible)} eligible, {len(rejected)} rejected"
        )
        return eligible, rejected


# ── Vessel Ranker ─────────────────────────────────────────────────────────────

class VesselRanker:
    """
    Ranks eligible vessels by:
      1. Forecast freight rate (lower = better)
      2. Estimated turnaround time (lower = better)
      3. Total voyage cost (rate × cargo volume)

    Uses forecast rates from the LightGBM model output.
    """

    def __init__(self, port_constraint_engine: PortConstraintEngine | None = None):
        self.constraint_engine = port_constraint_engine or PortConstraintEngine()

    def _estimate_turnaround(self, port_name: str, vessel_class: str, cargo_volume_t: float) -> float:
        """
        Estimate port turnaround time (days) based on cargo volume and port handling rate.
        Formula: volume / handling_rate + 1 day berth overhead
        """
        port = PORT_CONSTRAINTS[port_name]
        handling_rate = port["handling_rate_tpd"]
        return round(cargo_volume_t / handling_rate + 1.0, 1)

    def rank(
        self,
        port_name: str,
        cargo_volume_t: float,
        forecast_rates: dict[str, dict],   # {vessel_class: {forecast, lower_80, upper_80}}
    ) -> list[VesselRecommendation]:
        """
        Main ranking method.

        Args:
            port_name: Destination port name
            cargo_volume_t: Cargo parcel size in tonnes
            forecast_rates: Forecast output from LightGBM for each vessel class

        Returns:
            List of VesselRecommendation sorted by cost efficiency (rank 1 = best)
        """
        eligible, rejected = self.constraint_engine.filter_eligible_vessels(port_name, cargo_volume_t)

        if not eligible:
            logger.warning(f"No eligible vessels for {port_name} with {cargo_volume_t:,.0f}t cargo")
            return []

        recommendations = []
        for constraint_result in eligible:
            vc = constraint_result.vessel_class
            rates = forecast_rates.get(vc, {})
            if not rates:
                logger.warning(f"No forecast available for {vc} — skipping")
                continue

            forecast_rate = rates.get("forecast", 0.0)
            turnaround_days = self._estimate_turnaround(port_name, vc, cargo_volume_t)
            total_cost = forecast_rate * cargo_volume_t

            recommendations.append(VesselRecommendation(
                rank=0,  # set after sort
                vessel_class=vc,
                forecast_rate_usd_per_tonne=round(forecast_rate, 2),
                forecast_lower=round(rates.get("lower_80", forecast_rate * 0.9), 2),
                forecast_upper=round(rates.get("upper_80", forecast_rate * 1.1), 2),
                estimated_turnaround_days=turnaround_days,
                total_voyage_cost_usd=round(total_cost, 0),
                cost_per_tonne=round(forecast_rate, 2),
                constraint_check=constraint_result,
                recommendation_reason=(
                    f"Eligible: draft {constraint_result.vessel_draft}m ≤ {constraint_result.port_max_draft}m, "
                    f"LOA {constraint_result.vessel_loa}m ≤ {constraint_result.port_max_loa}m"
                ),
            ))

        # Sort by total cost (lowest first)
        recommendations.sort(key=lambda r: r.total_voyage_cost_usd)
        for i, rec in enumerate(recommendations):
            rec.rank = i + 1

        logger.success(
            f"Vessel ranking for {port_name}: "
            + " > ".join([f"#{r.rank} {r.vessel_class} (${r.cost_per_tonne}/t)" for r in recommendations])
        )
        return recommendations

    def to_dataframe(self, recommendations: list[VesselRecommendation]) -> pd.DataFrame:
        """Convert recommendation list to a clean DataFrame for Streamlit display."""
        rows = []
        for r in recommendations:
            rows.append({
                "Rank":                  r.rank,
                "Vessel Class":          r.vessel_class,
                "Rate ($/tonne)":        r.forecast_rate_usd_per_tonne,
                "Lower 80% CI":          r.forecast_lower,
                "Upper 80% CI":          r.forecast_upper,
                "Turnaround (days)":     r.estimated_turnaround_days,
                "Total Voyage Cost ($)": f"{r.total_voyage_cost_usd:,.0f}",
                "Status":                "✅ Eligible",
                "Reason":                r.recommendation_reason,
            })
        return pd.DataFrame(rows)
