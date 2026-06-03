"""
ALUMINIUM SUBSTITUTION SOLVER
================================================
Three-Material linear optimization engine for:
  • Primary Aluminium Ingot (99% Purity)
  • Secondary Aluminium Ingot (97% Purity)
  • Aluminium Notch Bar (95% Purity)

Constraints and equations sourced strictly from the 
Aluminium VIU Excel Workbook (SOLVER sheet).
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
    page_title="Aluminium Substitution Solver",
    page_icon="🧠",
    layout="wide",
)

# Colour palette (Three-Material)
C_PRIM   = "#2196F3"   # blue   – Primary Al
C_SEC    = "#9C27B0"   # purple – Secondary Al
C_NOTCH  = "#FF9800"   # amber  – Al Notch Bar
C_GRID   = "#EEEEEE"
C_BG     = "#FAFAFA"
C_TEXT   = "#333333"

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
    font-size: 22px; font-weight: 800; color: #1A237E;
    text-transform: uppercase; letter-spacing: 0.05em;
    border-bottom: 3px solid #2196F3;
    padding-bottom: 8px; margin-bottom: 24px; margin-top: 10px;
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
# SIDEBAR – ALL INPUT PARAMETERS (Replicating UX Structure)
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🧠 Aluminium Solver Engine")
    st.divider()

    st.markdown("### A. Comparison Selection")
    st.radio("Select Analysis:", ["Primary vs Secondary vs Notch Bar"], index=0)
    
    st.divider()
    st.markdown("### B. Financial Parameters")
    P_Price            = st.number_input("Primary Al Price (₹/MT)",    value=380000, step=1000)
    S_Price            = st.number_input("Secondary Al Price (₹/MT)",  value=340000, step=1000)
    N_Price            = st.number_input("Al Notch Bar Price (₹/MT)",  value=335000, step=1000)
    P_Power_Tariff     = st.number_input("Power Tariff (₹/kWh)",       value=6.5, step=0.1)
    P_Electrode_Cost   = st.number_input("Electrode Cost (₹/kg)",      value=240, step=10)
    P_Steel_Value      = st.number_input("Steel Value (₹/MT)",         value=60000, step=1000)
    P_Margin_Steel     = st.number_input("Meltshop Margin (₹/MT)",     value=2800, step=100)
    P_Retreatment_Cost = st.number_input("LF Re-treatment Cost (₹)",   value=15000, step=500)

    st.divider()
    st.markdown("### C. Technical Parameters")
    P_Purity = st.slider("Primary Al Purity (%)",   98.0, 99.9, 99.0, 0.1) / 100
    S_Purity = st.slider("Secondary Al Purity (%)", 90.0, 99.0, 97.0, 0.1) / 100
    N_Purity = st.slider("Notch Bar Purity (%)",    90.0, 99.0, 95.0, 0.1) / 100
    P_Rec    = st.slider("Primary Recovery (%)",    40.0, 60.0, 49.0, 0.5) / 100
    S_Rec    = st.slider("Secondary Recovery (%)",  40.0, 60.0, 46.0, 0.5) / 100
    N_Rec    = st.slider("Notch Bar Recovery (%)",  40.0, 60.0, 46.0, 0.5) / 100

    st.divider()
    st.markdown("### D. Operational Parameters")
    P_Heat_Size  = st.slider("Heat Size (MT)",      100, 350, 190, 5)
    P_Cycle_Time = st.slider("Cycle Time (min)",     30,  90,  50, 1)
    P_LF_Eff     = st.slider("LF Efficiency (%)",  25.0, 80.0, 40.0, 1.0) / 100

    st.divider()
    st.markdown("### E. Realization Factors")
    R_Power       = st.slider("Power Realization",       0.0, 1.0, 1.0, 0.1)
    R_Yield       = st.slider("Yield Realization",       0.0, 1.0, 0.5, 0.1)
    R_Cleanliness = st.slider("Cleanliness Realization", 0.0, 1.0, 0.4, 0.1)

    st.divider()
    st.markdown("### F. Enterprise Savings")
    Annual_Consumption = st.number_input("Annual Alloy Cons. (MT)", value=5000, step=100)

# ══════════════════════════════════════════════════════════════════════════════
# DATA PREPARATION (Strictly referencing Workbook Logic)
# ══════════════════════════════════════════════════════════════════════════════

# Effective Al Delivered
Eff_P = P_Purity * P_Rec
Eff_S = S_Purity * S_Rec
Eff_N = N_Purity * N_Rec

# Hardcoded base penalties from the exact Workbook Solver Equation:
# "Weighted Operational Penalty (₹/MT) -> y*(0) + x*(4673) + z*(8760)"
Base_Pen_P = 0
Base_Pen_S = 4673
Base_Pen_N = 8760

# Final Effective Cost per MT Alloy (Objective to minimize)
Cost_P = P_Price + Base_Pen_P
Cost_S = S_Price + Base_Pen_S
Cost_N = N_Price + Base_Pen_N

# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🧠 Optimal Aluminium Substitution Solver</div>', unsafe_allow_html=True)
st.markdown("Calculates the mathematically cheapest blend of **Primary Al Ingot**, **Secondary Al Ingot**, and **Al Notch Bar** that perfectly satisfies strict metallurgical limits via Linear Programming.")

# Dictionary containing grade-specific metallurgical constraints strictly from SOLVER sheet
grades_data = {
    "Commodity Structural (IS2062/E250)": {"al_lim": 0.48, "therm_lim": 5.5, "rec_lim": 3.50, "inc_lim": 0.060, "ret_lim": 2.50, "sn_max": 1.00},
    "TMT / Rebar (Fe500D)":               {"al_lim": 0.50, "therm_lim": 4.0, "rec_lim": 3.20, "inc_lim": 0.050, "ret_lim": 2.30, "sn_max": 0.80},
    "HSLA / API (API X70)":               {"al_lim": 0.55, "therm_lim": 2.5, "rec_lim": 2.80, "inc_lim": 0.040, "ret_lim": 2.00, "sn_max": 0.25},
    "Automotive (DP600)":                 {"al_lim": 0.58, "therm_lim": 2.0, "rec_lim": 2.50, "inc_lim": 0.035, "ret_lim": 1.80, "sn_max": 0.15},
    "IF Steel (Deep Draw IF)":            {"al_lim": 0.59, "therm_lim": 1.5, "rec_lim": 2.15, "inc_lim": 0.032, "ret_lim": 1.55, "sn_max": 0.10},
    "Electrical Steel (CRGO / CRNO)":     {"al_lim": 0.60, "therm_lim": 1.1, "rec_lim": 2.05, "inc_lim": 0.031, "ret_lim": 1.50, "sn_max": 0.00},
}

gc1, gc2 = st.columns([1.5, 2.5])
sel_grade = gc1.selectbox("Select Target Steel Grade", list(grades_data.keys()), index=0)
limits = grades_data[sel_grade]

st.markdown("#### Metallurgical Constraints")
sc1, sc2, sc3, sc4, sc5, sc6 = st.columns(6)
max_al   = sc1.slider("Min Effective Al (kg/T)", 0.40, 0.70, limits["al_lim"], step=0.01)
max_thm  = sc2.slider("Max Thermal Burden",      1.0, 6.0, limits["therm_lim"], step=0.1)
max_rec  = sc3.slider("Max Recovery Var",        1.5, 4.0, limits["rec_lim"], step=0.05)
max_inc  = sc4.slider("Max Inclusion Idx",       0.02, 0.08, limits["inc_lim"], step=0.005, format="%.3f")
max_ret  = sc5.slider("Max Re-treatment Risk",   1.0, 3.0, limits["ret_lim"], step=0.1)
max_sn   = sc6.slider("Max Sec/Notch Share",     0.0, 1.0, limits["sn_max"], step=0.05)

# ── LINEAR PROGRAMMING ENGINE ──
# Array Indices: [0] Primary, [1] Secondary, [2] Notch Bar
c_cost = [Cost_P, Cost_S, Cost_N]

# Sum of all fractional alloy additions must equal 100%
A_eq = [[1, 1, 1]]
b_eq = [1]

# Inequality constraints (A_ub * [P, S, N]^T <= b_ub)
A_ub = [
    [-Eff_P, -Eff_S, -Eff_N],   # Effective Al Delivered (Negative for >= constraint)
    [0.0,    1.0,    2.5],      # Thermal Burden Index
    [2.0,    3.0,    3.5],      # Recovery Variability (StDev %)
    [0.03,   0.045,  0.055],    # Inclusion Severity Index
    [1.5,    2.0,    2.5],      # LF Re-treatment Risk
    [0.0,    1.0,    1.0],      # Max Secondary / Notch Share combined
]

b_ub = [
    -max_al,
    max_thm,
    max_rec,
    max_inc,
    max_ret,
    max_sn
]

# Execute Scipy Optimizer
res = linprog(c_cost, A_eq=A_eq, b_eq=b_eq, A_ub=A_ub, b_ub=b_ub, bounds=[(0, 1), (0, 1), (0, 1)])

st.markdown("#### Optimization Result")
if res.success:
    mix = res.x
    blended_cost_mt_alloy = res.fun
    
    # Calculate Effective Al of the resultant blend
    blend_eff_al = (mix[0] * Eff_P) + (mix[1] * Eff_S) + (mix[2] * Eff_N)
    
    # Calculate True Cost per MT of Effective Al for robust comparison
    cost_eff_prim  = Cost_P / Eff_P
    cost_eff_sec   = Cost_S / Eff_S
    cost_eff_notch = Cost_N / Eff_N
    cost_eff_blend = blended_cost_mt_alloy / blend_eff_al
    
    savings_vs_primary = cost_eff_prim - cost_eff_blend

    rc1, rc2 = st.columns(2)
    rc1.success(f"##### Final Effective Cost: \n ### **₹{cost_eff_blend:,.0f}** per MT Eff. Al")
    
    if savings_vs_primary > 10:
        rc2.info(f"##### Projected Savings vs 100% Primary: \n ### **₹{savings_vs_primary:,.0f}** per MT Eff. Al")
    else:
        rc2.info(f"##### Projected Savings vs 100% Primary: \n ### **₹0** (100% Primary is optimal)")

    # ── Pie Chart Result ──
    fig_pie = go.Figure(data=[go.Pie(
        labels=["Primary Al Ingot", "Secondary Al Ingot", "Al Notch Bar"], 
        values=[round(m, 4) for m in mix], 
        hole=0.45, 
        marker_colors=[C_PRIM, C_SEC, C_NOTCH],
        textinfo="label+percent"
    )])
    fig_pie.update_layout(title=f"Optimal Procurement Ratio for {sel_grade}", height=380, template="plotly_white")
    st.plotly_chart(fig_pie, use_container_width=True)

    # ── Deep Dive & Insights ──
    st.markdown("---")
    st.markdown("#### 📊 Deep Dive & Insights")
    
    col_insight1, col_insight2 = st.columns(2)
    
    with col_insight1:
        # Cost Comparison Chart (Standardized to Cost per MT Effective Al)
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Bar(
            x=["100% Primary", "Optimal Blend", "100% Secondary", "100% Notch Bar"],
            y=[cost_eff_prim, cost_eff_blend, cost_eff_sec, cost_eff_notch],
            marker_color=[C_PRIM, "#1A237E", C_SEC, C_NOTCH],
            text=[f"₹{cost_eff_prim:,.0f}", f"₹{cost_eff_blend:,.0f}", f"₹{cost_eff_sec:,.0f}", f"₹{cost_eff_notch:,.0f}"],
            textposition="auto",
            hovertemplate="%{x}<br>₹%{y:,.0f}/MT Eff. Al<extra></extra>"
        ))
        fig_cost.update_layout(**_layout("Effective Cost Comparison (₹/MT Effective Al)", "Cost (₹)", 380))
        st.plotly_chart(fig_cost, use_container_width=True)
        
    with col_insight2:
        # Constraint Utilization Chart
        actual_therm = mix[1] * 1.0 + mix[2] * 2.5
        actual_rec   = mix[0] * 2.0 + mix[1] * 3.0 + mix[2] * 3.5
        actual_inc   = mix[0] * 0.03 + mix[1] * 0.045 + mix[2] * 0.055
        actual_ret   = mix[0] * 1.5 + mix[1] * 2.0 + mix[2] * 2.5
        actual_sn    = mix[1] + mix[2]
        
        utils = [
            (actual_sn / max_sn) * 100 if max_sn else (100 if actual_sn > 0 else 0),
            (actual_ret / max_ret) * 100 if max_ret else 0,
            (actual_inc / max_inc) * 100 if max_inc else 0,
            (actual_rec / max_rec) * 100 if max_rec else 0,
            (actual_therm / max_thm) * 100 if max_thm else 0
        ]
        labels = ["Max Sec/Notch Share", "LF Re-treatment", "Inclusion Severity", "Recovery Var", "Thermal Burden"]
        
        fig_util = go.Figure()
        fig_util.add_trace(go.Bar(
            y=labels, x=utils, orientation='h',
            marker_color="#26A69A",
            text=[f"{u:.1f}%" for u in utils],
            textposition="inside"
        ))
        fig_util.add_vline(x=100, line_dash="dash", line_color="red", annotation_text="Limit (100%)")
        fig_util.update_layout(**_layout("Constraint Utilization (% of Max Limit Used)", "% Used", 380))
        fig_util.update_xaxes(range=[0, max(110, max(utils)*1.1)])
        st.plotly_chart(fig_util, use_container_width=True)
        
    # Table of exact values
    st.markdown("#### Metallurgical Profile of the Optimal Blend")
    df_profile = pd.DataFrame({
        "Parameter": [
            "Effective Al Delivered (kg/T)", 
            "Thermal Burden Index", 
            "Recovery Variability (StDev %)", 
            "Inclusion Severity Index", 
            "LF Re-treatment Risk (%)", 
            "Secondary & Notch Share"
        ],
        "Blend Actual": [blend_eff_al, actual_therm, actual_rec, actual_inc, actual_ret, actual_sn],
        "Maximum Allowed": [max_al, max_thm, max_rec, max_inc, max_ret, max_sn],
    })
    
    # Status calculation (Note Effective Al is a minimum constraint, others are maximums)
    df_profile["Status"] = np.where(
        df_profile["Parameter"] == "Effective Al Delivered (kg/T)",
        np.where(df_profile["Blend Actual"] <= df_profile["Maximum Allowed"] + 1e-6, "🛑 Binding Constraint", "✅ Safe (Surplus)"),
        np.where(df_profile["Blend Actual"] >= df_profile["Maximum Allowed"] - 1e-6, "🛑 Binding Constraint", "✅ Safe")
    )
    
    # Format values for display
    def format_val(val, is_pct):
        return f"{val*100:.2f}%" if is_pct else f"{val:.4f}"
        
    df_profile["Blend Actual"] = df_profile.apply(lambda row: format_val(row["Blend Actual"], row["Parameter"] == "Secondary & Notch Share"), axis=1)
    df_profile["Maximum Allowed"] = df_profile.apply(lambda row: format_val(row["Maximum Allowed"], row["Parameter"] == "Secondary & Notch Share"), axis=1)

    # Style the dataframe status column
    def color_status(val):
        return "color: #D32F2F; font-weight: bold" if "Binding" in val else "color: #388E3C"
        
    st.dataframe(df_profile.style.map(color_status, subset=["Status"]), use_container_width=True)

else:
    st.error("⚠️ **Constraint Violation:** The chosen metallurgical limits are too strict to be met using any combination of these three alloys. Please relax the constraints (e.g. lower the Min Effective Al requirement or raise the Max Sec/Notch Share).")


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown("""
<div style="text-align:center; color:#90A4AE; font-size:12px; padding:8px 0;">
  Aluminium Substitution Solver &nbsp;|&nbsp; All formulas sourced strictly from the Excel workbook 
  (SOLVER sheet & constraint equations) &nbsp;|&nbsp; 
  Three-Material optimization Engine.
</div>
""", unsafe_allow_html=True)