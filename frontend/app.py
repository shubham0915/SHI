"""
Phase 5 — Streamlit Dashboard Entry Point
SIH26006: Intelligent Freight Forecasting Platform
"""

import streamlit as st

st.set_page_config(
    page_title="FreightIQ — SIH26006",
    page_icon="🚢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background: #0f1117; }
    .metric-card {
        background: linear-gradient(135deg, #1e2130, #252a40);
        border: 1px solid #2d3555;
        border-radius: 12px;
        padding: 1.2rem;
    }
    .stButton>button {
        background: linear-gradient(135deg, #3b82f6, #2563eb);
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("# 🚢 FreightIQ — Intelligent Freight Forecasting")
st.markdown("**SIH26006** · East Coast India Bulk Cargo Decision Support Platform")
st.divider()

def custom_metric(title, value, tooltip=""):
    st.markdown(f"""
    <div class="metric-card" title="{tooltip}">
        <div style="color: #94a3b8; font-size: 0.9rem; font-weight: 600; margin-bottom: 0.5rem; line-height: 1.2;">
            {title}
        </div>
        <div style="color: #f8fafc; font-size: 1.8rem; font-weight: 700; line-height: 1.2;">
            {value}
        </div>
    </div>
    """, unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    custom_metric("Ports Covered", "7", "Paradip, Vizag, Gangavaram, Gopalpur, Dhamra, Sagar-Sandheads, Haldia")
with col2:
    custom_metric("Trade Routes", "9", "Australia, USA, Mozambique, Russia, Indonesia → East Coast India")
with col3:
    custom_metric("Vessel Classes", "4", "Handysize, Supramax, Panamax, Capesize")
with col4:
    custom_metric("Forecast Horizon", "180d", "Short-term (30d) and mid-term (180d) contract windows")

st.divider()

st.markdown("""
### 📋 Available Modules

| Page | What it does |
|---|---|
| **🔮 Freight Forecast** | Predict freight rates with confidence intervals for any route × vessel class |
| **🚢 Vessel Recommender** | Find the best vessel for your cargo after filtering port physical constraints |
| **⚠️ Risk Alerts** | Early-warning flags for rate volatility and port congestion |
| **🗺️ Port Explorer** | Browse all East Coast Indian port infrastructure constraints |
| **⏱️ Market Timing** | Find the optimal window to fix your charter contract |

→ **Select a page from the left sidebar to begin.**
""")
