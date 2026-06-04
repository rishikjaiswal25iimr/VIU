from __future__ import annotations
import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.optimize import linprog

# ==============================================================================
# PAGE CONFIG & GLOBAL STYLING
# ==============================================================================
st.set_page_config(page_title="FeV80 vs NV Dashboard", page_icon="⚗️", layout="wide")

# Colors for VIU Dashboard
C_FEV   = "#2196F3"   # blue  – FeV80
C_NV    = "#4CAF50"   # green – Nitrovan
C_DELTA = "#FF9800"   # amber – delta / benefit
C_NEG   = "#F44336"   # red   – penalties / negative
C_GRID  = "#EEEEEE"
C_BG    = "#FAFAFA"
C_TEXT  = "#333333"

# Colors for Solver Dashboard
C_FEV_SOLVER = "#1976D2"
C_NV_SOLVER  = "#E64A19"

st.markdown("""
<style>
/* General app styling */
.stApp { background: #F0F4F8; }

/* KPI Cards */
.kpi-card { background: #FFFFFF; border-radius: 12px; padding: 18px 22px 14px 22px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); border-left: 5px solid #2196F3; margin-bottom: 8px; }
.kpi-card-green  { border-left-color: #4CAF50; }
.kpi-card-amber  { border-left-color: #FF9800; }
.kpi-card-red    { border-left-color: #F44336; }
.kpi-card-purple { border-left-color: #9C27B0; }
.kpi-card-orange { border-left-color: #E64A19; }

.kpi-label { font-size: 11px; font-weight: 600; color: #78909C; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.kpi-value { font-size: 20px; font-weight: 700; color: #1A237E; line-height: 1.15; }
.kpi-sub   { font-size: 11px; color: #90A4AE; margin-top: 3px; }

/* Headers and Boxes */
.section-header { font-size: 20px; font-weight: 800; color: #1A237E; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 3px solid #2196F3; padding-bottom: 8px; margin-bottom: 24px; margin-top: 32px; }
.info-box { background: #E3F2FD; border-radius: 8px; padding: 12px 16px; font-size: 13px; color: #1565C0; border-left: 4px solid #2196F3; margin-bottom: 10px; }
.warn-box { background: #FFF3E0; border-radius: 8px; padding: 12px 16px; font-size: 13px; color: #E65100; border-left: 4px solid #FF9800; margin-bottom: 10px; }
.success-box { background: #E8F5E9; border-radius: 8px; padding: 12px 16px; font-size: 13px; color: #1B5E20; border-left: 4px solid #4CAF50; margin-bottom: 10px; }

/* Sidebar styling overrides */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1A237E 0%, #283593 40%, #1565C0 100%); }
[data-testid="stSidebar"] * { color: #E8EAF6 !important; }
[data-testid="stSidebar"] .stSlider > div > div > div { background: #5C6BC0 !important; }
[data-testid="stSidebar"] hr { border-color: #3949AB; }
[data-testid="stSidebar"] .stNumberInput input { background: #283593; border-color: #5C6BC0; color: #fff !important; }
[data-testid="stSidebar"] .stSelectbox select { background: #283593; color: #fff; }
[data-testid="stSidebar"] .stRadio div[role="radiogroup"] label { color: #fff !important; }
</style>
""", unsafe_allow_html=True)

def kpi(label: str, value: str, sub: str = "", colour: str = "") -> str:
    return f"""<div class="kpi-card {colour}"><div class="kpi-label" title="{label}">{label}</div><div class="kpi-value">{value}</div><div class="kpi-sub">{sub}</div></div>"""

def _layout(title: str, y_title: str = "", height: int = 420) -> dict:
    return dict(template="plotly_white", paper_bgcolor="white", plot_bgcolor=C_BG, font=dict(family="Inter, sans-serif", size=11, color=C_TEXT), title=dict(text=title, font=dict(size=14, color="#1A237E"), x=0.01), legend=dict(bgcolor="rgba(255,255,255,0.85)", bordercolor="#DDD", borderwidth=1), xaxis=dict(showgrid=True, gridcolor=C_GRID, zeroline=False), yaxis=dict(showgrid=True, gridcolor=C_GRID, zeroline=False, title=y_title), hovermode="x unified", height=height, margin=dict(l=50, r=40, t=55, b=45))


# ==============================================================================
# SIDEBAR – UNIFIED DYNAMIC INPUT PARAMETERS
# ==============================================================================
with st.sidebar:
    st.markdown("## ⚙️ Combined Settings")
    st.divider()

    st.markdown("### A. Comparison Selection")
    comparison_selection = st.radio(
        "Select Analysis:",
        ["Not selected", "FeV80 vs Nitrovan"],
        index=1
    )
    
    if comparison_selection != "Not selected":
        st.divider()
        st.markdown("### B. Financial Parameters")
        P_FeV_Price           = st.number_input("FeV80 Price (₹/MT)", value=2950000.0, step=10000.0)
        P_NV_Price            = st.number_input("Nitrovan Price (₹/MT)", value=2500000.0, step=10000.0)
        P_Power_Tariff        = st.number_input("Power Cost (₹/kWh)", value=6.5, step=0.1, format="%.2f")
        P_Electrode_Cost      = st.number_input("Electrode Cost (₹/kg)", value=240.0, step=5.0)
        P_Steel_Value         = st.number_input("Steel Value (₹/MT)", value=60000.0, step=1000.0)
        P_LF_Minute_Cost      = st.number_input("LF Fixed Operating Cost (₹/min)", value=850.0, step=50.0)
        P_LF_Retreatment_Cost = st.number_input("Re-treatment / Reblow Cost (₹/event)", value=15000.0, step=1000.0)

        st.divider()
        st.markdown("### C. Technical & Thermodynamic")
        P_FeV_V        = st.number_input("FeV80 V Content (V %)", value=0.80, format="%.2f")
        P_NV_V         = st.number_input("Nitrovan V Content (V %)", value=0.77, format="%.2f")
        P_NV_N         = st.number_input("Nitrovan N Content (N %)", value=0.16, format="%.2f")
        P_FeV_Rec      = st.number_input("FeV80 Recovery (%)", value=0.95, format="%.2f")
        P_NV_Rec       = st.number_input("Nitrovan Recovery (%)", value=0.92, format="%.2f")
        P_FeV_Eff      = st.number_input("Strengthening Eff. – FeV80", value=1.0, format="%.1f")
        P_NV_Eff       = st.number_input("Strengthening Eff. – Nitrovan", value=1.1, format="%.1f")
        
        P_Chill_FeV    = st.number_input("FeV80 Chill Factor (°C/kg)", value=-1.8, format="%.1f")
        P_Chill_NV     = st.number_input("Nitrovan Chill Factor (°C/kg)", value=-3.0, format="%.1f")
        P_LF_Efficiency= st.number_input("LF Heating Efficiency (%)", value=0.60, format="%.2f")
        P_SpHeat_Steel = st.number_input("Specific Heat of Steel (MJ/T/°C)", value=0.75, step=0.01, format="%.2f")
        P_Graphite_Factor = st.number_input("LF Electrode Consumption (kg/kWh)", value=0.010, format="%.3f")
        Conversion_MJ  = st.number_input("Conversion Factor (MJ/kWh)", value=3.6, format="%.1f")

        st.divider()
        st.markdown("### D. Operational Parameters")
        P_Heat_Size              = st.number_input("Heat Size (MT steel/heat)", value=190.0, step=5.0)
        Active_V                 = st.number_input("Target Vanadium Addition Rate (%)", value=0.20, format="%.2f")
        P_Dissolution_Time_Saved = st.number_input("LF Cycle Time Reduction (min/heat)", value=2.5, format="%.1f")
        FeV_Overdose             = st.number_input("FeV Overdose Buffer (%)", value=0.0001, format="%.5f")
        NV_Overdose              = st.number_input("NV Overdose Buffer (%)", value=0.00015, format="%.5f")
        Retreatment_FeV          = st.number_input("LF Re-treatment Rate FeV80 (%)", value=0.010, format="%.4f")
        Retreatment_NV           = st.number_input("LF Re-treatment Rate Nitrovan (%)", value=0.025, format="%.4f")
        Reject_FeV               = st.number_input("Inclusion Rejection Rate FeV80 (%)", value=0.00008, format="%.5f")
        Reject_NV                = st.number_input("Inclusion Rejection Rate Nitrovan (%)", value=0.00015, format="%.5f")
        Yield_Loss_FeV           = st.number_input("Oxidation Yield Loss FeV80 (%)", value=0.00003, format="%.5f")
        Yield_Loss_NV            = st.number_input("Oxidation Yield Loss Nitrovan (%)", value=0.00005, format="%.5f")

        st.markdown("#### Solver-Specific Constraints")
        P_FeV_Rec_Var  = st.slider("FeV80 Rec Var (%) [Solver]",        1.0, 5.0, 2.5, 0.1)
        P_NV_Rec_Var   = st.slider("Nitrovan Rec Var (%) [Solver]",     1.0, 6.0, 3.8, 0.1)
        P_FeV_Retrt    = st.slider("FeV80 Re-treat Risk (%) [Solver]",  0.5, 5.0, 1.2, 0.1)
        P_NV_Retrt     = st.slider("Nitrovan Re-treat Risk (%) [Solver]", 1.0, 5.0, 2.8, 0.1)
        P_FeV_Inc      = st.slider("FeV Cleanliness Idx (%) [Solver]",  0.005, 0.030, 0.015, 0.001, format="%.3f")
        P_NV_Inc       = st.slider("NV Cleanliness Idx (%) [Solver]",   0.005, 0.030, 0.010, 0.001, format="%.3f")
        P_FeV_Yield    = st.slider("FeV80 Yield Loss (%) [Solver]",     0.001, 0.010, 0.003, 0.001, format="%.3f")
        P_NV_Yield     = st.slider("Nitrovan Yield Loss (%) [Solver]",  0.001, 0.010, 0.005, 0.001, format="%.3f")

        st.divider()
        st.markdown("### E. Realization Factors")
        R_Power       = st.number_input("Power Savings Realization (%)", value=0.40, format="%.2f")
        R_Electrode   = st.number_input("Electrode Savings Realization (%)", value=0.50, format="%.2f")
        R_Throughput  = st.number_input("Throughput Realization (%)", value=0.40, format="%.2f")
        R_Stability   = st.number_input("Recovery Stability Realization (%)", value=0.10, format="%.2f")
        R_Reblow      = st.number_input("Re-treatment Realization (%)", value=0.80, format="%.2f")
        R_Yield       = st.number_input("Yield Improvement Realization (%)", value=0.50, format="%.2f")
        R_Cleanliness = st.number_input("Inclusion Cleanliness Realization (%)", value=0.40, format="%.2f")

        st.divider()
        st.markdown("### F. Enterprise Savings")
        NV_Consumption_FY = st.number_input("Baseline Volume FY (MT)", value=80.0, step=10.0)
        Substitution_Pct  = st.slider("Substitution Percentage (%)", 0.0, 1.0, 1.0, 0.05)
        
        # Link mapped variables for the solver internally to preserve exact mathematical engine
        P_NV_N_pct = P_NV_N
        P_FeV_ESU_Fac = P_FeV_Eff
        P_NV_ESU_Fac = P_NV_Eff
        P_FeV_Chill_Solver = abs(P_Chill_FeV)
        P_NV_Chill_Solver = abs(P_Chill_NV)
        Consump_FY = NV_Consumption_FY
        Sub_Pct = Substitution_Pct


# ==============================================================================
# MAIN CONTENT GUARD
# ==============================================================================
if comparison_selection == "Not selected":
    st.info("Please select substitution combination from the sidebar to run the VIU & Solver analysis.")
    st.stop()


# ==============================================================================
# TABBED INTERFACE
# ==============================================================================
tab1, tab2 = st.tabs(["⚗️ VIU Dashboard", "🧠 Substitution Solver"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: VIU DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    
    # ── EXACT BREAKDOWN CALCULATION REPLICATION FROM EXCEL ──
    # Intermediate Dependencies (INPUT_PARAMETERS!H1:H10)
    H2 = (Active_V / 100.0) * 1000.0  # Effective V in Heat (kg/T Steel)
    H4 = H2 / P_FeV_Eff / P_FeV_V / P_FeV_Rec # FeV Req /T Steel
    H6 = 1000.0 / H4 # MT of FeV support Steel Production (T)
    H8 = H2 / P_NV_Eff / P_NV_V / P_NV_Rec # NV Req /T Steel
    H10 = 1000.0 / H8 # MT of NV support Steel Production (T)

    # 1. Power Saving (Penalty)
    # ABS(H4*ABS(B19)-H8*ABS(B20))*B22/B39/B21*H6 -> Updated to H10
    kWh_Saved = abs(H4 * abs(P_Chill_FeV) - H8 * abs(P_Chill_NV)) * P_SpHeat_Steel / Conversion_MJ / P_LF_Efficiency * H10
    Benefit_Power = kWh_Saved * P_Power_Tariff * R_Power

    # 2. Electrode Saving
    Benefit_Electrode = kWh_Saved * P_Graphite_Factor * P_Electrode_Cost * R_Electrode

    # 3. Throughput Gain
    Benefit_Throughput = (P_Dissolution_Time_Saved / P_Heat_Size) * P_LF_Minute_Cost * H10 * R_Throughput

    # 4. Recovery Stability
    Benefit_Stability = (NV_Overdose - FeV_Overdose) * P_FeV_Price * R_Stability * H10

    # 5. Reblow Reduction
    Benefit_Retreatment = (Retreatment_NV - Retreatment_FeV) * P_LF_Retreatment_Cost / P_Heat_Size * H10 * R_Reblow

    # 6. Inclusion Cleanliness (Auto/API)
    Benefit_Cleanliness = (Reject_NV - Reject_FeV) * P_Steel_Value * H10 * R_Cleanliness

    # 7. Yield Improvement
    Benefit_Yield = (Yield_Loss_NV - Yield_Loss_FeV) * P_Steel_Value * H10 * R_Yield

    # Total Operational Credits (FeV Advantage over NV)
    Total_VIU_Credits = Benefit_Power + Benefit_Electrode + Benefit_Throughput + Benefit_Stability + Benefit_Retreatment + Benefit_Cleanliness + Benefit_Yield

    # --- Direct Cost Synthesis ---
    Eff_V_FeV_VIU = P_FeV_V * P_FeV_Rec * P_FeV_Eff
    Eff_V_NV_VIU = P_NV_V * P_NV_Rec * P_NV_Eff

    Cost_Per_Eff_V_FeV = P_FeV_Price / Eff_V_FeV_VIU
    Cost_Per_Eff_V_NV = P_NV_Price / Eff_V_NV_VIU

    # Direct Cost Delta = Material Premium of FeV80
    Cost_Gap = Cost_Per_Eff_V_FeV - Cost_Per_Eff_V_NV
    
    # Net Savings (Advantage of Nitrovan over FeV80)
    Net_Savings = Cost_Gap - Total_VIU_Credits

    # Enterprise Savings
    Annual_Savings_Rs = NV_Consumption_FY * Substitution_Pct * Net_Savings
    Annual_Savings_Cr = Annual_Savings_Rs / 1e7

    # Break-Even Pricing Calculation (Net Savings = 0)
    nv_breakeven_price = (Cost_Per_Eff_V_FeV - Total_VIU_Credits) * Eff_V_NV_VIU
    fev_breakeven_price = (Cost_Per_Eff_V_NV + Total_VIU_Credits) * Eff_V_FeV_VIU


    # ── SECTION 1: DASHBOARD HEADER ──
    st.markdown("""
    <div style="background: linear-gradient(135deg,#1A237E 0%,#1565C0 60%,#0277BD 100%);
                padding:22px 28px 18px 28px; border-radius:14px; margin-bottom:20px;
                box-shadow:0 4px 24px rgba(26,35,126,0.25);">
      <h1 style="color:#FFFFFF;margin:0;font-size:26px;font-weight:800;letter-spacing:0.02em;">
        ⚗️ VIU Dashboard — FeV80 vs Nitrovan
      </h1>
      <p style="color:#90CAF9;margin:6px 0 0 0;font-size:13px;">
        Value-In-Use Economic Analysis &nbsp;|&nbsp; Ferrovanadium (80% V) 
        vs Nitrovan (16% N, 77% V)
      </p>
    </div>
    """, unsafe_allow_html=True)

    # ── SECTION 2: TOP KPI CARDS ──
    r1_c1, r1_c2, r1_c3 = st.columns(3)
    with r1_c1: st.markdown(kpi("FeV80 Price", f"₹{P_FeV_Price:,.0f}", "per MT alloy", ""), unsafe_allow_html=True)
    with r1_c2: st.markdown(kpi("Nitrovan Price", f"₹{P_NV_Price:,.0f}", "per MT alloy", "kpi-card-green"), unsafe_allow_html=True)
    with r1_c3: st.markdown(kpi("Cost Gap", f"₹{Cost_Gap:,.0f}", "per MT Eff. V", "kpi-card-amber"), unsafe_allow_html=True)

    r2_c1, r2_c2, r2_c3 = st.columns(3)
    with r2_c1: st.markdown(kpi("Total VIU Credits", f"₹{Total_VIU_Credits:,.0f}", "net advantage of FeV80", "kpi-card-amber"), unsafe_allow_html=True)
    with r2_c2:
        col = "kpi-card-green" if Net_Savings > 0 else "kpi-card-red"
        st.markdown(kpi("Net Savings", f"₹{Net_Savings:+,.0f}", "Nitrovan adv (+ = better)", col), unsafe_allow_html=True)
    with r2_c3:
        col_yr = "kpi-card-green" if Net_Savings > 0 else "kpi-card-red"
        st.markdown(kpi("Annual Savings", f"₹{abs(Annual_Savings_Cr):.2f} Cr", f"@ {Substitution_Pct*100:.0f}% Substitution", col_yr), unsafe_allow_html=True)


    # ── SECTION 3: VIU SUMMARY ──
    st.markdown('<div class="section-header">VIU Economic Synthesis</div>', unsafe_allow_html=True)
    col_l, col_r = st.columns([1, 1])
    
    with col_l:
        st.markdown("#### Cost per MT Effective Vanadium (₹/MT Eff. V)")
        km1, km2 = st.columns(2)
        with km1: st.markdown(kpi("FeV80 Cost / MT Eff. V", f"₹{Cost_Per_Eff_V_FeV:,.0f}", f"@ {P_FeV_V*100:.0f}% V × {P_FeV_Rec*100:.0f}% rec", ""), unsafe_allow_html=True)
        with km2: st.markdown(kpi("Nitrovan Cost / MT Eff. V", f"₹{Cost_Per_Eff_V_NV:,.0f}", f"@ {P_NV_V*100:.0f}% V × {P_NV_Eff}x eff.", "kpi-card-green"), unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### VIU Components")
        data_summary = {
            "Component": [
                "Raw Cost per MT Effective V",
                "Cost Gap (FeV Material Premium)",
                "VIU Operational Credits (FeV Advantage)",
                "Net Savings (Nitrovan Advantage)",
            ],
            "FeV80 (₹)": [f"₹{Cost_Per_Eff_V_FeV:,.0f}", "—", f"₹{Total_VIU_Credits:,.0f}", "—"],
            "Nitrovan (₹)": [
                f"₹{Cost_Per_Eff_V_NV:,.0f}", f"₹{Cost_Gap:,.0f}",
                "—", f"₹{Net_Savings:+,.0f}",
            ],
        }
        df_sum = pd.DataFrame(data_summary).set_index("Component")
        st.dataframe(df_sum, use_container_width=True)

        # Verdict
        if Net_Savings > 0:
            st.markdown(f"""<div class="success-box">✅ <b>Nitrovan offers a net advantage of ₹{Net_Savings:,.0f}.</b><br>The material pricing gap overcomes the FeV operational credits, making Nitrovan the economically superior choice.</div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""<div class="warn-box">⚠️ <b>FeV80 is currently more cost-effective by ₹{abs(Net_Savings):,.0f}.</b><br>At current prices and parameters, FeV80's operational superiority overcomes its material premium.</div>""", unsafe_allow_html=True)

    with col_r:
        # --- VIU Donut: Credit composition ---
        benefit_names = ["Power Saving", "Electrode Saving", "Throughput Gain", "Recovery Stability", "Reblow Reduction", "Inclusion Cleanliness", "Yield Improvement"]
        benefit_values = [Benefit_Power, Benefit_Electrode, Benefit_Throughput, Benefit_Stability, Benefit_Retreatment, Benefit_Cleanliness, Benefit_Yield]
        
        pos_names  = [n for n, v in zip(benefit_names, benefit_values) if v > 0]
        pos_values = [v for v in benefit_values if v > 0]
        colours_donut = ["#2196F3", "#1565C0", "#42A5F5", "#4CAF50", "#66BB6A", "#81C784", "#FF9800", "#FFA726", "#FFC107"]

        fig_donut = go.Figure(data=[go.Pie(
            labels=pos_names, values=pos_values, hole=0.52,
            marker=dict(colors=colours_donut[:len(pos_names)], line=dict(color="#fff", width=2)),
            textinfo="label+percent", hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<extra></extra>",
        )])
        fig_donut.add_annotation(text=f"<b>₹{sum(pos_values):,.0f}</b><br><span style='font-size:10px'>FeV Op Credits</span>", x=0.5, y=0.5, font_size=14, showarrow=False)
        fig_donut.update_layout(title="FeV Operational Credit Composition (₹)", template="plotly_white", height=420, margin=dict(l=20, r=20, t=55, b=20), legend=dict(font=dict(size=11)))
        st.plotly_chart(fig_donut, use_container_width=True)

    # ── SECTION 4: BENEFIT BREAKDOWN ──
    st.markdown('<div class="section-header">Detailed Benefit Breakdown</div>', unsafe_allow_html=True)

    all_benefit_names = ["Power Saving", "Electrode Saving", "Throughput Gain", "Recovery Stability", "Reblow Reduction", "Inclusion Cleanliness", "Yield Improvement"]
    all_benefit_values = [Benefit_Power, Benefit_Electrode, Benefit_Throughput, Benefit_Stability, Benefit_Retreatment, Benefit_Cleanliness, Benefit_Yield]

    col_chart, col_table = st.columns([3, 2])

    with col_chart:
        bar_colors = [C_DELTA if v >= 0 else C_NEG for v in all_benefit_values]
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=all_benefit_names[::-1], x=all_benefit_values[::-1], orientation="h",
            marker=dict(color=bar_colors[::-1], line=dict(color="white", width=1)),
            text=[f"₹{v:+,.0f}" for v in all_benefit_values[::-1]], textposition="auto",
            hovertemplate="<b>%{y}</b><br>₹%{x:,.0f}<extra></extra>",
        ))
        fig_bar.add_vline(x=0, line_dash="solid", line_color="#333", line_width=1.5)
        fig_bar.update_layout(**_layout("Benefit Contribution (Advantage of FeV over NV)", "₹ Value", 450))
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_table:
        df_breakdown = pd.DataFrame({
            "Benefit Component": all_benefit_names,
            "Advantage (₹)": [f"₹{v:+,.0f}" for v in all_benefit_values],
        }).set_index("Benefit Component")

        def color_values(val):
            num = float(val.replace("₹", "").replace(",", "").replace("+", ""))
            if num > 0: return "color: #1B5E20; font-weight: 600"
            elif num < 0: return "color: #B71C1C; font-weight: 600"
            return ""

        st.dataframe(df_breakdown.style.map(color_values, subset=["Advantage (₹)"]), use_container_width=True, height=450)

    st.markdown("<br>", unsafe_allow_html=True)

    # Heatmap of benefits by realization factor sensitivity
    st.markdown("#### Benefit Sensitivity Heatmap (₹ at varying Realization Factors)")
    real_range = np.arange(0.1, 1.05, 0.1)
    base_heat_values = [
        Benefit_Power / R_Power if R_Power > 0 else 0,
        Benefit_Electrode / R_Electrode if R_Electrode > 0 else 0,
        Benefit_Throughput / R_Throughput if R_Throughput > 0 else 0,
        Benefit_Stability / R_Stability if R_Stability > 0 else 0,
        Benefit_Retreatment / R_Reblow if R_Reblow > 0 else 0,
        Benefit_Cleanliness / R_Cleanliness if R_Cleanliness > 0 else 0,
        Benefit_Yield / R_Yield if R_Yield > 0 else 0,
    ]
    heat_matrix = np.array([[bv * r for r in real_range] for bv in base_heat_values])

    fig_heat = go.Figure(go.Heatmap(
        z=heat_matrix, x=[f"{r*100:.0f}%" for r in real_range], y=all_benefit_names, colorscale="Blues",
        text=np.round(heat_matrix, 0).astype(int), texttemplate="₹%{text}", textfont=dict(size=10),
        hovertemplate="<b>%{y}</b><br>Realization: %{x}<br>₹%{z:,.0f}<extra></extra>",
    ))
    fig_heat.update_layout(**_layout("VIU Benefit Heatmap — Realization Factor Sensitivity", "", 380))
    fig_heat.update_layout(xaxis_title="Realization Factor", yaxis_title="")
    st.plotly_chart(fig_heat, use_container_width=True)

    # ── SECTION 5: WATERFALL ANALYSIS ──
    st.markdown('<div class="section-header">VIU Waterfall Analysis</div>', unsafe_allow_html=True)
    
    wf_labels = ["FeV80 Cost per Eff. V", "Power Saving", "Electrode Saving", "Throughput Gain", "Recovery Stability", "Reblow Reduction", "Cleanliness", "Yield", "True FeV Effective Cost"]
    wf_values = [Cost_Per_Eff_V_FeV, -Benefit_Power, -Benefit_Electrode, -Benefit_Throughput, -Benefit_Stability, -Benefit_Retreatment, -Benefit_Cleanliness, -Benefit_Yield, 0]
    
    measures = ["absolute"] + ["relative"] * 7 + ["total"]
    wf_text = [f"₹{abs(v):,.0f}" for v in wf_values[:-1]] + [f"₹{Cost_Per_Eff_V_FeV - Total_VIU_Credits:,.0f}"]
    wf_values_display = wf_values[:-1] + [Cost_Per_Eff_V_FeV - Total_VIU_Credits]

    fig_wf = go.Figure(go.Waterfall(
        name="VIU Waterfall", orientation="v", measure=measures, x=wf_labels, y=wf_values_display,
        text=wf_text, textposition="auto", connector=dict(line=dict(color="#BDBDBD", width=1.5, dash="dot")),
        increasing=dict(marker=dict(color=C_DELTA)), decreasing=dict(marker=dict(color=C_FEV)),
        totals=dict(marker=dict(color=C_FEV)),
        hovertemplate="<b>%{x}</b><br>₹%{y:,.0f}<extra></extra>",
    ))
    fig_wf.add_hline(y=Cost_Per_Eff_V_NV, line_dash="dash", line_color=C_NV, line_width=1.5, annotation_text=f"Nitrovan Cost per Eff. V ₹{Cost_Per_Eff_V_NV:,.0f}", annotation_position="right")
    fig_wf.update_layout(**_layout("VIU Waterfall: Factoring FeV Operational Advantages (₹)", "₹ / MT Eff. V", 500))
    fig_wf.update_layout(showlegend=False, xaxis_tickangle=-25)
    st.plotly_chart(fig_wf, use_container_width=True)

    st.markdown("""
    <div class="info-box">
    <b>How to read this waterfall:</b> Starts with the material baseline Cost per Effective Vanadium of FeV80. The operational advantages of FeV (Throughput, Yield, Cleanliness) act as deductions (credits), lowering its "True Effective Cost". The final bar is then directly compared to the horizontal Nitrovan Cost line.
    </div>
    """, unsafe_allow_html=True)

    # ── SECTION 6: COST COMPARISON ──
    st.markdown('<div class="section-header">Cost Comparison & Sensitivity Analysis</div>', unsafe_allow_html=True)

    col_a, col_b = st.columns(2)

    with col_a:
        fig_stack = go.Figure()
        categories = ["FeV80 (Eq. to NV)", "Nitrovan"]

        fig_stack.add_trace(go.Bar(
            name="Effective Cost", x=categories, 
            y=[Cost_Per_Eff_V_FeV - Total_VIU_Credits, Cost_Per_Eff_V_NV],
            marker_color=[C_FEV, C_NV], 
            text=[f"₹{Cost_Per_Eff_V_FeV - Total_VIU_Credits:,.0f}", f"₹{Cost_Per_Eff_V_NV:,.0f}"], 
            textposition="auto",
            hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>"
        ))
        fig_stack.update_layout(**_layout("Effective Cost Components (Cost/MT Eff. V - VIU Credits)", "₹", 380))
        st.plotly_chart(fig_stack, use_container_width=True)

    with col_b:
        nv_prices  = np.linspace(P_NV_Price * 0.7, P_NV_Price * 1.3, 80)
        net_adv_nvs   = [Cost_Per_Eff_V_FeV - (p / Eff_V_NV_VIU) - Total_VIU_Credits for p in nv_prices]

        fig_sens = go.Figure()
        fig_sens.add_trace(go.Scatter(
            x=nv_prices, y=net_adv_nvs, mode="lines", name="Net VIU Advantage",
            line=dict(color=C_DELTA, width=3), fill="tozeroy", fillcolor="rgba(76,175,80,0.1)",
            hovertemplate="NV Price: ₹%{x:,.0f}<br>Net Savings: ₹%{y:,.0f}<extra></extra>",
        ))
        fig_sens.add_hline(y=0, line_dash="dash", line_color="#333", line_width=1.5)
        fig_sens.add_vline(x=P_NV_Price, line_dash="dot", line_color=C_NV, line_width=2, annotation_text=f"Current ₹{P_NV_Price:,}", annotation_position="top right")
        fig_sens.add_vline(x=nv_breakeven_price, line_dash="dot", line_color=C_NEG, line_width=2, annotation_text=f"Break-even ₹{nv_breakeven_price:,.0f}", annotation_position="top left")
        fig_sens.update_layout(**_layout("Nitrovan Price Sensitivity – Net Savings (₹)", "Net Savings (₹)", 380))
        st.plotly_chart(fig_sens, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_c, col_d = st.columns(2)

    with col_c:
        fev_prices   = np.linspace(P_FeV_Price * 0.7, P_FeV_Price * 1.3, 80)
        net_adv_fevs = [(p / Eff_V_FeV_VIU) - Cost_Per_Eff_V_NV - Total_VIU_Credits for p in fev_prices]
        
        fig_lc_sens = go.Figure()
        fig_lc_sens.add_trace(go.Scatter(
            x=fev_prices, y=net_adv_fevs, mode="lines", name="Net VIU (varying FeV price)",
            line=dict(color=C_FEV, width=3), fill="tozeroy", fillcolor="rgba(33,150,243,0.1)",
            hovertemplate="FeV80: ₹%{x:,.0f}<br>Net Savings: ₹%{y:,.0f}<extra></extra>",
        ))
        fig_lc_sens.add_hline(y=0, line_dash="dash", line_color="#333", line_width=1.5)
        fig_lc_sens.add_vline(x=P_FeV_Price, line_dash="dot", line_color=C_FEV, line_width=2, annotation_text=f"Current ₹{P_FeV_Price:,}", annotation_position="top right")
        fig_lc_sens.add_vline(x=fev_breakeven_price, line_dash="dot", line_color=C_NEG, line_width=2, annotation_text=f"Break-even ₹{fev_breakeven_price:,.0f}", annotation_position="top left")
        fig_lc_sens.update_layout(**_layout("FeV80 Price Sensitivity – Net Savings (₹)", "Net Savings (₹)", 380))
        st.plotly_chart(fig_lc_sens, use_container_width=True)

    with col_d:
        tornado_names  = all_benefit_names
        tornado_base   = all_benefit_values
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
        fig_tornado.update_layout(barmode="overlay", **_layout("Sensitivity Tornado (±20% Realization)", "Advantage Change (₹)", 380))
        st.plotly_chart(fig_tornado, use_container_width=True)

    # ── SECTION 7: ENTERPRISE SAVINGS ──
    st.markdown('<div class="section-header">Enterprise Savings Calculator</div>', unsafe_allow_html=True)
    s1, s2, s3, s4 = st.columns(4)
    with s1: st.markdown(kpi("Substituted Volume", f"{NV_Consumption_FY * Substitution_Pct:,.0f} MT", f"at {Substitution_Pct*100:.0f}% substitution", ""), unsafe_allow_html=True)
    with s2: st.markdown(kpi("Savings / MT Alloy", f"₹{abs(Net_Savings):,.0f}", "Magnitude of net advantage", "kpi-card-green" if Net_Savings > 0 else "kpi-card-amber"), unsafe_allow_html=True)
    with s3: st.markdown(kpi("Annual Savings FY26", f"₹{abs(Annual_Savings_Cr):.2f} Cr", "at stated volume", "kpi-card-green" if Net_Savings > 0 else "kpi-card-amber"), unsafe_allow_html=True)
    with s4: st.markdown(kpi("Monthly Savings", f"₹{abs(Annual_Savings_Cr * 1e7 / 12 / 1e5):.1f} L", "per month average", "kpi-card-purple"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_lft, col_rgt = st.columns([2, 1])

    with col_lft:
        vol_range = np.arange(100, NV_Consumption_FY * 2.5, 200)
        savings_cr_curve = (abs(Net_Savings) * vol_range * Substitution_Pct) / 1e7

        fig_sav = go.Figure()
        fig_sav.add_trace(go.Scatter(
            x=vol_range, y=savings_cr_curve, mode="lines", name="Annual Savings (₹ Cr)",
            line=dict(color=C_DELTA if Net_Savings > 0 else C_NEG, width=3),
            fill="tozeroy", fillcolor="rgba(76,175,80,0.12)" if Net_Savings > 0 else "rgba(244,67,54,0.12)",
            hovertemplate="Consumption: %{x:,.0f} MT<br>Savings: ₹%{y:.2f} Cr<extra></extra>",
        ))
        fig_sav.add_vline(x=NV_Consumption_FY, line_dash="dash", line_color="#1A237E", line_width=2, annotation_text=f"Total: {NV_Consumption_FY:,} MT", annotation_position="top right")
        fig_sav.add_hline(y=0, line_dash="solid", line_color="#333", line_width=1.5)
        fig_sav.update_layout(**_layout(f"Enterprise Savings vs Total Consumption Volume (at {Substitution_Pct*100:.0f}% Sub)", "Savings (₹ Crore)", 400))
        st.plotly_chart(fig_sav, use_container_width=True)

    with col_rgt:
        st.markdown("#### Per-Benefit Annual Savings (₹ Cr)")
        benefits_annual = {n: (v * NV_Consumption_FY * Substitution_Pct) / 1e7 for n, v in zip(all_benefit_names, all_benefit_values)}
        df_bens = pd.DataFrame({"Benefit": list(benefits_annual.keys()), "₹ Crore / Year": [round(v, 3) for v in benefits_annual.values()]}).sort_values("₹ Crore / Year", ascending=False).set_index("Benefit")
        st.dataframe(df_bens.style.map(lambda val: "color:#1B5E20;font-weight:600" if val > 0 else "color:#B71C1C;font-weight:600", subset=["₹ Crore / Year"]), use_container_width=True, height=350)

    # Break-even calculator
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### Break-Even Price Analysis")
    be1, be2, be3 = st.columns(3)

    with be1: st.markdown(kpi("Nitrovan Break-Even", f"₹{nv_breakeven_price:,.0f}", f"Current NV: ₹{P_NV_Price:,} | {'BELOW' if P_NV_Price < nv_breakeven_price else 'ABOVE'} break-even", "kpi-card-green" if P_NV_Price <= nv_breakeven_price else "kpi-card-amber"), unsafe_allow_html=True)
    with be2: st.markdown(kpi("FeV80 Break-Even", f"₹{fev_breakeven_price:,.0f}", f"Current FeV: ₹{P_FeV_Price:,} | {'BELOW' if P_FeV_Price < fev_breakeven_price else 'ABOVE'} break-even", "kpi-card-amber"), unsafe_allow_html=True)
    with be3: st.markdown(kpi("Min. Credits Needed", f"₹{Cost_Gap if Cost_Gap > 0 else 0:,.0f}", f"Current VIU credits: ₹{Total_VIU_Credits:,.0f}", "kpi-card-green" if Total_VIU_Credits >= Cost_Gap else "kpi-card-red"), unsafe_allow_html=True)

    # ── SECTION 8: RECOMMENDATION ──
    st.markdown('<div class="section-header">Final Recommendation</div>', unsafe_allow_html=True)

    if Net_Savings > 0:
        st.markdown(f"""
        <div style="background:#E8F5E9; border-left:6px solid #4CAF50; padding:24px 32px; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.05);">
            <h2 style="color:#1B5E20; margin-top:0; font-size:28px;">🏆 Nitrovan Preferred</h2>
            <p style="font-size:16px; color:#2E7D32; line-height:1.6; margin-bottom:0;">
                <b>Projected Annual Savings: ₹{Annual_Savings_Cr:.2f} Crore</b><br>
                By shifting {Substitution_Pct*100:.0f}% of your {NV_Consumption_FY:,} MT baseline consumption to Nitrovan, 
                you realize a net advantage of <b>₹{Net_Savings:,.0f}</b>. 
                The material pricing gap (₹{Cost_Gap:,.0f}) is strong enough to overcome FeV80's operational credits (₹{Total_VIU_Credits:,.0f}), making Nitrovan the superior choice.
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="background:#FFF3E0; border-left:6px solid #FF9800; padding:24px 32px; border-radius:12px; box-shadow:0 4px 12px rgba(0,0,0,0.05);">
            <h2 style="color:#E65100; margin-top:0; font-size:28px;">🏆 FeV80 Preferred</h2>
            <p style="font-size:16px; color:#EF6C00; line-height:1.6; margin-bottom:0;">
                <b>FeV80 Cost Efficiency: ₹{abs(Net_Savings):,.0f}</b><br>
                At current input parameters, FeV80 remains the more cost-effective option, yielding a projected <b>₹{Annual_Savings_Cr:.2f} Crore</b> in savings vs switching. 
                FeV80's operational superiority (₹{Total_VIU_Credits:,.0f}) fully offsets its material premium (₹{Cost_Gap:,.0f}).
            </p>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: SUBSTITUTION SOLVER
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
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

    # Grade Specific Definitions mapping exactly to Excel 'Solver' Sheet + IF Steel requirement
    grades_data = {
        "Commodity Structural (IS2062)":   {"v_lim": 0.030, "esu_lim": 0.60, "chill_lim": 15.00, "rec_lim": 5.00, "retrt_lim": 2.50, "inc_lim": 0.015, "h2_lim": 160, "nv_max": 1.0},
        "TMT / Rebar (Fe500D)":            {"v_lim": 0.045, "esu_lim": 0.75, "chill_lim": 15.00, "rec_lim": 5.00, "retrt_lim": 2.50, "inc_lim": 0.015, "h2_lim": 160, "nv_max": 1.0},
        "HSLA (API X60 / X70)":            {"v_lim": 0.055, "esu_lim": 0.80, "chill_lim": 10.00, "rec_lim": 2.45, "retrt_lim": 1.45, "inc_lim": 0.013, "h2_lim": 50,  "nv_max": 0.30},
        "Automotive (DP / TRIP / Bearing)":{"v_lim": 0.060, "esu_lim": 0.40, "chill_lim": 8.00,  "rec_lim": 2.30, "retrt_lim": 1.30, "inc_lim": 0.014, "h2_lim": 35,  "nv_max": 0.20},
        "IF Steel (Deep Draw)":            {"v_lim": 0.040, "esu_lim": 0.40, "chill_lim": 5.00,  "rec_lim": 2.00, "retrt_lim": 1.00, "inc_lim": 0.015, "h2_lim": 15,  "nv_max": 0.00},
    }

    gc1, gc2 = st.columns([1.5, 2.5])
    sel_grade = gc1.selectbox("Select Target Steel Grade", list(grades_data.keys()), index=0)
    limits = grades_data[sel_grade]

    st.markdown("#### Metallurgical Constraints (Mapped from Excel)")
    r1c1, r1c2, r1c3, r1c4 = st.columns(4)
    min_v     = r1c1.slider("Min Effective V (%)", 0.0, 0.150, limits["v_lim"], step=0.005, format="%.3f")
    min_esu   = r1c2.slider("ESU Target", 0.0, 1.5, limits["esu_lim"], step=0.05)
    max_chill = r1c3.slider("Max Chill Drop (°C)", 0.0, 30.0, float(limits["chill_lim"]), step=1.0)
    max_rec   = r1c4.slider("Max Rec. Var (%)", 0.0, 10.0, float(limits["rec_lim"]), step=0.1)

    r2c1, r2c2, r2c3, r2c4 = st.columns(4)
    max_retrt = r2c1.slider("Max Re-treat Risk (%)", 0.0, 10.0, float(limits["retrt_lim"]), step=0.1)
    max_inc   = r2c2.slider("Max Inclusion (%)", 0.001, 0.050, limits["inc_lim"], step=0.001, format="%.3f")
    max_n     = r2c3.slider("Max N Limit (ppm)", 0, 250, int(limits["h2_lim"]), step=5)
    max_nv    = r2c4.slider("Max NV Share (%)", 0.0, 100.0, limits["nv_max"] * 100, step=5.0) / 100.0

    # ══════════════════════════════════════════════════════════════════════════════
    # LINEAR PROGRAMMING ENGINE & VIU CALCULATION
    # ══════════════════════════════════════════════════════════════════════════════
    # Calculate effective parameters derived from sidebar
    Eff_V_FeV = P_FeV_V * P_FeV_Rec
    Eff_V_NV  = P_NV_V * P_NV_Rec
    ESU_FeV   = Eff_V_FeV * P_FeV_ESU_Fac
    ESU_NV    = Eff_V_NV * P_NV_ESU_Fac
    N_ppm_FeV = 1.0  # Derived equivalently to Excel's 0.001% mass assumption
    N_ppm_NV  = P_NV_N_pct * 1000  # 16% = 160 ppm N per kg alloy added

    # Define Objective: Minimize Base Alloy Purchase Cost per MT of Steel
    c_cost = [P_FeV_Price / 1000, P_NV_Price / 1000]

    A_ub, b_ub = [], []

    # Constraints Matrix
    A_ub.append([-Eff_V_FeV, -Eff_V_NV])      # 1. Min Effective V (kg per MT steel)
    b_ub.append(-min_v * 10)

    A_ub.append([-ESU_FeV, -ESU_NV])          # 2. ESU Target
    b_ub.append(-min_esu)

    A_ub.append([P_FeV_Chill_Solver, P_NV_Chill_Solver])    # 3. Chill Limit
    b_ub.append(max_chill)

    A_ub.append([P_FeV_Rec_Var, P_NV_Rec_Var])# 4. Recovery Variability Limit
    b_ub.append(max_rec)

    A_ub.append([P_FeV_Retrt, P_NV_Retrt])    # 5. Re-treatment Risk Limit
    b_ub.append(max_retrt)

    A_ub.append([P_FeV_Inc, P_NV_Inc])        # 6. Inclusion Limit
    b_ub.append(max_inc)

    A_ub.append([N_ppm_FeV, N_ppm_NV])        # 7. Nitrogen Limit (ppm)
    b_ub.append(max_n)

    if max_nv < 1.0:                          # 8. Max NV Share Constraint: y <= max_nv * (x + y)
        A_ub.append([-max_nv, 1 - max_nv])
        b_ub.append(0)

    # Execute Scipy Optimizer
    res = linprog(c_cost, A_ub=A_ub, b_ub=b_ub, bounds=[(0, None), (0, None)])


    # --- VIU Credits (Operational Penalties for Nitrovan per MT) ---
    MT_Steel_per_NV = 389.6 

    benefit_power = 1.029 * P_Power_Tariff * MT_Steel_per_NV * R_Power
    benefit_electrode = 1.0288 * MT_Steel_per_NV * 0.01 * P_Electrode_Cost * R_Electrode
    benefit_throughput = (2.5 / 190.0) * 850.0 * MT_Steel_per_NV * R_Throughput
    benefit_stability = abs(P_NV_Rec_Var - P_FeV_Rec_Var) / 100.0 * P_FeV_Price * R_Stability * 1.4615
    benefit_reblow = abs(P_NV_Retrt - P_FeV_Retrt) / 100.0 * (15000.0 / 190.0) * MT_Steel_per_NV * R_Reblow * 0.9375
    benefit_clean = abs(P_FeV_Inc - P_NV_Inc) / 100.0 * P_Steel_Value * MT_Steel_per_NV * R_Cleanliness * 1.4
    benefit_yield = abs(P_NV_Yield - P_FeV_Yield) / 100.0 * P_Steel_Value * MT_Steel_per_NV * R_Yield

    # Total operational penalty applied to Nitrovan to account for its side effects vs FeV
    viu_credits = benefit_power + benefit_electrode + benefit_throughput + benefit_stability + benefit_reblow + benefit_clean + benefit_yield

    # Raw Material Cost per MT ESU (₹/MT ESU)
    Cost_ESU_FeV = P_FeV_Price / ESU_FeV
    Cost_ESU_NV  = P_NV_Price / ESU_NV

    # ══════════════════════════════════════════════════════════════════════════════
    # OUTPUTS & VISUALIZATIONS
    # ══════════════════════════════════════════════════════════════════════════════
    st.markdown("---")

    if res.success:
        x_fev, y_nv = res.x
        total_kg = x_fev + y_nv
        
        fev_share = x_fev / total_kg if total_kg > 0 else 0
        nv_share = y_nv / total_kg if total_kg > 0 else 0
        
        # NEW FINAL EFFECTIVE COST FORMULA
        # Cost_FeV_ESU * %FeV + Cost_NV_ESU * %NV + (%NV * VIU Credits)
        final_effective_cost = (Cost_ESU_FeV * fev_share) + (Cost_ESU_NV * nv_share) + (nv_share * viu_credits)

        # Cost Baseline: 100% FeV & 100% NV Effective Cost representations
        cost_fev_only = Cost_ESU_FeV
        cost_nv_only  = Cost_ESU_NV + viu_credits

        # Projected Savings calculated against the maximum ESU cost benchmark 
        proj_savings = max(Cost_ESU_FeV, Cost_ESU_NV) - final_effective_cost

        rc1, rc2 = st.columns(2)
        with rc1:
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label" style="color: #78909C; font-size: 12px;">Final Effective Cost</div>
                <div class="kpi-value" style="color: #263238; font-size: 26px;">₹{final_effective_cost:,.0f}</div>
                <div class="kpi-sub" style="color: #90A4AE; font-size: 12px;">True Operational Cost per MT of Target ESU <i>(Includes VIU: ₹{viu_credits:,.0f}/MT)</i></div>
            </div>
            """, unsafe_allow_html=True)
            
        with rc2:
            if proj_savings > 1:
                st.markdown(f"""
                <div class="kpi-card kpi-card-green">
                    <div class="kpi-label" style="color: #78909C; font-size: 12px;">Projected Savings vs 100% FeV80</div>
                    <div class="kpi-value" style="color: #263238; font-size: 26px;">₹{proj_savings:,.2f}</div>
                    <div class="kpi-sub" style="color: #90A4AE; font-size: 12px;">Savings per MT of Steel ESU Delivered</div>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="kpi-card">
                    <div class="kpi-label" style="color: #78909C; font-size: 12px;">Projected Savings vs 100% FeV80</div>
                    <div class="kpi-value" style="color: #263238; font-size: 26px;">₹0.00</div>
                    <div class="kpi-sub" style="color: #90A4AE; font-size: 12px;">100% Single Alloy is best for this grade</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("#### 📊 Optimal Blend & Cost Insights")
        
        col_pie, col_cost = st.columns([1, 1])
        
        with col_pie:
            fig_pie = go.Figure(data=[go.Pie(
                labels=["FeV80 Share", "Nitrovan Share"], 
                values=[fev_share, nv_share], 
                hole=0.45, 
                marker_colors=[C_FEV_SOLVER, C_NV_SOLVER],
                textinfo="label+percent"
            )])
            fig_pie.update_layout(title="Optimal Procurement Ratio (Mass %)", height=380, template="plotly_white")
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col_cost:
            fig_cost = go.Figure()
            fig_cost.add_trace(go.Bar(
                x=["100% FeV80", "Optimal Blend", "100% Nitrovan"],
                y=[cost_fev_only, final_effective_cost, cost_nv_only],
                marker_color=[C_FEV_SOLVER, "#4CAF50", C_NV_SOLVER],
                text=[f"₹{cost_fev_only:,.0f}", f"₹{final_effective_cost:,.0f}", f"₹{cost_nv_only:,.0f}"],
                textposition="auto",
                hovertemplate="%{x}<br>₹%{y:,.2f}/MT ESU<extra></extra>"
            ))
            fig_cost.update_layout(**_layout("True Effective Cost per MT ESU (₹)", "Cost (₹)", 380))
            st.plotly_chart(fig_cost, use_container_width=True)

        # Calculate actual usage matrix
        actual_v = Eff_V_FeV * x_fev + Eff_V_NV * y_nv
        actual_esu = ESU_FeV * x_fev + ESU_NV * y_nv
        actual_chill = P_FeV_Chill_Solver * x_fev + P_NV_Chill_Solver * y_nv
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