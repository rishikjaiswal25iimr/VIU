"""
COMBINED DASHBOARD – MC FeMn vs Mn Briquette
================================================
Tab 1: Value-in-Use (VIU) Dashboard
Tab 2: Substitution Solver (Linear Programming)

All formulas, calculations, limits, and optimization equations 
are sourced strictly from the original Excel logic and kept completely unmodified.
"""

from __future__ import annotations
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from scipy.optimize import linprog

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & THEME
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="VIU & Solver Dashboard",
    page_icon="⚗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colour palette
C_MCFEMN   = "#2196F3"   # blue  – MC FeMn
C_BRIQ     = "#4CAF50"   # green – Mn Briquette
C_DELTA    = "#FF9800"   # amber – delta / benefit
C_NEG      = "#F44336"   # red   – penalties / negative
C_BG       = "#FAFAFA"
C_TEXT     = "#333333"
C_GRID     = "#EEEEEE"

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

/* ---------- KPI cards ---------- */
.kpi-card {
    background: #FFFFFF;
    border-radius: 12px;
    padding: 18px 22px 14px 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    border-left: 5px solid #2196F3;
    margin-bottom: 8px;
}
.kpi-card-green  { border-left-color: #4CAF50; }
.kpi-card-amber  { border-left-color: #FF9800; }
.kpi-card-red    { border-left-color: #F44336; }
.kpi-card-purple { border-left-color: #9C27B0; }
.kpi-label { font-size: 12px; font-weight: 600; color: #78909C; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
.kpi-value { font-size: 26px; font-weight: 700; color: #1A237E; line-height: 1.15; }
.kpi-sub   { font-size: 12px; color: #90A4AE; margin-top: 3px; }

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
.solver-kpi-box {
    background: #FFFFFF; border-radius: 12px;
    padding: 18px 22px; border: 1px solid #E2E8F0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS: Plotly layout templates & KPIs
# ══════════════════════════════════════════════════════════════════════════════
def _layout_viu(title: str, y_title: str = "", height: int = 420) -> dict:
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

def _layout_solver(title: str, y_title: str = "", height: int = 380) -> dict:
    return dict(
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, sans-serif", size=12, color=C_TEXT),
        title=dict(text=title, font=dict(size=14, color="#1A237E"), x=0.01),
        xaxis=dict(showgrid=True, gridcolor=C_GRID, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=C_GRID, zeroline=False, title=y_title),
        hovermode="closest",
        height=height,
        margin=dict(l=50, r=20, t=40, b=40),
    )

def kpi(label: str, value: str, sub: str = "", colour: str = "") -> str:
    cls = f"kpi-card {colour}"
    return f"""
    <div class="{cls}">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{value}</div>
      <div class="kpi-sub">{sub}</div>
    </div>"""

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR – ALL INPUT PARAMETERS (Master source for both tabs)
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ⚙️ Dashboard Controls")
    st.divider()

    st.markdown("### A. Comparison Selection")
    comparison_selection = st.radio(
        "Select Analysis:",
        ["Not selected", "MC FeMn vs Mn Briquette"],
        index=1
    )
    
    if comparison_selection != "Not selected":
        st.divider()
        st.markdown("### B. Financial Parameters")
        P_MCFeMn_Price       = st.number_input("MC FeMn Price (₹/MT)",        value=130000, step=1000, min_value=50000, max_value=400000)
        P_Briq_Price         = st.number_input("Mn Briquette Price (₹/MT)",   value=175000, step=1000, min_value=50000, max_value=600000)
        P_Power_Tariff       = st.number_input("Power Tariff (₹/kWh)",        value=6.5,   step=0.1, min_value=1.0,   max_value=20.0, format="%.2f")
        P_Electrode_Cost     = st.number_input("Electrode Cost (₹/kg)",       value=240,   step=10,  min_value=50,    max_value=800)
        P_Steel_Value        = st.number_input("Steel Value (₹/MT)",          value=60000, step=1000, min_value=20000, max_value=200000)
        P_Margin_Steel       = st.number_input("Throughput Margin (₹/MT)",    value=2800,  step=100, min_value=500,   max_value=10000)
        P_LF_Retreatment_Cost= st.number_input("LF Re-treatment Cost (₹/heat)",value=15000, step=500, min_value=2000,  max_value=50000)
        P_RH_Corr_Cost       = st.number_input("RH Correction Cost (₹/heat)", value=2500,  step=100, min_value=500,   max_value=10000)
        P_Ladle_Reline_Cost  = st.number_input("Ladle Reline Cost (₹)",       value=1500000,step=50000,min_value=200000,max_value=5000000)
        P_Scrap_Price        = st.number_input("Scrap / Fe Credit (₹/MT)",    value=35000, step=500, min_value=5000,  max_value=80000)

        st.divider()
        st.markdown("### C. Technical Parameters")
        P_MCFeMn_Mn  = st.slider("MC FeMn Mn Content (%)",  60.0, 85.0, 70.0, 0.5) / 100
        P_Briq_Mn    = st.slider("Mn Briquette Mn Content (%)", 90.0, 100.0, 99.0, 0.1) / 100
        P_MCFeMn_Rec = st.slider("MC FeMn Recovery (%)",    70.0, 99.0, 85.0, 0.5) / 100
        P_Briq_Rec   = st.slider("Mn Briquette Recovery (%)", 80.0, 99.9, 95.0, 0.5) / 100
        P_MCFeMn_Fe  = st.slider("MC FeMn Fe Content (%)",  5.0,  35.0, 20.0, 0.5) / 100
        P_MCFeMn_C   = st.slider("MC FeMn Carbon (%)",      0.1,  2.5,  1.5,  0.1) / 100
        P_Briq_C     = st.slider("Mn Briquette Carbon (%)", 0.01, 0.5,  0.1,  0.01) / 100
        P_SpHeat_Steel  = st.slider("Steel Specific Heat (MJ/T/°C)", 0.5, 1.0, 0.75, 0.01)
        P_Chill_MCFeMn  = st.slider("MC FeMn Chill (°C/heat)", 1.0, 10.0, 5.0, 0.1)
        P_Chill_Briq    = st.slider("Briq Chill (°C/heat)", 0.5, 5.0, 1.0, 0.1)
        H2_Degas_Rate   = st.slider("H₂ Degas Rate (ppm/min)",    0.02, 0.10, 0.045, 0.005)

        st.divider()
        st.markdown("### D. Operational Parameters")
        P_Heat_Size  = st.slider("Heat Size (MT)",            100,  350,  190,  5)
        P_Cycle_Time = st.slider("LF Cycle Time (min)",        30,   90,   53,  1)
        P_Ladle_Life = st.slider("Ladle Life (heats)",         50,  200,  100,  5)
        P_Alloy_Target = st.number_input("Mn Addition Target (%)", value=0.4, step=0.01, min_value=0.1, max_value=2.0, format="%.2f")
        P_LF_Efficiency = st.slider("LF Efficiency (%)",       25.0, 80.0, 45.0, 1.0) / 100
        P_Arc_Duty      = st.slider("Arc Duty Cycle (%)",      30.0, 90.0, 60.0, 1.0) / 100
        P_Reheat_Rate   = st.slider("Reheat Rate (°C/min)",     2.0,  6.0,  3.5,  0.1)
        P_Graphite_Factor = st.slider("Electrode Wear (kg/kWh)", 0.002, 0.020, 0.010, 0.001)
        MCFeMn_Overdose    = st.slider("MC FeMn Overdose Buffer (%)",  0.5,  8.0,  5.0,  0.1) / 100
        Briq_Overdose      = st.slider("Mn Briq Overdose Buffer (%)",   0.1,  4.0,  1.5,  0.1) / 100
        MCFeMn_Rec_Var     = st.slider("MC FeMn Recovery Std-Dev (%)", 0.5,  8.0,  5.0,  0.1) / 100
        Briq_Rec_Var       = st.slider("Mn Briq Recovery Std-Dev (%)",  0.5,  4.0,  1.5,  0.1) / 100
        Reject_MCFeMn      = st.number_input("MC FeMn Rejection Rate", value=0.0002, format="%.5f", step=0.0001)
        Reject_Briq        = st.number_input("Mn Briq Rejection Rate", value=0.0000, format="%.5f", step=0.0001)
        Retreatment_MCFeMn = st.slider("MC FeMn Re-treatment Rate (%)",1.0,  10.0, 4.0,  0.1) / 100
        Retreatment_Briq   = st.slider("Mn Briq Re-treatment Rate (%)", 0.5,  5.0,  2.0,  0.1) / 100
        C_Corr_Freq_MCFeMn = st.slider("Carbon Correction Frequency", 0.02, 0.30, 0.10, 0.01)
        H2_Pickup_Briq     = st.slider("H₂ Pickup Briq (ppm)",         0.01, 0.20, 0.09, 0.01)
        P_Yield_Factor     = st.number_input("Yield Improvement Factor", value=0.0003, format="%.5f", step=0.0001)
        Refractory_Wear_Drop = st.slider("Refractory Wear Reduction (%)", 0.5, 8.0, 2.0, 0.5) / 100

        st.divider()
        st.markdown("### E. Realization Factors")
        R_Power       = st.slider("Power Realization",       0.50, 1.00, 0.90, 0.01)
        R_Electrode   = st.slider("Electrode Realization",   0.50, 1.00, 0.90, 0.01)
        R_Throughput  = st.slider("Throughput Realization",  0.10, 0.80, 0.25, 0.01)
        R_Stability   = st.slider("Stability Realization",   0.20, 1.00, 0.50, 0.01)
        R_Reblow      = st.slider("Reblow Realization",      0.30, 1.00, 0.50, 0.01)
        R_Cleanliness = st.slider("Cleanliness Realization", 0.10, 1.00, 1.00, 0.01)
        R_Yield       = st.slider("Yield Realization",       0.05, 0.50, 0.25, 0.01)
        R_Carbon      = st.slider("Carbon Corr. Realization",0.20, 1.00, 1.00, 0.01)
        R_Hydrogen    = st.slider("Hydrogen Penalty Realization", 0.20, 1.00, 0.50, 0.01)
        R_Refractory  = st.slider("Refractory Realization",  0.10, 1.00, 1.00, 0.01)

        st.divider()
        st.markdown("### F. Enterprise Savings")
        Briq_Consumption_FY = st.number_input("Consumption (MT)", value=24000, step=100, min_value=100, max_value=100000)
        Substitution_Pct    = st.slider("% Substitution", 0.0, 1.0, 0.05, 0.05)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN CONTENT GUARD
# ══════════════════════════════════════════════════════════════════════════════
if comparison_selection == "Not selected":
    st.info("Please select substitution combination from the sidebar to run the analysis.")
    st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# TABS SETUP
# ══════════════════════════════════════════════════════════════════════════════
tab1, tab2 = st.tabs(["⚗️ VIU Dashboard", "🧠 Substitution Solver"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: VIU DASHBOARD 
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    # --- CORE CALCULATIONS (EXACT EXCEL REPLICATION - COLUMN F LOGIC) ---
    
    # Calculate true mass balance for substitutions (Excel Power Calc Engine basis)
    Active_Mn_per_Heat = P_Heat_Size * (P_Alloy_Target / 100.0 * 1000.0)
    MCFeMn_per_Heat = Active_Mn_per_Heat / (P_MCFeMn_Mn * P_MCFeMn_Rec)
    Briq_per_Heat = Active_Mn_per_Heat / (P_Briq_Mn * P_Briq_Rec)
    
    Scale_Factor = 1000.0 / Briq_per_Heat  # Converts ₹/heat to ₹/MT Briquette
    kWh_MJ = 3.6
    
    # --- Power Saving (Rigorous Mass Balance Basis per MT Briquette) ---
    Delta_Temp_Rigorous = P_Chill_MCFeMn - P_Chill_Briq
    Energy_Saved_per_Heat = (P_Heat_Size * P_SpHeat_Steel * Delta_Temp_Rigorous) / (kWh_MJ * P_LF_Efficiency)
    Benefit_Power = Energy_Saved_per_Heat * P_Power_Tariff * R_Power * Scale_Factor
    
    # --- Electrode Saving ---
    Benefit_Electrode = Energy_Saved_per_Heat * P_Graphite_Factor * P_Electrode_Cost * R_Electrode * Scale_Factor
    
    # --- Throughput Gain ---
    Time_Saved_Min = Delta_Temp_Rigorous / P_Reheat_Rate
    Benefit_Throughput = (Time_Saved_Min / P_Cycle_Time) * P_Heat_Size * P_Margin_Steel * R_Throughput * Scale_Factor
    
    # --- Recovery Stability ---
    Cost_MC_Overdose = MCFeMn_per_Heat * MCFeMn_Overdose * (P_MCFeMn_Price / 1000.0)
    Cost_Briq_Overdose = Briq_per_Heat * Briq_Overdose * (P_Briq_Price / 1000.0)
    Benefit_Stability = (Cost_MC_Overdose - Cost_Briq_Overdose) * R_Stability * Scale_Factor
    
    # --- Re-treatment Reduction ---
    Benefit_Retreatment = (Retreatment_MCFeMn - Retreatment_Briq) * P_LF_Retreatment_Cost * R_Reblow * Scale_Factor
    
    # --- Cleanliness ---
    Benefit_Cleanliness = (Reject_MCFeMn - Reject_Briq) * P_Steel_Value * P_Heat_Size * R_Cleanliness * Scale_Factor
    
    # --- Yield Improvement ---
    Benefit_Yield = P_Yield_Factor * P_Steel_Value * P_Heat_Size * R_Yield * Scale_Factor
    
    # --- Carbon Correction Avoidance ---
    Benefit_Carbon = C_Corr_Freq_MCFeMn * P_RH_Corr_Cost * R_Carbon * Scale_Factor
    
    # --- Hydrogen Penalty ---
    Benefit_Hydrogen = -(H2_Pickup_Briq / H2_Degas_Rate) * P_RH_Corr_Cost * R_Hydrogen * Scale_Factor
    
    # --- Refractory Life ---
    Benefit_Refractory = (P_Ladle_Reline_Cost / P_Ladle_Life) * Refractory_Wear_Drop * R_Refractory * Scale_Factor
    
    # --- Gross Operational Credits ---
    Gross_Op_Benefits = (
        Benefit_Power + Benefit_Electrode + Benefit_Throughput +
        Benefit_Stability + Benefit_Retreatment + Benefit_Cleanliness +
        Benefit_Yield + Benefit_Carbon + Benefit_Hydrogen + Benefit_Refractory
    )
    
    # ══ VIU SUMMARY EXACT LOGIC ═══════════════════════════════════════════════════
    Alloy_Per_MT_Mn_MC   = 1.0 / (P_MCFeMn_Mn * P_MCFeMn_Rec)
    Alloy_Per_MT_Mn_Briq = 1.0 / (P_Briq_Mn   * P_Briq_Rec)
    
    Cost_Per_Mn_MC   = Alloy_Per_MT_Mn_MC   * P_MCFeMn_Price
    Cost_Per_Mn_Briq = Alloy_Per_MT_Mn_Briq * P_Briq_Price
    Iron_Credit_MC   = P_MCFeMn_Fe * P_Scrap_Price
    
    # Direct cost delta is the normalized Cost per Active Mn difference
    Cost_Per_Mn_Delta = Cost_Per_Mn_Briq - Cost_Per_Mn_MC
    
    # Excel calculates Total_Op_Credits by deducting the lost Iron Credit as a penalty for Briquette
    Lost_Iron_Credit_per_MT_Briq = Iron_Credit_MC
    
    Total_Op_Credits = Gross_Op_Benefits - Lost_Iron_Credit_per_MT_Briq
    
    # Net Value in Use Advantage = Total VIU Credits - Direct Cost Delta
    Savings_Per_MT = Total_Op_Credits - Cost_Per_Mn_Delta
    
    # --- New Enterprise Savings Formula ---
    Annual_Savings_Rs = Briq_Consumption_FY * Substitution_Pct * Savings_Per_MT
    Annual_Savings_Cr = Annual_Savings_Rs / 1e7

    # ── SECTION 1: DASHBOARD HEADER ──
    st.markdown("""
    <div style="background: linear-gradient(135deg,#1A237E 0%,#1565C0 60%,#0277BD 100%);
                padding:22px 28px 18px 28px; border-radius:14px; margin-bottom:20px;
                box-shadow:0 4px 24px rgba(26,35,126,0.25);">
      <h1 style="color:#FFFFFF;margin:0;font-size:26px;font-weight:800;letter-spacing:0.02em;">
        ⚗️ VIU Dashboard — MC FeMn vs Mn Briquette
      </h1>
      <p style="color:#90CAF9;margin:6px 0 0 0;font-size:13px;">
        Value-In-Use Economic Analysis &nbsp;|&nbsp; Medium-Carbon Ferromanganese (70% Mn) 
        vs Manganese Metal Briquette (99% Mn)
      </p>
    </div>
    """, unsafe_allow_html=True)
    
    # ── SECTION 2: TOP KPI CARDS ──
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    with c1:
        st.markdown(kpi("MC FeMn Price", f"₹{P_MCFeMn_Price:,.0f}", "per MT alloy", ""), unsafe_allow_html=True)
    with c2:
        st.markdown(kpi("Mn Briquette Price", f"₹{P_Briq_Price:,.0f}", "per MT alloy", "kpi-card-green"), unsafe_allow_html=True)
    with c3:
        col_gap = "kpi-card-green" if Cost_Per_Mn_Delta <= 0 else "kpi-card-amber"
        st.markdown(kpi("Mn Cost Gap", f"₹{Cost_Per_Mn_Delta:,.0f}", "per MT Active Mn", col_gap), unsafe_allow_html=True)
    with c4:
        st.markdown(kpi("Total VIU Credits", f"₹{Total_Op_Credits:,.0f}", "net benefit / MT alloy", "kpi-card-green"), unsafe_allow_html=True)
    with c5:
        col = "kpi-card-green" if Savings_Per_MT > 0 else "kpi-card-red"
        lbl = "Net Savings / MT Alloy"
        st.markdown(kpi(lbl, f"₹{Savings_Per_MT:+,.0f}", "Briquette advantage", col), unsafe_allow_html=True)
    with c6:
        col_yr = "kpi-card-green" if Annual_Savings_Cr > 0 else "kpi-card-red"
        st.markdown(kpi("Annual Savings FY26", f"₹{abs(Annual_Savings_Cr):.2f} Cr", f"@ {Substitution_Pct*100:.0f}% Substitution", col_yr), unsafe_allow_html=True)
    
    # ── SECTION 3: VIU SUMMARY ──
    st.markdown('<div class="section-header">VIU Economic Synthesis</div>', unsafe_allow_html=True)
    col_l, col_r = st.columns([1, 1])
    with col_l:
        st.markdown("#### Cost per Active Manganese (₹/MT Mn)")
        km1, km2 = st.columns(2)
        with km1:
            st.markdown(kpi("MC FeMn Cost/MT Mn", f"₹{Cost_Per_Mn_MC:,.0f}", f"@ {P_MCFeMn_Mn*100:.1f}% Mn × {P_MCFeMn_Rec*100:.0f}% rec", ""), unsafe_allow_html=True)
        with km2:
            st.markdown(kpi("Mn Briq Cost/MT Mn", f"₹{Cost_Per_Mn_Briq:,.0f}", f"@ {P_Briq_Mn*100:.1f}% Mn × {P_Briq_Rec*100:.0f}% rec", "kpi-card-green"), unsafe_allow_html=True)
    
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### VIU Components")
        data_summary = {
            "Component": [
                "Cost per MT Active Mn",
                "Direct Cost Delta (Briquette vs MC)",
                "Gross Operational Credits",
                "Lost Iron Credit Penalty",
                "Total Net Credits",
                "Net VIU Advantage (Credits − Delta)",
            ],
            "MC FeMn (₹/MT)": [
                f"₹{Cost_Per_Mn_MC:,.0f}", "—",
                "—", "—", "—", "—",
            ],
            "Mn Briquette (₹/MT)": [
                f"₹{Cost_Per_Mn_Briq:,.0f}", f"₹{Cost_Per_Mn_Delta:,.0f}",
                f"₹{Gross_Op_Benefits:,.0f}", f"-₹{Lost_Iron_Credit_per_MT_Briq:,.0f}",
                f"₹{Total_Op_Credits:,.0f}", f"₹{Savings_Per_MT:+,.0f}",
            ],
        }
        df_sum = pd.DataFrame(data_summary).set_index("Component")
        st.dataframe(df_sum, use_container_width=True)
    
        # Verdict
        if Savings_Per_MT > 0:
            st.markdown(f"""
            <div class="success-box">
            ✅ <b>Mn Briquette offers a net advantage of ₹{Savings_Per_MT:,.0f}/MT alloy.</b><br>
            Favorable active Mn pricing coupled with operational credits makes Briquettes the economically superior choice.
            </div>""", unsafe_allow_html=True)
        elif Savings_Per_MT < -2000:
            st.markdown(f"""
            <div class="warn-box">
            ⚠️ <b>MC FeMn is currently more cost-effective by ₹{abs(Savings_Per_MT):,.0f}/MT.</b><br>
            At current prices and parameters, the MC FeMn price advantage outweighs Briquette operational credits.
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="info-box">
            ℹ️ <b>Near economic parity.</b> Net VIU: ₹{Savings_Per_MT:+,.0f}/MT alloy.
            Consider plant-specific factors and grade-specific requirements.
            </div>""", unsafe_allow_html=True)
    
    with col_r:
        # --- VIU Donut: Credit composition ---
        benefit_names = [
            "Power Saving", "Electrode Saving", "Throughput Gain",
            "Recovery Stability", "Re-treatment Reduction",
            "Cleanliness Benefit", "Yield Improvement",
            "Carbon Avoidance", "Refractory Benefit",
        ]
        benefit_values = [
            Benefit_Power, Benefit_Electrode, Benefit_Throughput,
            Benefit_Stability, Benefit_Retreatment, Benefit_Cleanliness,
            Benefit_Yield, Benefit_Carbon, Benefit_Refractory,
        ]
        pos_names  = [n for n, v in zip(benefit_names, benefit_values) if v > 0]
        pos_values = [v for v in benefit_values if v > 0]
    
        colours_donut = [
            "#2196F3", "#1565C0", "#42A5F5",
            "#4CAF50", "#66BB6A", "#81C784",
            "#FF9800", "#FFA726", "#FFC107",
        ]
    
        fig_donut = go.Figure(data=[go.Pie(
            labels=pos_names, values=pos_values,
            hole=0.52,
            marker=dict(colors=colours_donut[:len(pos_names)], line=dict(color="#fff", width=2)),
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}/MT<extra></extra>",
        )])
        fig_donut.add_annotation(
            text=f"<b>₹{Gross_Op_Benefits:,.0f}</b><br><span style='font-size:10px'>Gross Credits</span>",
            x=0.5, y=0.5, font_size=14, showarrow=False,
        )
        fig_donut.update_layout(
            title="Gross Operational Credit Composition (₹/MT Alloy)",
            template="plotly_white", height=420,
            margin=dict(l=20, r=20, t=55, b=20),
            legend=dict(font=dict(size=11)),
        )
        st.plotly_chart(fig_donut, use_container_width=True)
    
        # Summary KPIs
        k1, k2 = st.columns(2)
        with k1:
            st.markdown(kpi("Alloy/MT Active Mn (MC)", f"{Alloy_Per_MT_Mn_MC:.3f} MT", "MC FeMn required", ""), unsafe_allow_html=True)
        with k2:
            st.markdown(kpi("Alloy/MT Active Mn (Briq)", f"{Alloy_Per_MT_Mn_Briq:.3f} MT", "Mn Briquette required", "kpi-card-green"), unsafe_allow_html=True)
    
    # ── SECTION 4: BENEFIT BREAKDOWN ──
    st.markdown('<div class="section-header">Detailed Benefit Breakdown</div>', unsafe_allow_html=True)
    
    all_benefit_names = [
        "Power Saving", "Electrode Saving", "Throughput Gain",
        "Recovery Stability", "Re-treatment Reduction",
        "Cleanliness Benefit", "Yield Improvement",
        "Carbon Avoidance", "Hydrogen Penalty",
        "Refractory Benefit",
    ]
    all_benefit_values = [
        Benefit_Power, Benefit_Electrode, Benefit_Throughput,
        Benefit_Stability, Benefit_Retreatment, Benefit_Cleanliness,
        Benefit_Yield, Benefit_Carbon, Benefit_Hydrogen, Benefit_Refractory,
    ]
    all_benefit_basis = [
        f"ΔT={Delta_Temp_Rigorous:.2f}°C/heat, {P_LF_Efficiency*100:.0f}% LF eff, {R_Power*100:.0f}% real.",
        f"E_saved={Energy_Saved_per_Heat:.1f} kWh/heat, {P_Graphite_Factor*1000:.0f}g/kWh, {R_Electrode*100:.0f}% real.",
        f"Time saved={Time_Saved_Min:.2f} min/heat, {R_Throughput*100:.0f}% real.",
        f"Overdose cost Δ=₹{Cost_MC_Overdose - Cost_Briq_Overdose:,.0f}/heat, {R_Stability*100:.0f}% real.",
        f"Miss Δ={(Retreatment_MCFeMn-Retreatment_Briq)*100:.1f}%, {R_Reblow*100:.0f}% real.",
        f"Reject Δ={(Reject_MCFeMn-Reject_Briq)*100:.4f}%, {R_Cleanliness*100:.0f}% real.",
        f"Yield factor={P_Yield_Factor*1e6:.1f}ppm, {R_Yield*100:.0f}% real.",
        f"C-corr freq={C_Corr_Freq_MCFeMn*100:.0f}%, ₹{P_RH_Corr_Cost}/heat, {R_Carbon*100:.0f}% real.",
        f"H₂ pickup={H2_Pickup_Briq:.3f}ppm, degas={H2_Degas_Rate:.3f}ppm/min.",
        f"Wear drop={Refractory_Wear_Drop*100:.1f}%, ladle cost=₹{P_Ladle_Reline_Cost:,}.",
    ]
    
    col_chart, col_table = st.columns([3, 2])
    
    with col_chart:
        bar_colors = [C_DELTA if v >= 0 else C_NEG for v in all_benefit_values]
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=all_benefit_names[::-1],
            x=all_benefit_values[::-1],
            orientation="h",
            marker=dict(color=bar_colors[::-1], line=dict(color="white", width=1)),
            text=[f"₹{v:+,.0f}" for v in all_benefit_values[::-1]],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>₹%{x:,.0f}/MT alloy<extra></extra>",
        ))
        fig_bar.add_vline(x=0, line_dash="solid", line_color="#333", line_width=1.5)
        fig_bar.update_layout(
            **_layout_viu("Gross Benefit Contribution per MT Alloy (₹/MT)", "₹/MT Alloy", 460)
        )
        fig_bar.update_layout(xaxis=dict(showgrid=True, gridcolor=C_GRID, zeroline=False))
        st.plotly_chart(fig_bar, use_container_width=True)
    
    with col_table:
        df_breakdown = pd.DataFrame({
            "Benefit Component": all_benefit_names,
            "₹/MT Alloy": [f"₹{v:+,.0f}" for v in all_benefit_values],
            "Basis & Assumptions": all_benefit_basis,
        }).set_index("Benefit Component")
    
        def color_values(val):
            num = float(val.replace("₹", "").replace(",", "").replace("+", ""))
            if num > 0:
                return "color: #1B5E20; font-weight: 600"
            elif num < 0:
                return "color: #B71C1C; font-weight: 600"
            return ""
    
        st.dataframe(
            df_breakdown.style.map(color_values, subset=["₹/MT Alloy"]),
            use_container_width=True, height=460,
        )
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Heatmap of benefits by realization factor sensitivity
    st.markdown("#### Benefit Sensitivity Heatmap (₹/MT at varying Realization Factors)")
    real_range = np.arange(0.1, 1.05, 0.1)
    heat_names = [
        "Power Saving", "Electrode Saving", "Throughput Gain",
        "Recovery Stability", "Re-treatment Reduction",
        "Cleanliness", "Yield", "Carbon Avoidance",
    ]
    base_heat_values = [
        Energy_Saved_per_Heat * P_Power_Tariff * Scale_Factor,
        Energy_Saved_per_Heat * P_Graphite_Factor * P_Electrode_Cost * Scale_Factor,
        (Time_Saved_Min / P_Cycle_Time) * P_Heat_Size * P_Margin_Steel * Scale_Factor,
        (Cost_MC_Overdose - Cost_Briq_Overdose) * Scale_Factor,
        (Retreatment_MCFeMn - Retreatment_Briq) * P_LF_Retreatment_Cost * Scale_Factor,
        (Reject_MCFeMn - Reject_Briq) * P_Steel_Value * P_Heat_Size * Scale_Factor,
        P_Yield_Factor * P_Steel_Value * P_Heat_Size * Scale_Factor,
        C_Corr_Freq_MCFeMn * P_RH_Corr_Cost * Scale_Factor,
    ]
    heat_matrix = np.array([[bv * r for r in real_range] for bv in base_heat_values])
    
    fig_heat = go.Figure(go.Heatmap(
        z=heat_matrix,
        x=[f"{r*100:.0f}%" for r in real_range],
        y=heat_names,
        colorscale="Blues",
        text=np.round(heat_matrix, 0).astype(int),
        texttemplate="₹%{text}",
        textfont=dict(size=10),
        hovertemplate="<b>%{y}</b><br>Realization: %{x}<br>₹%{z:,.0f}/MT<extra></extra>",
    ))
    fig_heat.update_layout(
        **_layout_viu("VIU Benefit Heatmap — Realization Factor Sensitivity", "", 380)
    )
    fig_heat.update_layout(xaxis_title="Realization Factor", yaxis_title="")
    st.plotly_chart(fig_heat, use_container_width=True)
    
    # ── SECTION 5: WATERFALL ANALYSIS ──
    st.markdown('<div class="section-header">VIU Waterfall Analysis</div>', unsafe_allow_html=True)
    
    wf_labels = [
        "MC FeMn Active Mn Cost", "Power Saving", "Electrode Saving",
        "Throughput Gain", "Recovery Stability", "Re-treatment Reduction",
        "Cleanliness", "Yield", "Carbon Avoidance", "Hydrogen Penalty",
        "Refractory Life", "Lost Iron Credit", "Mn Briquette Active Mn Cost",
    ]
    wf_values = [
        Cost_Per_Mn_MC, Benefit_Power, Benefit_Electrode,
        Benefit_Throughput, Benefit_Stability, Benefit_Retreatment,
        Benefit_Cleanliness, Benefit_Yield, Benefit_Carbon,
        Benefit_Hydrogen, Benefit_Refractory, -Lost_Iron_Credit_per_MT_Briq,
        0, # total placeholder
    ]
    
    measures = ["absolute"] + ["relative"] * (len(wf_labels) - 2) + ["total"]
    wf_text = [f"₹{abs(v):,.0f}" for v in wf_values[:-1]] + [f"₹{Cost_Per_Mn_Briq:,.0f}"]
    wf_values_display = wf_values[:-1] + [Cost_Per_Mn_Briq]
    
    wf_colors = ["#1A237E"]
    for v in wf_values[1:-1]:
        wf_colors.append(C_DELTA if v > 0 else C_NEG)
    wf_colors.append("#4CAF50")
    
    fig_wf = go.Figure(go.Waterfall(
        name="VIU Waterfall", orientation="v", measure=measures,
        x=wf_labels, y=wf_values_display, text=wf_text, textposition="outside",
        connector=dict(line=dict(color="#BDBDBD", width=1.5, dash="dot")),
        increasing=dict(marker=dict(color=C_DELTA)),
        decreasing=dict(marker=dict(color=C_NEG)),
        totals=dict(marker=dict(color="#4CAF50" if Cost_Per_Mn_Briq <= Cost_Per_Mn_MC + Total_Op_Credits else C_NEG)),
        hovertemplate="<b>%{x}</b><br>₹%{y:,.0f}<extra></extra>",
    ))
    fig_wf.add_hline(
        y=Cost_Per_Mn_Briq, line_dash="dash", line_color="#4CAF50", line_width=1.5,
        annotation_text=f"Mn Briq Cost/MT Mn ₹{Cost_Per_Mn_Briq:,.0f}", annotation_position="right",
    )
    fig_wf.update_layout(
        **_layout_viu("VIU Waterfall: Active Mn Cost & Operational Adjustments (₹/MT)", "₹/MT", 520)
    )
    fig_wf.update_layout(showlegend=False, xaxis_tickangle=-30)
    st.plotly_chart(fig_wf, use_container_width=True)
    
    st.markdown("""
    <div class="info-box">
    <b>How to read this waterfall:</b> Visualizes the synthesis mapping the Base Cost per MT Active Mn of MC FeMn, adding the operational 
    advantage benefits (Power, Electrode, Throughput, etc.) as credits against the Mn Briquette target price. 
    The Iron Credit is applied as a penalty deduction (because Mn Briquettes lack the free iron found in MC FeMn). 
    The final bar is the market cost per MT of Active Mn for Mn Briquettes. If the total height of MC FeMn + Benefits - Penalties 
    exceeds the Mn Briquette bar, Briquettes are the more cost-effective choice.
    </div>
    """, unsafe_allow_html=True)
    
    # ── SECTION 6: COST COMPARISON ──
    st.markdown('<div class="section-header">Cost Comparison & Sensitivity Analysis</div>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    
    with col_a:
        fig_stack = go.Figure()
        categories = ["MC FeMn", "Mn Briquette"]
    
        fig_stack.add_trace(go.Bar(
            name="Cost per MT Active Mn", x=categories, y=[Cost_Per_Mn_MC, Cost_Per_Mn_Briq],
            marker_color=[C_MCFEMN, C_BRIQ], text=[f"₹{Cost_Per_Mn_MC:,.0f}", f"₹{Cost_Per_Mn_Briq:,.0f}"],
            textposition="inside",
        ))
        fig_stack.add_trace(go.Bar(
            name="Gross Operational Credits (deduct)", x=categories, y=[0, -Gross_Op_Benefits],
            marker_color=["rgba(0,0,0,0)", "#FFC107"], text=["", f"-₹{Gross_Op_Benefits:,.0f}"],
            textposition="inside",
        ))
        fig_stack.add_trace(go.Bar(
            name="Lost Iron Credit Penalty (add)", x=categories, y=[0, Lost_Iron_Credit_per_MT_Briq],
            marker_color=["rgba(0,0,0,0)", "#FF7043"], text=["", f"+₹{Lost_Iron_Credit_per_MT_Briq:,.0f}"],
            textposition="inside",
        ))
        fig_stack.update_layout(
            barmode="relative", **_layout_viu("Effective Cost Components (₹/MT Active Mn)", "₹/MT", 420),
        )
        st.plotly_chart(fig_stack, use_container_width=True)
    
    with col_b:
        briq_prices  = np.linspace(P_MCFeMn_Price * 0.8, P_MCFeMn_Price * 2.5, 80)
        cost_mn_briqs = (1.0 / (P_Briq_Mn * P_Briq_Rec)) * briq_prices
        net_viuss   = Total_Op_Credits - (cost_mn_briqs - Cost_Per_Mn_MC)
        breakeven   = (Cost_Per_Mn_MC + Total_Op_Credits) * (P_Briq_Mn * P_Briq_Rec)
    
        fig_sens = go.Figure()
        fig_sens.add_trace(go.Scatter(
            x=briq_prices, y=net_viuss, mode="lines", name="Net VIU Advantage",
            line=dict(color=C_DELTA, width=3), fill="tozeroy", fillcolor="rgba(76,175,80,0.1)",
            hovertemplate="Briquette Price: ₹%{x:,.0f}<br>Net Advantage: ₹%{y:,.0f}/MT<extra></extra>",
        ))
        fig_sens.add_hline(y=0, line_dash="dash", line_color="#333", line_width=1.5)
        fig_sens.add_vline(x=P_Briq_Price, line_dash="dot", line_color=C_BRIQ, line_width=2,
                           annotation_text=f"Current ₹{P_Briq_Price:,}", annotation_position="top right")
        fig_sens.add_vline(x=breakeven, line_dash="dot", line_color=C_NEG, line_width=2,
                           annotation_text=f"Break-even ₹{breakeven:,.0f}", annotation_position="top left")
        fig_sens.update_layout(
            **_layout_viu("Mn Briquette Price Sensitivity – Net VIU Advantage (₹/MT)", "Net Advantage (₹/MT)", 420)
        )
        st.plotly_chart(fig_sens, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_c, col_d = st.columns(2)
    
    with col_c:
        mc_prices   = np.linspace(P_Briq_Price * 0.3, P_Briq_Price * 1.2, 80)
        cost_mn_mcs = (1.0 / (P_MCFeMn_Mn * P_MCFeMn_Rec)) * mc_prices
        net_mc_sens = Total_Op_Credits - (Cost_Per_Mn_Briq - cost_mn_mcs)
        
        fig_mc_sens = go.Figure()
        fig_mc_sens.add_trace(go.Scatter(
            x=mc_prices, y=net_mc_sens, mode="lines", name="Net VIU (varying MC FeMn price)",
            line=dict(color=C_MCFEMN, width=3), fill="tozeroy", fillcolor="rgba(33,150,243,0.1)",
            hovertemplate="MC FeMn: ₹%{x:,.0f}<br>Net Advantage: ₹%{y:,.0f}/MT<extra></extra>",
        ))
        fig_mc_sens.add_hline(y=0, line_dash="dash", line_color="#333", line_width=1.5)
        fig_mc_sens.add_vline(x=P_MCFeMn_Price, line_dash="dot", line_color=C_MCFEMN, line_width=2,
                              annotation_text=f"Current ₹{P_MCFeMn_Price:,}", annotation_position="top right")
        fig_mc_sens.update_layout(
            **_layout_viu("MC FeMn Price Sensitivity – Net VIU Advantage (₹/MT)", "Net Advantage (₹/MT)", 380)
        )
        st.plotly_chart(fig_mc_sens, use_container_width=True)
    
    with col_d:
        tornado_names  = ["Power Saving", "Electrode Saving", "Throughput Gain",
                          "Recovery Stability", "Re-treatment", "Cleanliness",
                          "Carbon Avoidance", "Refractory"]
        tornado_base   = [Benefit_Power, Benefit_Electrode, Benefit_Throughput,
                          Benefit_Stability, Benefit_Retreatment, Benefit_Cleanliness,
                          Benefit_Carbon, Benefit_Refractory]
        tornado_low    = [v * 0.80 for v in tornado_base]
        tornado_high   = [v * 1.20 for v in tornado_base]
    
        fig_tornado = go.Figure()
        fig_tornado.add_trace(go.Bar(
            y=tornado_names[::-1], x=[h - b for h, b in zip(tornado_high[::-1], tornado_base[::-1])],
            orientation="h", name="+20%", marker_color=C_DELTA, base=[b for b in tornado_base[::-1]],
        ))
        fig_tornado.add_trace(go.Bar(
            y=tornado_names[::-1], x=[l - b for l, b in zip(tornado_low[::-1], tornado_base[::-1])],
            orientation="h", name="−20%", marker_color="#EF9A9A", base=[b for b in tornado_base[::-1]],
        ))
        fig_tornado.update_layout(
            barmode="overlay", **_layout_viu("Sensitivity Tornado (±20% Realization)", "₹/MT Alloy", 380),
        )
        st.plotly_chart(fig_tornado, use_container_width=True)
    
    st.markdown("#### Side-by-Side Cost per Active Manganese Summary")
    df_cmp = pd.DataFrame({
        "Metric": [
            "Market Price (₹/MT alloy)", "Active Mn Content (%)", "Mn Recovery (%)",
            "Effective Mn Efficiency (%)", "Alloy Needed per MT Active Mn (MT)",
            "Raw Cost per MT Active Mn (₹)", "Gross Operational Credits (₹/MT alloy)",
            "Lost Iron Credit Penalty (₹/MT alloy)", "Net Adjusted Cost per MT Active Mn (₹)",
        ],
        "MC FeMn": [
            f"₹{P_MCFeMn_Price:,}", f"{P_MCFeMn_Mn*100:.1f}%", f"{P_MCFeMn_Rec*100:.1f}%",
            f"{P_MCFeMn_Mn*P_MCFeMn_Rec*100:.1f}%", f"{Alloy_Per_MT_Mn_MC:.3f} MT",
            f"₹{Cost_Per_Mn_MC:,.0f}", "—", "—", f"₹{Cost_Per_Mn_MC:,.0f}",
        ],
        "Mn Briquette": [
            f"₹{P_Briq_Price:,}", f"{P_Briq_Mn*100:.1f}%", f"{P_Briq_Rec*100:.1f}%",
            f"{P_Briq_Mn*P_Briq_Rec*100:.1f}%", f"{Alloy_Per_MT_Mn_Briq:.3f} MT",
            f"₹{Cost_Per_Mn_Briq:,.0f}", f"₹{Gross_Op_Benefits:,.0f}",
            f"₹{Lost_Iron_Credit_per_MT_Briq:,.0f}", f"₹{Cost_Per_Mn_Briq - Total_Op_Credits:,.0f}",
        ],
    }).set_index("Metric")
    st.dataframe(df_cmp, use_container_width=True)
    
    # ── SECTION 7: ENTERPRISE SAVINGS ──
    st.markdown('<div class="section-header">Enterprise Savings Calculator</div>', unsafe_allow_html=True)
    
    s1, s2, s3, s4 = st.columns(4)
    with s1:
        st.markdown(kpi("Substituted Volume", f"{Briq_Consumption_FY * Substitution_Pct:,.0f} MT", f"at {Substitution_Pct*100:.0f}% substitution", ""), unsafe_allow_html=True)
    with s2:
        st.markdown(kpi("Savings / MT Alloy", f"₹{abs(Savings_Per_MT):,.0f}", "Magnitude of net advantage", "kpi-card-green" if Savings_Per_MT > 0 else "kpi-card-amber"), unsafe_allow_html=True)
    with s3:
        abs_savings_yr = abs(Annual_Savings_Cr)
        st.markdown(kpi("Annual Savings FY26", f"₹{abs_savings_yr:.2f} Cr", "at stated volume", "kpi-card-green" if Savings_Per_MT > 0 else "kpi-card-amber"), unsafe_allow_html=True)
    with s4:
        monthly = Annual_Savings_Cr * 1e7 / 12 / 1e5
        st.markdown(kpi("Monthly Savings", f"₹{abs(monthly):.1f} L", "per month average", "kpi-card-purple"), unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    col_lft, col_rgt = st.columns([2, 1])
    
    with col_lft:
        vol_range = np.arange(1000, Briq_Consumption_FY * 2.5, 500)
        savings_cr = (Savings_Per_MT * vol_range * Substitution_Pct) / 1e7
    
        fig_sav = go.Figure()
        fig_sav.add_trace(go.Scatter(
            x=vol_range, y=savings_cr, mode="lines", name="Annual Savings (₹ Cr)",
            line=dict(color=C_DELTA if Savings_Per_MT > 0 else C_NEG, width=3),
            fill="tozeroy", fillcolor="rgba(76,175,80,0.12)" if Savings_Per_MT > 0 else "rgba(244,67,54,0.12)",
            hovertemplate="Consumption: %{x:,.0f} MT<br>Savings: ₹%{y:.2f} Cr<extra></extra>",
        ))
        fig_sav.add_vline(
            x=Briq_Consumption_FY, line_dash="dash", line_color="#1A237E", line_width=2,
            annotation_text=f"Total: {Briq_Consumption_FY:,} MT → ₹{Annual_Savings_Cr:.2f} Cr (@ {Substitution_Pct*100:.0f}% Sub)",
            annotation_position="top right",
        )
        fig_sav.add_hline(y=0, line_dash="solid", line_color="#333", line_width=1.5)
        fig_sav.update_layout(
            **_layout_viu(f"Enterprise Savings vs Total Consumption Volume (at {Substitution_Pct*100:.0f}% Sub)", "Savings (₹ Crore)", 400)
        )
        st.plotly_chart(fig_sav, use_container_width=True)
    
        st.markdown(f"#### 3-Year Savings Projection (5% annual price escalation)")
        years = ["FY 2026", "FY 2027", "FY 2028"]
        escalation = [1.0, 1.05, 1.1025]
        proj_savings = [Annual_Savings_Cr * e for e in escalation]
        cumulative_cr = np.cumsum(proj_savings)
    
        fig_3yr = go.Figure()
        fig_3yr.add_trace(go.Bar(
            x=years, y=proj_savings, name="Annual Savings (₹ Cr)",
            marker_color=[C_DELTA if s > 0 else C_NEG for s in proj_savings],
            text=[f"₹{v:.2f} Cr" for v in proj_savings], textposition="outside",
        ))
        fig_3yr.add_trace(go.Scatter(
            x=years, y=cumulative_cr, mode="lines+markers+text", name="Cumulative (₹ Cr)",
            line=dict(color="#9C27B0", width=2.5, dash="dash"),
            marker=dict(size=9, color="#9C27B0"), text=[f"₹{v:.2f} Cr" for v in cumulative_cr],
            textposition="top center",
        ))
        fig_3yr.update_layout(
            **_layout_viu("3-Year Enterprise Savings Projection (₹ Crore)", "₹ Crore", 380)
        )
        st.plotly_chart(fig_3yr, use_container_width=True)
    
    with col_rgt:
        st.markdown("#### Per-Benefit Annual Savings (₹ Cr)")
        benefits_annual = {
            n: (v * Briq_Consumption_FY * Substitution_Pct) / 1e7
            for n, v in zip(all_benefit_names, all_benefit_values)
        }
        df_bens = pd.DataFrame({
            "Benefit": list(benefits_annual.keys()),
            "₹ Crore / Year": [round(v, 3) for v in benefits_annual.values()],
        }).sort_values("₹ Crore / Year", ascending=False).set_index("Benefit")
    
        def style_ben(val):
            return "color:#1B5E20;font-weight:600" if val > 0 else "color:#B71C1C;font-weight:600"
    
        st.dataframe(
            df_bens.style.map(style_ben, subset=["₹ Crore / Year"]),
            use_container_width=True, height=350,
        )
    
        st.markdown("#### Savings Components Sunburst")
        pos_bens  = [(n, (v * Briq_Consumption_FY * Substitution_Pct) / 1e7) for n, v in zip(all_benefit_names, all_benefit_values) if v > 0]
        sun_labels = ["Gross VIU Credits"] + [p[0] for p in pos_bens]
        sun_parents = [""] + ["Gross VIU Credits"] * len(pos_bens)
        sun_values = [sum(p[1] for p in pos_bens)] + [p[1] for p in pos_bens]
    
        fig_sun = go.Figure(go.Sunburst(
            labels=sun_labels, parents=sun_parents, values=sun_values,
            branchvalues="total", hovertemplate="<b>%{label}</b><br>₹%{value:.3f} Cr<extra></extra>",
            marker=dict(colors=["#1A237E"] + colours_donut[:len(pos_bens)]),
        ))
        fig_sun.update_layout(
            title="Savings Sunburst (₹ Cr)", template="plotly_white", height=380,
            margin=dict(l=5, r=5, t=40, b=5),
        )
        st.plotly_chart(fig_sun, use_container_width=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Break-Even Price Analysis")
    be1, be2, be3 = st.columns(3)
    
    briq_eff = P_Briq_Mn * P_Briq_Rec
    mc_eff = P_MCFeMn_Mn * P_MCFeMn_Rec
    
    briq_breakeven_price = (Cost_Per_Mn_MC + Total_Op_Credits) * briq_eff
    mc_breakeven_price  = (Cost_Per_Mn_Briq - Total_Op_Credits) * mc_eff
    min_credits_needed  = Cost_Per_Mn_Delta
    
    with be1:
        st.markdown(kpi("Mn Briq Break-Even Price", f"₹{briq_breakeven_price:,.0f}",
                        f"Current: ₹{P_Briq_Price:,} | {'BELOW' if P_Briq_Price <= briq_breakeven_price else 'ABOVE'} break-even",
                        "kpi-card-green" if P_Briq_Price <= briq_breakeven_price else "kpi-card-amber"), unsafe_allow_html=True)
    with be2:
        st.markdown(kpi("MC FeMn Break-Even Price", f"₹{mc_breakeven_price:,.0f}",
                        f"Current: ₹{P_MCFeMn_Price:,} | {'BELOW' if P_MCFeMn_Price <= mc_breakeven_price else 'ABOVE'} break-even",
                        "kpi-card-green" if P_MCFeMn_Price <= mc_breakeven_price else "kpi-card-amber"), unsafe_allow_html=True)
    with be3:
        st.markdown(kpi("Min. Credits Needed", f"₹{min_credits_needed:,.0f}",
                        f"Current credits: ₹{Total_Op_Credits:,.0f} | {'✅ Sufficient' if Total_Op_Credits >= min_credits_needed else '❌ Insufficient'}",
                        "kpi-card-green" if Total_Op_Credits >= min_credits_needed else "kpi-card-red"), unsafe_allow_html=True)
    
    st.markdown('<div class="section-header">Final Recommendation</div>', unsafe_allow_html=True)
    
    if Savings_Per_MT > 0:
        st.markdown(f"""
        <div style="background:#E8F5E9; border-left:6px solid #4CAF50; padding:24px 32px; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.05);">
            <h2 style="color:#1B5E20; margin-top:0; font-size:28px;">🏆 Mn Briquette Preferred</h2>
            <p style="font-size:16px; color:#2E7D32; line-height:1.6; margin-bottom:0;">
                <b>Projected Annual Savings: ₹{Annual_Savings_Cr:.2f} Crore</b><br>
                By shifting {Substitution_Pct*100:.0f}% of your {Briq_Consumption_FY:,} MT baseline consumption to Mn Briquettes, 
                you realize a net advantage of <b>₹{Savings_Per_MT:,.0f}/MT alloy</b>. 
                The base price efficiency and operational credits (₹{Total_Op_Credits:,.0f}/MT) make it a highly 
                economic choice.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:#FFF3E0; border-left:6px solid #FF9800; padding:24px 32px; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.05);">
            <h2 style="color:#E65100; margin-top:0; font-size:28px;">🏆 MC FeMn Preferred</h2>
            <p style="font-size:16px; color:#EF6C00; line-height:1.6; margin-bottom:0;">
                <b>MC FeMn Cost Efficiency: ₹{abs(Savings_Per_MT):,.0f}/MT alloy</b><br>
                At current input parameters, MC FeMn remains the more cost-effective option, yielding a projected <b>₹{abs(Annual_Savings_Cr):.2f} Crore</b> in savings vs switching. 
                The Briquette operational credits (₹{Total_Op_Credits:,.0f}/MT) 
                do not fully offset the active Mn cost dynamics. 
                Adjust substitution strategies or renegotiate market pricing to break-even.
            </p>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: SUBSTITUTION SOLVER
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="section-header">⚙️ Optimal Alloy Substitution Solver</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="info-box">
        <b>Linear Programming Engine:</b> Calculates the mathematically cheapest blend of <b>MC FeMn (70% Mn)</b> and <b>Mn Briquette (99% Mn)</b> that perfectly satisfies strict metallurgical limits for the selected steel grade. Uses inputs dynamically from the master sidebar.
    </div>
    """, unsafe_allow_html=True)
    
    # Grade-Specific Constraints Dictionary (From SOLVER Sheet)
    grades_data = {
        "Commodity (IS2062)":   {"c_lim": 0.010, "rec_lim": 0.060, "inc_lim": 0.12, "reblow_lim": 0.05, "briq_max": 0.0},
        "TMT/Rebar (Fe500D)":   {"c_lim": 0.008, "rec_lim": 0.050, "inc_lim": 0.10, "reblow_lim": 0.04, "briq_max": 0.0},
        "HSLA/API (API X70)":   {"c_lim": 0.005, "rec_lim": 0.030, "inc_lim": 0.05, "reblow_lim": 0.02, "briq_max": 1.0},
        "Automotive (DP600)":   {"c_lim": 0.003, "rec_lim": 0.020, "inc_lim": 0.03, "reblow_lim": 0.02, "briq_max": 1.0},
        "Electrical (CRGO)":    {"c_lim": 0.0015,"rec_lim": 0.015, "inc_lim": 0.02, "reblow_lim": 0.01, "briq_max": 1.0},
        "IF Steel (Deep Draw)": {"c_lim": 0.001, "rec_lim": 0.015, "inc_lim": 0.02, "reblow_lim": 0.01, "briq_max": 1.0},
    }
    
    with st.container():
        st.markdown('<div class="solver-kpi-box" style="margin-bottom: 30px;">', unsafe_allow_html=True)
        sel_grade = st.selectbox("Select Target Steel Grade", list(grades_data.keys()), index=0)
        limits = grades_data[sel_grade]
        
        st.markdown("<h4 style='color:#333; margin-top:20px; font-size:16px; font-weight:700; border-bottom:1px solid #eee; padding-bottom:10px;'>Metallurgical Constraints (Active Limit Modifiers)</h4>", unsafe_allow_html=True)
        
        # Custom Sliders replacing number inputs for constraints
        c1_s, c2_s, c3_s, c4_s, c5_s = st.columns(5)
        max_c      = c1_s.slider("Max Carbon Limit",    0.001, 0.250, limits["c_lim"], step=0.001, format="%.3f")
        max_rec    = c2_s.slider("Max Recovery Var",    0.005, 0.100, limits["rec_lim"], step=0.005, format="%.3f")
        max_inc    = c3_s.slider("Max Cleanliness",     0.01,  0.20,  limits["inc_lim"], step=0.01)
        max_reblow = c4_s.slider("Max Reblow Risk",     0.01,  0.10,  limits["reblow_lim"], step=0.01)
        max_briq   = c5_s.slider("Max Briq Share (%)",  0.0,   100.0, limits["briq_max"] * 100, step=5.0) / 100.0
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ══════════════════════════════════════════════════════════════════════════════
    # LINEAR PROGRAMMING SOLVER (Match exact Javascript / Excel Logic)
    # ══════════════════════════════════════════════════════════════════════════════
    # Calculate Costs per MT of Active Manganese based on INPUT_PARAMETER formulas
    # MC FeMn formula accounts for iron credit subtraction directly mapping the Excel SOLVER cost output
    cost_mc = (P_MCFeMn_Price / (P_MCFeMn_Mn * P_MCFeMn_Rec)) - (P_MCFeMn_Fe * P_Scrap_Price)
    cost_briq = P_Briq_Price / (P_Briq_Mn * P_Briq_Rec)
    
    # Objective array: [MC FeMn, Briquette] cost per MT of Effective Mn
    c_cost = [cost_mc, cost_briq]
    
    # Equality constraints (Sum of allocations = 100% of Active Mn target)
    A_eq = [[1, 1]]
    b_eq = [1]
    
    # Inequality constraints (A_ub * [x, y]^T <= b_ub) mapped from SOLVER Sheet indices
    A_ub = [
        [P_MCFeMn_C, P_Briq_C],               # Carbon Input Index 
        [MCFeMn_Rec_Var, Briq_Rec_Var],       # Recovery Variability
        [0.09, 0.03],                         # Cleanliness Index (Hardcoded from Excel)
        [Retreatment_MCFeMn, Retreatment_Briq], # Reblow Risk Index
        [0, 1],                               # Max Briq Share (y <= max_briq)
    ]
    b_ub = [max_c, max_rec, max_inc, max_reblow, max_briq]
    
    # Execute Scipy Optimizer
    res = linprog(c_cost, A_eq=A_eq, b_eq=b_eq, A_ub=A_ub, b_ub=b_ub, bounds=[(0, 1), (0, 1)])
    
    st.markdown("<h4 style='color:#333; margin-top:10px; margin-bottom:15px; font-size:18px; font-weight:700;'>Optimization Result</h4>", unsafe_allow_html=True)
    
    if res.success:
        mix = res.x
        opt_x = mix[0]  # MC FeMn
        opt_y = mix[1]  # Briquette
        blended_cost = res.fun
        
        # Calculate savings logic vs highest single commodity
        max_single_cost = max(cost_mc, cost_briq)
        savings = max_single_cost - blended_cost
    
        # Result Banners
        col_res1, col_res2 = st.columns(2)
        col_res1.markdown(f"""
        <div style="background:#F0FDF4; border:1px solid #BBF7D0; padding:16px; border-radius:12px;">
            <div style="font-size:14px; font-weight:700; color:#15803D; margin-bottom:4px;">Final Effective Cost</div>
            <div style="font-size:24px; font-weight:800; color:#166534;">₹{blended_cost:,.0f} <span style="font-size:14px; font-weight:400;">per MT Eff. Mn</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        sav_display = f"₹{savings:,.0f}" if savings > 10 else "₹0"
        col_res2.markdown(f"""
        <div style="background:#EFF6FF; border:1px solid #BFDBFE; padding:16px; border-radius:12px;">
            <div style="font-size:14px; font-weight:700; color:#1D4ED8; margin-bottom:4px;">Projected Savings vs Single Alloy</div>
            <div style="font-size:24px; font-weight:800; color:#1E3A8A;">{sav_display} <span style="font-size:14px; font-weight:400;">per MT Eff. Mn</span></div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
    
        # Charts Row
        chart_col1, chart_col2, chart_col3 = st.columns(3)
        
        with chart_col1:
            # Pie Chart Result
            fig_pie = go.Figure(data=[go.Pie(
                labels=["MC FeMn Share", "Mn Briquette Share"], 
                values=[opt_x, opt_y], hole=0.4, 
                marker_colors=[C_MCFEMN, C_BRIQ], textinfo="label+percent"
            )])
            fig_pie.update_layout(**_layout_solver(f"Optimal Ratio for {sel_grade}"))
            st.plotly_chart(fig_pie, use_container_width=True)
    
        with chart_col2:
            # Cost Comparison Chart
            fig_cost = go.Figure()
            fig_cost.add_trace(go.Bar(
                x=["100% MC FeMn", "Optimal Blend", "100% Mn Briq"],
                y=[cost_mc, blended_cost, cost_briq],
                marker_color=[C_MCFEMN, "#9C27B0", C_BRIQ],
                text=[f"₹{cost_mc:,.0f}", f"₹{blended_cost:,.0f}", f"₹{cost_briq:,.0f}"],
                textposition="auto",
            ))
            fig_cost.update_layout(**_layout_solver("Effective Cost Comparison", "Cost (₹)"))
            st.plotly_chart(fig_cost, use_container_width=True)
    
        with chart_col3:
            # Constraint Utilization Chart
            actual_c      = opt_x * P_MCFeMn_C + opt_y * P_Briq_C
            actual_rec    = opt_x * MCFeMn_Rec_Var + opt_y * Briq_Rec_Var
            actual_inc    = opt_x * 0.09 + opt_y * 0.03
            actual_reblow = opt_x * Retreatment_MCFeMn + opt_y * Retreatment_Briq
            actual_briq   = opt_y
            
            utils = [
                (actual_briq / max_briq) * 100 if max_briq else 0,
                (actual_reblow / max_reblow) * 100 if max_reblow else 0,
                (actual_inc / max_inc) * 100 if max_inc else 0,
                (actual_rec / max_rec) * 100 if max_rec else 0,
                (actual_c / max_c) * 100 if max_c else 0
            ]
            labels = ["Max Briq Share", "Reblow Risk", "Cleanliness", "Recovery Var", "Carbon Limit"]
            
            fig_util = go.Figure()
            fig_util.add_trace(go.Bar(
                y=labels, x=utils, orientation='h', marker_color="#26A69A",
                text=[f"{u:.1f}%" for u in utils], textposition="inside"
            ))
            fig_util.add_vline(x=100, line_dash="dash", line_color="red")
            fig_util.update_layout(**_layout_solver("Constraint Utilization (%)", ""))
            fig_util.update_xaxes(range=[0, max(110, max(utils)*1.1)])
            st.plotly_chart(fig_util, use_container_width=True)
    
        # Table of exact values
        st.markdown("<h4 style='color:#333; margin-top:20px; font-size:16px; font-weight:700; border-bottom:1px solid #eee; padding-bottom:10px;'>Metallurgical Profile of the Optimal Blend</h4>", unsafe_allow_html=True)
        df_profile = pd.DataFrame({
            "Parameter": ["Carbon Input Index", "Recovery Variability", "Cleanliness Index", "Reblow Risk Index", "Briquette Share"],
            "Blend Actual": [actual_c, actual_rec, actual_inc, actual_reblow, actual_briq],
            "Maximum Allowed": [max_c, max_rec, max_inc, max_reblow, max_briq],
        })
        
        # Use small tolerance for float comparison to flag binding limits
        df_profile["Status"] = np.where(df_profile["Blend Actual"] >= df_profile["Maximum Allowed"] - 1e-5, "🛑 Binding Constraint", "✅ Safe")
        
        def format_val(val, is_pct):
            return f"{val*100:.2f}%" if is_pct else f"{val:.4f}"
            
        df_profile["Blend Actual"] = df_profile.apply(lambda row: format_val(row["Blend Actual"], row["Parameter"] == "Briquette Share"), axis=1)
        df_profile["Maximum Allowed"] = df_profile.apply(lambda row: format_val(row["Maximum Allowed"], row["Parameter"] == "Briquette Share"), axis=1)
    
        def color_status(val):
            return "color: #D32F2F; font-weight: bold" if "Binding" in val else "color: #388E3C; font-weight: 500"
            
        st.dataframe(df_profile.style.map(color_status, subset=["Status"]), use_container_width=True)
    
    else:
        st.markdown("""
        <div style="background:#FEF2F2; border-left:4px solid #EF4444; padding:16px; border-radius:8px;">
            <div style="display:flex; align-items:center;">
                <div style="font-size:24px; margin-right:12px;">⚠️</div>
                <div>
                    <p style="font-size:14px; color:#B91C1C; font-weight:bold; margin:0;">Constraint Violation</p>
                    <p style="font-size:14px; color:#DC2626; margin:4px 0 0 0;">The chosen metallurgical limits are too strict to be met using these alloys simultaneously. Please relax the constraints.</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# COMMON FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown("""
<div style="text-align:center; color:#90A4AE; font-size:12px; padding:8px 0;">
  <b>Integrated Analytics Suite</b> &nbsp;|&nbsp; 
  VIU Dashboard & Substitution Solver Matrix (MC FeMn vs Mn Briquette) &nbsp;|&nbsp; 
  All operational logic uniquely synced across mathematical models.
</div>
""", unsafe_allow_html=True)