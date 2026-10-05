"""
Page 4 — Port Explorer
Shows all East Coast Indian port constraints in an interactive table + comparison view.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from src.config import PORT_CONSTRAINTS, VESSEL_SPECS

st.set_page_config(page_title="Port Explorer · FreightIQ", page_icon="🗺️", layout="wide")
st.title("🗺️ Port Explorer")
st.caption("East Coast Indian port infrastructure constraints & vessel compatibility matrix")
st.divider()

# ── Port Constraint Table ─────────────────────────────────────────────────────
port_df = pd.DataFrame(PORT_CONSTRAINTS).T.reset_index()
port_df.columns = ["Port", "Max Draft (m)", "Max LOA (m)", "Max Beam (m)",
                   "Berths", "Handling Rate (t/day)", "State", "Notes"]

st.subheader("📊 Port Infrastructure Reference Table")
st.dataframe(port_df, use_container_width=True, hide_index=True)
st.divider()

# ── Vessel Compatibility Matrix ────────────────────────────────────────────────
st.subheader("✅ Vessel Compatibility Matrix")
st.caption("Which vessel classes can physically call at each East Coast Indian port?")

from src.constraints.vessel_ranker import PortConstraintEngine

engine = PortConstraintEngine()
# Use a representative 50,000t cargo for the matrix
CARGO_T = 50_000

matrix = {}
for port in PORT_CONSTRAINTS:
    matrix[port] = {}
    for vessel in VESSEL_SPECS:
        result = engine.check_vessel(vessel, port, CARGO_T)
        matrix[port][vessel] = "✅" if result.is_eligible else "❌"

matrix_df = pd.DataFrame(matrix).T.reset_index()
matrix_df.columns = ["Port"] + list(VESSEL_SPECS.keys())
st.dataframe(matrix_df, use_container_width=True, hide_index=True)
st.caption(f"_Matrix computed for {CARGO_T:,}t reference cargo. Adjust cargo size in Vessel Recommender for exact results._")

st.divider()

# ── Draft Comparison Chart ─────────────────────────────────────────────────────
st.subheader("📏 Max Draft Comparison")

vessel_drafts = {vc: specs["draft_m"] for vc, specs in VESSEL_SPECS.items()}
port_drafts = {port: data["max_draft_m"] for port, data in PORT_CONSTRAINTS.items()}

fig = go.Figure()
fig.add_trace(go.Bar(
    name="Port Max Draft",
    x=list(port_drafts.keys()),
    y=list(port_drafts.values()),
    marker_color="#3b82f6",
    opacity=0.8,
))
for vc, draft in vessel_drafts.items():
    fig.add_hline(y=draft, line_dash="dash", annotation_text=vc, annotation_position="right")

fig.update_layout(
    title="Port Max Allowable Draft vs Vessel Class Draft Requirements",
    xaxis_title="Port",
    yaxis_title="Draft (metres)",
    template="plotly_dark",
    height=400,
)
st.plotly_chart(fig, use_container_width=True)
