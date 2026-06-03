"""
⚗️ Aluminium VIU Dashboard
================================================
Value-In-Use Economic Analysis | Primary Al Ingot vs Secondary Al Ingot vs Al Notch Bar
This app directly mirrors the React implementation and underlying Excel logic.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIGURATION & CUSTOM CSS
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Aluminium VIU Dashboard",
    page_icon="⚗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .kpi-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        display: flex;
        flex-direction: column;
        height: 100%;
        border-left: 4px solid;
    }
    .kpi-label {
        font-size: 10px;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 4px;
        line-height: 1.2;
    }
    .kpi-val {
        font-size: 20px;
        font-weight: 800;
        margin: 4px 0;
        line-height: 1.2;
    }
    .kpi-sub {
        font-size: 10px;
        color: #94a3b8;
        margin-top: auto;
        line-height: 1.2;
    }
    .section-header {
        font-size: 18px;
        font-weight: 700;
        color: #1e293b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        border-bottom: 2px solid #3b82f6;
        padding-bottom: 8px;
        margin-top: 32px;
        margin-bottom: 24px;
    }
    .custom-table {
        width: 100%;
        font-size: 14px;
        text-align: left;
        border-collapse: collapse;
        background: white;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid #e2e8f0;
    }
    .custom-table th {
        padding: 12px 16px;
        font-size: 12px;
        text-transform: uppercase;
        color: #64748b;
        border-bottom: 1px solid #e2e8f0;
    }
    .custom-table td {
        padding: 12px 16px;
        border-bottom: 1px solid #f1f5f9;
    }
</style>
""", unsafe_allow_html=True)

# Format Helpers
def fmt_cur(val): return f"₹{val:,.0f}"
def fmt_num(val, dec=1): return f"{val:,.{dec}f}"

# Colors
COLORS = {
    "primary": "#3b82f6", # Blue
    "secondary": "#f97316", # Orange
    "notch": "#a855f7", # Purple
    "delta": "#ef4444", # Red
    "benefit": "#22c55e", # Green
    "grid": "#f1f5f9",
    "text": "#334155"
}

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR PARAMETERS (Matching React State)
# ══════════════════════════════════════════════════════════════════════════════
st.sidebar.markdown("<h2 style='color: white; margin-bottom: 0;'>⚗️ Aluminium VIU</h2>", unsafe_allow_html=True)
st.sidebar.markdown("<div style='background: rgba(255,255,255,0.1); padding: 8px; border-radius: 6px; margin-bottom: 20px;'><span style='font-size: 10px; font-weight: bold; color: #cbd5e1; text-transform: uppercase;'>A. Comparison Selection</span><br/><span style='font-size: 12px; font-weight: bold; color: white;'>Primary vs Secondary vs Notch Bar</span></div>", unsafe_allow_html=True)

st.sidebar.markdown("<h4 style='color:#93c5fd; font-size:12px; text-transform:uppercase; border-bottom:1px solid #3b82f6; padding-bottom:4px;'>B. Financial</h4>", unsafe_allow_html=True)
pPriPrice = st.sidebar.slider("Primary Al (₹/MT)", 200000, 600000, 380000, 1000)
pSecPrice = st.sidebar.slider("Secondary Al (₹/MT)", 200000, 600000, 340000, 1000)
pNotchPrice = st.sidebar.slider("Notch Bar (₹/MT)", 200000, 600000, 335000, 1000)
pPowerTariff = st.sidebar.slider("Power (₹/kWh)", 2.0, 15.0, 6.5, 0.1)
pElectrodeCost = st.sidebar.slider("Electrode (₹/kg)", 100, 800, 240, 10)
pSteelValue = st.sidebar.slider("Steel Value (₹/MT)", 30000, 150000, 60000, 1000)
pSlagCost = st.sidebar.slider("Slag (₹/MT)", 100, 3000, 800, 100)
pMarginSteel = st.sidebar.slider("CM (₹/MT)", 500, 10000, 2800, 100)
pRetreatmentCost = st.sidebar.slider("Re-treat (₹/heat)", 5000, 50000, 15000, 1000)

st.sidebar.markdown("<h4 style='color:#93c5fd; font-size:12px; text-transform:uppercase; border-bottom:1px solid #3b82f6; padding-bottom:4px; margin-top:16px;'>C. Technical</h4>", unsafe_allow_html=True)
activeAlTarget = st.sidebar.slider("Active Al Target (kg/T)", 0.5, 5.0, 2.0, 0.1)
pPriPurity = st.sidebar.slider("Pri Purity (%)", 90.0, 100.0, 99.0, 0.1)
pSecPurity = st.sidebar.slider("Sec Purity (%)", 80.0, 99.0, 97.0, 0.1)
pNotchPurity = st.sidebar.slider("Notch Purity (%)", 80.0, 99.0, 95.0, 0.1)
pPriRec = st.sidebar.slider("Pri Recovery (%)", 20.0, 80.0, 49.0, 1.0)
pSecRec = st.sidebar.slider("Sec Recovery (%)", 20.0, 80.0, 46.0, 1.0)
pNotchRec = st.sidebar.slider("Notch Recovery (%)", 20.0, 80.0, 46.0, 1.0)

st.sidebar.markdown("<h4 style='color:#93c5fd; font-size:12px; text-transform:uppercase; border-bottom:1px solid #3b82f6; padding-bottom:4px; margin-top:16px;'>D. Operational</h4>", unsafe_allow_html=True)
pHeatSize = st.sidebar.slider("Heat Size (MT)", 50, 350, 190, 5)
pLfEff = st.sidebar.slider("LF Efficiency (%)", 10.0, 80.0, 40.0, 1.0)
pTimeSec = st.sidebar.slider("Time Delay - Sec (min)", 0.0, 10.0, 0.5, 0.1)
pTimeNotch = st.sidebar.slider("Time Delay - Notch (min)", 0.0, 10.0, 1.0, 0.1)
pDrossSec = st.sidebar.slider("Dross - Sec (kg/MT)", 0, 100, 20, 1)
pDrossNotch = st.sidebar.slider("Dross - Notch (kg/MT)", 0, 100, 40, 1)
pSlagSec = st.sidebar.slider("Slag - Sec (kg/MT)", 0.0, 150.0, 55.4, 0.1)
pSlagNotch = st.sidebar.slider("Slag - Notch (kg/MT)", 0.0, 150.0, 55.0, 0.1)
pOverdoseSec = st.sidebar.slider("Overdose - Sec (%)", 0.0, 10.0, 0.5, 0.1)
pOverdoseNotch = st.sidebar.slider("Overdose - Notch (%)", 0.0, 10.0, 0.5, 0.1)
pInclusionSec = st.sidebar.slider("Reject Drop - Sec (%)", 0.0, 0.1, 0.010, 0.005, format="%.3f")
pInclusionNotch = st.sidebar.slider("Reject Drop - Notch (%)", 0.0, 0.1, 0.025, 0.005, format="%.3f")
pYieldSec = st.sidebar.slider("Yield Drop - Sec (%)", 0.0, 0.1, 0.010, 0.005, format="%.3f")
pYieldNotch = st.sidebar.slider("Yield Drop - Notch (%)", 0.0, 0.1, 0.020, 0.005, format="%.3f")
pRetreatSec = st.sidebar.slider("Re-treat - Sec (%)", 0.0, 5.0, 0.66, 0.05)
pRetreatNotch = st.sidebar.slider("Re-treat - Notch (%)", 0.0, 5.0, 1.33, 0.05)

st.sidebar.markdown("<h4 style='color:#93c5fd; font-size:12px; text-transform:uppercase; border-bottom:1px solid #3b82f6; padding-bottom:4px; margin-top:16px;'>E. Realization</h4>", unsafe_allow_html=True)
rPower = st.sidebar.slider("Power (%)", 0.0, 100.0, 100.0, 1.0)
rElectrode = st.sidebar.slider("Electrode (%)", 0.0, 100.0, 100.0, 1.0)
rThroughput = st.sidebar.slider("Throughput (%)", 0.0, 100.0, 40.0, 1.0)
rStability = st.sidebar.slider("Stability (%)", 0.0, 100.0, 50.0, 1.0)
rSlag = st.sidebar.slider("Slag (%)", 0.0, 100.0, 50.0, 1.0)
rCleanliness = st.sidebar.slider("Cleanliness (%)", 0.0, 100.0, 40.0, 1.0)
rYield = st.sidebar.slider("Yield (%)", 0.0, 100.0, 50.0, 1.0)
rReblow = st.sidebar.slider("Reblow (%)", 0.0, 100.0, 75.0, 1.0)

st.sidebar.markdown("<h4 style='color:#93c5fd; font-size:12px; text-transform:uppercase; border-bottom:1px solid #3b82f6; padding-bottom:4px; margin-top:16px;'>F. Enterprise</h4>", unsafe_allow_html=True)
st.sidebar.markdown("<span style='font-size: 12px; color: #cbd5e1;'>Baseline Alloy</span><br/><div style='background: rgba(255,255,255,0.1); padding: 6px; border-radius: 4px; font-size: 14px; margin-bottom: 12px; color: #94a3b8;'>Primary Al Ingot (Locked)</div>", unsafe_allow_html=True)
consumptionMt = st.sidebar.slider("Consumption (MT Alloy)", 1000, 20000, 4325, 100)
substitutionPct = st.sidebar.slider("% Substitution", 0.0, 100.0, 50.0, 5.0)

# ══════════════════════════════════════════════════════════════════════════════
# CORE ENGINE (React Logic Transpiled)
# ══════════════════════════════════════════════════════════════════════════════

# 1. Efficiency & Steel Supported
effPri = (pPriPurity / 100) * (pPriRec / 100)
effSec = (pSecPurity / 100) * (pSecRec / 100)
effNotch = (pNotchPurity / 100) * (pNotchRec / 100)

reqPri = 1 / effPri 
reqSec = 1 / effSec
reqNotch = 1 / effNotch

rawCostPriEff = pPriPrice * reqPri
rawCostSecEff = pSecPrice * reqSec
rawCostNotchEff = pNotchPrice * reqNotch

steelSuppPri = 1000 * effPri / activeAlTarget
steelSuppSec = 1000 * effSec / activeAlTarget
steelSuppNotch = 1000 * effNotch / activeAlTarget

# 2. Exact Excel Formulas per MT Alloy
pPowerSec = ((pDrossSec * 2.5) / 3.6 / (pLfEff/100)) * pPowerTariff * (rPower/100)
pElecSec = (pPowerSec / pPowerTariff) * 0.0015 * pElectrodeCost * (rElectrode/100) if pPowerTariff > 0 else 0
pThroughputSec = (pTimeSec / pHeatSize) * pMarginSteel * steelSuppSec * (rThroughput/100)
pRecSec = (pOverdoseSec/100) * (pSecPrice/1000) * steelSuppSec * (rStability/100)
pSlagHandlingSec = pSlagSec * (pSlagCost/1000) * (rSlag/100)
pIncSec = (pInclusionSec/100) * pSteelValue * steelSuppSec * (rCleanliness/100)
pYieldDropSec = (pYieldSec/100) * pSteelValue * steelSuppSec * (rYield/100)
pRetreatDropSec = (pRetreatSec/100) * pRetreatmentCost * (steelSuppSec / pHeatSize) * (rReblow/100)

totalPenSecAlloy = pPowerSec + pElecSec + pThroughputSec + pRecSec + pSlagHandlingSec + pIncSec + pYieldDropSec + pRetreatDropSec
totalPenSecEff = totalPenSecAlloy * reqSec

pPowerNotch = ((pDrossNotch * 2.5) / 3.6 / (pLfEff/100)) * pPowerTariff * (rPower/100)
pElecNotch = (pPowerNotch / pPowerTariff) * 0.0015 * pElectrodeCost * (rElectrode/100) if pPowerTariff > 0 else 0
pThroughputNotch = (pTimeNotch / pHeatSize) * pMarginSteel * steelSuppNotch * (rThroughput/100)
pRecNotch = (pOverdoseNotch/100) * (pNotchPrice/1000) * steelSuppNotch * (rStability/100)
pSlagHandlingNotch = pSlagNotch * (pSlagCost/1000) * (rSlag/100)
pIncNotch = (pInclusionNotch/100) * pSteelValue * steelSuppNotch * (rCleanliness/100)
pYieldDropNotch = (pYieldNotch/100) * pSteelValue * steelSuppNotch * (rYield/100)
pRetreatDropNotch = (pRetreatNotch/100) * pRetreatmentCost * (steelSuppNotch / pHeatSize) * (rReblow/100)

totalPenNotchAlloy = pPowerNotch + pElecNotch + pThroughputNotch + pRecNotch + pSlagHandlingNotch + pIncNotch + pYieldDropNotch + pRetreatDropNotch
totalPenNotchEff = totalPenNotchAlloy * reqNotch

# 3. Net Costs
netCostPri = rawCostPriEff 
netCostSec = rawCostSecEff + totalPenSecEff
netCostNotch = rawCostNotchEff + totalPenNotchEff

# 4. Enterprise Savings
options = [
    {'name': 'Primary', 'netCost': netCostPri, 'rawCost': rawCostPriEff, 'eff': effPri, 'req': reqPri},
    {'name': 'Secondary', 'netCost': netCostSec, 'rawCost': rawCostSecEff, 'eff': effSec, 'req': reqSec},
    {'name': 'Notch Bar', 'netCost': netCostNotch, 'rawCost': rawCostNotchEff, 'eff': effNotch, 'req': reqNotch}
]

baselineObj = options[0] # Fixed to Primary
bestOpt = min(options, key=lambda x: x['netCost'])

totalEffAlDemand = consumptionMt * baselineObj['eff']

gapRawPriSec = rawCostPriEff - rawCostSecEff
gapRawPriNotch = rawCostPriEff - rawCostNotchEff
saveNetSec = netCostPri - netCostSec
saveNetNotch = netCostPri - netCostNotch

annualSaveSecCr = (totalEffAlDemand * saveNetSec * (substitutionPct/100)) / 1e7
annualSaveNotchCr = (totalEffAlDemand * saveNetNotch * (substitutionPct/100)) / 1e7

maxEdge = max(0, baselineObj['netCost'] - bestOpt['netCost'])
annualSavingsCr = (totalEffAlDemand * maxEdge * (substitutionPct/100)) / 1e7

# Break Even Prices
beSecPrice = (netCostPri - totalPenSecEff) * effSec
beNotchPrice = (netCostPri - totalPenNotchEff) * effNotch
bestAltNet = min(netCostSec, netCostNotch)
bePriPrice = bestAltNet * effPri

# Dictionaries for easy active state referencing
penSecBase = [pPowerSec, pElecSec, pThroughputSec, pRecSec, pSlagHandlingSec, pIncSec, pYieldDropSec, pRetreatDropSec]
penNotchBase = [pPowerNotch, pElecNotch, pThroughputNotch, pRecNotch, pSlagHandlingNotch, pIncNotch, pYieldDropNotch, pRetreatDropNotch]
penaltyLabels = ["Power", "Electrode", "Throughput", "Recovery Buffer", "Slag Handling", "Inclusion Risk", "Yield Loss", "Re-treatment"]


# ══════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD UI
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div style="background: linear-gradient(135deg, #1A237E, #1565C0); padding: 24px; border-radius: 16px; color: white; margin-bottom: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
    <h1 style="margin:0; font-size: 28px; font-weight: 800;">⚗️ Aluminium VIU Dashboard</h1>
    <p style="margin: 8px 0 0 0; font-size: 14px; color: #bfdbfe;">Value-In-Use Economic Analysis | Primary Al Ingot vs Secondary Al Ingot vs Al Notch Bar</p>
</div>
""", unsafe_allow_html=True)

# --- KPI Cards ---
def render_kpi(label, value, sub, border_hex, is_positive_logic=None):
    if is_positive_logic is True:
        val_color = "#16a34a" # green
    elif is_positive_logic is False:
        val_color = "#dc2626" # red
    else:
        val_color = "#1e293b" # default dark
        
    return f"""
    <div class="kpi-card" style="border-color: {border_hex};">
        <span class="kpi-label">{label}</span>
        <span class="kpi-val" style="color: {val_color};">{value}</span>
        <span class="kpi-sub">{sub}</span>
    </div>
    """

# ROW 1 & 2 & 3 in a grid
c1, c2, c3 = st.columns(3)
with c1: st.markdown(render_kpi("Primary Al Price", fmt_cur(pPriPrice), "Market Price", COLORS["primary"]), unsafe_allow_html=True)
with c2: st.markdown(render_kpi("Secondary Al Price", fmt_cur(pSecPrice), "Market Price", COLORS["secondary"]), unsafe_allow_html=True)
with c3: st.markdown(render_kpi("Notch Bar Price", fmt_cur(pNotchPrice), "Market Price", COLORS["notch"]), unsafe_allow_html=True)

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

c4, c5, c6 = st.columns(3)
with c4: st.markdown(render_kpi("Al Cost Gap - Pri vs Sec", fmt_cur(gapRawPriSec), "Raw Cost spread / MT Eff Al", "#fb923c", gapRawPriSec > 0), unsafe_allow_html=True)
with c5: st.markdown(render_kpi("Net Savings - Sec vs Pri", fmt_cur(saveNetSec), "Net advantage of Sec / MT", COLORS["secondary"], saveNetSec > 0), unsafe_allow_html=True)
with c6: st.markdown(render_kpi("Annual Savings (Sec)", f"₹{abs(annualSaveSecCr):.2f} Cr", "Positive Savings" if annualSaveSecCr >= 0 else "Loss / Penalty", "#22c55e" if annualSaveSecCr >= 0 else "#ef4444", annualSaveSecCr >= 0), unsafe_allow_html=True)

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

c7, c8, c9 = st.columns(3)
with c7: st.markdown(render_kpi("Al Cost Gap - Pri vs Notch", fmt_cur(gapRawPriNotch), "Raw Cost spread / MT Eff Al", "#c084fc", gapRawPriNotch > 0), unsafe_allow_html=True)
with c8: st.markdown(render_kpi("Net Savings - Notch vs Pri", fmt_cur(saveNetNotch), "Net advantage of Notch / MT", COLORS["notch"], saveNetNotch > 0), unsafe_allow_html=True)
with c9: st.markdown(render_kpi("Annual Savings (Notch)", f"₹{abs(annualSaveNotchCr):.2f} Cr", "Positive Savings" if annualSaveNotchCr >= 0 else "Loss / Penalty", "#22c55e" if annualSaveNotchCr >= 0 else "#ef4444", annualSaveNotchCr >= 0), unsafe_allow_html=True)


# --- VIU Economic Synthesis ---
st.markdown("<div class='section-header'>VIU Economic Synthesis</div>", unsafe_allow_html=True)
synthesis_html = f"""
<table class="custom-table">
    <tr style="background: #f8fafc;">
        <th style="width: 25%;">Metric</th>
        <th style="width: 25%; text-align: center; color: #1e40af; background: #eff6ff;">Primary Al Ingot</th>
        <th style="width: 25%; text-align: center; color: #c2410c; background: #fff7ed;">Secondary Al Ingot</th>
        <th style="width: 25%; text-align: center; color: #6b21a8; background: #faf5ff;">Al Notch Bar</th>
    </tr>
    <tr>
        <td style="font-weight: 500; color: #475569;">Market Price (₹/MT Alloy)</td>
        <td style="text-align: center;">{fmt_cur(pPriPrice)}</td>
        <td style="text-align: center;">{fmt_cur(pSecPrice)}</td>
        <td style="text-align: center;">{fmt_cur(pNotchPrice)}</td>
    </tr>
    <tr>
        <td style="font-weight: 500; color: #475569;">Effective Al Recovery (%)</td>
        <td style="text-align: center;">{effPri*100:.2f}%</td>
        <td style="text-align: center;">{effSec*100:.2f}%</td>
        <td style="text-align: center;">{effNotch*100:.2f}%</td>
    </tr>
    <tr>
        <td style="font-weight: 500; color: #475569;">Raw Cost per MT Eff Al (₹)</td>
        <td style="text-align: center; font-family: monospace;">{fmt_cur(rawCostPriEff)}</td>
        <td style="text-align: center; font-family: monospace;">{fmt_cur(rawCostSecEff)}</td>
        <td style="text-align: center; font-family: monospace;">{fmt_cur(rawCostNotchEff)}</td>
    </tr>
    <tr style="background: rgba(239, 68, 68, 0.05);">
        <td style="font-weight: 500; color: #dc2626;">Total Op. Penalties (₹/MT Eff Al)</td>
        <td style="text-align: center; color: #94a3b8;">Baseline</td>
        <td style="text-align: center; color: #dc2626; font-weight: bold;">+{fmt_cur(totalPenSecEff)}</td>
        <td style="text-align: center; color: #dc2626; font-weight: bold;">+{fmt_cur(totalPenNotchEff)}</td>
    </tr>
    <tr style="background: #f8fafc; border-top: 2px solid #cbd5e1;">
        <td style="font-weight: 800; color: #1e293b; font-size: 15px;">Net Adjusted Cost per MT Eff Al</td>
        <td style="text-align: center; font-size: 18px; font-weight: 800; color: {'#16a34a' if bestOpt['name']=='Primary' else '#334155'};">{fmt_cur(netCostPri)}</td>
        <td style="text-align: center; font-size: 18px; font-weight: 800; color: {'#16a34a' if bestOpt['name']=='Secondary' else '#334155'};">{fmt_cur(netCostSec)}</td>
        <td style="text-align: center; font-size: 18px; font-weight: 800; color: {'#16a34a' if bestOpt['name']=='Notch Bar' else '#334155'};">{fmt_cur(netCostNotch)}</td>
    </tr>
</table>
"""
st.markdown(synthesis_html, unsafe_allow_html=True)


# --- Detailed Penalty Breakdown ---
st.markdown("<div class='section-header'>Detailed Penalty Breakdown</div>", unsafe_allow_html=True)

view_alt = st.radio("Select View:", ["Secondary Al Ingot", "Al Notch Bar"], horizontal=True)

# Select Active data
if view_alt == "Secondary Al Ingot":
    activeBasePen = penSecBase
    activeTotalEff = totalPenSecEff
    activeReq = reqSec
    activeRaw = rawCostSecEff
    activeNet = netCostSec
    altName = "Secondary"
    c_alt = COLORS["secondary"]
else:
    activeBasePen = penNotchBase
    activeTotalEff = totalPenNotchEff
    activeReq = reqNotch
    activeRaw = rawCostNotchEff
    activeNet = netCostNotch
    altName = "Notch"
    c_alt = COLORS["notch"]

effPenalties = [p * activeReq for p in activeBasePen]

d_col1, d_col2 = st.columns(2)

with d_col1:
    st.markdown("<div style='background:white; padding:20px; border-radius:12px; border:1px solid #e2e8f0;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='font-size:14px; font-weight:bold; color:#334155; margin-top:0;'>Penalty Composition (₹/MT Eff Al)</h4>", unsafe_allow_html=True)
    
    fig_donut = go.Figure(data=[go.Pie(
        labels=penaltyLabels, 
        values=effPenalties, 
        hole=0.6,
        textinfo='none',
        marker=dict(colors=["#E53935", "#D32F2F", "#C62828", "#FF5252", "#FF1744", "#D50000", "#F44336", "#E57373"])
    )])
    fig_donut.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        showlegend=True,
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        annotations=[dict(text=f"+{fmt_cur(activeTotalEff)}<br><span style='font-size:10px;color:#94a3b8'>Total Penalty</span>", x=0.5, y=0.5, font_size=16, showarrow=False, font_weight="bold")]
    )
    st.plotly_chart(fig_donut, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

with d_col2:
    st.markdown("<div style='background:white; padding:20px; border-radius:12px; border:1px solid #e2e8f0; height:100%;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='font-size:14px; font-weight:bold; color:#334155; margin-top:0;'>Monetized Cost Drivers</h4>", unsafe_allow_html=True)
    
    # Sort for bar chart
    sorted_idx = np.argsort(effPenalties)
    
    fig_hbar = go.Figure(go.Bar(
        x=[effPenalties[i] for i in sorted_idx],
        y=[penaltyLabels[i] for i in sorted_idx],
        orientation='h',
        marker_color=COLORS["delta"],
        text=[f"+{fmt_cur(effPenalties[i])}" for i in sorted_idx],
        textposition='outside'
    ))
    fig_hbar.update_layout(
        margin=dict(t=10, b=10, l=10, r=10),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, tickfont=dict(size=11, color='#334155')),
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )
    st.plotly_chart(fig_hbar, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)


st.markdown("<div style='background:white; padding:24px; border-radius:12px; border:1px solid #e2e8f0; margin-top:24px;'>", unsafe_allow_html=True)
st.markdown(f"<h4 style='font-size:14px; font-weight:bold; color:#334155; margin-top:0; border-bottom:2px solid #e2e8f0; padding-bottom:8px; text-transform:uppercase;'>VIU Waterfall: {view_alt}</h4>", unsafe_allow_html=True)

fig_water = go.Figure(go.Waterfall(
    orientation = "v",
    measure = ["absolute"] + ["relative"] * 8 + ["total"],
    x = ["Raw Cost"] + penaltyLabels + ["Net Cost"],
    textposition = "outside",
    text = [fmt_cur(activeRaw)] + [f"+{fmt_cur(v)}" for v in effPenalties] + [fmt_cur(activeNet)],
    y = [activeRaw] + effPenalties + [activeNet],
    connector = {"line":{"color":"#94a3b8", "dash":"dot"}},
    decreasing = {"marker":{"color":COLORS["delta"]}},
    increasing = {"marker":{"color":COLORS["delta"]}},
    totals = {"marker":{"color":"#1e293b"}}
))
# Add target line
fig_water.add_hline(y=netCostPri, line_dash="dash", line_color=COLORS["primary"], annotation_text=f"Primary Net Benchmark: {fmt_cur(netCostPri)}", annotation_position="top right", annotation_font_color=COLORS["primary"])

fig_water.update_layout(
    height=400,
    margin=dict(t=30, b=40, l=40, r=40),
    showlegend=False,
    paper_bgcolor='rgba(0,0,0,0)',
    plot_bgcolor='rgba(0,0,0,0)',
    yaxis=dict(range=[min(activeRaw, netCostPri)*0.95, max(activeNet, netCostPri)*1.05], showgrid=True, gridcolor='#f1f5f9')
)
st.plotly_chart(fig_water, use_container_width=True, config={'displayModeBar': False})
st.markdown("<div style='background:#eff6ff; border-left:4px solid #3b82f6; padding:12px; font-size:12px; color:#1e40af; border-radius:4px;'><b>Waterfall Logic:</b> Starts at the cheaper raw material price. Each operational penalty (energy loss, inclusions, time delay) is added as a premium. If the final Net Cost bar surpasses the Primary baseline (dashed line), the 'cheaper' material is actually more expensive in-use.</div>", unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)


# --- Benefit Sensitivity Heatmap ---
st.markdown("<div class='section-header'>Benefit Sensitivity Heatmap (₹/MT at varying Realization)</div>", unsafe_allow_html=True)

pct_levels = [10, 30, 50, 70, 90, 100]
realizations = [rPower, rElectrode, rThroughput, rStability, rSlag, rCleanliness, rYield, rReblow]

# Generate Heatmap HTML matrix directly mimicking React gradient style
max_heat = max([activeBasePen[i] * (100 / (realizations[i] or 1)) for i in range(8)]) if any(activeBasePen) else 1

heat_html = """
<div style="background:white; padding: 24px; border-radius:12px; border:1px solid #e2e8f0; overflow-x:auto;">
    <table style="width:100%; border-collapse:collapse; min-width:700px;">
        <tr>
            <th style="padding:8px; text-align:left; font-size:10px; color:#64748b; border-bottom:1px solid #cbd5e1;">Penalty Component (₹/MT Alloy)</th>
"""
for p in pct_levels:
    heat_html += f"<th style='padding:8px; text-align:center; font-size:10px; color:#64748b; border-bottom:1px solid #cbd5e1;'>{p}%</th>"
heat_html += "</tr>"

for rIdx, label in enumerate(penaltyLabels):
    heat_html += f"<tr><td style='padding:8px; font-size:12px; font-weight:500; color:#334155; border-bottom:1px solid #f1f5f9;'>{label}</td>"
    for pct in pct_levels:
        val = activeBasePen[rIdx] * (pct / (realizations[rIdx] or 1))
        opacity = max(0.05, min(1.0, val / max_heat)) if max_heat > 0 else 0.05
        display_val = f"+{val:.0f}" if val > 5 else "-"
        bg_col = f"rgba(244, 67, 54, {opacity})"
        heat_html += f"""
        <td style='padding:8px; border-bottom:1px solid #f1f5f9;'>
            <div style="background:{bg_col}; padding:6px; border-radius:4px; text-align:center; font-family:monospace; font-size:10px; font-weight:600; color:#1e293b;">
                {display_val}
            </div>
        </td>"""
    heat_html += "</tr>"
heat_html += "</table></div>"
st.markdown(heat_html, unsafe_allow_html=True)


# --- Cost Comparison & Sensitivity Analysis ---
st.markdown("<div class='section-header'>Cost Comparison & Sensitivity Analysis</div>", unsafe_allow_html=True)

c10, c11 = st.columns(2)

with c10:
    st.markdown("<div style='background:white; padding:20px; border-radius:12px; border:1px solid #e2e8f0; height:100%;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='font-size:14px; font-weight:bold; color:#334155; margin-top:0;'>Effective Cost Components</h4>", unsafe_allow_html=True)
    
    fig_stack = go.Figure(data=[
        go.Bar(name='Raw Base', x=['Primary Al', 'Secondary Al', 'Notch Bar'], y=[rawCostPriEff, rawCostSecEff, rawCostNotchEff], marker_color=[COLORS["primary"], COLORS["secondary"], COLORS["notch"]]),
        go.Bar(name='Op Penalties', x=['Primary Al', 'Secondary Al', 'Notch Bar'], y=[0, totalPenSecEff, totalPenNotchEff], marker_color=COLORS["delta"])
    ])
    fig_stack.update_layout(
        barmode='stack', height=300, margin=dict(t=10,b=30,l=10,r=10),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(showgrid=True, gridcolor='#f1f5f9'), showlegend=False
    )
    # Add text annotations for totals
    for i, v in enumerate([netCostPri, netCostSec, netCostNotch]):
        fig_stack.add_annotation(x=i, y=v+10000, text=fmt_cur(v), showarrow=False, font=dict(size=12, color="#334155"))
        
    st.plotly_chart(fig_stack, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

with c11:
    st.markdown("<div style='background:white; padding:20px; border-radius:12px; border:1px solid #e2e8f0; height:100%;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='font-size:14px; font-weight:bold; color:#334155; margin-top:0;'>Price Sensitivity of Substitutes</h4>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:10px; color:#64748b; margin-top:-10px;'>Net advantage vs Primary Al as substitute market price changes (Primary held constant).</p>", unsafe_allow_html=True)
    
    sens_prices = list(range(300000, 420000, 20000))
    sec_saves = [netCostPri - ((p * reqSec) + totalPenSecEff) for p in sens_prices]
    notch_saves = [netCostPri - (((p - 5000) * reqNotch) + totalPenNotchEff) for p in sens_prices]
    
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(x=sens_prices, y=sec_saves, mode='lines', name='Sec vs Pri', line=dict(color=COLORS["secondary"], width=3)))
    fig_line.add_trace(go.Scatter(x=sens_prices, y=notch_saves, mode='lines', name='Notch vs Pri', line=dict(color=COLORS["notch"], width=3)))
    fig_line.add_hline(y=0, line_dash="dash", line_color="#94a3b8")
    
    fig_line.update_layout(
        height=260, margin=dict(t=10,b=20,l=40,r=10),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(yanchor="top", y=0.99, xanchor="right", x=0.99, bgcolor="rgba(255,255,255,0.8)"),
        xaxis=dict(tickformat="d", showgrid=False), yaxis=dict(showgrid=True, gridcolor='#f1f5f9')
    )
    st.plotly_chart(fig_line, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

c12, c13 = st.columns(2)

with c12:
    st.markdown("<div style='background:white; padding:20px; border-radius:12px; border:1px solid #e2e8f0; height:100%;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='font-size:14px; font-weight:bold; color:#334155; margin-top:0;'>Sensitivity Tornado (±20% Realization)</h4>", unsafe_allow_html=True)
    
    pos_deltas = []
    neg_deltas = []
    for i in range(8):
        base_val = activeBasePen[i] * (100 / (realizations[i] or 1))
        current = activeBasePen[i]
        val_plus = base_val * (min(100, realizations[i] + 20) / 100)
        val_minus = base_val * (max(0, realizations[i] - 20) / 100)
        pos_deltas.append(val_plus - current)
        neg_deltas.append(val_minus - current) # Will be negative

    fig_tor = go.Figure()
    fig_tor.add_trace(go.Bar(y=penaltyLabels, x=neg_deltas, orientation='h', name='-20% Realization', marker_color='#4ade80'))
    fig_tor.add_trace(go.Bar(y=penaltyLabels, x=pos_deltas, orientation='h', name='+20% Realization', marker_color='#f87171'))
    
    fig_tor.update_layout(
        barmode='relative', height=300, margin=dict(t=10,b=10,l=10,r=10),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#f1f5f9', zerolinecolor='#94a3b8'),
        yaxis=dict(autorange="reversed"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig_tor, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

with c13:
    st.markdown("<div style='background:white; padding:20px; border-radius:12px; border:1px solid #e2e8f0; height:100%; overflow-x:auto;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='font-size:14px; font-weight:bold; color:#334155; margin-top:0;'>Side-by-Side Cost Summary</h4>", unsafe_allow_html=True)
    
    summary_html = f"""
    <table class="custom-table" style="margin-top: 16px;">
        <tr style="background: #f8fafc;">
            <th>Metric</th><th>Primary</th><th>Secondary</th><th>Notch Bar</th>
        </tr>
        <tr><td>Alloy Req. (MT/Eff MT)</td><td>{reqPri:.3f}</td><td>{reqSec:.3f}</td><td>{reqNotch:.3f}</td></tr>
        <tr><td>Raw Cost (₹/MT Eff)</td><td>{fmt_cur(rawCostPriEff)}</td><td>{fmt_cur(rawCostSecEff)}</td><td>{fmt_cur(rawCostNotchEff)}</td></tr>
        <tr><td style="color:#ef4444;">Total Penalty (₹/MT Eff)</td><td>-</td><td style="color:#ef4444;">+{fmt_cur(totalPenSecEff)}</td><td style="color:#ef4444;">+{fmt_cur(totalPenNotchEff)}</td></tr>
        <tr style="background: #f8fafc;"><td style="font-weight:bold;">Net Adj. Cost</td><td style="font-weight:bold;">{fmt_cur(netCostPri)}</td><td style="font-weight:bold;">{fmt_cur(netCostSec)}</td><td style="font-weight:bold;">{fmt_cur(netCostNotch)}</td></tr>
    </table>
    """
    st.markdown(summary_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# --- Enterprise Savings Calculator ---
st.markdown("<div class='section-header'>Enterprise Savings Calculator</div>", unsafe_allow_html=True)

c14, c15, c16, c17 = st.columns(4)
with c14: st.markdown(render_kpi("Substituted Volume", f"{fmt_num(consumptionMt * (substitutionPct/100), 0)} MT", f"@ {substitutionPct}% Substitution", "#6366f1"), unsafe_allow_html=True)
with c15: st.markdown(render_kpi("Savings / MT Alloy", fmt_cur(maxEdge / baselineObj['req']), f"Advantage of {bestOpt['name']}", COLORS["benefit"], True), unsafe_allow_html=True)
with c16: st.markdown(render_kpi("Annual Savings", f"₹{fmt_num(annualSavingsCr, 2)} Cr", "Total Projected Benefit", COLORS["benefit"], True), unsafe_allow_html=True)
with c17: st.markdown(render_kpi("Monthly Savings", f"₹{fmt_num((annualSavingsCr * 100) / 12, 1)} L", "Avg Run-Rate", COLORS["benefit"], True), unsafe_allow_html=True)

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

c18, c19, c20 = st.columns(3)
with c18:
    st.markdown("<div style='background:white; padding:20px; border-radius:12px; border:1px solid #e2e8f0; height:100%;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='font-size:14px; font-weight:bold; color:#334155; margin-top:0;'>Savings Vs Volume (₹ Cr)</h4>", unsafe_allow_html=True)
    
    vol_x = [f"{(v*2000)/1000}k" for v in range(1,6)]
    vol_y = [((v*2000) * baselineObj['eff'] * maxEdge * (substitutionPct/100))/1e7 for v in range(1,6)]
    
    fig_vol = go.Figure(go.Scatter(x=vol_x, y=vol_y, mode='lines+markers', line=dict(color=COLORS["benefit"], width=3)))
    fig_vol.update_layout(height=200, margin=dict(t=10,b=20,l=20,r=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='#f1f5f9'))
    st.plotly_chart(fig_vol, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

with c19:
    st.markdown("<div style='background:white; padding:20px; border-radius:12px; border:1px solid #e2e8f0; height:100%;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='font-size:14px; font-weight:bold; color:#334155; margin-top:0;'>3-Year Projection (5% Esc)</h4>", unsafe_allow_html=True)
    
    esc_vals = [annualSavingsCr * 1, annualSavingsCr * 1.05, annualSavingsCr * 1.1025]
    fig_esc = go.Figure(go.Bar(x=['Year 1', 'Year 2', 'Year 3'], y=esc_vals, marker_color=COLORS["benefit"], text=[f"₹{v:.2f}" for v in esc_vals], textposition='outside'))
    fig_esc.update_layout(height=200, margin=dict(t=10,b=20,l=20,r=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(showgrid=False, showticklabels=False))
    st.plotly_chart(fig_esc, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

with c20:
    st.markdown("<div style='background:white; padding:20px; border-radius:12px; border:1px solid #e2e8f0; height:100%;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='font-size:14px; font-weight:bold; color:#334155; margin-top:0; text-align:center;'>Savings Components</h4>", unsafe_allow_html=True)
    
    raw_save = baselineObj['rawCost'] - bestOpt['rawCost']
    op_avoid = max(0, (baselineObj['netCost'] - baselineObj['rawCost']) - (bestOpt['netCost'] - bestOpt['rawCost']))
    
    fig_comp = go.Figure(data=[go.Pie(labels=["Base Raw Savings", "Op. Penalty Avoidance"], values=[raw_save, op_avoid], hole=0.6, marker_colors=["#1E88E5", "#43A047"], textinfo='none')])
    fig_comp.update_layout(height=200, margin=dict(t=10,b=10,l=10,r=10), showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', annotations=[dict(text=f"₹{fmt_num(annualSavingsCr, 2)}<br><span style='font-size:10px;color:#94a3b8'>Cr Total</span>", x=0.5, y=0.5, font_size=14, showarrow=False, font_weight="bold")])
    st.plotly_chart(fig_comp, use_container_width=True, config={'displayModeBar': False})
    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

c21, c22 = st.columns(2)

with c21:
    st.markdown("<div style='background:white; padding:20px; border-radius:12px; border:1px solid #e2e8f0; height:100%;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='font-size:14px; font-weight:bold; color:#334155; margin-top:0;'>Per-Benefit Annual Savings (₹ Cr)</h4>", unsafe_allow_html=True)
    
    b_table_html = """<table class="custom-table" style="margin-top: 16px;">
        <tr style="background: #f8fafc;"><th>Benefit Area</th><th style="text-align: right;">Value (Cr/Yr)</th></tr>"""
    
    base_pen_arr = penSecBase if baselineObj['name'] == 'Secondary' else (penNotchBase if baselineObj['name'] == 'Notch Bar' else [0]*8)
    best_pen_arr = penSecBase if bestOpt['name'] == 'Secondary' else (penNotchBase if bestOpt['name'] == 'Notch Bar' else [0]*8)
    
    for i, lbl in enumerate(penaltyLabels):
        bVal = base_pen_arr[i] * baselineObj['req'] if base_pen_arr else 0
        oVal = best_pen_arr[i] * bestOpt['req'] if best_pen_arr else 0
        saved_eff = max(0, bVal - oVal)
        saved_cr = (totalEffAlDemand * saved_eff * (substitutionPct/100)) / 1e7
        disp_val = f"₹{saved_cr:.3f}" if saved_cr > 0 else "-"
        
        b_table_html += f"<tr><td>{lbl}</td><td style='text-align: right; font-family: monospace; font-weight: bold; color: #16a34a;'>{disp_val}</td></tr>"
        
    b_table_html += "</table>"
    st.markdown(b_table_html, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

with c22:
    st.markdown("<div style='background:white; padding:20px; border-radius:12px; border:1px solid #e2e8f0; height:100%;'>", unsafe_allow_html=True)
    st.markdown("<h4 style='font-size:14px; font-weight:bold; color:#334155; margin-top:0;'>Break-Even Price Analysis</h4>", unsafe_allow_html=True)
    st.markdown("<p style='font-size:10px; color:#64748b; margin-top:-10px;'>Calculates the market price at which the alternative perfectly offsets Primary Al's higher base cost via its operational penalties.</p>", unsafe_allow_html=True)
    
    def be_row(label, current, be_val):
        is_viable = current <= be_val
        val_col = "#16a34a" if is_viable else "#ef4444"
        return f"""
        <div style="display: flex; justify-content: space-between; align-items: center; padding: 12px; border-radius: 8px; border: 1px solid #e2e8f0; background: #f8fafc; margin-bottom: 12px;">
            <span style="font-size: 12px; font-weight: bold; color: #334155; width: 33%;">{label}</span>
            <span style="font-size: 12px; font-family: monospace; color: #94a3b8; text-decoration: line-through;">{fmt_cur(current)}</span>
            <span style="font-size: 14px; font-family: monospace; font-weight: bold; color: {val_col};">{fmt_cur(be_val)}</span>
        </div>
        """
        
    st.markdown(be_row("Primary Break-Even", pPriPrice, bePriPrice), unsafe_allow_html=True)
    st.markdown(be_row("Secondary Break-Even", pSecPrice, beSecPrice), unsafe_allow_html=True)
    st.markdown(be_row("Notch Bar Break-Even", pNotchPrice, beNotchPrice), unsafe_allow_html=True)
    
    st.markdown("<div style='text-align: center; font-size: 10px; color: #94a3b8; font-style: italic; margin-top: 16px;'>Green indicates the current market price is below the break-even threshold (economically viable).</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# --- Final Recommendation ---
is_switching = bestOpt['name'] != baselineObj['name']
bg_col = "#ecfdf5" if is_switching else "#fff7ed"
brd_col = "#10b981" if is_switching else "#f97316"
txt_h = "#065f46" if is_switching else "#9a3412"
txt_p = "#047857" if is_switching else "#c2410c"

rec_html = f"""
<div style="background: {bg_col}; border-left: 8px solid {brd_col}; padding: 32px; border-radius: 16px; margin-top: 32px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);">
    <h3 style="font-size: 24px; font-weight: 800; color: {txt_h}; margin-top: 0; margin-bottom: 12px;">🏆 {bestOpt['name']} Preferred</h3>
"""

if is_switching:
    rec_html += f"""
    <p style="font-size: 14px; line-height: 1.6; color: {txt_p}; margin: 0;">
        <b>Projected Annual Savings: ₹{annualSavingsCr:.2f} Crore</b><br/>
        By shifting <b>{substitutionPct}%</b> of your <b>{baselineObj['name']}</b> consumption to <b>{bestOpt['name']}</b>, you realize a net advantage of <b>{fmt_cur(maxEdge / bestOpt['req'])}/MT Alloy</b>. 
        The initial market price discount outweighs the monetized operational penalties (energy loss, inclusions, slag).
    </p>
    """
else:
    rec_html += f"""
    <p style="font-size: 14px; line-height: 1.6; color: {txt_p}; margin: 0;">
        <b>Optimal Baseline Maintained: ₹0 Crore Switching Incentive</b><br/>
        Your current baseline <b>{baselineObj['name']}</b> is mathematically optimal under the specified operational parameters and current market prices. 
        The alternative options do not offer a sufficient raw material discount to overcome their associated operational penalties in the Ladle Furnace.
    </p>
    """

rec_html += "</div>"
st.markdown(rec_html, unsafe_allow_html=True)