"""
Phase 4 — FastAPI Backend
Reference: SupplyChain_Demand_Forecasting_MLOPS (amitabh1609) — FastAPI serving pattern

5 core endpoints:
  POST /api/v1/forecast    → freight rate forecast with confidence intervals
  POST /api/v1/recommend   → ranked vessel recommendation after constraint filter
  POST /api/v1/risk        → volatility flag + congestion score
  POST /api/v1/timing      → optimal charter window (market entry timing)
  GET  /api/v1/ports       → port constraint reference data
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from backend.routers import forecast, recommend, risk, ports, timing


# ── Lifespan (startup/shutdown) ───────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚢 Freight Forecasting API starting up...")
    # TODO: pre-load trained models into memory here for fast inference
    yield
    logger.info("API shutting down.")


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="SIH26006 — Intelligent Freight Forecasting API",
    description=(
        "ML-driven freight rate forecasting and vessel chartering decision support "
        "for bulk cargo procurement to India's East Coast ports."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(forecast.router,  prefix="/api/v1", tags=["Forecasting"])
app.include_router(recommend.router, prefix="/api/v1", tags=["Vessel Recommendation"])
app.include_router(risk.router,      prefix="/api/v1", tags=["Risk & Alerts"])
app.include_router(ports.router,     prefix="/api/v1", tags=["Port Reference Data"])
app.include_router(timing.router,    prefix="/api/v1", tags=["Market Timing"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "SIH26006 Freight Forecasting API",
        "status": "operational",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
