# 🚢 SIH26006 — Intelligent Freight Forecasting Model
### Optimized Vessel Chartering & Bulk Cargo Procurement — East Coast India

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110-green)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35-red)](https://streamlit.io)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.3-orange)](https://lightgbm.readthedocs.io)

---

## Problem
India's East Coast bulk cargo chartering is **fully reactive** — daily spot-market checks, no predictive strategy.
This leads to: suboptimal vessel selection, missed cheap charter windows, and avoidable vessel idle time.

## Solution
A **4-layer ML pipeline** that:
1. **Forecasts freight rates** per route × vessel class with confidence intervals
2. **Recommends the best vessel type** after filtering port physical constraints (draft, LOA, beam)
3. **Identifies optimal charter timing** — when to fix short/mid-term contracts
4. **Flags risk** — volatility, congestion, and idle/deadheading scenarios

---

## Project Structure

```
SHI/
├── data/                      # Raw → Processed → Features pipeline
│   ├── raw/
│   │   ├── freight_rates/     # BDI, BPI, route-specific CSVs
│   │   ├── commodity/         # Brent, coal, grain indices
│   │   └── port_constraints/  # Port physical specs
│   ├── processed/
│   ├── features/
│   └── seed/                  # Port & vessel reference tables
│
├── src/                       # Core ML + business logic
│   ├── data/                  # Ingestion, preprocessing, feature engineering
│   ├── models/                # ARIMA, Prophet, LightGBM, backtesting
│   ├── constraints/           # Port constraint DB + vessel ranker
│   ├── risk/                  # Volatility, congestion, idle-time advisory
│   └── utils/                 # Metrics, logging
│
├── backend/                   # FastAPI serving layer
│   └── routers/               # /forecast /recommend /risk /ports /timing
│
├── frontend/                  # Streamlit dashboard
│   └── pages/                 # 5 dashboard pages
│
├── database/                  # PostgreSQL schema + migrations
├── notebooks/                 # Exploration & experimentation
└── tests/                     # Unit + integration tests
```

---

## Development Phases

| Phase | Milestone | Reference Repo |
|---|---|---|
| **Phase 1** | Data collection + port constraint DB | Freight-Prediction |
| **Phase 2** | ARIMA/Prophet baseline + backtesting | boa-forecaster |
| **Phase 3** | LightGBM/Optuna + vessel ranking | boa-forecaster + FreightIQ |
| **Phase 4** | Risk module + FastAPI backend | SupplyChain_MLOPS |
| **Phase 5** | Streamlit dashboard + Docker | SupplyChain_MLOPS + FreightIQ |

---

## Quick Start

```bash
# 1. Clone and setup
git clone <your-repo>
cd SHI
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env with your DB credentials

# 3. Seed the database
python scripts/seed_db.py

# 4. Run backend
cd backend && uvicorn main:app --reload

# 5. Run dashboard
cd frontend && streamlit run app.py

# OR — Run everything with Docker
docker-compose up --build
```

---

## Trade Lanes in Scope

**Origins:** Australia · USA · Mozambique · Russia · Indonesia  
**Destinations:** Paradip · Vizag · Gangavaram · Gopalpur · Dhamra · Sagar-Sandheads · Haldia  
**Vessel Classes:** Handysize · Supramax · Panamax · Capesize

---

## Tech Stack

| Layer | Tools |
|---|---|
| Data Processing | Python, Pandas, NumPy |
| Forecasting / ML | ARIMA, Prophet, LightGBM, Optuna, SHAP |
| Backend API | FastAPI, Uvicorn |
| Dashboard | Streamlit, Plotly |
| Database | PostgreSQL |
| Deployment | Docker, Docker Compose |
