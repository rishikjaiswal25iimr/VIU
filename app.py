"""
ALUMINIUM SUBSTITUTION SOLVER
================================================
Three-Material Optimization Engine:
- Primary Aluminium Ingot
- Secondary Aluminium Ingot
- Aluminium Notch Bar

This application isolates the Linear Programming solver 
and UI/UX components strictly for the Aluminium VIU model.
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
    page_icon="⚗️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Colour palette for the 3 Materials
C_PRIMARY = "#1565C0"    # Deep Blue  - Primary Ingot
C_SEC     = "#4CAF50"    # Green      - Secondary Ingot
C_NOTCH   = "#FF9800"    # Amber      - Notch Bar
C_GRID    = "#EEEEEE"
C_BG      = "#FAFAFA"
C_TEXT    = "#333333"

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
[data-testid="stSidebar"] hr { border-color: #3949AB; }

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
.kpi-label { font-size: 12px; font-weight: 600; color: #78909C; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
.kpi-value { font-size: 26px; font-weight: 700; color: #1A237E; line-height: 1.15; }

/* ---------- section headers ---------- */
.section-header {
    font-size: 20px; font-weight: 800; color: #1A237E;
    text-transform: uppercase; letter-spacing: 0.05em;
    border-bottom: 3px solid #2196F3;
    padding-bottom: 8px; margin-bottom: 24px; margin-top: 32px;
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
# CONSTANTS & METALLURGICAL DATA (From Excel source of truth)
# ══════════════════════════════════════════════════════════════════════════════
# Baseline properties extracted from VIU_SUMMARY & BREAKDOWN_CALC
EFF_AL_PRI   = 0.4851
EFF_AL_SEC   = 0.4462
EFF_AL_NOTCH = 0.4370

PENALTY_PRI   = 0.0
PENALTY_SEC   = 2857.71
PENALTY_NOTCH = 5129.87

# Dictionary containing grade-specific metallurgical constraints
grades_data = {
    "Commodity Structural (IS2062/E250)": {"therm_lim": 5.5, "rec_lim": 3.50, "inc_lim": 0.060, "reblow_lim": 2.50, "sec_notch_max": 1.00},
    "TMT / Rebar (Fe500D)":               {"therm_lim": 4.0, "rec_lim": 3.20, "inc_lim": 0.050, "reblow_lim": 2.30, "sec_notch_max": 0.80},
    "HSLA / API (API X70)":               {"therm_lim": 2.5, "rec_lim": 2.80, "inc_lim": 0.040, "reblow_lim": 2.00, "sec_notch_max": 0.30},
    "IF Steel (Deep Draw IF)":            {"therm_lim": 1.5, "rec_lim": 2.15, "inc_lim": 0.032, "reblow_lim": 1.55, "sec_notch_max": 0.10},
    "Electrical Steel (CRGO / CRNO)":     {"therm_lim": 1.1, "rec_lim": 2.05, "inc_lim": 0.031, "reblow_lim": 1.50, "sec_notch_max": 0.00},
}


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR: DYNAMIC PRICING ENGINE
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 📊 Market Prices (₹/MT)")
    st.markdown("<p style='font-size:12px; color:#B0BEC5; margin-top:-10px;'>Adjust market prices to see how the solver dynamically shifts the optimal procurement ratio.</p>", unsafe_allow_html=True)
    
    price_pri   = st.number_input("Primary Al Ingot", value=380000, step=1000)
    price_sec   = st.number_input("Secondary Al Ingot", value=340000, step=1000)
    price_notch = st.number_input("Al Notch Bar", value=335000, step=1000)
    st.divider()
    
# Dynamic VIU Effective Cost Calculation (Objective Function)
COST_EFF_PRIMARY   = (price_pri + PENALTY_PRI) / EFF_AL_PRI
COST_EFF_SECONDARY = (price_sec + PENALTY_SEC) / EFF_AL_SEC
COST_EFF_NOTCH     = (price_notch + PENALTY_NOTCH) / EFF_AL_NOTCH


# ══════════════════════════════════════════════════════════════════════════════
# MAIN UI: SUBSTITUTION SOLVER
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">🧠 Optimal Aluminium Substitution Solver</div>', unsafe_allow_html=True)
st.markdown("""
Calculates the mathematically cheapest blend of **Primary Al Ingot**, **Secondary Al Ingot**, and **Al Notch Bar** that perfectly satisfies strict metallurgical limits.
""")

gc1, gc2 = st.columns([1.5, 2.5])
sel_grade = gc1.selectbox("Select Target Steel Grade", list(grades_data.keys()), index=0)
limits = grades_data[sel_grade]

st.markdown("#### Metallurgical Constraints")
sc1, sc2, sc3, sc4, sc5 = st.columns(5)
max_therm     = sc1.slider("Max Thermal Burden", 1.0, 7.0, limits["therm_lim"], step=0.1)
max_rec       = sc2.slider("Max Recovery Var",   1.0, 4.0, limits["rec_lim"], step=0.05)
max_inc       = sc3.slider("Max Inclusion (%)",  0.010, 0.080, limits["inc_lim"], step=0.002, format="%.3f")
max_reblow    = sc4.slider("Max Reblow Risk",    1.0, 3.0, limits["reblow_lim"], step=0.05)
max_sec_notch = sc5.slider("Max Sec/Notch (%)",  0.0, 100.0, limits["sec_notch_max"] * 100, step=5.0) / 100.0

# ══════════════════════════════════════════════════════════════════════════════
# LINEAR PROGRAMMING ENGINE (3 Variables: x, y, z)
# ══════════════════════════════════════════════════════════════════════════════
# Variables:
# x[0] = Primary Al Ingot share
# x[1] = Secondary Al Ingot share
# x[2] = Al Notch Bar share

# Objective array: Cost per MT of Effective Al
c_cost = [COST_EFF_PRIMARY, COST_EFF_SECONDARY, COST_EFF_NOTCH]

# Equality constraints: Sum of shares = 100%
A_eq = [[1, 1, 1]]
b_eq = [1]

# Inequality constraints (A_ub * [x, y, z]^T <= b_ub)
A_ub = [
    [1.0,  4.5,   6.2],    # Thermal Burden Index
    [2.0,  3.0,   3.5],    # Recovery Variability (StDev %)
    [0.03, 0.045, 0.055],  # Inclusion Severity Index (%)
    [1.5,  2.0,   2.5],    # LF Re-treatment Risk (%)
    [0.0,  1.0,   1.0],    # Max Secondary / Notch Share
]
b_ub = [max_therm, max_rec, max_inc, max_reblow, max_sec_notch]

# Execute Scipy Optimizer
res = linprog(c_cost, A_eq=A_eq, b_eq=b_eq, A_ub=A_ub, b_ub=b_ub, bounds=[(0, 1), (0, 1), (0, 1)])

st.markdown("#### Optimization Result")
if res.success:
    mix = np.clip(res.x, 0, 1)  # Clip to fix floating point precision (e.g. -0.0)
    blended_cost = res.fun
    
    # Calculate savings vs 100% Primary Ingot (The benchmark commodity)
    baseline_cost = COST_EFF_PRIMARY
    savings = baseline_cost - blended_cost

    rc1, rc2 = st.columns(2)
    rc1.success(f"##### Final Effective Cost of Blend: \n ### **₹{blended_cost:,.0f}** per MT Eff. Al")
    
    if savings > 10:
        rc2.info(f"##### Projected Savings vs 100% Primary: \n ### **₹{savings:,.0f}** per MT Eff. Al")
    else:
        rc2.info(f"##### Projected Savings vs 100% Primary: \n ### **₹0** (100% Primary is optimal)")

    # Pie Chart Result (3 Slices)
    fig_pie = go.Figure(data=[go.Pie(
        labels=["Primary Ingot", "Secondary Ingot", "Al Notch Bar"], 
        values=[round(m, 4) for m in mix], 
        hole=0.4, 
        marker_colors=[C_PRIMARY, C_SEC, C_NOTCH],
        textinfo="label+percent"
    )])
    fig_pie.update_layout(title=f"Optimal Procurement Ratio for {sel_grade}", height=380, template="plotly_white")
    st.plotly_chart(fig_pie, use_container_width=True)
    
    # Shadow Price / Break-even insight for Notch Bar
    be_notch = COST_EFF_SECONDARY * EFF_AL_NOTCH - PENALTY_NOTCH
    if mix[2] < 0.001 and be_notch > 0:
        st.markdown(f"""
        <div style="background:#FFF8E1; border-left:5px solid #FF9800; padding:15px; border-radius:6px; margin-bottom:20px;">
            <b style="color:#F57C00;">💡 Why is Al Notch Bar excluded (0%)?</b><br>
            <span style="color:#5D4037; font-size:14px;">At the current input prices, <b>Secondary Ingot</b> completely dominates Notch Bar. Secondary Ingot provides better metallurgical properties AND a lower Final Effective Cost. To mathematically force the LP solver to select Notch Bar, its market price must drop below the VIU Break-Even point of <b>₹{be_notch:,.0f}/MT</b>. <i>(Try lowering the Notch Bar price in the sidebar to see it enter the blend!)</i></span>
        </div>
        """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════════════
    # INSIGHTS & CHARTS
    # ══════════════════════════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("#### 📊 Deep Dive & Insights")
    
    col_insight1, col_insight2 = st.columns(2)
    
    with col_insight1:
        # Cost Comparison Chart
        fig_cost = go.Figure()
        fig_cost.add_trace(go.Bar(
            x=["100% Primary", "Optimal Blend", "100% Secondary", "100% Notch Bar"],
            y=[COST_EFF_PRIMARY, blended_cost, COST_EFF_SECONDARY, COST_EFF_NOTCH],
            marker_color=[C_PRIMARY, "#9C27B0", C_SEC, C_NOTCH],
            text=[f"₹{COST_EFF_PRIMARY:,.0f}", f"₹{blended_cost:,.0f}", f"₹{COST_EFF_SECONDARY:,.0f}", f"₹{COST_EFF_NOTCH:,.0f}"],
            textposition="auto",
            hovertemplate="%{x}<br>₹%{y:,.0f}/MT<extra></extra>"
        ))
        
        # Determine the dynamic range so bars don't look completely flat
        min_cost = min(COST_EFF_PRIMARY, blended_cost, COST_EFF_SECONDARY, COST_EFF_NOTCH) * 0.95
        fig_cost.update_layout(**_layout("Effective Cost Comparison (₹/MT Active Al)", "Cost (₹)", 380))
        fig_cost.update_yaxes(range=[min_cost, max(COST_EFF_PRIMARY, COST_EFF_NOTCH)*1.02])
        st.plotly_chart(fig_cost, use_container_width=True)
        
    with col_insight2:
        # Constraint Utilization Chart
        actual_therm  = mix[0] * 1.0  + mix[1] * 4.5   + mix[2] * 6.2
        actual_rec    = mix[0] * 2.0  + mix[1] * 3.0   + mix[2] * 3.5
        actual_inc    = mix[0] * 0.03 + mix[1] * 0.045 + mix[2] * 0.055
        actual_reblow = mix[0] * 1.5  + mix[1] * 2.0   + mix[2] * 2.5
        actual_sec_n  = mix[1] + mix[2]
        
        utils = [
            (actual_sec_n / max_sec_notch) * 100 if max_sec_notch else 0,
            (actual_reblow / max_reblow) * 100 if max_reblow else 0,
            (actual_inc / max_inc) * 100 if max_inc else 0,
            (actual_rec / max_rec) * 100 if max_rec else 0,
            (actual_therm / max_therm) * 100 if max_therm else 0
        ]
        labels = ["Max Sec/Notch Share", "LF Re-treatment Risk", "Inclusion Severity", "Recovery Variability", "Thermal Burden"]
        
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
        fig_util.update_layout(**_layout("Constraint Utilization (% of Max Limit Used)", "% Used", 380))
        fig_util.update_xaxes(range=[0, max(110, max(utils)*1.1)])
        st.plotly_chart(fig_util, use_container_width=True)
        
    # Table of exact values
    st.markdown("#### Metallurgical Profile of the Optimal Blend")
    df_profile = pd.DataFrame({
        "Parameter": ["Thermal Burden Index", "Recovery Variability", "Inclusion Severity Index", "LF Re-treatment Risk", "Sec/Notch Share"],
        "Blend Actual": [actual_therm, actual_rec, actual_inc, actual_reblow, actual_sec_n],
        "Maximum Allowed": [max_therm, max_rec, max_inc, max_reblow, max_sec_notch],
    })
    
    # Use small tolerance for float comparison to flag binding limits
    df_profile["Status"] = np.where(df_profile["Blend Actual"] >= df_profile["Maximum Allowed"] - 1e-6, "🛑 Binding Constraint", "✅ Safe")
    
    # Format values properly (percentages vs regular decimals)
    def format_val(val, is_pct):
        return f"{val*100:.2f}%" if is_pct else f"{val:.4f}"
        
    df_profile["Blend Actual"] = df_profile.apply(lambda row: format_val(row["Blend Actual"], row["Parameter"] == "Sec/Notch Share"), axis=1)
    df_profile["Maximum Allowed"] = df_profile.apply(lambda row: format_val(row["Maximum Allowed"], row["Parameter"] == "Sec/Notch Share"), axis=1)

    # Style the dataframe status column
    def color_status(val):
        return "color: #D32F2F; font-weight: bold" if "Binding" in val else "color: #388E3C"
        
    st.dataframe(df_profile.style.map(color_status, subset=["Status"]), use_container_width=True)

else:
    st.error("⚠️ **Constraint Violation:** The chosen metallurgical limits are too strict to be met using these alloys. Please relax the constraints.")

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
st.markdown("""
<div style="text-align:center; color:#90A4AE; font-size:12px; padding:8px 0;">
  Aluminium VIU Solver – Primary Ingot vs Secondary Ingot vs Notch Bar &nbsp;|&nbsp; 
  All constraint equations sourced from Excel workbook &nbsp;|&nbsp; 
  Optimizes the blend to minimize Final Effective Cost while respecting metallurgical boundary conditions.
</div>
""", unsafe_allow_html=True)