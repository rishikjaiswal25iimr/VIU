from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & THEME
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Aluminium VIU Dashboard",
    page_icon="🏭",
    layout="wide",
)

# Colour palette
C_PRI      = "#2196F3"   # blue  – Primary Al
C_SEC      = "#009688"   # teal  – Secondary Al
C_NOTCH    = "#FF9800"   # amber – Al Notch Bar
C_DELTA    = "#4CAF50"   # green – benefit / savings
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
    background: linear-gradient(180deg, #263238 0%, #37474F 40%, #455A64 100%);
}
[data-testid="stSidebar"] * { color: #ECEFF1 !important; }
[data-testid="stSidebar"] .stSlider > div > div > div { background: #78909C !important; }
[data-testid="stSidebar"] hr { border-color: #546E7A; }
[data-testid="stSidebar"] .stNumberInput input { background: #37474F; border-color: #78909C; color: #fff !important; }
[data-testid="stSidebar"] .stSelectbox select { background: #37474F; color: #fff; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { color: #fff !important; }

/* ---------- KPI cards ---------- */
.kpi-card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 18px 22px 14px 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    border-left: 5px solid #2196F3;
    margin-bottom: 8px;
}
.kpi-card-teal   { border-left-color: #009688; }
.kpi-card-amber  { border-left-color: #FF9800; }
.kpi-card-green  { border-left-color: #4CAF50; }
.kpi-card-red    { border-left-color: #F44336; }
.kpi-card-purple { border-left-color: #9C27B0; }
.kpi-label { font-size: 11px; font-weight: 600; color: #78909C; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
.kpi-value { font-size: 22px; font-weight: 700; color: #263238; line-height: 1.15; }
.kpi-sub   { font-size: 11px; color: #90A4AE; margin-top: 3px; }

/* ---------- section headers ---------- */
.section-header {
    font-size: 20px; font-weight: 800; color: #263238;
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
.warn-box {
    background: #FFF3E0; border-radius: 8px;
    padding: 12px 16px; font-size: 13px; color: #E65100;
    border-left: 4px solid #FF9800; margin-bottom: 10px;
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
        title=dict(text=title, font=dict(size=15, color="#263238"), x=0.01),
        legend=dict(bgcolor="rgba(255,255,255,0.85)", bordercolor="#DDD", borderwidth=1),
        xaxis=dict(showgrid=True, gridcolor=C_GRID, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=C_GRID, zeroline=False, title=y_title),
        hovermode="x unified",
        height=height,
        margin=dict(l=60, r=30, t=55, b=45),
    )

# ══════════════════════════════════════════════════════════════════════════════
# KPI CARD HELPER
# ══════════════════════════════════════════════════════════════════════════════
def kpi(label: str, value: str, sub: str = "", colour: str = "") -> str:
    cls = f"kpi-card {colour}"
    return f"""
    <div class="{cls}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>"""

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR – ALL INPUT PARAMETERS
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏭 Aluminium VIU Dashboard")
    st.divider()

    st.markdown("### A. Comparison Selection")
    comparison_selection = st.radio(
        "Select Analysis:",
        ["Not selected", "Aluminium Alloys Comparison"],
        index=0
    )
    
    if comparison_selection != "Not selected":
        st.divider()
        st.markdown("### B. Financial Parameters")
        P_Pri_Price          = st.number_input("Primary Al Price (₹/MT)",      value=380000, step=1000, min_value=100000)
        P_Sec_Price          = st.number_input("Secondary Al Price (₹/MT)",    value=340000, step=1000, min_value=100000)
        P_Notch_Price        = st.number_input("Al Notch Bar Price (₹/MT)",    value=335000, step=1000, min_value=100000)
        P_Power_Cost         = st.number_input("Power Cost (₹/kWh)",           value=6.5,    step=0.1,  format="%.2f")
        P_Electrode_Cost     = st.number_input("Electrode Cost (₹/kg)",        value=240,    step=10)
        P_Steel_Value        = st.number_input("Steel Value (₹/MT)",           value=60000,  step=1000)
        P_Slag_Cost          = st.number_input("Ladle Slag Handling (₹/MT)",   value=800,    step=50)
        P_Margin_Steel       = st.number_input("Throughput Margin (₹/MT)",     value=2800,   step=100)
        P_LF_Retreatment     = st.number_input("LF Re-treatment Cost (₹/heat)",value=15000,  step=500)

        st.divider()
        st.markdown("### C. Technical Parameters")
        P_Pri_Purity   = st.slider("Primary Al Purity (%)",     95.0, 99.9, 99.0, 0.1) / 100
        P_Sec_Purity   = st.slider("Secondary Al Purity (%)",   90.0, 99.0, 97.0, 0.1) / 100
        P_Notch_Purity = st.slider("Al Notch Bar Purity (%)",   85.0, 98.0, 95.0, 0.1) / 100
        
        P_Pri_Rec      = st.slider("Primary Al Recovery (%)",   30.0, 70.0, 49.0, 0.5) / 100
        P_Sec_Rec      = st.slider("Secondary Al Recovery (%)", 30.0, 70.0, 46.0, 0.5) / 100
        P_Notch_Rec    = st.slider("Notch Bar Recovery (%)",    30.0, 70.0, 46.0, 0.5) / 100
        
        # Default updated to 99.89%
        P_Pri_Yield    = st.slider("Primary Metallic Yield (%)",   99.0, 100.0, 99.89, 0.01) / 100
        P_Sec_Yield    = st.slider("Secondary Metallic Yield (%)", 99.0, 100.0, 99.88, 0.01) / 100
        P_Notch_Yield  = st.slider("Notch Bar Metallic Yield (%)", 99.0, 100.0, 99.87, 0.01) / 100

        P_LF_Efficiency= st.slider("LF Thermal Efficiency (%)", 20.0, 80.0, 40.0, 1.0) / 100
        P_SpHeat       = st.slider("Specific Heat Impurities (MJ/kg)", 1.0, 5.0, 2.5, 0.1)

        st.divider()
        st.markdown("### D. Operational Parameters")
        P_Heat_Size    = st.slider("Heat Size (MT)",            100,  350,  190,  5)
        P_Cycle_Time   = st.slider("LF Cycle Time (min)",        30,   90,   53,  1)
        Active_Al      = st.number_input("Al Addition Target (%)", value=0.2, step=0.01, format="%.3f")
        
        P_Pri_Overdose   = st.number_input("Primary Overdose Buffer",   value=0.02, format="%.3f")
        P_Sec_Overdose   = st.number_input("Secondary Overdose Buffer", value=0.03, format="%.3f")
        P_Notch_Overdose = st.number_input("Notch Bar Overdose Buffer", value=0.035, format="%.3f")
        
        P_Pri_Reject     = st.number_input("Primary Rejection Rate",    value=0.0003, format="%.5f")
        P_Sec_Reject     = st.number_input("Secondary Rejection Rate",  value=0.00045, format="%.5f")
        P_Notch_Reject   = st.number_input("Notch Bar Rejection Rate",  value=0.00055, format="%.5f")

        P_Pri_Retreat    = st.number_input("Primary Re-treatment Rate",   value=0.015, format="%.3f")
        P_Sec_Retreat    = st.number_input("Secondary Re-treatment Rate", value=0.020, format="%.3f")
        P_Notch_Retreat  = st.number_input("Notch Bar Re-treatment Rate", value=0.025, format="%.3f")

        Extra_Time_Sec   = st.slider("Extra Time - Sec (min)",   0.0, 5.0, 0.5, 0.1)
        Extra_Time_Notch = st.slider("Extra Time - Notch (min)", 0.0, 5.0, 1.0, 0.1)
        
        P_Elec_Wear      = st.number_input("Electrode Wear (kg/kWh)", value=0.0015, format="%.4f")
        
        Dross_Pri_Sec    = st.slider("Dross Diff Pri vs Sec (kg/MT)",   0.0, 50.0, 20.0, 1.0)
        Dross_Pri_Notch  = st.slider("Dross Diff Pri vs Notch (kg/MT)", 0.0, 80.0, 40.0, 1.0)
        
        Slag_Pri_Sec     = st.slider("Slag Diff Pri vs Sec (kg/T)",     0.0, 100.0, 55.4, 0.1)
        Slag_Pri_Notch   = st.slider("Slag Diff Pri vs Notch (kg/T)",   0.0, 100.0, 55.0, 0.1)

        st.divider()
        st.markdown("### E. Realization Factors")
        R_Power       = st.slider("Power Realization",       0.0, 1.0, 1.00, 0.05)
        R_Electrode   = st.slider("Electrode Realization",   0.0, 1.0, 1.00, 0.05)
        R_Throughput  = st.slider("Throughput Realization",  0.0, 1.0, 0.10, 0.05) # Default updated to 0.10
        R_Stability   = st.slider("Stability Realization",   0.0, 1.0, 0.50, 0.05)
        R_Slag        = st.slider("Slag Handling Realization",0.0, 1.0, 0.50, 0.05)
        R_Cleanliness = st.slider("Cleanliness Realization", 0.0, 1.0, 0.40, 0.05) # Default updated to 0.40
        R_Yield       = st.slider("Yield Realization",       0.0, 1.0, 0.50, 0.05)
        R_Reblow      = st.slider("Reblow Realization",      0.0, 1.0, 1.00, 0.05)

        st.divider()
        st.markdown("### F. Enterprise Savings")
        Al_Consumption_FY = st.number_input("Base Al Consumption (MT)", value=4325, step=100, min_value=100) # Default updated to 4325
        Substitution_Pct  = st.slider("% Substitution", 0.0, 1.0, 0.50, 0.05)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT GUARD
# ══════════════════════════════════════════════════════════════════════════════
if comparison_selection == "Not selected":
    st.info("Please select the substitution combination to run the VIU analysis.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# CORE CALCULATIONS (EXACT EXCEL REPLICATION)
# ══════════════════════════════════════════════════════════════════════════════

# --- 1. Effective Al Delivery ---
Eff_Pri   = P_Pri_Purity * P_Pri_Rec
Eff_Sec   = P_Sec_Purity * P_Sec_Rec
Eff_Notch = P_Notch_Purity * P_Notch_Rec

# Alloy Required to Deliver 1 MT of Effective Al (MT)
Req_Pri   = 1.0 / Eff_Pri
Req_Sec   = 1.0 / Eff_Sec
Req_Notch = 1.0 / Eff_Notch

# Raw Material Cost per MT Effective Al
Raw_Cost_Pri   = P_Pri_Price * Req_Pri
Raw_Cost_Sec   = P_Sec_Price * Req_Sec
Raw_Cost_Notch = P_Notch_Price * Req_Notch

# Active Al Target in kg/MT Steel
Active_Al_kg_T = (Active_Al / 100.0) * 1000.0

# Alloy required per MT Steel
Alloy_T_Pri   = Active_Al_kg_T / Eff_Pri
Alloy_T_Sec   = Active_Al_kg_T / Eff_Sec
Alloy_T_Notch = Active_Al_kg_T / Eff_Notch

# Steel Supported per 1 MT of Alloy
Steel_Pri   = 1000.0 / Alloy_T_Pri
Steel_Sec   = 1000.0 / Alloy_T_Sec
Steel_Notch = 1000.0 / Alloy_T_Notch

# --- 2. Operational Penalties (Relative to Primary Al Baseline) ---
# Primary is the benchmark; its penalties are exactly 0.
# We compute absolute penalties for Secondary and Notch per MT of Alloy.

# Power Penalty
Extra_kWh_Sec   = (Dross_Pri_Sec * P_SpHeat) / 3.6 / P_LF_Efficiency
Extra_kWh_Notch = (Dross_Pri_Notch * P_SpHeat) / 3.6 / P_LF_Efficiency
Pen_Power_Sec   = Extra_kWh_Sec * P_Power_Cost * R_Power
Pen_Power_Notch = Extra_kWh_Notch * P_Power_Cost * R_Power

# Electrode Penalty
Pen_Elec_Sec   = Extra_kWh_Sec * P_Elec_Wear * P_Electrode_Cost * R_Electrode
Pen_Elec_Notch = Extra_kWh_Notch * P_Elec_Wear * P_Electrode_Cost * R_Electrode

# Throughput Penalty
Pen_Time_Sec   = (Extra_Time_Sec / P_Cycle_Time) * P_Heat_Size * P_Margin_Steel * (1000.0 / (Alloy_T_Sec * P_Heat_Size)) * R_Throughput
Pen_Time_Notch = (Extra_Time_Notch / P_Cycle_Time) * P_Heat_Size * P_Margin_Steel * (1000.0 / (Alloy_T_Notch * P_Heat_Size)) * R_Throughput

# Recovery Stability Penalty
Pen_Stab_Sec   = (P_Sec_Overdose - P_Pri_Overdose) * (P_Sec_Price / 1000.0) * Steel_Sec * R_Stability
Pen_Stab_Notch = (P_Notch_Overdose - P_Pri_Overdose) * (P_Notch_Price / 1000.0) * Steel_Notch * R_Stability

# Slag Handling Penalty
Pen_Slag_Sec   = Slag_Pri_Sec * (P_Slag_Cost / 1000.0) * R_Slag
Pen_Slag_Notch = Slag_Pri_Notch * (P_Slag_Cost / 1000.0) * R_Slag

# Inclusion Cleanliness Penalty
Pen_Clean_Sec   = (P_Sec_Reject - P_Pri_Reject) * P_Steel_Value * Steel_Sec * R_Cleanliness
Pen_Clean_Notch = (P_Notch_Reject - P_Pri_Reject) * P_Steel_Value * Steel_Notch * R_Cleanliness

# Yield Improvement Penalty
Pen_Yield_Sec   = (P_Pri_Yield - P_Sec_Yield) * P_Steel_Value * Steel_Sec * R_Yield
Pen_Yield_Notch = (P_Pri_Yield - P_Notch_Yield) * P_Steel_Value * Steel_Notch * R_Yield

# Re-treatment Reduction Penalty
Pen_Reblow_Sec   = (P_Sec_Retreat - P_Pri_Retreat) * P_LF_Retreatment * (Steel_Sec / P_Heat_Size) * R_Reblow
Pen_Reblow_Notch = (P_Notch_Retreat - P_Pri_Retreat) * P_LF_Retreatment * (Steel_Notch / P_Heat_Size) * R_Reblow


# ══ VIU SUMMARY EXACT LOGIC ═══════════════════════════════════════════════════
# Total Penalties per MT Alloy
Total_Pen_Sec   = Pen_Power_Sec + Pen_Elec_Sec + Pen_Time_Sec + Pen_Stab_Sec + Pen_Slag_Sec + Pen_Clean_Sec + Pen_Yield_Sec + Pen_Reblow_Sec
Total_Pen_Notch = Pen_Power_Notch + Pen_Elec_Notch + Pen_Time_Notch + Pen_Stab_Notch + Pen_Slag_Notch + Pen_Clean_Notch + Pen_Yield_Notch + Pen_Reblow_Notch

# Total Penalties Converted to Effective Al Basis
Conv_Pen_Sec   = Total_Pen_Sec * Req_Sec
Conv_Pen_Notch = Total_Pen_Notch * Req_Notch

# Final Adjusted Cost per MT Effective Al
Adj_Cost_Pri   = Raw_Cost_Pri
Adj_Cost_Sec   = Raw_Cost_Sec + Conv_Pen_Sec
Adj_Cost_Notch = Raw_Cost_Notch + Conv_Pen_Notch

# Determine the Optimal Choice
costs = {"Primary Al Ingot": Adj_Cost_Pri, "Secondary Al Ingot": Adj_Cost_Sec, "Al Notch Bar": Adj_Cost_Notch}
best_commodity = min(costs, key=costs.get)
best_cost = costs[best_commodity]

# Enterprise Savings Calculation
Total_Eff_Al_Req = Al_Consumption_FY * Eff_Pri
Baseline_Spend   = Total_Eff_Al_Req * Adj_Cost_Pri
Optimal_Spend    = Total_Eff_Al_Req * best_cost

Savings_Rs = (Baseline_Spend - Optimal_Spend) * Substitution_Pct
Annual_Savings_Cr = Savings_Rs / 1e7

# Compute Savings/MT vs Baseline Primary
Savings_Per_MT_Eff_Al = Adj_Cost_Pri - best_cost

# --- Dynamic Comparison Parameter Metrics for Top KPI Grid ---
# 1. Raw Al cost gaps (per MT Effective Al)
Cost_Gap_Pri_Sec   = Raw_Cost_Pri - Raw_Cost_Sec
Cost_Gap_Pri_Notch = Raw_Cost_Pri - Raw_Cost_Notch

# 2. Total VIU Converted operational penalty differences (per MT Effective Al)
Total_VIU_Credits_Pri_Sec   = Conv_Pen_Sec
Total_VIU_Credits_Pri_Notch = Conv_Pen_Notch

# 3. Net Savings (per MT Effective Al)
Net_Savings_Pri_Sec   = Adj_Cost_Pri - Adj_Cost_Sec
Net_Savings_Pri_Notch = Adj_Cost_Pri - Adj_Cost_Notch

# 4. Annual Value of substitution (in Crore)
Annual_Savings_Pri_Sec_Cr   = (Total_Eff_Al_Req * Net_Savings_Pri_Sec * Substitution_Pct) / 1e7
Annual_Savings_Pri_Notch_Cr = (Total_Eff_Al_Req * Net_Savings_Pri_Notch * Substitution_Pct) / 1e7


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD RENDERING
# ══════════════════════════════════════════════════════════════════════════════

# ── SECTION 1: DASHBOARD HEADER ──
st.markdown("""
<div style="background: linear-gradient(135deg,#263238 0%,#37474F 60%,#455A64 100%);
            padding:22px 28px 18px 28px; border-radius:14px; margin-bottom:20px;
            box-shadow:0 4px 24px rgba(38,50,56,0.25);">
  <h1 style="color:#FFFFFF;margin:0;font-size:26px;font-weight:800;letter-spacing:0.02em;">
    🏭 Aluminium VIU Dashboard — Primary vs Secondary vs Notch Bar
  </h1>
  <p style="color:#B0BEC5;margin:6px 0 0 0;font-size:13px;">
    Value-In-Use Economic Analysis &nbsp;|&nbsp; Quantifying the true metallurgical cost of impurities, physical form, and chemistry variability.
  </p>
</div>
""", unsafe_allow_html=True)

# ── SECTION 2: TOP KPI CARDS ──
st.markdown("### 📊 Enterprise KPI Dashboard Overview")

# -- ROW 1: Global Portfolio Metrics --
st.markdown("##### 🌐 Global Portfolio Metrics")
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.markdown(kpi("Primary Al Price", f"₹{P_Pri_Price:,.0f}", "per MT alloy", ""), unsafe_allow_html=True)
with c2:
    st.markdown(kpi("Secondary Al Price", f"₹{P_Sec_Price:,.0f}", "per MT alloy", "kpi-card-teal"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi("Al Notch Bar Price", f"₹{P_Notch_Price:,.0f}", "per MT alloy", "kpi-card-amber"), unsafe_allow_html=True)
with c4:
    st.markdown(kpi("Lowest VIU Cost", f"₹{best_cost:,.0f}", "per MT Effective Al", "kpi-card-green"), unsafe_allow_html=True)
with c5:
    st.markdown(kpi("Optimal Choice", f"{best_commodity}", "Lowest total cost", "kpi-card-green"), unsafe_allow_html=True)
with c6:
    st.markdown(kpi("Max Annual Savings", f"₹{Annual_Savings_Cr:.2f} Cr", f"vs Primary @ {Substitution_Pct*100:.0f}% Sub", "kpi-card-green" if Annual_Savings_Cr > 0 else "kpi-card-purple"), unsafe_allow_html=True)

# -- ROW 2: Primary vs Secondary Deep-Dive --
st.markdown("##### 🔬 Primary vs. Secondary Al Ingot Deep-Dive")
cs1, cs2, cs3, cs4 = st.columns(4)
with cs1:
    st.markdown(kpi("Al Cost Gap (Pri vs Sec)", f"₹{Cost_Gap_Pri_Sec:,.0f}", "per MT Effective Al (Raw Premium)", "kpi-card-teal"), unsafe_allow_html=True)
with cs2:
    st.markdown(kpi("Total VIU Credits (Pri vs Sec)", f"₹{Total_VIU_Credits_Pri_Sec:,.0f}", "per MT Effective Al (Op Penalties avoided)", "kpi-card-teal"), unsafe_allow_html=True)
with cs3:
    color_ps = "kpi-card-green" if Net_Savings_Pri_Sec < 0 else "kpi-card-red"
    text_ps = f"₹{abs(Net_Savings_Pri_Sec):,.0f}" + (" (Sec Favored)" if Net_Savings_Pri_Sec < 0 else " (Pri Favored)")
    st.markdown(kpi("Net Savings (Pri vs Sec)", text_ps, "Adjusted Cost Delta per MT Effective Al", color_ps), unsafe_allow_html=True)
with cs4:
    color_pas = "kpi-card-green" if Annual_Savings_Pri_Sec_Cr < 0 else "kpi-card-red"
    text_pas = f"₹{abs(Annual_Savings_Pri_Sec_Cr):.2f} Cr" + (" (Sec Favored)" if Annual_Savings_Pri_Sec_Cr < 0 else " (Pri Favored)")
    st.markdown(kpi("Annual Savings (Pri vs Sec)", text_pas, f"@ {Substitution_Pct*100:.0f}% Substitution", color_pas), unsafe_allow_html=True)

# -- ROW 3: Primary vs Notch Bar Deep-Dive --
st.markdown("##### 📐 Primary vs. Aluminium Notch Bar Deep-Dive")
cn1, cn2, cn3, cn4 = st.columns(4)
with cn1:
    st.markdown(kpi("Al Cost Gap (Pri vs Notch)", f"₹{Cost_Gap_Pri_Notch:,.0f}", "per MT Effective Al (Raw Premium)", "kpi-card-amber"), unsafe_allow_html=True)
with cn2:
    st.markdown(kpi("Total VIU Credits (Pri vs Notch)", f"₹{Total_VIU_Credits_Pri_Notch:,.0f}", "per MT Effective Al (Op Penalties avoided)", "kpi-card-amber"), unsafe_allow_html=True)
with cn3:
    color_pn = "kpi-card-green" if Net_Savings_Pri_Notch < 0 else "kpi-card-red"
    text_pn = f"₹{abs(Net_Savings_Pri_Notch):,.0f}" + (" (Notch Favored)" if Net_Savings_Pri_Notch < 0 else " (Pri Favored)")
    st.markdown(kpi("Net Savings (Pri vs Notch)", text_pn, "Adjusted Cost Delta per MT Effective Al", color_pn), unsafe_allow_html=True)
with cn4:
    color_pan = "kpi-card-green" if Annual_Savings_Pri_Notch_Cr < 0 else "kpi-card-red"
    text_pan = f"₹{abs(Annual_Savings_Pri_Notch_Cr):.2f} Cr" + (" (Notch Favored)" if Annual_Savings_Pri_Notch_Cr < 0 else " (Pri Favored)")
    st.markdown(kpi("Annual Savings (Pri vs Notch)", text_pan, f"@ {Substitution_Pct*100:.0f}% Substitution", color_pan), unsafe_allow_html=True)


# ── SECTION 3: VIU SUMMARY ──
st.markdown('<div class="section-header">VIU Economic Synthesis</div>', unsafe_allow_html=True)
col_l, col_r = st.columns([1.1, 0.9])
with col_l:
    st.markdown("#### VIU Components (per MT Effective Aluminium)")
    data_summary = {
        "Metric": [
            "Market Price (₹/MT alloy)",
            "Active Al Purity (%)",
            "Physical Recovery (%)",
            "Effective Al Efficiency (%)",
            "Alloy Required per MT Eff. Al",
            "Base Cost (₹/MT Eff. Al)",
            "Operational Penalties (Converted)",
            "Total VIU Adjusted Cost (₹/MT)",
        ],
        "Primary Al": [
            f"₹{P_Pri_Price:,.0f}",
            f"{P_Pri_Purity*100:.1f}%",
            f"{P_Pri_Rec*100:.1f}%",
            f"{Eff_Pri*100:.2f}%",
            f"{Req_Pri:.3f} MT",
            f"₹{Raw_Cost_Pri:,.0f}",
            "— (Baseline)",
            f"₹{Adj_Cost_Pri:,.0f}",
        ],
        "Secondary Al": [
            f"₹{P_Sec_Price:,.0f}",
            f"{P_Sec_Purity*100:.1f}%",
            f"{P_Sec_Rec*100:.1f}%",
            f"{Eff_Sec*100:.2f}%",
            f"{Req_Sec:.3f} MT",
            f"₹{Raw_Cost_Sec:,.0f}",
            f"+₹{Conv_Pen_Sec:,.0f}",
            f"₹{Adj_Cost_Sec:,.0f}",
        ],
        "Al Notch Bar": [
            f"₹{P_Notch_Price:,.0f}",
            f"{P_Notch_Purity*100:.1f}%",
            f"{P_Notch_Rec*100:.1f}%",
            f"{Eff_Notch*100:.2f}%",
            f"{Req_Notch:.3f} MT",
            f"₹{Raw_Cost_Notch:,.0f}",
            f"+₹{Conv_Pen_Notch:,.0f}",
            f"₹{Adj_Cost_Notch:,.0f}",
        ]
    }
    df_sum = pd.DataFrame(data_summary).set_index("Metric")
    st.dataframe(df_sum, use_container_width=True)

    # Verdict
    if best_commodity == "Primary Al Ingot":
        st.markdown(f"""
        <div class="warn-box">
        ⚠️ <b>Primary Aluminium Ingot is the most cost-effective choice.</b><br>
        Despite higher market prices, the severe metallurgical and operational penalties (₹{Conv_Pen_Sec:,.0f} for Secondary, ₹{Conv_Pen_Notch:,.0f} for Notch) incurred by lower-tier alloys make them economically inferior on a Value-in-Use basis.
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="success-box">
        ✅ <b>{best_commodity} offers a net VIU advantage.</b><br>
        The upfront price discount of {best_commodity} overcomes its operational penalties, resulting in an effective saving of ₹{Savings_Per_MT_Eff_Al:,.0f} per MT of Effective Aluminium compared to Primary Ingot.
        </div>""", unsafe_allow_html=True)

with col_r:
    # --- VIU Grouped Bar: Penalty Composition ---
    penalty_names = [
        "Power Penalty", "Electrode Penalty", "Throughput Penalty",
        "Recovery Stability", "Slag Handling",
        "Cleanliness", "Yield Loss", "Re-treatment Risk"
    ]
    pen_sec_vals = [
        Pen_Power_Sec, Pen_Elec_Sec, Pen_Time_Sec,
        Pen_Stab_Sec, Pen_Slag_Sec, Pen_Clean_Sec,
        Pen_Yield_Sec, Pen_Reblow_Sec
    ]
    pen_notch_vals = [
        Pen_Power_Notch, Pen_Elec_Notch, Pen_Time_Notch,
        Pen_Stab_Notch, Pen_Slag_Notch, Pen_Clean_Notch,
        Pen_Yield_Notch, Pen_Reblow_Notch
    ]

    fig_pen = go.Figure()
    fig_pen.add_trace(go.Bar(name='Secondary Al', x=penalty_names, y=pen_sec_vals, marker_color=C_SEC))
    fig_pen.add_trace(go.Bar(name='Al Notch Bar', x=penalty_names, y=pen_notch_vals, marker_color=C_NOTCH))

    fig_pen.update_layout(
        barmode='group',
        **_layout("Absolute Operational Penalties (₹ per MT Alloy)", "₹/MT Alloy", 380)
    )
    fig_pen.update_layout(
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_pen, use_container_width=True)


# ── SECTION 4: BENEFIT BREAKDOWN ──
st.markdown('<div class="section-header">Detailed Operational Penalty Breakdown</div>', unsafe_allow_html=True)

col_chart, col_table = st.columns([2.5, 3])

with col_chart:
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        y=penalty_names[::-1],
        x=pen_sec_vals[::-1],
        orientation="h",
        name="Secondary Al",
        marker_color=C_SEC,
    ))
    fig_bar.add_trace(go.Bar(
        y=penalty_names[::-1],
        x=pen_notch_vals[::-1],
        orientation="h",
        name="Notch Bar",
        marker_color=C_NOTCH,
    ))
    fig_bar.update_layout(
        barmode="group",
        **_layout("Penalty Severity Ranking (₹/MT Alloy)", "₹/MT Alloy", 480)
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with col_table:
    breakdown_basis = [
        f"Extra Heat (Sec: {Extra_kWh_Sec:.1f} kWh, Notch: {Extra_kWh_Notch:.1f} kWh), LF Eff: {P_LF_Efficiency*100:.0f}%",
        f"Wear rate {P_Elec_Wear*1000:.1f}g/kWh, Cost: ₹{P_Electrode_Cost}/kg",
        f"Extra Time (Sec: {Extra_Time_Sec}m, Notch: {Extra_Time_Notch}m), Margin: ₹{P_Margin_Steel}/T",
        f"Overdose Diff (Sec: {(P_Sec_Overdose-P_Pri_Overdose)*100:.2f}%, Notch: {(P_Notch_Overdose-P_Pri_Overdose)*100:.2f}%)",
        f"Slag Vol Diff (Sec: {Slag_Pri_Sec:.1f} kg, Notch: {Slag_Pri_Notch:.1f} kg)",
        f"Reject Diff (Sec: {(P_Sec_Reject-P_Pri_Reject)*100:.3f}%, Notch: {(P_Notch_Reject-P_Pri_Reject)*100:.3f}%)",
        f"Yield Drop (Sec: {(P_Pri_Yield-P_Sec_Yield)*100:.2f}%, Notch: {(P_Pri_Yield-P_Notch_Yield)*100:.2f}%)",
        f"Reblow Diff (Sec: {(P_Sec_Retreat-P_Pri_Retreat)*100:.2f}%, Notch: {(P_Notch_Retreat-P_Pri_Retreat)*100:.2f}%)",
    ]

    df_breakdown = pd.DataFrame({
        "Penalty Component": penalty_names,
        "Secondary (₹/MT)": [f"₹{v:,.0f}" for v in pen_sec_vals],
        "Notch Bar (₹/MT)": [f"₹{v:,.0f}" for v in pen_notch_vals],
        "Basis & Assumptions": breakdown_basis,
    }).set_index("Penalty Component")

    def color_values(val):
        num = float(val.replace("₹", "").replace(",", ""))
        return "color: #B71C1C; font-weight: 600" if num > 0 else ""

    st.dataframe(
        df_breakdown.style.map(color_values, subset=["Secondary (₹/MT)", "Notch Bar (₹/MT)"]),
        use_container_width=True, height=480,
    )

st.markdown("<br>", unsafe_allow_html=True)

# Heatmap of penalties by realization factor sensitivity
st.markdown("#### Penalty Sensitivity Heatmap (Secondary Al, ₹/MT at varying Realization Factors)")
real_range = np.arange(0.1, 1.05, 0.1)
heat_matrix = []
base_heat_values = [
    Pen_Power_Sec / R_Power if R_Power > 0 else Extra_kWh_Sec * P_Power_Cost,
    Pen_Elec_Sec / R_Electrode if R_Electrode > 0 else Extra_kWh_Sec * P_Elec_Wear * P_Electrode_Cost,
    Pen_Time_Sec / R_Throughput if R_Throughput > 0 else (Extra_Time_Sec / P_Cycle_Time) * P_Heat_Size * P_Margin_Steel * (1000.0 / (Alloy_T_Sec * P_Heat_Size)),
    Pen_Stab_Sec / R_Stability if R_Stability > 0 else (P_Sec_Overdose - P_Pri_Overdose) * (P_Sec_Price / 1000.0) * Steel_Sec,
    Pen_Slag_Sec / R_Slag if R_Slag > 0 else Slag_Pri_Sec * (P_Slag_Cost / 1000.0),
    Pen_Clean_Sec / R_Cleanliness if R_Cleanliness > 0 else (P_Sec_Reject - P_Pri_Reject) * P_Steel_Value * Steel_Sec,
    Pen_Yield_Sec / R_Yield if R_Yield > 0 else (P_Pri_Yield - P_Sec_Yield) * P_Steel_Value * Steel_Sec,
    Pen_Reblow_Sec / R_Reblow if R_Reblow > 0 else (P_Sec_Retreat - P_Pri_Retreat) * P_LF_Retreatment * (Steel_Sec / P_Heat_Size),
]
heat_matrix = np.array([[bv * r for r in real_range] for bv in base_heat_values])

# Theme/font color modified to 'YlOrRd' with solid high-contrast dark-slate gray label font
fig_heat = go.Figure(go.Heatmap(
    z=heat_matrix,
    x=[f"{r*100:.0f}%" for r in real_range],
    y=penalty_names,
    colorscale="YlOrRd",
    text=np.round(heat_matrix, 0).astype(int),
    texttemplate="₹%{text}",
    textfont=dict(size=10, color="#1E293B"),
    hovertemplate="<b>%{y}</b><br>Realization: %{x}<br>Penalty: ₹%{z:,.0f}/MT<extra></extra>",
))
fig_heat.update_layout(
    **_layout("VIU Penalty Heatmap — Realization Factor Sensitivity", "", 380)
)
fig_heat.update_layout(xaxis_title="Realization Factor", yaxis_title="")
st.plotly_chart(fig_heat, use_container_width=True)


# ── SECTION 5: WATERFALL ANALYSIS ──
st.markdown('<div class="section-header">VIU Waterfall Analysis</div>', unsafe_allow_html=True)

# Build waterfall showing how Secondary Al price escalates due to penalties
wf_labels = [
    "Base Secondary Cost",
    "Power Penalty",
    "Electrode Penalty",
    "Throughput Penalty",
    "Recovery Stability",
    "Slag Handling",
    "Cleanliness Risk",
    "Yield Loss",
    "Re-treatment Risk",
    "True Adjusted Cost (Sec)",
]

# Convert penalties to Effective Al basis for the waterfall
wf_values = [
    Raw_Cost_Sec,
    Pen_Power_Sec * Req_Sec,
    Pen_Elec_Sec * Req_Sec,
    Pen_Time_Sec * Req_Sec,
    Pen_Stab_Sec * Req_Sec,
    Pen_Slag_Sec * Req_Sec,
    Pen_Clean_Sec * Req_Sec,
    Pen_Yield_Sec * Req_Sec,
    Pen_Reblow_Sec * Req_Sec,
    0,  # total placeholder
]

measures = ["absolute"] + ["relative"] * (len(wf_labels) - 2) + ["total"]
wf_text = [f"₹{v:,.0f}" for v in wf_values[:-1]] + [f"₹{Adj_Cost_Sec:,.0f}"]

wf_values_display = wf_values[:-1] + [Adj_Cost_Sec]

fig_wf = go.Figure(go.Waterfall(
    name="VIU Waterfall",
    orientation="v",
    measure=measures,
    x=wf_labels,
    y=wf_values_display,
    text=wf_text,
    textposition="outside",
    connector=dict(line=dict(color="#BDBDBD", width=1.5, dash="dot")),
    increasing=dict(marker=dict(color=C_NEG)),
    decreasing=dict(marker=dict(color=C_DELTA)),
    totals=dict(marker=dict(color=C_SEC)),
    hovertemplate="<b>%{x}</b><br>₹%{y:,.0f}/MT Eff. Al<extra></extra>",
))
fig_wf.add_hline(
    y=Adj_Cost_Pri, line_dash="dash", line_color=C_PRI, line_width=2,
    annotation_text=f"Primary Benchmark ₹{Adj_Cost_Pri:,.0f}", annotation_position="top left",
)
fig_wf.update_layout(
    **_layout("VIU Waterfall: Secondary Al True Cost Escalation (₹/MT Effective Al)", "₹/MT Effective Al", 520)
)
fig_wf.update_layout(showlegend=False, xaxis_tickangle=-30)
st.plotly_chart(fig_wf, use_container_width=True)

st.markdown("""
<div class="info-box">
<b>How to read this waterfall:</b> Visualizes the VIU synthesis on an <b>Effective Aluminium</b> basis. 
Starting with the raw base cost of Secondary Aluminium, we sequentially add the metallurgical and operational penalties 
(converted to the Effective Al basis). If the final bar (True Adjusted Cost) exceeds the dashed line (Primary Benchmark), 
then Secondary Aluminium is economically unviable despite its cheaper upfront price.
</div>
""", unsafe_allow_html=True)


# ── SECTION 6: COST COMPARISON ──
st.markdown('<div class="section-header">Cost Comparison & Sensitivity Analysis</div>', unsafe_allow_html=True)

col_a, col_b = st.columns(2)

with col_a:
    # Stacked bar: price components
    fig_stack = go.Figure()
    categories = ["Primary Al", "Secondary Al", "Al Notch Bar"]

    fig_stack.add_trace(go.Bar(
        name="Raw Base Cost (₹/MT Eff Al)", x=categories,
        y=[Raw_Cost_Pri, Raw_Cost_Sec, Raw_Cost_Notch],
        marker_color=[C_PRI, C_SEC, C_NOTCH],
        text=[f"₹{Raw_Cost_Pri:,.0f}", f"₹{Raw_Cost_Sec:,.0f}", f"₹{Raw_Cost_Notch:,.0f}"],
        textposition="inside",
    ))
    fig_stack.add_trace(go.Bar(
        name="Operational Penalties (add)", x=categories,
        y=[0, Conv_Pen_Sec, Conv_Pen_Notch],
        marker_color=["rgba(0,0,0,0)", C_NEG, C_NEG],
        text=["", f"+₹{Conv_Pen_Sec:,.0f}", f"+₹{Conv_Pen_Notch:,.0f}"],
        textposition="inside",
    ))
    
    fig_stack.update_layout(
        barmode="stack",
        **_layout("Total Effective Cost Composition (₹/MT Effective Al)", "₹/MT", 420),
    )
    st.plotly_chart(fig_stack, use_container_width=True)

with col_b:
    # Secondary Price Sensitivity
    sec_prices  = np.linspace(P_Pri_Price * 0.7, P_Pri_Price * 1.1, 80)
    # Re-running the math for varying Secondary prices
    raw_cost_secs = sec_prices * Req_Sec
    fixed_pen_sec = Pen_Power_Sec + Pen_Elec_Sec + Pen_Time_Sec + Pen_Slag_Sec + Pen_Clean_Sec + Pen_Yield_Sec + Pen_Reblow_Sec
    var_pen_sec_mult = (P_Sec_Overdose - P_Pri_Overdose) * (1 / 1000.0) * Steel_Sec * R_Stability
    
    adj_cost_secs = raw_cost_secs + (fixed_pen_sec + sec_prices * var_pen_sec_mult) * Req_Sec
    net_viu_secs = Adj_Cost_Pri - adj_cost_secs

    # Find approximate break-even
    breakeven_idx = np.abs(net_viu_secs).argmin()
    breakeven_price = sec_prices[breakeven_idx]

    fig_sens = go.Figure()
    fig_sens.add_trace(go.Scatter(
        x=sec_prices, y=net_viu_secs,
        mode="lines", name="Secondary Net Advantage",
        line=dict(color=C_SEC, width=3),
        fill="tozeroy",
        fillcolor="rgba(0,150,136,0.15)",
        hovertemplate="Sec Price: ₹%{x:,.0f}<br>Net Advantage: ₹%{y:,.0f}/MT Eff Al<extra></extra>",
    ))
    fig_sens.add_hline(y=0, line_dash="dash", line_color="#333", line_width=1.5)
    fig_sens.add_vline(x=P_Sec_Price, line_dash="dot", line_color=C_SEC, line_width=2,
                       annotation_text=f"Current ₹{P_Sec_Price:,}", annotation_position="top right")
    fig_sens.add_vline(x=breakeven_price, line_dash="dot", line_color=C_NEG, line_width=2,
                       annotation_text=f"Break-even ≈ ₹{breakeven_price:,.0f}", annotation_position="top left")
    fig_sens.update_layout(
        **_layout("Secondary Price Sensitivity – Net VIU Advantage (₹/MT Eff Al)", "Net Advantage (₹)", 420)
    )
    st.plotly_chart(fig_sens, use_container_width=True)

st.markdown("<br>", unsafe_allow_html=True)


# ── SECTION 7: ENTERPRISE SAVINGS ──
st.markdown('<div class="section-header">Enterprise Savings Calculator</div>', unsafe_allow_html=True)

# Top KPI row
s1, s2, s3, s4 = st.columns(4)
with s1:
    substituted_eff = Total_Eff_Al_Req * Substitution_Pct
    st.markdown(kpi("Substituted Eff. Volume", f"{substituted_eff:,.0f} MT", f"Effective Al at {Substitution_Pct*100:.0f}% substitution", ""), unsafe_allow_html=True)
with s2:
    st.markdown(kpi("Savings / MT Eff. Al", f"₹{abs(Savings_Per_MT_Eff_Al):,.0f}", "Magnitude of net advantage", "kpi-card-green" if Annual_Savings_Cr > 0 else "kpi-card-purple"), unsafe_allow_html=True)
with s3:
    abs_savings_yr = abs(Annual_Savings_Cr)
    st.markdown(kpi("Annual Savings FY26", f"₹{abs_savings_yr:.2f} Cr", "at stated volume", "kpi-card-green" if Annual_Savings_Cr > 0 else "kpi-card-purple"), unsafe_allow_html=True)
with s4:
    monthly = Annual_Savings_Cr * 1e7 / 12 / 1e5
    st.markdown(kpi("Monthly Savings", f"₹{abs(monthly):.1f} L", "per month average", "kpi-card-amber"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

col_lft, col_rgt = st.columns([2, 1])

with col_lft:
    # Savings vs consumption volume chart
    vol_range = np.arange(1000, Al_Consumption_FY * 2.5, 500)
    # Savings dynamically driven
    savings_cr = ((Adj_Cost_Pri - best_cost) * (vol_range * Eff_Pri) * Substitution_Pct) / 1e7

    fig_sav = go.Figure()
    fig_sav.add_trace(go.Scatter(
        x=vol_range, y=savings_cr,
        mode="lines", name="Annual Savings (₹ Cr)",
        line=dict(color=C_DELTA if Savings_Per_MT_Eff_Al > 0 else C_PRI, width=3),
        fill="tozeroy",
        fillcolor="rgba(76,175,80,0.12)" if Savings_Per_MT_Eff_Al > 0 else "rgba(33,150,243,0.12)",
        hovertemplate="Consumption: %{x:,.0f} MT<br>Savings/Avoided Loss: ₹%{y:.2f} Cr<extra></extra>",
    ))
    fig_sav.add_vline(
        x=Al_Consumption_FY, line_dash="dash", line_color="#263238", line_width=2,
        annotation_text=f"Total: {Al_Consumption_FY:,} MT → ₹{Annual_Savings_Cr:.2f} Cr",
        annotation_position="top left",
    )
    fig_sav.add_hline(y=0, line_dash="solid", line_color="#333", line_width=1.5)
    
    title_text = f"Enterprise Optimization Value vs Consumption Volume (@ {Substitution_Pct*100:.0f}% Sub)"
    fig_sav.update_layout(
        **_layout(title_text, "Value (₹ Crore)", 400)
    )
    st.plotly_chart(fig_sav, use_container_width=True)

    # 3-year projection (annual compounding with 5% price escalation)
    st.markdown(f"#### 3-Year Strategic Optimization Value (5% annual price escalation)")
    years = ["FY 2026", "FY 2027", "FY 2028"]
    escalation = [1.0, 1.05, 1.1025]
    proj_savings = [abs(Annual_Savings_Cr) * e for e in escalation]
    cumulative_cr = np.cumsum(proj_savings)

    fig_3yr = go.Figure()
    fig_3yr.add_trace(go.Bar(
        x=years, y=proj_savings,
        name="Annual Value (₹ Cr)",
        marker_color=[C_DELTA if Annual_Savings_Cr > 0 else C_PRI for _ in proj_savings],
        text=[f"₹{v:.2f} Cr" for v in proj_savings],
        textposition="outside",
    ))
    fig_3yr.add_trace(go.Scatter(
        x=years, y=cumulative_cr,
        mode="lines+markers+text", name="Cumulative (₹ Cr)",
        line=dict(color="#FF9800", width=2.5, dash="dash"),
        marker=dict(size=9, color="#FF9800"),
        text=[f"₹{v:.2f} Cr" for v in cumulative_cr],
        textposition="top center",
    ))
    fig_3yr.update_layout(
        **_layout("3-Year Cumulative Value (₹ Crore)", "₹ Crore", 380)
    )
    st.plotly_chart(fig_3yr, use_container_width=True)

with col_rgt:
    st.markdown("#### Break-Even Price Analysis")
    
    # Secondary Break-even against Primary
    sec_be = (Adj_Cost_Pri - (Conv_Pen_Sec)) / Req_Sec
    # Notch Break-even against Primary
    notch_be = (Adj_Cost_Pri - (Conv_Pen_Notch)) / Req_Notch

    st.markdown(kpi("Sec. Al Break-Even Price", f"₹{sec_be:,.0f}",
                    f"Current Sec: ₹{P_Sec_Price:,} | {'BELOW' if P_Sec_Price < sec_be else 'ABOVE'} break-even",
                    "kpi-card-green" if P_Sec_Price <= sec_be else "kpi-card-red"), unsafe_allow_html=True)
    
    st.markdown(kpi("Notch Bar Break-Even Price", f"₹{notch_be:,.0f}",
                    f"Current Notch: ₹{P_Notch_Price:,} | {'BELOW' if P_Notch_Price < notch_be else 'ABOVE'} break-even",
                    "kpi-card-green" if P_Notch_Price <= notch_be else "kpi-card-red"), unsafe_allow_html=True)
    
    st.markdown(kpi("Max Viable Penalty Limit", f"₹{(Adj_Cost_Pri - Raw_Cost_Sec) / Req_Sec:,.0f}",
                    f"Current Sec penalties must drop below this to justify ₹{P_Sec_Price:,}",
                    "kpi-card-amber"), unsafe_allow_html=True)


# ── SECTION 8: RECOMMENDATION ──
st.markdown('<div class="section-header">Final Recommendation</div>', unsafe_allow_html=True)

if best_commodity == "Primary Al Ingot":
    st.markdown(f"""
    <div style="background:#FFF3E0; border-left:6px solid #FF9800; padding:24px 32px; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.05);">
        <h2 style="color:#E65100; margin-top:0; font-size:28px;">🏆 Primary Aluminium Preferred</h2>
        <p style="font-size:16px; color:#EF6C00; line-height:1.6; margin-bottom:0;">
            <b>Cost Protection Value: ₹{abs(Annual_Savings_Cr):.2f} Crore</b><br>
            At current parameters, maintaining {Substitution_Pct*100:.0f}% of your consumption in <b>Primary Aluminium Ingot</b> 
            protects the meltshop from severe operational penalties associated with lower-grade alternatives. 
            The upfront price discounts of Secondary Ingot and Notch Bar fail to offset their massive VIU penalties 
            (such as high inclusion rejection risks, slag handling, and recovery instability).<br><br>
            <b>Action:</b> Do not substitute unless Secondary Al price drops below the break-even of <b>₹{sec_be:,.0f}/MT</b>.
        </p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"""
    <div style="background:#E8F5E9; border-left:6px solid #4CAF50; padding:24px 32px; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.05);">
        <h2 style="color:#1B5E20; margin-top:0; font-size:28px;">🏆 {best_commodity} Preferred</h2>
        <p style="font-size:16px; color:#2E7D32; line-height:1.6; margin-bottom:0;">
            <b>Projected Annual Savings: ₹{Annual_Savings_Cr:.2f} Crore</b><br>
            By shifting {Substitution_Pct*100:.0f}% of your baseline consumption to <b>{best_commodity}</b>, 
            you realize a net Value-in-Use advantage of <b>₹{Savings_Per_MT_Eff_Al:,.0f} per MT of Effective Aluminium</b>. 
            The market price discount of {best_commodity} is large enough to comfortably absorb the incurred operational penalties 
            (₹{Conv_Pen_Sec if best_commodity == 'Secondary Al Ingot' else Conv_Pen_Notch:,.0f} per MT Effective Al).
        </p>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown("""
<div style="text-align:center; color:#90A4AE; font-size:12px; padding:8px 0;">
  Aluminium VIU Dashboard &nbsp;|&nbsp; Primary vs Secondary vs Notch Bar &nbsp;|&nbsp; 
  All metallurgical formulas sourced from standardized Aluminium VIU Workbook.
</div>
""", unsafe_allow_html=True)