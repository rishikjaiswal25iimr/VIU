"""
VIU DASHBOARD – FeSi70 vs Si Metal
================================================
Optimal Substitution Solver
Calculates the mathematically cheapest blend of FeSi70
against 98% Silicon Metal based on metallurgical constraints.

All formulas sourced from the FeSi vs Si Metal Excel file.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy.optimize import linprog

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & THEME
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="FeSi vs Si Metal Solver",
    page_icon="⚗️",
    layout="wide",
)

# Colour palette matching the requested theme
C_FESI     = "#2196F3"   # blue  – FeSi70
C_SIMETAL  = "#4CAF50"   # green – Si Metal
C_DELTA    = "#FF9800"   # amber – delta / benefit
C_NEG      = "#F44336"   # red   – penalties / negative
C_GRID     = "#EEEEEE"
C_BG       = "#FAFAFA"
C_TEXT     = "#333333"

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ---------- page background ---------- */
.stApp { background: #F0F4F8; }

/* ---------- sidebar ---------- */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1A237E 0%, #283593 40%, #1565C0 100%);
}
[data-testid="stSidebar"] * { color: #E8EAF6 !important; }
[data-testid="stSidebar"] .stSlider > div > div > div { background: #5C6BC0 !important; }
[data-testid="stSidebar"] hr { border-color: #3949AB; }
[data-testid="stSidebar"] .stNumberInput input { background: #283593; border-color: #5C6BC0; color: #fff !important; }
[data-testid="stSidebar"] .stSelectbox select { background: #283593; color: #fff; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { color: #fff !important; }

/* ---------- section headers ---------- */
.section-header {
    font-size: 20px; font-weight: 800; color: #1A237E;
    text-transform: uppercase; letter-spacing: 0.05em;
    border-bottom: 3px solid #2196F3;
    padding-bottom: 8px; margin-bottom: 24px; margin-top: 32px;
}

/* ---------- info boxes ---------- */
.info-box {
    background: #E3F2FD; border-radius: 8px;
    padding: 12px 16px; font-size: 13px; color: #1565C0;
    border-left: 4px solid #2196F3; margin-bottom: 10px;
}
.success-box {
    background: #E8F5E9; border-radius: 8px;
    padding: 12px 16px; font-size: 13px; color: #1B5E20;
    border-left: 4px solid #4CAF50; margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HELPER: Plotly layout template
# ══════════════════════════════════════════════════════════════════════════════
def _layout(title: str, y_title: str = "", height: int = 420) -> dict:
    return dict(
        template="plotly_white",
        paper_bgcolor="white",
        plot_bgcolor=C_BG,
        font=dict(family="Inter, sans-serif", size=12, color=C_TEXT),
        title=dict(text=title, font=dict(size=15, color="#1A237E"), x=0.01),
        legend=dict(bgcolor="rgba(255,255,255,0.85)", bordercolor="#DDD", borderwidth=1),
        xaxis=dict(showgrid=True, gridcolor=C_GRID, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=C_GRID, zeroline=False, title=y_title),
        hovermode="x unified",
        height=height,
        margin=dict(l=60, r=30, t=55, b=45),
    )

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR – ALL INPUT PARAMETERS (FeSi vs Si Metal Specific)
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚗️ VIU Substitution Solver")
    st.divider()

    st.markdown("### A. Comparison Selection")
    comparison_selection = st.radio(
        "Select Analysis:",
        ["Not selected", "FeSi70 vs Si Metal"],
        index=1
    )
    
    if comparison_selection != "Not selected":
        st.divider()
        st.markdown("### B. Financial Parameters")
        P_FeSi_Price          = st.number_input("FeSi70 Price (₹/MT)",        value=111500, step=1000)
        P_SiMetal_Price       = st.number_input("Si Metal Price (₹/MT)",      value=143000, step=1000)
        P_Power_Tariff        = st.number_input("Power Tariff (₹/kWh)",       value=6.5, step=0.1)
        P_Scrap_Price         = st.number_input("Scrap Cost (₹/MT)",          value=35000, step=500)
        P_Electrode_Cost      = st.number_input("Electrode Cost (₹/kg)",      value=240, step=10)
        P_Steel_Value         = st.number_input("Steel Value (₹/MT)",         value=60000, step=1000)
        P_Slag_Handling       = st.number_input("Ladle Slag Cost (₹/MT)",     value=600, step=50)
        P_Margin_Steel        = st.number_input("Meltshop Margin (₹/MT)",     value=2800, step=100)
        P_LF_Retreatment_Cost = st.number_input("LF Re-treatment Cost (₹)",   value=15000, step=500)

        st.divider()
        st.markdown("### C. Technical Parameters")
        P_FeSi_Si      = st.slider("FeSi70 Si Content (%)",    60.0, 80.0, 70.0, 0.5) / 100
        P_SiMetal_Si   = st.slider("Si Metal Si Content (%)",  95.0, 99.9, 98.0, 0.1) / 100
        P_FeSi_Rec     = st.slider("FeSi70 Recovery (%)",      80.0, 99.0, 90.0, 0.5) / 100
        P_SiMetal_Rec  = st.slider("Si Metal Recovery (%)",    85.0, 99.9, 93.0, 0.5) / 100
        P_FeSi_Fe      = st.slider("FeSi70 Fe Content (%)",    15.0, 30.0, 25.0, 0.5) / 100
        P_LF_Efficiency= st.slider("LF Efficiency (%)",        25.0, 80.0, 45.0, 1.0) / 100

        st.divider()
        st.markdown("### D. Operational Parameters")
        P_Heat_Size       = st.slider("Heat Size (MT)",             100, 350, 190, 5)
        P_Cycle_Saved     = st.slider("LF Cycle Time Saved (min)",  1, 10, 2, 1)
        Ca_Wire_FeSi      = st.slider("Ca-Wire FeSi (kg/T)",        0.5, 2.0, 1.0, 0.1)
        Ca_Wire_SiMetal   = st.slider("Ca-Wire Si Metal (kg/T)",    0.1, 1.5, 0.65, 0.05)
        P_TempRise_FeSi   = st.slider("Temp Rise FeSi (°C/kg Si)",  0.5, 2.5, 1.38, 0.01)
        P_TempRise_Si     = st.slider("Temp Rise Si (°C/kg Si)",    1.0, 3.0, 1.95, 0.01)
        Reject_FeSi       = st.number_input("FeSi Rejection Rate",      value=0.0005, format="%.5f", step=0.0001)
        Reject_SiMetal    = st.number_input("Si Metal Rejection Rate",  value=0.00035, format="%.5f", step=0.0001)
        Retreatment_FeSi  = st.slider("FeSi Re-treatment Freq (%)", 1.0, 5.0, 2.5, 0.1) / 100
        Retreatment_Si    = st.slider("Si Re-treatment Freq (%)",   0.5, 3.0, 1.0, 0.1) / 100

        st.divider()
        st.markdown("### E. Realization Factors")
        R_Power       = st.slider("Power Realization",       0.50, 1.00, 0.90, 0.01)
        R_Electrode   = st.slider("Electrode Realization",   0.50, 1.00, 0.90, 0.01)
        R_Throughput  = st.slider("Throughput Realization",  0.10, 1.00, 0.40, 0.01)
        R_Cleanliness = st.slider("Cleanliness Realization", 0.10, 1.00, 0.30, 0.01)
        R_Yield       = st.slider("Yield Realization",       0.05, 0.50, 0.20, 0.01)
        R_CaWire      = st.slider("Ca-Wire Realization",     0.10, 1.00, 0.50, 0.01)

        st.divider()
        st.markdown("### F. Enterprise Savings")
        Si_Consumption_FY = st.number_input("Consumption (MT)", value=5000, step=100)
        Substitution_Pct  = st.slider("% Substitution", 0.0, 1.0, 0.50, 0.05)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT GUARD
# ══════════════════════════════════════════════════════════════════════════════
if comparison_selection == "Not selected":
    st.info("Please select 'FeSi70 vs Si Metal' to run the Solver.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# CORE COST CALCULATIONS FOR SOLVER OBJECTIVE FUNCTION
# ══════════════════════════════════════════════════════════════════════════════
# Objective: Minimize Effective Raw Material Cost per MT Active Si
Cost_Per_Si_FeSi    = P_FeSi_Price / (P_FeSi_Si * P_FeSi_Rec)
Cost_Per_Si_SiMetal = P_SiMetal_Price / (P_SiMetal_Si * P_SiMetal_Rec)

# Deduct Iron Credit inherently present in FeSi70
Iron_Credit_Per_Si_FeSi = (P_FeSi_Fe * P_Scrap_Price) / (P_FeSi_Si * P_FeSi_Rec)
Net_Cost_FeSi = Cost_Per_Si_FeSi - Iron_Credit_Per_Si_FeSi
Net_Cost_SiMetal = Cost_Per_Si_SiMetal


# ══════════════════════════════════════════════════════════════════════════════
# SUBSTITUTION SOLVER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
<div style="background: linear-gradient(135deg,#1A237E 0%,#1565C0 60%,#0277BD 100%);
            padding:22px 28px 18px 28px; border-radius:14px; margin-bottom:20px;
            box-shadow:0 4px 24px rgba(26,35,126,0.25);">
  <h1 style="color:#FFFFFF;margin:0;font-size:26px;font-weight:800;letter-spacing:0.02em;">
    🧠 Optimal Alloy Substitution Solver
  </h1>
  <p style="color:#90CAF9;margin:6px 0 0 0;font-size:13px;">
    Calculates the mathematically cheapest blend of FeSi70 and 98% Si Metal that perfectly satisfies strict metallurgical limits.
  </p>
</div>
""", unsafe_allow_html=True)

# Exact Steel Grade Constraints from Excel SOLVER Sheet
grades_data = {
    "Commodity Structural (IS2062)":   {"chill_lim": -1500, "rec_lim": 5.0, "inc_lim": 1.50, "ret_lim": 25.0, "simetal_max": 0.0},
    "TMT / Rebar (Fe500D)":            {"chill_lim": -1500, "rec_lim": 5.0, "inc_lim": 1.50, "ret_lim": 25.0, "simetal_max": 0.0},
    "HSLA (API X60 / X70)":            {"chill_lim": -1300, "rec_lim": 3.0, "inc_lim": 0.40, "ret_lim": 10.0, "simetal_max": 0.40},
    "Automotive (DP / TRIP / Bearing)":{"chill_lim": -1200, "rec_lim": 2.0, "inc_lim": 0.15, "ret_lim": 5.0,  "simetal_max": 0.60},
    "IF Steel (Deep Draw)":            {"chill_lim": -1100, "rec_lim": 1.5, "inc_lim": 0.08, "ret_lim": 2.5,  "simetal_max": 1.00},
    "Electrical Steel (CRNGO / CRGO)": {"chill_lim": -1050, "rec_lim": 1.0, "inc_lim": 0.03, "ret_lim": 1.0,  "simetal_max": 1.00},
}

# Base Alloy Property Coefficients
fesi_chill = -1500
si_chill   = -1000
fesi_rec   = 5.0
si_rec     = 1.0
fesi_inc   = 1.50
si_inc     = 0.03
fesi_ret   = 25.0
si_ret     = 1.0

gc1, gc2 = st.columns([1.5, 2.5])
sel_grade = gc1.selectbox("Select Target Steel Grade", list(grades_data.keys()), index=0)
limits = grades_data[sel_grade]

st.markdown("#### Metallurgical Constraints")
sc1, sc2, sc3, sc4, sc5 = st.columns(5)
min_chill   = sc1.slider("Min Thermal Limit (kJ/kg)", -2000, 0, limits["chill_lim"], step=50)
max_rec     = sc2.slider("Max Recovery Var (%)",      0.5, 10.0, limits["rec_lim"], step=0.5)
max_inc     = sc3.slider("Max Inclusion (Al wt%)",    0.01, 2.00, limits["inc_lim"], step=0.01)
max_ret     = sc4.slider("Max Re-treatment Risk",     0.5, 30.0, limits["ret_lim"], step=0.5)
max_simetal = sc5.slider("Max Si Metal Share (%)",    0.0, 100.0, limits["simetal_max"] * 100, step=5.0) / 100.0

# ── Linear Programming Engine ──
# Objective array: [FeSi, Si Metal] effective cost per MT of Active Si
c_cost = [Net_Cost_FeSi, Net_Cost_SiMetal]

# Equality constraints (Sum of allocations = 100% of Active Si target)
A_eq = [[1, 1]]
b_eq = [1]

# Inequality constraints (A_ub * [x, y]^T <= b_ub)
A_ub = [
    [-fesi_chill, -si_chill],  # Thermal Drop: fesi_chill*x + si_chill*y >= min_chill -> -fesi_chill*x - si_chill*y <= -min_chill
    [fesi_rec, si_rec],        # Recovery Variability
    [fesi_inc, si_inc],        # Cleanliness Index
    [fesi_ret, si_ret],        # LF Re-treatment Risk
    [0, 1],                    # Max Si Metal Share (y <= max_simetal)
]
b_ub = [-min_chill, max_rec, max_inc, max_ret, max_simetal]

# Execute Scipy Optimizer
res = linprog(c_cost, A_eq=A_eq, b_eq=b_eq, A_ub=A_ub, b_ub=b_ub, bounds=[(0, 1), (0, 1)])

st.markdown("#### Optimization Result")
if res.success:
    mix = res.x
    blended_cost = res.fun
    
    costlier_commodity_cost = max(Net_Cost_FeSi, Net_Cost_SiMetal)
    savings = costlier_commodity_cost - blended_cost

    rc1, rc2 = st.columns(2)
    rc1.success(f"##### Final Effective Cost: \n ### **₹{blended_cost:,.0f}** per MT Eff. Si")
    
    if savings > 10:
        rc2.info(f"##### Projected Savings vs Single Commodity: \n ### **₹{savings:,.0f}** per MT Eff. Si")
    else:
        rc2.info(f"##### Projected Savings vs Single Commodity: \n ### **₹0** (100% Single Alloy is best)")

    # Pie Chart Result
    fig_pie = go.Figure(data=[go.Pie(
        labels=["FeSi70 Share", "Si Metal Share"], 
        values=[round(m, 4) for m in mix], 
        hole=0.4, 
        marker_colors=[C_FESI, C_SIMETAL],
        textinfo="label+percent"
    )])
    fig_pie.update_layout(title=f"Optimal Procurement Ratio for {sel_grade}", height=380, template="plotly_white")
    st.plotly_chart(fig_pie, use_container_width=True)

    # ── DEEP DIVE & INSIGHTS ──
    st.markdown("---")
    st.markdown("#### 📊 Deep Dive & Insights")
    
    col_insight1, col_insight2 = st.columns(2)
    
    with col_insight1:
        # Cost Comparison Chart
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Bar(
            x=["100% FeSi70", "Optimal Blend", "100% Si Metal"],
            y=[Net_Cost_FeSi, blended_cost, Net_Cost_SiMetal],
            marker_color=[C_FESI, "#9C27B0", C_SIMETAL],
            text=[f"₹{Net_Cost_FeSi:,.0f}", f"₹{blended_cost:,.0f}", f"₹{Net_Cost_SiMetal:,.0f}"],
            textposition="auto",
            hovertemplate="%{x}<br>₹%{y:,.0f}/MT<extra></extra>"
        ))
        fig_cost.update_layout(**_layout("Effective Cost Comparison (₹/MT Active Si)", "Cost (₹)", 380))
        st.plotly_chart(fig_cost, use_container_width=True)
        
    with col_insight2:
        # Constraint Utilization Chart
        actual_chill   = mix[0] * fesi_chill + mix[1] * si_chill
        actual_rec     = mix[0] * fesi_rec   + mix[1] * si_rec
        actual_inc     = mix[0] * fesi_inc   + mix[1] * si_inc
        actual_ret     = mix[0] * fesi_ret   + mix[1] * si_ret
        actual_simetal = mix[1]
        
        utils = [
            (actual_simetal / max_simetal) * 100 if max_simetal > 0 else 0,
            (actual_ret / max_ret) * 100 if max_ret else 0,
            (actual_inc / max_inc) * 100 if max_inc else 0,
            (actual_rec / max_rec) * 100 if max_rec else 0,
            (actual_chill / min_chill) * 100 if min_chill else 0  # Both values are negative, so division yields positive %
        ]
        labels = ["Max Si Metal Share", "Re-treatment Risk", "Cleanliness", "Recovery Var", "Thermal Limit"]
        
        fig_util = go.Figure()
        fig_util.add_trace(go.Bar(
            y=labels,
            x=utils,
            orientation='h',
            marker_color="#26A69A",
            text=[f"{u:.1f}%" for u in utils],
            textposition="inside"
        ))
        fig_util.add_vline(x=100, line_dash="dash", line_color="red", annotation_text="Limit (100%)")
        fig_util.update_layout(**_layout("Constraint Utilization (% of Limit Used)", "% Used", 380))
        fig_util.update_xaxes(range=[0, max(110, max(utils)*1.1)])
        st.plotly_chart(fig_util, use_container_width=True)
        
    # Table of exact values
    st.markdown("#### Metallurgical Profile of the Optimal Blend")
    df_profile = pd.DataFrame({
        "Parameter": ["Thermal Limit (kJ/kg)", "Recovery Variability (%)", "Cleanliness Index (Al wt%)", "Re-treatment Risk", "Si Metal Share"],
        "Blend Actual": [actual_chill, actual_rec, actual_inc, actual_ret, actual_simetal],
        "Limit Threshold": [min_chill, max_rec, max_inc, max_ret, max_simetal],
    })
    
    # Check for binding constraints using standard linear programming tolerance
    df_profile["Status"] = [
        "🛑 Binding Constraint" if abs(actual_chill - min_chill) < 1e-6 else "✅ Safe",
        "🛑 Binding Constraint" if actual_rec >= max_rec - 1e-6 else "✅ Safe",
        "🛑 Binding Constraint" if actual_inc >= max_inc - 1e-6 else "✅ Safe",
        "🛑 Binding Constraint" if actual_ret >= max_ret - 1e-6 else "✅ Safe",
        "🛑 Binding Constraint" if max_simetal > 0 and actual_simetal >= max_simetal - 1e-6 else "✅ Safe",
    ]
    
    # Format values (percentages for Si Metal Share, decimals for the rest)
    def format_val(val, is_pct, is_int):
        if is_pct: return f"{val*100:.2f}%"
        if is_int: return f"{val:.0f}"
        return f"{val:.4f}"
        
    df_profile["Blend Actual"] = df_profile.apply(lambda row: format_val(row["Blend Actual"], row["Parameter"] == "Si Metal Share", "Thermal" in row["Parameter"]), axis=1)
    df_profile["Limit Threshold"] = df_profile.apply(lambda row: format_val(row["Limit Threshold"], row["Parameter"] == "Si Metal Share", "Thermal" in row["Parameter"]), axis=1)

    # Style the dataframe status column
    def color_status(val):
        return "color: #D32F2F; font-weight: bold" if "Binding" in val else "color: #388E3C; font-weight: 500"
        
    st.dataframe(df_profile.style.map(color_status, subset=["Status"]), use_container_width=True)

else:
    st.error("⚠️ **Constraint Violation:** The chosen metallurgical limits are too strict to be met using these alloys. Please relax the constraints.")


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown("""
<div style="text-align:center; color:#90A4AE; font-size:12px; padding:8px 0;">
  Substitution Solver – FeSi70 vs Si Metal &nbsp;|&nbsp; All formulas sourced from Excel workbook 
  (SOLVER → INPUT_PARAMETER → BREAKDOWN_CALC) &nbsp;|&nbsp; 
  Cost functions dynamically update based on sidebar inputs.
</div>
""", unsafe_allow_html=True)