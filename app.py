"""
VIU DASHBOARD – MC FeMn vs Mn Briquette
================================================
Value-in-Use comparison of Medium-Carbon Ferromanganese (70% Mn)
against Mn Briquette (99.0% Mn).

All formulas sourced exclusively from the Excel file:
  • INPUT_PARAMETER sheet  → adjustable parameters
  • BREAKDOWN_CALC sheet   → benefit calculations
  • VIU_SUMMARY sheet      → synthesis & enterprise savings

Architecture & UX identical to the reference LC FeMn dashboard.
"""

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
    page_title="VIU Dashboard - MC FeMn vs Briquette",
    page_icon="⚗️",
    layout="wide",
)

# Colour palette (Matched to reference)
C_MCFEMN   = "#2196F3"   # blue  – MC FeMn
C_EMM      = "#4CAF50"   # green – Mn Briquette
C_DELTA    = "#FF9800"   # amber – delta / benefit
C_NEG      = "#F44336"   # red   – penalties / negative
C_GRID     = "#E0E0E0"
C_BG       = "#FAFAFA"
C_TEXT     = "#263238"

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR / INPUT PARAMETERS
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("⚙️ Simulation Parameters")

    with st.expander("A. Comparison Selection", expanded=True):
        st.info("Comparing **MC FeMn (70%)** vs **Mn Briquette (99%)**")

    with st.expander("B. Financial Parameters", expanded=False):
        P_MCFeMn_Price = st.number_input("MC FeMn Price (₹/MT)", value=130000, step=1000)
        P_Briq_Price = st.number_input("Mn Briquette Price (₹/MT)", value=175000, step=1000)
        P_Power_Tariff = st.number_input("Power Tariff (₹/kWh)", value=6.5, step=0.1)
        P_Electrode_Cost = st.number_input("Electrode Cost (₹/kg)", value=240, step=10)
        P_Steel_Value = st.number_input("Steel Value (₹/MT)", value=60000, step=1000)
        P_Margin_Steel = st.number_input("Variable Margin (₹/MT steel)", value=2800, step=100)
        P_LF_Retreatment_Cost = st.number_input("LF Retreatment Cost (₹/heat)", value=15000, step=1000)
        P_RH_Extension_Cost = st.number_input("RH Extension Cost (₹/heat)", value=2500, step=100)
        P_Scrap_Price = st.number_input("Scrap / Iron Price (₹/MT)", value=35000, step=1000)

    with st.expander("C. Technical Parameters", expanded=False):
        P_MCFeMn_Mn = st.number_input("MC FeMn Active Mn (%)", value=70.0, step=1.0) / 100
        P_Briq_Mn = st.number_input("Mn Briq Active Mn (%)", value=99.0, step=1.0) / 100
        P_MCFeMn_Rec = st.number_input("MC FeMn Recovery (%)", value=85.0, step=1.0) / 100
        P_Briq_Rec = st.number_input("Mn Briq Recovery (%)", value=95.0, step=1.0) / 100
        P_MCFeMn_Fe = st.number_input("MC FeMn Iron Content (%)", value=20.0, step=1.0) / 100
        P_MCFeMn_C = st.number_input("MC FeMn Carbon Content (%)", value=1.5, step=0.1) / 100
        P_Briq_C = st.number_input("Mn Briq Carbon Content (%)", value=0.1, step=0.05) / 100

    with st.expander("D. Operational Parameters", expanded=False):
        P_Heat_Size = st.number_input("Heat Size (MT)", value=190, step=5)
        P_LF_Heating_Rate = st.number_input("LF Heating Rate (°C/min)", value=3.5, step=0.1)
        P_LF_Heat_Cap = st.number_input("Specific Heat / LF Heat Cap", value=1.17, step=0.01)
        P_LF_Efficiency = st.number_input("LF Efficiency (%)", value=78.0, step=1.0) / 100
        P_Electrode_Wear = st.number_input("Electrode Wear (kg/kWh)", value=0.01, step=0.001, format="%.3f")
        P_Turnaround_Time = st.number_input("Turnaround Time (min)", value=53, step=1)
        P_Thermal_Advantage = st.number_input("Thermal Advantage (°C)", value=4.0, step=0.5)

        st.markdown("---")
        MCFeMn_Rec_Var = st.number_input("MC FeMn Rec. Variability (±%)", value=5.0, step=0.5) / 100
        Briq_Rec_Var = st.number_input("Mn Briq Rec. Variability (±%)", value=1.5, step=0.1) / 100
        Reject_MCFeMn = st.number_input("MC FeMn Rejection Rate (%)", value=0.02, step=0.01, format="%.3f") / 100
        Reject_Briq = st.number_input("Mn Briq Rejection Rate (%)", value=0.0, step=0.01) / 100
        Retreatment_MCFeMn = st.number_input("MC FeMn Retreatment Freq (%)", value=4.0, step=0.5) / 100
        Retreatment_Briq = st.number_input("Mn Briq Retreatment Freq (%)", value=2.0, step=0.5) / 100
        C_Corr_Freq_MCFeMn = st.number_input("RH C-Correction Freq (%)", value=10.0, step=1.0) / 100
        P_Yield = st.number_input("Liquid Steel Yield Gain (%)", value=0.03, step=0.01, format="%.3f") / 100

    with st.expander("E. Realization Factors", expanded=False):
        R_Power_Corr = st.slider("Power Realization (%)", 0, 100, 100) / 100
        R_Electrode_Corr = st.slider("Electrode Realization (%)", 0, 100, 100) / 100
        R_Throughput_Corr = st.slider("Throughput Realization (%)", 0, 100, 25) / 100
        R_Yield_Corr = st.slider("Yield Realization (%)", 0, 100, 25) / 100
        R_Clean_Corr = st.slider("Cleanliness Realization (%)", 0, 100, 100) / 100
        R_Retreatment_Corr = st.slider("Retreatment Realization (%)", 0, 100, 50) / 100
        R_RH_Corr = st.slider("RH Correction Realization (%)", 0, 100, 100) / 100
        R_Recovery_Corr = st.slider("Recovery Stability Realization (%)", 0, 100, 50) / 100

    with st.expander("F. Enterprise Savings", expanded=False):
        Annual_Steel = st.number_input("Annual Steel Prod. (MT)", value=2000000, step=100000)
        Avg_Mn_Target = st.number_input("Avg Mn Addition (%)", value=0.40, step=0.05) / 100


# ══════════════════════════════════════════════════════════════════════════════
# CORE CALCULATIONS (EXCEL LOGIC REPLICATION)
# ══════════════════════════════════════════════════════════════════════════════

# 1. Base requirements per MT Active Mn
req_mc = 1 / (P_MCFeMn_Mn * P_MCFeMn_Rec)
req_briq = 1 / (P_Briq_Mn * P_Briq_Rec)

# Base Costs per MT Active Mn
cost_mn_mc = req_mc * P_MCFeMn_Price
cost_mn_briq = req_briq * P_Briq_Price
base_price_benefit_per_briq = (cost_mn_mc - cost_mn_briq) / req_briq

# 2. Iron Credit Penalty per MT Briq
iron_credit_mc = req_mc * P_MCFeMn_Fe * P_Scrap_Price
iron_penalty_per_briq = -iron_credit_mc / req_briq

# 3. Operational Benefits per MT Briq
STD_Mn_Target = 0.004 
req_briq_per_heat = (P_Heat_Size * STD_Mn_Target) / (P_Briq_Mn * P_Briq_Rec)

Conversion_Factor = 3.6
kWh_saved = (P_Heat_Size * P_LF_Heat_Cap * P_Thermal_Advantage) / (Conversion_Factor * P_LF_Efficiency)

ben_power = (kWh_saved * P_Power_Tariff * R_Power_Corr) / req_briq_per_heat
ben_electrode = (kWh_saved * P_Electrode_Wear * P_Electrode_Cost * R_Electrode_Corr) / req_briq_per_heat

time_saved = P_Thermal_Advantage / P_LF_Heating_Rate
fractional_heat = time_saved / P_Turnaround_Time
ben_throughput = (fractional_heat * P_Heat_Size * P_Margin_Steel * R_Throughput_Corr) / req_briq_per_heat

ben_recovery = ((req_mc * P_MCFeMn_Price * MCFeMn_Rec_Var) - (req_briq * P_Briq_Price * Briq_Rec_Var)) * R_Recovery_Corr / req_briq
ben_retreatment = ((Retreatment_MCFeMn - Retreatment_Briq) * P_LF_Retreatment_Cost * R_Retreatment_Corr) / req_briq_per_heat
ben_clean = ((Reject_MCFeMn - Reject_Briq) * P_Steel_Value * P_Heat_Size * R_Clean_Corr) / req_briq_per_heat
ben_yield = (P_Yield * P_Steel_Value * P_Heat_Size * R_Yield_Corr) / req_briq_per_heat
ben_carbon = (C_Corr_Freq_MCFeMn * P_RH_Extension_Cost * R_RH_Corr) / req_briq_per_heat

# 4. Synthesize Totals
total_ops_viu = ben_power + ben_electrode + ben_throughput + ben_recovery + ben_retreatment + ben_clean + ben_yield + ben_carbon
net_viu_benefit = base_price_benefit_per_briq + iron_penalty_per_briq + total_ops_viu
breakeven_price = P_Briq_Price + net_viu_benefit
effective_briq_cost = P_Briq_Price - net_viu_benefit

# 5. Enterprise Calculations
Total_Mn_Required = Annual_Steel * Avg_Mn_Target
Total_Briq_Required = Total_Mn_Required / (P_Briq_Mn * P_Briq_Rec)
annual_savings_rupees = Total_Briq_Required * net_viu_benefit
annual_savings_cr = annual_savings_rupees / 10_000_000


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD UI / UX
# ══════════════════════════════════════════════════════════════════════════════

st.title("VIU DASHBOARD – MC FeMn vs Mn Briquette")
st.markdown("Value-in-Use comparison of **Medium-Carbon Ferromanganese (70% Mn)** against **Mn Briquette (99.0% Mn)**.")

tab1, = st.tabs(["📊 VIU Dashboard"])

with tab1:
    # --- KPI ROW ---
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1: st.metric("MC FeMn Price", f"₹ {P_MCFeMn_Price:,.0f}/MT")
    with col2: st.metric("Mn Briquette Price", f"₹ {P_Briq_Price:,.0f}/MT")
    with col3: st.metric("Cost/MT Mn (MC FeMn)", f"₹ {cost_mn_mc:,.0f}")
    with col4: st.metric("Cost/MT Mn (Briq)", f"₹ {cost_mn_briq:,.0f}")
    with col5: st.metric("Total Net VIU Benefit", f"₹ {net_viu_benefit:,.0f}/MT")
    with col6: st.metric("Breakeven Price (Briq)", f"₹ {breakeven_price:,.0f}/MT")

    st.divider()

    # --- MAIN SECTIONS ---
    c_left, c_right = st.columns([1, 1.2], gap="large")

    with c_left:
        st.subheader("1. Core Economic Synthesis")
        df_base = pd.DataFrame({
            "Parameter": ["Active Mn Content", "Assumed Process Recovery", "Required Alloy per MT Active Mn", "Base Cost per MT Active Mn"],
            "MC FeMn (70%)": [f"{P_MCFeMn_Mn*100:.1f}%", f"{P_MCFeMn_Rec*100:.1f}%", f"{req_mc:.3f} MT", f"₹ {cost_mn_mc:,.0f}"],
            "Mn Briquette (99%)": [f"{P_Briq_Mn*100:.1f}%", f"{P_Briq_Rec*100:.1f}%", f"{req_briq:.3f} MT", f"₹ {cost_mn_briq:,.0f}"]
        })
        st.dataframe(df_base, hide_index=True, use_container_width=True)

        st.subheader("2. Value-in-Use Breakdown (₹ / MT Briquette)")
        breakdown_data = [
            ("Base Price Advantage", base_price_benefit_per_briq, "Price Diff per MT Mn"),
            ("Iron Credit Penalty", iron_penalty_per_briq, "Loss of free Fe from MC FeMn"),
            ("Power Saving", ben_power, f"{P_Thermal_Advantage}°C Thermal Adv."),
            ("Electrode Saving", ben_electrode, "Reduced arc-on time"),
            ("Throughput Gain", ben_throughput, "Faster LF turnaround"),
            ("Recovery Stability", ben_recovery, "Tighter chemistry control"),
            ("Re-treatment Red.", ben_retreatment, "Fewer reblows"),
            ("Cleanliness Gain", ben_clean, "Fewer exogenous inclusions"),
            ("Yield Gain", ben_yield, "Higher liquid yield"),
            ("Carbon Avoidance", ben_carbon, "Avoided RH extension")
        ]
        df_breakdown = pd.DataFrame(breakdown_data, columns=["Value Component", "₹ / MT Briquette", "Mechanism"])
        df_breakdown["₹ / MT Briquette"] = df_breakdown["₹ / MT Briquette"].apply(lambda x: f"₹ {x:,.0f}")
        
        def color_val(val):
            try:
                num = float(val.replace("₹", "").replace(",", ""))
                if num > 0: return 'color: #388E3C; font-weight: bold'
                elif num < 0: return 'color: #D32F2F; font-weight: bold'
            except: pass
            return ''

        st.dataframe(df_breakdown.style.map(color_val, subset=["₹ / MT Briquette"]), hide_index=True, use_container_width=True)

    with c_right:
        st.subheader("📈 Net Benefit Waterfall (₹ / MT Briquette)")
        
        wf_names = [x[0] for x in breakdown_data]
        wf_vals = [x[1] for x in breakdown_data]
        
        fig_wf = go.Figure(go.Waterfall(
            orientation="v",
            measure=["relative"] * len(wf_names) + ["total"],
            x=wf_names + ["Total Net VIU"],
            y=wf_vals + [net_viu_benefit],
            text=[f"{v/1000:+.1f}k" for v in wf_vals] + [f"{net_viu_benefit/1000:+.1f}k"],
            textposition="outside",
            decreasing={"marker": {"color": C_NEG}},
            increasing={"marker": {"color": C_EMM}},
            totals={"marker": {"color": C_MCFEMN}}
        ))
        fig_wf.update_layout(
            margin=dict(l=20, r=20, t=30, b=80),
            height=350,
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor=C_GRID, title="₹ / MT"),
            xaxis=dict(tickangle=-45)
        )
        st.plotly_chart(fig_wf, use_container_width=True)

        st.subheader("📊 Cost Comparison per MT Active Mn")
        
        # Calculate costs per MT Active Mn
        cost_mc_per_mn = cost_mn_mc
        cost_briq_base_per_mn = cost_mn_briq
        total_benefit_per_mn = net_viu_benefit * req_briq
        effective_briq_cost_per_mn = cost_briq_base_per_mn - total_benefit_per_mn

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=["MC FeMn (70%)", "Mn Briquette (99%)"],
            y=[cost_mc_per_mn, effective_briq_cost_per_mn],
            marker_color=[C_MCFEMN, C_EMM],
            text=[f"₹ {cost_mc_per_mn:,.0f}", f"₹ {effective_briq_cost_per_mn:,.0f}"],
            textposition="auto"
        ))
        fig_bar.update_layout(
            title="Effective Cost to Deliver 1 MT of Active Mn (Lower is Better)",
            margin=dict(l=20, r=20, t=40, b=20),
            height=250,
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor=C_GRID, title="₹ / MT Active Mn")
        )
        st.plotly_chart(fig_bar, use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# ENTERPRISE SAVINGS & RECOMMENDATION
# ══════════════════════════════════════════════════════════════════════════════
    st.divider()
    c_bottom_left, c_bottom_right = st.columns([1, 1], gap="large")

    with c_bottom_left:
        st.subheader("🏭 Enterprise Savings Impact")
        st.write(f"**Annual Steel Production:** {Annual_Steel:,.0f} MT")
        st.write(f"**Average Mn Addition:** {Avg_Mn_Target*100:.2f}%")
        st.write(f"**Total Mn Briquette Required:** {Total_Briq_Required:,.0f} MT/year")
        
        st.write("")
        if annual_savings_cr > 0:
            st.success(f"### Total Annual Enterprise Savings: ₹ {annual_savings_cr:,.2f} Crores")
        else:
            st.error(f"### Total Annual Enterprise Loss: ₹ {abs(annual_savings_cr):,.2f} Crores")

    with c_bottom_right:
        st.subheader("💡 Final Recommendation")
        st.write("")
        if net_viu_benefit > 0:
            st.success(f"""
**✅ Adopt Mn Briquette (99%)**

Mn Briquette provides a positive Net Value-in-Use benefit of **₹ {net_viu_benefit:,.0f} per MT**. 
Even at a premium purchase price, the operational efficiencies, recovery stability, and downstream yield gains vastly outweigh the cost differences. 

Maximum acceptable purchase price (Breakeven): **₹ {breakeven_price:,.0f}/MT**.
            """)
        else:
            st.error(f"""
**⚠️ Retain MC FeMn (70%)**

Mn Briquette results in a net Value-in-Use penalty of **₹ {abs(net_viu_benefit):,.0f} per MT**. 
The current purchase premium for Briquettes is not justified by the operational savings generated. 

Negotiate Briquette price down to at least **₹ {breakeven_price:,.0f}/MT** before switching.
            """)

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown("""
<div style="text-align:center; color:#90A4AE; font-size:12px; padding:8px 0;">
  VIU Dashboard – MC FeMn vs Mn Briquette &nbsp;|&nbsp; All formulas sourced from Excel workbook.
</div>
""", unsafe_allow_html=True)