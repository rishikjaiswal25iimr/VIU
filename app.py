"""
ALUMINIUM SUBSTITUTION SOLVER
================================================
Three-Material linear optimization engine for:
  • Primary Aluminium Ingot (99% Purity)
  • Secondary Aluminium Ingot (97% Purity)
  • Aluminium Notch Bar (95% Purity)

Constraints and equations sourced strictly from the 
Aluminium VIU Excel Workbook. Includes explicit, dynamic
mapping of all 52 Input Parameters to Breakdown Calcs.
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

C_PRIM   = "#2196F3"
C_SEC    = "#9C27B0"
C_NOTCH  = "#FF9800"
C_GRID   = "#EEEEEE"
C_BG     = "#FAFAFA"
C_TEXT   = "#333333"

st.markdown("""
<style>
.stApp { background: #F0F4F8; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1A237E 0%, #283593 40%, #1565C0 100%); }
[data-testid="stSidebar"] * { color: #E8EAF6 !important; }
[data-testid="stSidebar"] .stSlider > div > div > div { background: #5C6BC0 !important; }
[data-testid="stSidebar"] hr { border-color: #3949AB; }
[data-testid="stSidebar"] .stNumberInput input { background: #283593; border-color: #5C6BC0; color: #fff !important; }
[data-testid="stSidebar"] .stSelectbox select { background: #283593; color: #fff; }
.section-header {
    font-size: 22px; font-weight: 800; color: #1A237E;
    text-transform: uppercase; letter-spacing: 0.05em;
    border-bottom: 3px solid #2196F3;
    padding-bottom: 8px; margin-bottom: 24px; margin-top: 10px;
}
</style>
""", unsafe_allow_html=True)

def _layout(title: str, y_title: str = "", height: int = 420) -> dict:
    return dict(
        template="plotly_white", paper_bgcolor="white", plot_bgcolor=C_BG,
        font=dict(family="Inter, sans-serif", size=12, color=C_TEXT),
        title=dict(text=title, font=dict(size=15, color="#1A237E"), x=0.01),
        legend=dict(bgcolor="rgba(255,255,255,0.85)", bordercolor="#DDD", borderwidth=1),
        xaxis=dict(showgrid=True, gridcolor=C_GRID, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=C_GRID, zeroline=False, title=y_title),
        hovermode="x unified", height=height, margin=dict(l=60, r=30, t=55, b=45),
    )

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR – ALL INPUT PARAMETERS
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🧠 Aluminium Solver Engine")
    st.divider()

    with st.expander("B. Financial Parameters", expanded=True):
        P_Price          = st.number_input("Primary Al Price (₹/MT)", value=380000, step=1000)
        S_Price          = st.number_input("Secondary Al Price (₹/MT)", value=340000, step=1000)
        N_Price          = st.number_input("Al Notch Bar Price (₹/MT)", value=335000, step=1000)
        P_Power_Cost     = st.number_input("Power Cost (₹/kWh)", value=6.5, step=0.1)
        P_Electrode_Cost = st.number_input("Electrode Cost (₹/kg)", value=240, step=10)
        P_Steel_Value    = st.number_input("Steel Value (₹/MT)", value=60000, step=1000)
        P_Slag_Cost      = st.number_input("Ladle Slag Handling Cost (₹/MT)", value=800, step=50)
        P_Margin         = st.number_input("Meltshop Contrib. Margin (₹/MT)", value=2800, step=100)
        P_Retreat_Cost   = st.number_input("LF Re-treatment Cost (₹/heat)", value=15000, step=500)

    with st.expander("C. Technical Parameters", expanded=False):
        P_Purity         = st.number_input("Primary Al Purity (Al %)", value=0.99, step=0.01)
        S_Purity         = st.number_input("Secondary Al Purity (Al %)", value=0.97, step=0.01)
        N_Purity         = st.number_input("Al Notch Bar Purity (Al %)", value=0.95, step=0.01)
        P_Heat_Size      = st.number_input("Heat Size (MT steel/heat)", value=190, step=5)
        P_Cycle_Time     = st.number_input("LF/RH Cycle Time (minutes)", value=53, step=1)
        P_LF_Eff         = st.number_input("LF Heating Efficiency (%)", value=0.4, step=0.05)
        P_Spec_Heat      = st.number_input("Specific Heat of Steel (MJ)", value=0.75, step=0.05)
        P_Imp_Sens_Heat  = st.number_input("Impurity Sensible Heat (MJ/kg)", value=2.5, step=0.1)
        Target_Al_Pct    = st.number_input("Target Al in Steel (%)", value=0.2, step=0.01)
        Al_Deox          = st.number_input("Al Needed for Deox (kg/T)", value=0.68, step=0.01)
        Net_Al_Target    = st.number_input("Total Net Al Target (kg/T)", value=1.08, step=0.01)
        P_Rec            = st.number_input("Physical Recovery - Primary (%)", value=0.49, step=0.01)
        S_Rec            = st.number_input("Physical Recovery - Secondary (%)", value=0.46, step=0.01)
        N_Rec            = st.number_input("Physical Recovery - Notch Bar (%)", value=0.46, step=0.01)

    with st.expander("D. Operational Penalties & Frequencies", expanded=False):
        P_Overdose       = st.number_input("Primary Al Overdose Buffer (%)", value=0.02, step=0.005, format="%.3f")
        S_Overdose       = st.number_input("Secondary Al Overdose Buffer (%)", value=0.03, step=0.005, format="%.3f")
        N_Overdose       = st.number_input("Al Notch Bar Overdose Buffer (%)", value=0.035, step=0.005, format="%.3f")
        P_Reject         = st.number_input("Primary Al Rejection Rate (%)", value=0.0003, step=0.0001, format="%.5f")
        S_Reject         = st.number_input("Secondary Al Rejection Rate (%)", value=0.00045, step=0.0001, format="%.5f")
        N_Reject         = st.number_input("Al Notch Bar Rejection Rate (%)", value=0.00055, step=0.0001, format="%.5f")
        P_Reblow         = st.number_input("Primary Al Reblow Frequency (%)", value=0.015, step=0.005, format="%.3f")
        S_Reblow         = st.number_input("Secondary Al Reblow Frequency (%)", value=0.02, step=0.005, format="%.3f")
        N_Reblow         = st.number_input("Al Notch Bar Reblow Frequency (%)", value=0.025, step=0.005, format="%.3f")
        P_MetYield       = st.number_input("Primary Al Metallic Yield (%)", value=0.9989, step=0.0001, format="%.4f")
        S_MetYield       = st.number_input("Secondary Al Metallic Yield (%)", value=0.9988, step=0.0001, format="%.4f")
        N_MetYield       = st.number_input("Al Notch Bar Metallic Yield (%)", value=0.9987, step=0.0001, format="%.4f")
        S_Extra_Time     = st.number_input("Extra Process Time - Secondary", value=0.5, step=0.1)
        N_Extra_Time     = st.number_input("Extra Process Time - Notch", value=1.0, step=0.1)

    with st.expander("E. Thermodynamic & Physics Variables", expanded=False):
        Stoich_Conv      = st.number_input("Stoichiometric Conversion", value=1.889)
        Conv_Fact        = st.number_input("Conversion Factor (MJ/kWh)", value=3.6)
        Elec_Cons        = st.number_input("Electrode Cons. Rate (kg/kWh)", value=0.0015, format="%.4f")
        Dross_S          = st.number_input("Dross Diff Primary/Secondary", value=20.0)
        Dross_N          = st.number_input("Dross Diff Primary/Notch", value=40.0)
        Dross_SN         = st.number_input("Dross Diff Secondary/Notch", value=20.0)
        Slag_Diff_S      = st.number_input("Slag Diff Primary/Secondary", value=55.4)
        Slag_Diff_N      = st.number_input("Slag Diff Primary/Notch", value=55.0)
        Slag_Diff_SN     = st.number_input("Slag Diff Secondary/Notch", value=0.0)

    with st.expander("F. Realization Factors & Enterprise", expanded=False):
        R_Rec            = st.number_input("Recovery Realization (%)", value=0.5, step=0.1)
        R_Slag           = st.number_input("Slag Attribution (%)", value=0.5, step=0.1)
        R_Clean          = st.number_input("Cleanliness Realization (%)", value=0.4, step=0.1)
        R_Thru           = st.number_input("Throughput Realization (%)", value=0.4, step=0.1)
        R_Yield          = st.number_input("Yield Realization (%)", value=0.5, step=0.1)
        Annual_Consumption = st.number_input("Annual Consumption (MT Eff Al/Yr)", value=4325, step=100)

# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND BREAKDOWN CALCULATIONS (Mapped Exactly to Excel Formulas)
# ══════════════════════════════════════════════════════════════════════════════

# Derived Input H1/I1 and H4/I4 Logic
Req_S_T = (Target_Al_Pct / 100) * 1000 / S_Purity / S_Rec
Supp_S  = 1000 / Req_S_T

Req_N_T = (Target_Al_Pct / 100) * 1000 / N_Purity / N_Rec
Supp_N  = 1000 / Req_N_T

# --- Secondary Al Ingot Penalties (Primary over Secondary) ---
kWh_Sav_S   = Dross_S * P_Imp_Sens_Heat / Conv_Fact / P_LF_Eff
Pen_Power_S = kWh_Sav_S * P_Power_Cost
Pen_Elec_S  = kWh_Sav_S * Elec_Cons * P_Electrode_Cost
Pen_Thru_S  = S_Extra_Time * Supp_S / P_Heat_Size * P_Margin * R_Thru
Pen_Rec_S   = (S_Overdose - P_Overdose) * S_Price / 1000 * Supp_S * R_Rec
Pen_Slag_S  = Slag_Diff_S * P_Slag_Cost / 1000 * R_Slag
Pen_Clean_S = (S_Reject - P_Reject) * P_Steel_Value * Supp_S * R_Clean
Pen_Yield_S = (P_MetYield - S_MetYield) * P_Steel_Value * Supp_S * R_Yield
Pen_Retrt_S = (S_Reblow - P_Reblow) * P_Retreat_Cost * Supp_S / P_Heat_Size

Total_Pen_S = Pen_Power_S + Pen_Elec_S + Pen_Thru_S + Pen_Rec_S + Pen_Slag_S + Pen_Clean_S + Pen_Yield_S + Pen_Retrt_S

# --- Al Notch Bar Penalties (Primary over Notch Bar) ---
kWh_Sav_N   = Dross_N * P_Imp_Sens_Heat / Conv_Fact / P_LF_Eff
Pen_Power_N = kWh_Sav_N * P_Power_Cost
Pen_Elec_N  = kWh_Sav_N * Elec_Cons * P_Electrode_Cost
Pen_Thru_N  = N_Extra_Time * Supp_N / P_Heat_Size * P_Margin * R_Thru
Pen_Rec_N   = (N_Overdose - P_Overdose) * N_Price / 1000 * Supp_N * R_Rec
Pen_Slag_N  = Slag_Diff_N * P_Slag_Cost / 1000 * R_Slag
Pen_Clean_N = (N_Reject - P_Reject) * P_Steel_Value * Supp_N * R_Clean
Pen_Yield_N = (P_MetYield - N_MetYield) * P_Steel_Value * Supp_N * R_Yield
Pen_Retrt_N = (N_Reblow - P_Reblow) * P_Retreat_Cost * Supp_N / P_Heat_Size

Total_Pen_N = Pen_Power_N + Pen_Elec_N + Pen_Thru_N + Pen_Rec_N + Pen_Slag_N + Pen_Clean_N + Pen_Yield_N + Pen_Retrt_N

# --- VIU Summary Integration ---
Eff_P = P_Purity * P_Rec
Eff_S = S_Purity * S_Rec
Eff_N = N_Purity * N_Rec

Base_Cost_P = P_Price / Eff_P
Base_Cost_S = S_Price / Eff_S
Base_Cost_N = N_Price / Eff_N

Converted_Pen_S = Total_Pen_S / Eff_S
Converted_Pen_N = Total_Pen_N / Eff_N

Net_Eff_Cost_P = Base_Cost_P
Net_Eff_Cost_S = Base_Cost_S + Converted_Pen_S
Net_Eff_Cost_N = Base_Cost_N + Converted_Pen_N

# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🧠 Optimal Aluminium Substitution Solver</div>', unsafe_allow_html=True)
st.markdown("Calculates the mathematically cheapest blend of **Primary Al Ingot**, **Secondary Al Ingot**, and **Al Notch Bar** that perfectly satisfies strict metallurgical limits via Linear Programming.")

# Dictionary containing grade-specific metallurgical constraints (with relaxed Effective Al limits)
grades_data = {
    "Commodity Structural (IS2062/E250)": {"al_lim": 0.10, "therm_lim": 5.5, "rec_lim": 3.50, "inc_lim": 0.060, "ret_lim": 2.50, "sn_max": 1.00},
    "TMT / Rebar (Fe500D)":               {"al_lim": 0.20, "therm_lim": 4.0, "rec_lim": 3.20, "inc_lim": 0.050, "ret_lim": 2.30, "sn_max": 0.80},
    "HSLA / API (API X70)":               {"al_lim": 0.25, "therm_lim": 2.5, "rec_lim": 2.80, "inc_lim": 0.040, "ret_lim": 2.00, "sn_max": 0.25},
    "Automotive (DP600)":                 {"al_lim": 0.35, "therm_lim": 2.0, "rec_lim": 2.50, "inc_lim": 0.035, "ret_lim": 1.80, "sn_max": 0.15},
    "IF Steel (Deep Draw IF)":            {"al_lim": 0.45, "therm_lim": 1.5, "rec_lim": 2.15, "inc_lim": 0.032, "ret_lim": 1.55, "sn_max": 0.10},
    "Electrical Steel (CRGO / CRNO)":     {"al_lim": 0.48, "therm_lim": 1.1, "rec_lim": 2.05, "inc_lim": 0.031, "ret_lim": 1.50, "sn_max": 0.00},
}

gc1, gc2 = st.columns([1.5, 2.5])
sel_grade = gc1.selectbox("Select Target Steel Grade", list(grades_data.keys()), index=0)
limits = grades_data[sel_grade]

st.markdown("#### Metallurgical Constraints")
sc1, sc2, sc3, sc4, sc5, sc6 = st.columns(6)
max_al   = sc1.slider("Min Effective Al (kg/T)", 0.05, 0.70, limits["al_lim"], step=0.01)
max_thm  = sc2.slider("Max Thermal Burden",      1.0, 6.0, limits["therm_lim"], step=0.1)
max_rec  = sc3.slider("Max Recovery Var",        1.5, 4.0, limits["rec_lim"], step=0.05)
max_inc  = sc4.slider("Max Inclusion Idx",       0.0001, 0.0010, limits["inc_lim"], step=0.0001, format="%.4f")
max_ret  = sc5.slider("Max Re-treatment Risk",   1.0, 3.0, limits["ret_lim"], step=0.1)
max_sn   = sc6.slider("Max Sec/Notch Share",     0.0, 1.0, limits["sn_max"], step=0.05)

# ── LINEAR PROGRAMMING ENGINE ──
# Array Indices: [0] Primary, [1] Secondary, [2] Notch Bar
# Objective: Minimize Final Effective Cost per MT Alloy
c_cost = [P_Price, S_Price + Total_Pen_S, N_Price + Total_Pen_N]

# Sum of all fractional alloy additions must equal 100%
A_eq = [[1, 1, 1]]
b_eq = [1]

# Inequality constraints (A_ub * [P, S, N]^T <= b_ub)
A_ub = [
    [-Eff_P, -Eff_S, -Eff_N],           # Effective Al Delivered (Negative for >= constraint)
    [1.0,    3.0,    5.0],              # Thermal Burden Index
    [2.0,    3.0,    3.5],              # Recovery Variability (StDev %)
    [P_Reject, S_Reject, N_Reject],     # Inclusion Severity Index
    [1.5,    2.0,    2.5],              # LF Re-treatment Risk
    [0.0,    1.0,    1.0],              # Max Secondary / Notch Share combined
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
    
    # Calculate Effective Al of the resultant blend
    blend_eff_al = (mix[0] * Eff_P) + (mix[1] * Eff_S) + (mix[2] * Eff_N)
    
    # Calculate the True Final Effective Cost per MT of Effective Al: (B4+B9)/B3 equivalence
    cost_eff_blend = res.fun / blend_eff_al
    
    savings_vs_primary = Net_Eff_Cost_P - cost_eff_blend

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
        # Cost Comparison Chart
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Bar(
            x=["100% Primary", "Optimal Blend", "100% Secondary", "100% Notch Bar"],
            y=[Net_Eff_Cost_P, cost_eff_blend, Net_Eff_Cost_S, Net_Eff_Cost_N],
            marker_color=[C_PRIM, "#1A237E", C_SEC, C_NOTCH],
            text=[f"₹{Net_Eff_Cost_P:,.0f}", f"₹{cost_eff_blend:,.0f}", f"₹{Net_Eff_Cost_S:,.0f}", f"₹{Net_Eff_Cost_N:,.0f}"],
            textposition="auto",
            hovertemplate="%{x}<br>₹%{y:,.0f}/MT Eff. Al<extra></extra>"
        ))
        fig_cost.update_layout(**_layout("Net Effective Cost Comparison (₹/MT Effective Al)", "Cost (₹)", 380))
        st.plotly_chart(fig_cost, use_container_width=True)
        
    with col_insight2:
        # Constraint Utilization Chart
        actual_therm = mix[0] * 1.0 + mix[1] * 3.0 + mix[2] * 5.0
        actual_rec   = mix[0] * 2.0 + mix[1] * 3.0 + mix[2] * 3.5
        actual_inc   = mix[0] * P_Reject + mix[1] * S_Reject + mix[2] * N_Reject
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
    
    # Status calculation
    df_profile["Status"] = np.where(
        df_profile["Parameter"] == "Effective Al Delivered (kg/T)",
        np.where(df_profile["Blend Actual"] <= df_profile["Maximum Allowed"] + 1e-6, "🛑 Binding Constraint", "✅ Safe (Surplus)"),
        np.where(df_profile["Blend Actual"] >= df_profile["Maximum Allowed"] - 1e-6, "🛑 Binding Constraint", "✅ Safe")
    )
    
    # Format values for display
    def format_val(val, param):
        if param == "Secondary & Notch Share": return f"{val*100:.2f}%"
        if param == "Inclusion Severity Index": return f"{val:.5f}"
        return f"{val:.4f}"
        
    df_profile["Blend Actual"] = df_profile.apply(lambda row: format_val(row["Blend Actual"], row["Parameter"]), axis=1)
    df_profile["Maximum Allowed"] = df_profile.apply(lambda row: format_val(row["Maximum Allowed"], row["Parameter"]), axis=1)

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