"""
ALLOY SUBSTITUTION SOLVER – FeV80 vs Nitrovan (NV Metal)
================================================
Calculates the mathematically cheapest blend of Ferrovanadium (80% V)
and Nitrovan (16% N, 77% V) that perfectly satisfies strict metallurgical limits.

All formulas sourced exclusively from the Excel file:
  • INPUT_PARAMETER sheet
  • SOLVER sheet

This application focuses strictly on the Linear Programming optimization 
layer and grade-specific constraints as per the requirements.
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
    page_title="Alloy Substitution Solver",
    page_icon="🧠",
    layout="wide",
)

# Colour palette
C_FEV      = "#1976D2"   # blue  – FeV80
C_NV       = "#E64A19"   # deep orange – Nitrovan
C_DELTA    = "#FF9800"   # amber – benefit
C_NEG      = "#F44336"   # red   – penalty
C_GRID     = "#EEEEEE"
C_BG       = "#FAFAFA"
C_TEXT     = "#333333"

# ── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp { background: #F0F4F8; }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #263238 0%, #37474F 40%, #455A64 100%);
}
[data-testid="stSidebar"] * { color: #ECEFF1 !important; }
[data-testid="stSidebar"] .stSlider > div > div > div { background: #78909C !important; }
[data-testid="stSidebar"] hr { border-color: #546E7A; }
[data-testid="stSidebar"] .stNumberInput input { background: #37474F; border-color: #78909C; color: #fff !important; }
[data-testid="stSidebar"] .stSelectbox select { background: #37474F; color: #fff; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { color: #fff !important; }

.section-header {
    font-size: 22px; font-weight: 800; color: #263238;
    text-transform: uppercase; letter-spacing: 0.05em;
    border-bottom: 3px solid #1976D2;
    padding-bottom: 8px; margin-bottom: 24px; margin-top: 32px;
}

.kpi-card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 18px 22px 14px 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    border-left: 5px solid #1976D2;
    margin-bottom: 8px;
}
.kpi-card-orange { border-left-color: #E64A19; }
.kpi-card-green  { border-left-color: #4CAF50; }
.kpi-label { font-size: 12px; font-weight: 600; color: #78909C; text-transform: uppercase; margin-bottom: 4px; }
.kpi-value { font-size: 26px; font-weight: 700; color: #263238; line-height: 1.15; }
.kpi-sub   { font-size: 12px; color: #90A4AE; margin-top: 3px; }

.info-box {
    background: #E3F2FD; border-radius: 8px;
    padding: 12px 16px; font-size: 13px; color: #1565C0;
    border-left: 4px solid #1976D2; margin-bottom: 10px;
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
        title=dict(text=title, font=dict(size=15, color="#263238"), x=0.01),
        legend=dict(bgcolor="rgba(255,255,255,0.85)", bordercolor="#DDD", borderwidth=1),
        xaxis=dict(showgrid=True, gridcolor=C_GRID, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=C_GRID, zeroline=False, title=y_title),
        hovermode="x unified",
        height=height,
        margin=dict(l=60, r=30, t=55, b=45),
    )

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR – ALL INPUT PARAMETERS (Matches exact specified architecture)
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🧠 Alloy Substitution Solver")
    st.divider()

    st.markdown("### A. Comparison Selection")
    comparison_selection = st.radio(
        "Select Analysis:",
        ["Not selected", "FeV vs NV Metal"],
        index=1
    )
    
    st.divider()
    st.markdown("### B. Financial Parameters")
    P_FeV_Price       = st.number_input("FeV80 Price (₹/MT)",      value=2950000, step=10000)
    P_NV_Price        = st.number_input("Nitrovan Price (₹/MT)",   value=2500000, step=10000)
    P_Power_Tariff    = st.number_input("Power Cost (₹/kWh)",      value=6.5, step=0.1)
    P_Electrode_Cost  = st.number_input("Electrode Cost (₹/kg)",   value=240, step=10)
    P_Steel_Value     = st.number_input("Steel Value (₹/MT)",      value=60000, step=1000)

    st.divider()
    st.markdown("### C. Technical Parameters")
    P_FeV_V        = st.slider("FeV80 V Content (%)",      70.0, 85.0, 80.0, 0.5) / 100
    P_NV_V         = st.slider("Nitrovan V Content (%)",   70.0, 85.0, 77.0, 0.5) / 100
    P_NV_N_pct     = st.slider("Nitrovan N Content (%)",   10.0, 20.0, 16.0, 0.5) / 100
    P_FeV_Rec      = st.slider("FeV80 Recovery (%)",       80.0, 100.0, 95.0, 0.5) / 100
    P_NV_Rec       = st.slider("Nitrovan Recovery (%)",    80.0, 100.0, 92.0, 0.5) / 100
    P_FeV_ESU_Fac  = st.slider("Str. Efficiency - FeV80",  0.8, 1.2, 1.0, 0.05)
    P_NV_ESU_Fac   = st.slider("Str. Efficiency - NV",     0.8, 1.5, 1.1, 0.05)
    P_FeV_Chill    = st.slider("FeV80 Chill (°C/kg)",      1.0, 3.0, 1.8, 0.1)
    P_NV_Chill     = st.slider("Nitrovan Chill (°C/kg)",   2.0, 4.0, 3.0, 0.1)

    st.divider()
    st.markdown("### D. Operational Parameters")
    P_FeV_Rec_Var  = st.slider("FeV80 Rec Var (%)",        1.0, 5.0, 2.5, 0.1)
    P_NV_Rec_Var   = st.slider("Nitrovan Rec Var (%)",     1.0, 6.0, 3.8, 0.1)
    P_FeV_Retrt    = st.slider("FeV80 Re-treat Risk (%)",  0.5, 5.0, 1.2, 0.1)
    P_NV_Retrt     = st.slider("Nitrovan Re-treat Risk (%)", 1.0, 5.0, 2.8, 0.1)
    P_FeV_Inc      = st.slider("FeV Cleanliness Idx (%)",  0.005, 0.030, 0.015, 0.001, format="%.3f")
    P_NV_Inc       = st.slider("NV Cleanliness Idx (%)",   0.005, 0.030, 0.010, 0.001, format="%.3f")
    P_FeV_Yield    = st.slider("FeV80 Yield Loss (%)",     0.001, 0.010, 0.003, 0.001, format="%.3f")
    P_NV_Yield     = st.slider("Nitrovan Yield Loss (%)",  0.001, 0.010, 0.005, 0.001, format="%.3f")

    st.divider()
    st.markdown("### E. Realization Factors")
    R_Power       = st.slider("Power Realization",       0.20, 1.00, 0.40, 0.05)
    R_Electrode   = st.slider("Electrode Realization",   0.20, 1.00, 0.50, 0.05)
    R_Throughput  = st.slider("Throughput Realization",  0.10, 0.80, 0.40, 0.05)
    R_Stability   = st.slider("Stability Realization",   0.10, 1.00, 0.10, 0.05)
    R_Reblow      = st.slider("Re-treatment Realization",0.30, 1.00, 0.80, 0.05)
    R_Cleanliness = st.slider("Cleanliness Realization", 0.10, 0.70, 0.40, 0.05)
    R_Yield       = st.slider("Yield Realization",       0.10, 1.00, 0.50, 0.05)

    st.divider()
    st.markdown("### F. Enterprise Savings")
    Consump_FY = st.number_input("Total Alloy Consumption (MT)", value=1500, step=100)
    Sub_Pct    = st.slider("% Substitution", 0.0, 1.0, 0.30, 0.05)

if comparison_selection == "Not selected":
    st.info("Please select substitution combination to run the Substitution Solver.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# MAIN SOLVER LOGIC & INTERFACE
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="background: linear-gradient(135deg,#263238 0%,#455A64 60%,#607D8B 100%);
            padding:22px 28px 18px 28px; border-radius:14px; margin-bottom:20px;
            box-shadow:0 4px 24px rgba(38,50,56,0.25);">
  <h1 style="color:#FFFFFF;margin:0;font-size:26px;font-weight:800;letter-spacing:0.02em;">
    🧠 Alloy Substitution Solver — FeV vs NV Metal
  </h1>
  <p style="color:#CFD8DC;margin:6px 0 0 0;font-size:13px;">
    Calculates the mathematically cheapest blend of Ferrovanadium (80% V) and Nitrovan (16% N) 
    that perfectly satisfies strict metallurgical limits for target steel grades.
  </p>
</div>
""", unsafe_allow_html=True)

# Grade Specific Definitions mapping exactly to Excel 'Solver' Sheet
grades_data = {
    "Commodity Structural (IS2062)":   {"v_lim": 0.030, "esu_lim": 0.60, "chill_lim": 15.00, "rec_lim": 5.00, "retrt_lim": 2.50, "inc_lim": 0.015, "h2_lim": 160, "nv_max": 1.0},
    "TMT / Rebar (Fe500D)":            {"v_lim": 0.045, "esu_lim": 0.75, "chill_lim": 15.00, "rec_lim": 5.00, "retrt_lim": 2.50, "inc_lim": 0.015, "h2_lim": 160, "nv_max": 1.0},
    "HSLA (API X60 / X70)":            {"v_lim": 0.055, "esu_lim": 0.80, "chill_lim": 10.00, "rec_lim": 2.45, "retrt_lim": 1.45, "inc_lim": 0.013, "h2_lim": 50,  "nv_max": 0.30},
    "Automotive (DP / TRIP / Bearing)":{"v_lim": 0.060, "esu_lim": 0.40, "chill_lim": 8.00,  "rec_lim": 2.30, "retrt_lim": 1.30, "inc_lim": 0.014, "h2_lim": 35,  "nv_max": 0.20},
}

gc1, gc2 = st.columns([1.5, 2.5])
sel_grade = gc1.selectbox("Select Target Steel Grade", list(grades_data.keys()), index=0)
limits = grades_data[sel_grade]

st.markdown("#### Metallurgical Constraints (Mapped from Excel)")
r1c1, r1c2, r1c3, r1c4 = st.columns(4)
min_v     = r1c1.number_input("Min Effective V (%)", value=limits["v_lim"], step=0.005, format="%.3f")
min_esu   = r1c2.number_input("ESU Target", value=limits["esu_lim"], step=0.05)
max_chill = r1c3.number_input("Max Chill Drop (°C)", value=limits["chill_lim"], step=1.0)
max_rec   = r1c4.number_input("Max Rec. Var (%)", value=limits["rec_lim"], step=0.1)

r2c1, r2c2, r2c3, r2c4 = st.columns(4)
max_retrt = r2c1.number_input("Max Re-treat Risk (%)", value=limits["retrt_lim"], step=0.1)
max_inc   = r2c2.number_input("Max Inclusion (%)", value=limits["inc_lim"], step=0.001, format="%.3f")
max_n     = r2c3.number_input("Max N Limit (ppm)", value=limits["h2_lim"], step=5)
max_nv    = r2c4.number_input("Max NV Share (%)", value=limits["nv_max"] * 100, step=5.0) / 100.0


# ══════════════════════════════════════════════════════════════════════════════
# LINEAR PROGRAMMING ENGINE
# ══════════════════════════════════════════════════════════════════════════════
# Calculate effective parameters derived from sidebar
Eff_V_FeV = P_FeV_V * P_FeV_Rec
Eff_V_NV  = P_NV_V * P_NV_Rec
ESU_FeV   = Eff_V_FeV * P_FeV_ESU_Fac
ESU_NV    = Eff_V_NV * P_NV_ESU_Fac
N_ppm_FeV = 1.0  # Derived equivalently to Excel's 0.001% mass assumption
N_ppm_NV  = P_NV_N_pct * 1000  # 16% = 160 ppm N per kg alloy added

# Define Objective: Minimize Cost per MT of Steel
# cost = (P_FeV_Price / 1000) * x + (P_NV_Price / 1000) * y
c_cost = [P_FeV_Price / 1000, P_NV_Price / 1000]

A_ub = []
b_ub = []

# 1. Min Effective V Constraint (in kg per MT steel: % * 10)
# Eff_V_FeV*x + Eff_V_NV*y >= min_v * 10 => -Eff_V_FeV*x - Eff_V_NV*y <= -min_v * 10
A_ub.append([-Eff_V_FeV, -Eff_V_NV])
b_ub.append(-min_v * 10)

# 2. ESU Target Constraint
A_ub.append([-ESU_FeV, -ESU_NV])
b_ub.append(-min_esu)

# 3. Chill Limit Constraint
A_ub.append([P_FeV_Chill, P_NV_Chill])
b_ub.append(max_chill)

# 4. Recovery Variability Limit
A_ub.append([P_FeV_Rec_Var, P_NV_Rec_Var])
b_ub.append(max_rec)

# 5. Re-treatment Risk Limit
A_ub.append([P_FeV_Retrt, P_NV_Retrt])
b_ub.append(max_retrt)

# 6. Inclusion Limit
A_ub.append([P_FeV_Inc, P_NV_Inc])
b_ub.append(max_inc)

# 7. Nitrogen Limit (ppm)
A_ub.append([N_ppm_FeV, N_ppm_NV])
b_ub.append(max_n)

# 8. Max NV Share Constraint: y <= max_nv * (x + y)
if max_nv < 1.0:
    A_ub.append([-max_nv, 1 - max_nv])
    b_ub.append(0)

# Execute Scipy Optimizer
res = linprog(c_cost, A_ub=A_ub, b_ub=b_ub, bounds=[(0, None), (0, None)])


# ══════════════════════════════════════════════════════════════════════════════
# OUTPUTS & VISUALIZATIONS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("---")

if res.success:
    x_fev, y_nv = res.x
    total_kg = x_fev + y_nv
    
    fev_share = x_fev / total_kg if total_kg > 0 else 0
    nv_share = y_nv / total_kg if total_kg > 0 else 0
    
    cost_per_mt_steel = res.fun
    weighted_alloy_cost = (P_FeV_Price * fev_share) + (P_NV_Price * nv_share)

    # Cost Baseline: 100% FeV 
    # Calculate mass needed to meet Min V and ESU using FeV alone
    req_fev_for_v = (min_v * 10) / Eff_V_FeV
    req_fev_for_esu = min_esu / ESU_FeV
    fev_only_kg = max(req_fev_for_v, req_fev_for_esu)
    cost_fev_only = fev_only_kg * (P_FeV_Price / 1000)
    
    # Cost Baseline: 100% NV
    req_nv_for_v = (min_v * 10) / Eff_V_NV
    req_nv_for_esu = min_esu / ESU_NV
    nv_only_kg = max(req_nv_for_v, req_nv_for_esu)
    cost_nv_only = nv_only_kg * (P_NV_Price / 1000)

    savings_vs_base = cost_fev_only - cost_per_mt_steel

    rc1, rc2 = st.columns(2)
    with rc1:
        st.markdown(f"""
        <div class="kpi-card">
            <div class="kpi-label">Weighted Alloy Cost</div>
            <div class="kpi-value">₹{weighted_alloy_cost:,.0f}</div>
            <div class="kpi-sub">Cost per MT of Optimal Alloy Blend</div>
        </div>
        """, unsafe_allow_html=True)
        
    with rc2:
        if savings_vs_base > 1:
            st.markdown(f"""
            <div class="kpi-card kpi-card-green">
                <div class="kpi-label">Projected Savings vs 100% FeV80</div>
                <div class="kpi-value">₹{savings_vs_base:,.2f}</div>
                <div class="kpi-sub">Savings per MT of Steel Produced</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">Projected Savings vs 100% FeV80</div>
                <div class="kpi-value">₹0.00</div>
                <div class="kpi-sub">100% Single Alloy is best for this grade</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("#### 📊 Optimal Blend & Insights")
    
    col_pie, col_cost = st.columns([1, 1])
    
    with col_pie:
        fig_pie = go.Figure(data=[go.Pie(
            labels=["FeV80 Share", "Nitrovan Share"], 
            values=[fev_share, nv_share], 
            hole=0.45, 
            marker_colors=[C_FEV, C_NV],
            textinfo="label+percent"
        )])
        fig_pie.update_layout(title="Optimal Procurement Ratio (Mass %)", height=380, template="plotly_white")
        st.plotly_chart(fig_pie, use_container_width=True)
        
    with col_cost:
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Bar(
            x=["100% FeV80", "Optimal Blend", "100% Nitrovan"],
            y=[cost_fev_only, cost_per_mt_steel, cost_nv_only],
            marker_color=[C_FEV, "#4CAF50", C_NV],
            text=[f"₹{cost_fev_only:,.1f}", f"₹{cost_per_mt_steel:,.1f}", f"₹{cost_nv_only:,.1f}"],
            textposition="auto",
            hovertemplate="%{x}<br>₹%{y:,.2f}/MT Steel<extra></extra>"
        ))
        fig_cost.update_layout(**_layout("Cost to Fulfill Target per MT Steel (₹)", "Cost (₹)", 380))
        st.plotly_chart(fig_cost, use_container_width=True)

    # Calculate actual usage matrix
    actual_v = Eff_V_FeV * x_fev + Eff_V_NV * y_nv
    actual_esu = ESU_FeV * x_fev + ESU_NV * y_nv
    actual_chill = P_FeV_Chill * x_fev + P_NV_Chill * y_nv
    actual_rec = P_FeV_Rec_Var * x_fev + P_NV_Rec_Var * y_nv
    actual_retrt = P_FeV_Retrt * x_fev + P_NV_Retrt * y_nv
    actual_inc = P_FeV_Inc * x_fev + P_NV_Inc * y_nv
    actual_n = N_ppm_FeV * x_fev + N_ppm_NV * y_nv

    utils = [
        (nv_share / max_nv) * 100 if max_nv else 0,
        (actual_n / max_n) * 100 if max_n else 0,
        (actual_inc / max_inc) * 100 if max_inc else 0,
        (actual_retrt / max_retrt) * 100 if max_retrt else 0,
        (actual_rec / max_rec) * 100 if max_rec else 0,
        (actual_chill / max_chill) * 100 if max_chill else 0
    ]
    labels = ["Max NV Share", "Nitrogen Limit", "Cleanliness Limit", "Re-treatment Risk", "Recovery Var Limit", "Max Chill Drop"]
    
    st.markdown("#### Constraint Utilization & Metallurgical Profile")
    col_util, col_prof = st.columns([1, 1.2])
    
    with col_util:
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
        fig_util.update_layout(**_layout("Constraint Utilization (% of Max Limit Used)", "% Used", 350))
        fig_util.update_xaxes(range=[0, max(110, max(utils)*1.1)])
        st.plotly_chart(fig_util, use_container_width=True)

    with col_prof:
        df_profile = pd.DataFrame({
            "Parameter": [
                "Min Effective V (%)", "ESU Target", "Max Chill Drop (°C)", 
                "Recovery Variability", "Re-treatment Risk", "Cleanliness Index", 
                "Nitrogen (ppm)", "Nitrovan Share (%)"
            ],
            "Blend Actual": [
                actual_v / 10, actual_esu, actual_chill, actual_rec, 
                actual_retrt, actual_inc, actual_n, nv_share * 100
            ],
            "Constraint Limit": [
                min_v, min_esu, max_chill, max_rec, 
                max_retrt, max_inc, max_n, max_nv * 100
            ],
            "Type": ["Min", "Min", "Max", "Max", "Max", "Max", "Max", "Max"]
        })
        
        # Check binding logic based on min/max formulation
        tol = 1e-5
        def check_binding(row):
            if row["Type"] == "Min" and row["Blend Actual"] <= row["Constraint Limit"] + tol:
                return "🛑 Binding Constraint"
            elif row["Type"] == "Max" and row["Blend Actual"] >= row["Constraint Limit"] - tol:
                return "🛑 Binding Constraint"
            return "✅ Safe"
            
        df_profile["Status"] = df_profile.apply(check_binding, axis=1)
        
        # Formatting specific columns
        df_profile["Blend Actual"] = df_profile["Blend Actual"].apply(lambda x: f"{x:.4f}" if x < 1 else f"{x:.2f}")
        df_profile["Constraint Limit"] = df_profile["Constraint Limit"].apply(lambda x: f"{x:.4f}" if x < 1 else f"{x:.2f}")
        
        def color_status(val):
            return "color: #D32F2F; font-weight: bold" if "Binding" in val else "color: #388E3C"
            
        st.dataframe(df_profile.drop(columns=["Type"]).style.map(color_status, subset=["Status"]), use_container_width=True, height=350)

else:
    st.error("⚠️ **Constraint Violation:** The chosen metallurgical limits are too strict to be met simultaneously using these alloys. Please review the constraints for feasibility.")


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown("""
<div style="text-align:center; color:#90A4AE; font-size:12px; padding:8px 0;">
  Alloy Substitution Solver – FeV80 vs Nitrovan Metal &nbsp;|&nbsp; 
  All mathematical logic extracted and replicated precisely from Excel constraints. &nbsp;|&nbsp; 
  Optimal blend calculations based on minimizing active raw material cost under grade specifications.
</div>
""", unsafe_allow_html=True)