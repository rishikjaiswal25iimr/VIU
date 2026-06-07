"""
╔══════════════════════════════════════════════════════════════════════════════╗
║      UNIFIED COMMODITY INTELLIGENCE PLATFORM                                ║
║      app.py  |  Integrated (Manganese · Silicon · Aluminium)               ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  Manganese : Mn Briquette (97%) | LC FeMn (80%) | MC FeMn (70%)            ║
║  Silicon   : Silicon Metal (98% Si) | FeSi Alloy (70% Si)                  ║
║  Aluminium : Primary Aluminium Ingot                                        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

from __future__ import annotations
import json
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from scipy.optimize import linprog

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Commodity Intelligence Platform",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stMetricValue"] {
    font-size: 1.4rem !important;
}
[data-testid="stMetricLabel"] {
    font-size: 0.9rem !important;
}
[data-testid="stMetricDelta"] {
    font-size: 0.85rem !important;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

HORIZON_OPTIONS = {
    "4 weeks (1 month)":   4,
    "12 weeks (3 months)": 12,
    "26 weeks (6 months)": 26,
    "52 weeks (1 year)":   52,
    "104 weeks (2 years)": 104,
    "156 weeks (3 years)": 156,
}

ALL_PRODUCTS = [
    "Mn Briquette (97%)",
    "LC FeMn (80%)",
    "MC FeMn (70%)",
    "Silicon Metal (98% Si)",
    "FeSi Alloy (70% Si)",
    "Primary Al Ingot",
]

# ══════════════════════════════════════════════════════════════════════════════
# GLOBAL SIDEBAR — PRODUCT ROUTING
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🎯 Target Selection")
    product_choice = st.selectbox("Select Product:", ALL_PRODUCTS)

    st.divider()
    st.markdown("### 📐 Display Options")
    display_window = st.slider("History to show (weeks)", 52, 520, 260, step=26)
    horizon_label  = st.selectbox("Forecast horizon", list(HORIZON_OPTIONS.keys()), index=2)
    price_mode     = st.radio("Price display", ["₹/Kg (Real Price)", "Index Value"], index=0)
    show_regime    = st.checkbox("Show regime shading", value=True)
    show_market    = st.checkbox("Show market price overlay", value=True)
    show_ci        = st.checkbox("Show 95% confidence band", value=True)

    # Manganese-only extra options
    if product_choice in ["Mn Briquette (97%)", "LC FeMn (80%)", "MC FeMn (70%)"]:
        show_dual = st.checkbox("Show Dual-Axis Chart", value=False)

horizon_weeks = HORIZON_OPTIONS[horizon_label]


# ══════════════════════════════════════════════════════════════════════════════
# PRODUCT ROUTING HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def is_manganese():
    return product_choice in ["Mn Briquette (97%)", "LC FeMn (80%)", "MC FeMn (70%)"]

def is_silicon():
    return product_choice in ["Silicon Metal (98% Si)", "FeSi Alloy (70% Si)"]

def is_aluminium():
    return product_choice == "Primary Al Ingot"


# ══════════════════════════════════════════════════════════════════════════════
# ██████████████████████████   MANGANESE SECTION   ████████████████████████████
# ══════════════════════════════════════════════════════════════════════════════

# ── Design palette (Mn) ───────────────────────────────────────────────────────
MN_C_ACTUAL  = "#FF9800"
MN_C_HYBRID  = "#2196F3"
MN_C_FUTURE  = "#4CAF50"
MN_C_MARKET  = "#9C27B0"
MN_C_REG1    = "rgba(244, 67, 54, 0.15)"
MN_C_GRID    = "#EEEEEE"
MN_C_TEXT    = "#333333"
MN_C_CI      = "rgba(76, 175, 80, 0.12)"


def mn_layout(title: str, y_title: str = "Price", height: int = 460) -> dict:
    return dict(
        template="plotly_white", paper_bgcolor="white", plot_bgcolor="#FAFAFA",
        font=dict(family="sans-serif", size=12, color=MN_C_TEXT),
        title=dict(text=title, font=dict(size=16, color="#111"), x=0.01),
        legend=dict(bgcolor="rgba(255,255,255,0.8)", bordercolor="#CCC", borderwidth=1),
        xaxis=dict(showgrid=True, gridcolor=MN_C_GRID, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=MN_C_GRID, zeroline=False, title=y_title),
        hovermode="x unified", height=height, margin=dict(l=55, r=20, t=55, b=40),
    )


def mn_build_regime_shapes(dates: pd.DatetimeIndex, probs: np.ndarray, threshold: float = 0.5) -> list:
    labels = (probs > threshold).astype(int)
    shapes, in_block, t0 = [], False, None
    for d, lbl in zip(dates, labels):
        if lbl == 1 and not in_block:
            in_block, t0 = True, d
        elif lbl == 0 and in_block:
            shapes.append(dict(type="rect", xref="x", yref="paper",
                               x0=str(t0), x1=str(d), y0=0, y1=1,
                               fillcolor=MN_C_REG1, line_width=0, layer="below"))
            in_block = False
    if in_block:
        shapes.append(dict(type="rect", xref="x", yref="paper",
                           x0=str(t0), x1=str(dates[-1]), y0=0, y1=1,
                           fillcolor=MN_C_REG1, line_width=0, layer="below"))
    return shapes


def mn_get_latest_price(folder):
    try:
        return float(pd.read_csv(f"{folder}/historical_predictions.csv")["real_price"].iloc[-1]) * 1000
    except:
        return None


def mn_get_future_prices(folder):
    try:
        df = pd.read_csv(f"{folder}/future_forecast.csv", index_col=0, parse_dates=True)
        return df["real_price"] * 1000
    except:
        return None


# ── Manganese physics & VIU constants ────────────────────────────────────────
MN_HEAT_SIZE         = 190.0
MN_POWER_RATE        = 6.5
MN_ELECTRODE_RATE    = 240.0
MN_THROUGHPUT_MARGIN = 2800.0
MN_REBLOW_COST       = 15000.0
MN_STEEL_VALUE       = 60000.0
MN_RH_COST           = 2500.0


def mn_compute_operational_penalty(thermal, cycle, rec_diff, reblow, clean, yield_loss, rh, eff_mn, price):
    scale           = 200.0 / MN_HEAT_SIZE
    power_kwh_per_heat = (thermal * 0.75 * MN_HEAT_SIZE) / 3.6 / 0.78
    power           = power_kwh_per_heat * MN_POWER_RATE * scale
    electrode       = power_kwh_per_heat * 0.0028 * MN_ELECTRODE_RATE * scale
    throughput      = (cycle / 53.0) * MN_HEAT_SIZE * 0.30 * MN_THROUGHPUT_MARGIN * scale
    rec_ben         = ((rec_diff / 100.0) / eff_mn) * price * 0.50
    reblow_ben      = (reblow / 100.0) * MN_REBLOW_COST * scale
    rh_ben          = (rh / 100.0) * MN_RH_COST * scale
    clean_ben       = MN_STEEL_VALUE * (clean / 100.0) * 200.0 * 0.40
    yield_ben       = MN_STEEL_VALUE * (yield_loss / 100.0) * 200.0 * 0.50
    return power + electrode + throughput + rec_ben + reblow_ben + clean_ben + yield_ben + rh_ben


def render_manganese():
    """Render the full Manganese dashboard for the selected Mn product."""

    if "Briquette" in product_choice:
        alloy_code  = "Briquette"
        alloy_label = "Mn Briquette (97%)"
    elif "LC" in product_choice:
        alloy_code  = "LC"
        alloy_label = "LC FeMn (80%)"
    else:
        alloy_code  = "MC"
        alloy_label = "MC FeMn (70%)"

    output_dir = f"./outputs_{alloy_code}"

    # ── Data load ─────────────────────────────────────────────────────────────
    try:
        hist   = pd.read_csv(f"{output_dir}/historical_predictions.csv",
                              index_col=0, parse_dates=True)
        future = pd.read_csv(f"{output_dir}/future_forecast.csv",
                              index_col=0, parse_dates=True).iloc[:horizon_weeks]
        fi     = pd.read_csv(f"{output_dir}/feature_importance.csv") \
                   .sort_values("importance", ascending=False).head(15)
        with open(f"{output_dir}/model_metadata.json") as f:
            meta = json.load(f)
    except FileNotFoundError:
        st.error(
            f"⛔ Data for {alloy_code} not found. "
            f"Please run the pipeline using `python pipeline_master.py --alloy {alloy_code}` first."
        )
        st.stop()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown("## 📈 Mn Price Forecasting Engine")

    pred_col = "hybrid_prediction"
    mape     = float(np.mean(np.abs(
        (hist["actual"] - hist[pred_col]) / (hist["actual"] + 1e-9)
    )) * 100)

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    last_idx  = float(hist["actual"].iloc[-1])
    last_real = float(hist["real_price"].iloc[-1])
    nxt_real  = float(future["real_price"].iloc[0])
    end_real  = float(future["real_price"].iloc[-1])
    pct_chg   = ((nxt_real - last_real) / last_real) * 100 if last_real else 0

    c1.metric("Last Index",          f"{last_idx:.2f}")
    c2.metric("Last Actual (Rs/Kg)", f"₹{last_real:.2f}")
    c3.metric("Next-Wk Forecast",   f"₹{nxt_real:.2f}", delta=f"{pct_chg:+.1f}%")
    c4.metric("End Forecast",        f"₹{end_real:.2f}",
              delta=f"{len(future)} wks ahead", delta_color="off")
    c5.metric("In-Sample MAPE",      f"{mape:.2f}%")
    c6.metric("Scaling Factor",      f"{meta.get('scaling_factor', 0):.4f}",
              help=f"Anchored mathematically to {meta.get('anchor_date')} = ₹{meta.get('anchor_price', 0):.2f}")

    # ── Tabs (3 only — VIU & Substitution removed) ───────────────────────────
    tab1, tab2, tab3 = st.tabs(["📉 Price Forecast", "📊 Market Comparison", "🔀 Regime & Drivers"])

    # ── TAB 1: PRICE FORECAST ─────────────────────────────────────────────────
    with tab1:
        h = hist[hist.index >= hist.index[-1] - pd.DateOffset(weeks=display_window)].copy()
        use_real  = price_mode.startswith("₹")
        if use_real:
            actual_vals, y_title, future_col, fmt = h["real_price"], "Price (Rs/Kg)", "real_price", "₹%{y:.2f}"
        else:
            actual_vals, y_title, future_col, fmt = h["actual"], "Price Index", "predicted_index", "%{y:.2f}"

        fig1  = go.Figure()
        if show_regime and "regime_probability" in h.columns:
            for s in mn_build_regime_shapes(h.index, h["regime_probability"].values):
                fig1.add_shape(**s)

        full_x = list(h.index) + list(future.index)
        N, M   = len(h), len(future)

        fig1.add_trace(go.Scatter(
            x=full_x, y=list(actual_vals) + [None] * M,
            name="Index Price", line=dict(color=MN_C_HYBRID, width=3),
            hovertemplate="<b>%{x|%B %Y}</b><br>%{x|%Y-%m-%d}<br>Index Price: " + fmt + "<extra></extra>",
        ))
        if show_market and "market_price" in h.columns:
            fig1.add_trace(go.Scatter(
                x=full_x, y=list(h["market_price"]) + [None] * M,
                name="Market Price", line=dict(color=MN_C_MARKET, width=2.5),
                hovertemplate="<b>%{x|%B %Y}</b><br>%{x|%Y-%m-%d}<br>Market Price: " + fmt + "<extra></extra>",
            ))

        conn_val = actual_vals.iloc[-1]
        fp       = future[future_col]
        fut_y    = [None] * (N - 1) + [conn_val] + list(fp.values)

        idx_arr      = np.arange(1, M + 1)
        sigma        = np.std(fp.values) * 0.015 * idx_arr
        ci_up, ci_dn = list(fp.values + 1.96 * sigma), list(fp.values - 1.96 * sigma)
        ci_x         = [h.index[-1]] + list(future.index)
        fig1.add_trace(go.Scatter(
            x=ci_x + ci_x[::-1],
            y=[conn_val] + ci_up + ([conn_val] + ci_dn)[::-1],
            fill="toself", fillcolor=MN_C_CI, line=dict(width=0),
            name="95% CI", showlegend=True, hoverinfo="skip",
        ))

        custom_data = np.stack(
            ([None] * (N - 1) + [conn_val] + ci_up,
             [None] * (N - 1) + [conn_val] + ci_dn), axis=-1
        )
        htemplate = (
            "<b>%{x|%B %Y}</b><br>%{x|%Y-%m-%d}<br>Future Forecast Price: " + fmt +
            "<br>Max (95% CI): " + fmt.replace("%{y", "%{customdata[0]") +
            "<br>Min (95% CI): " + fmt.replace("%{y", "%{customdata[1]") + "<extra></extra>"
        )
        fig1.add_trace(go.Scatter(
            x=full_x, y=fut_y, name="Future Forecast Price",
            line=dict(color=MN_C_FUTURE, width=3),
            customdata=custom_data, hovertemplate=htemplate,
        ))

        fig1.update_layout(**mn_layout(f"{alloy_label} Price Trajectory", y_title, 470))
        st.plotly_chart(fig1, use_container_width=True)

        if show_dual:
            fig2 = make_subplots(specs=[[{"secondary_y": True}]])
            h_idx_vals = h["hybrid_prediction"]
            fig2.add_trace(go.Scatter(
                x=full_x, y=list(h_idx_vals) + [None] * M,
                name="Index", line=dict(color=MN_C_HYBRID, width=3),
                hovertemplate="<b>%{x|%B %Y}</b><br>%{x|%Y-%m-%d}<br>Index: %{y:.2f}<extra></extra>",
            ), secondary_y=False)
            fig2.add_trace(go.Scatter(
                x=full_x, y=list(h["real_price"]) + [None] * M,
                name="Index Price", line=dict(color=MN_C_ACTUAL, width=2.5, dash="dash"),
                hovertemplate="<b>%{x|%B %Y}</b><br>%{x|%Y-%m-%d}<br>Index Price: ₹%{y:.2f}<extra></extra>",
            ), secondary_y=True)
            fut_idx_y = [None] * (N - 1) + [h_idx_vals.iloc[-1]] + list(future["predicted_index"])
            fig2.add_trace(go.Scatter(
                x=full_x, y=fut_idx_y, name="Future Index",
                line=dict(color="#64B5F6", width=3),
                hovertemplate="<b>%{x|%B %Y}</b><br>%{x|%Y-%m-%d}<br>Future Index: %{y:.2f}<extra></extra>",
            ), secondary_y=False)
            fut_rp_y = [None] * (N - 1) + [h["real_price"].iloc[-1]] + list(future["real_price"])
            fig2.add_trace(go.Scatter(
                x=full_x, y=fut_rp_y, name="Future Index Price",
                line=dict(color="#FF5722", width=2.5, dash="dash"),
                hovertemplate="<b>%{x|%B %Y}</b><br>%{x|%Y-%m-%d}<br>Future Index Price: ₹%{y:.2f}<extra></extra>",
            ), secondary_y=True)
            fig2.update_layout(**mn_layout("Index vs Price — Dual Axis Comparison", "Price Index", 400))
            fig2.update_yaxes(title_text="Price Index (Solid Lines)", secondary_y=False)
            fig2.update_yaxes(title_text="Price Rs/Kg (Dashed Lines)", secondary_y=True, showgrid=False)
            st.plotly_chart(fig2, use_container_width=True)

    # ── TAB 2: MARKET COMPARISON ──────────────────────────────────────────────
    with tab2:
        if "market_price" in hist.columns:
            common = hist[["real_price", "market_price"]].dropna()
            if not common.empty:
                fig_mkt = go.Figure()
                fig_mkt.add_trace(go.Scatter(
                    x=common.index, y=common["market_price"],
                    name="Market Price", mode="lines",
                    line=dict(color=MN_C_MARKET, width=3),
                    hovertemplate="<b>%{x|%B %Y}</b><br>%{x|%Y-%m-%d}<br>Market Price: ₹%{y:.2f}<extra></extra>",
                ))
                fig_mkt.add_trace(go.Scatter(
                    x=common.index, y=common["real_price"],
                    name="Index Price", mode="lines",
                    line=dict(color=MN_C_HYBRID, width=2.5, dash="dash"),
                    hovertemplate="<b>%{x|%B %Y}</b><br>%{x|%Y-%m-%d}<br>Index Price: ₹%{y:.2f}<extra></extra>",
                ))
                fig_mkt.update_layout(**mn_layout("Market Comparison: Real vs Predicted", y_title="Rs/Kg", height=380))
                st.plotly_chart(fig_mkt, use_container_width=True)
                err       = common["real_price"] - common["market_price"]
                ec1, ec2, ec3 = st.columns(3)
                ec1.metric("RMSE vs Market", f"₹{float(np.sqrt((err**2).mean())):.2f}")
                ec2.metric("MAE vs Market",  f"₹{float(err.abs().mean()):.2f}")
                ec3.metric("MAPE vs Market", f"{float((err.abs() / common['market_price']).mean() * 100):.2f}%")
            else:
                st.info("📂 Market column exists, but dates did not match.")
        else:
            st.info("📂 No market price data found. The pipeline skipped it.")

    # ── TAB 3: REGIME & DRIVERS ───────────────────────────────────────────────
    with tab3:
        st.markdown("### 🌍 Underlying Macro Drivers Over Time")
        st.caption("Tracks the raw online data inputs. Normalized to start at 100 on the left side to compare relative growth.")

        driver_list      = ["simn", "mn_ore", "chn_electricity", "met_coal",
                            "dry_bulk_freight", "steel_etf", "usd_inr", "pick"]
        available_drivers = [d for d in driver_list if d in hist.columns]

        if available_drivers:
            fig_d  = go.Figure()
            plot_h = hist[hist.index >= hist.index[-1] - pd.DateOffset(weeks=display_window)]
            for d_col in available_drivers:
                first_valid = plot_h[d_col].dropna().iloc[0] if not plot_h[d_col].dropna().empty else 1.0
                fig_d.add_trace(go.Scatter(
                    x=plot_h.index,
                    y=(plot_h[d_col] / (first_valid + 1e-9)) * 100,
                    mode="lines",
                    name=d_col.replace("_", " ").title(),
                ))
            fig_d.update_layout(**mn_layout("Relative Movement of Key Drivers (Indexed to 100)", "Index Value", 400))
            st.plotly_chart(fig_d, use_container_width=True)

        st.divider()

        h_tab3 = hist[hist.index >= hist.index[-1] - pd.DateOffset(weeks=display_window)].copy()
        if "regime_probability" in hist.columns:
            st.markdown("### Market Regime State")
            fig_r = go.Figure(go.Scatter(
                x=h_tab3.index, y=h_tab3["regime_probability"],
                name="P(Supply Squeeze)", fill="tozeroy",
                fillcolor="rgba(244, 67, 54, 0.2)",
                line=dict(color="#D32F2F"),
            ))
            fig_r.update_layout(**mn_layout("P(Supply Squeeze / High Volatility)", "Probability", 250))
            st.plotly_chart(fig_r, use_container_width=True)

        fc1, fc2 = st.columns(2)
        fig_bar  = go.Figure(go.Bar(
            x=fi["importance"][::-1], y=fi["feature"][::-1],
            orientation="h", marker=dict(color="#3F51B5", opacity=0.85),
        ))
        fig_bar.update_layout(**mn_layout("Top Driver Importance", "Score", 400))
        fc1.plotly_chart(fig_bar, use_container_width=True)

        top_d = fi.head(7).copy()
        if fi.iloc[7:]["importance"].sum() > 0:
            top_d = pd.concat([
                top_d,
                pd.DataFrame([{"feature": "Other Variables", "importance": fi.iloc[7:]["importance"].sum()}]),
            ])
        fig_pie = go.Figure(data=[go.Pie(
            labels=top_d["feature"],
            values=(top_d["importance"] / top_d["importance"].sum()) * 100,
            hole=0.5,
        )])
        fig_pie.update_layout(
            title=dict(text=f"% Dependence of {alloy_code} on Drivers", font=dict(size=16), x=0.5),
            template="plotly_white", height=400,
        )
        fc2.plotly_chart(fig_pie, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ██████████████████████████   SILICON SECTION   ██████████████████████████████
# ══════════════════════════════════════════════════════════════════════════════

# ── Design palette (Si) ───────────────────────────────────────────────────────
SI_C_IDX    = "#1565C0"
SI_C_FESI   = "#6A1B9A"
SI_C_MARKET = "#E65100"
SI_C_FUTURE = "#2E7D32"
SI_C_CI     = "rgba(46, 125, 50, 0.10)"
SI_C_REG_H  = "rgba(211, 47, 47, 0.12)"
SI_C_REG_M  = "rgba(255, 152, 0, 0.10)"
SI_C_GRID   = "#EEEEEE"
SI_C_TEXT   = "#212121"
SI_C_VIU_G  = "#43A047"
SI_C_VIU_GR = "#9E9E9E"
SI_C_EP     = "#1565C0"
SI_C_EN     = "#E65100"

SI_DRIVER_LABELS = {
    "al_price": "Aluminium Price (LME)",
    "solar_etf": "Solar PV Demand (TAN)",
    "semiconductor_etf": "Semiconductor ETF (SOXX)",
    "china_etf": "China Industrial ETF (FXI)",
    "bdry_freight": "Baltic Dry Freight",
    "vix": "VIX (Risk Regime)",
    "thermal_coal_futures": "Thermal Coal Futures",
    "crude_oil": "WTI Crude Oil",
    "usd_inr": "USD/INR FX",
    "silica_quartz_index": "High-Purity Quartz Spot",
    "cny_inr": "CNY/INR FX",
    "hydrology_rainfall_index": "Hydrology / Reservoir Level",
    "petcoke_charcoal_index": "Reductant Index (Petcoke/Charcoal)",
    "electrode_consumables_index": "Graphite Electrode Prices",
    "gfex_silicon_futures": "GFEX Silicon Futures",
    "electricity_power_index": "Synthetic Electricity Power Index",
    "steel_etf": "Steel ETF (SLX)",
    "iron_ore": "Iron Ore Futures",
    "india_steel": "India Steel (JSW)",
    "zce_fesi_futures": "ZCE FeSi Futures",
    "carbon_emissions_futures": "EU ETS Carbon Spot (CBAM)",
    "fx_effect": "USD/CNY FX Effect",
    "shaanxi_semicoke": "Shaanxi Semi-Coke Spot",
    "magnesium_demand": "Magnesium Demand (Pidgeon)",
}

SI_DRIVER_PALETTE = [
    "#1565C0", "#6A1B9A", "#2E7D32", "#E65100", "#C62828",
    "#00838F", "#F9A825", "#4A148C", "#1B5E20", "#BF360C",
    "#0277BD", "#D84315", "#558B2F", "#6D4C41", "#546E7A",
    "#F06292", "#BA68C8", "#4DD0E1", "#9575CD", "#7986CB",
    "#81C784", "#FF8A65", "#A1887F", "#90A4AE", "#E57373",
]

STEEL_GRADES = {
    "Commodity Structural (IS2062 / E250)": {
        "eff_si_min": 0.72, "chill_limit": 11.0, "rec_var": 6.0,
        "reblow_max": 5.0, "inclusion_max": 0.050, "power_min": 40.0,
        "si_share_max": 0.40,
    },
    "TMT / Rebar (Fe500D)": {
        "eff_si_min": 0.75, "chill_limit": 10.5, "rec_var": 5.0,
        "reblow_max": 4.5, "inclusion_max": 0.048, "power_min": 50.0,
        "si_share_max": 0.50,
    },
    "HSLA (API X60 / X70)": {
        "eff_si_min": 0.80, "chill_limit": 10.0, "rec_var": 3.0,
        "reblow_max": 4.0, "inclusion_max": 0.042, "power_min": 60.0,
        "si_share_max": 0.70,
    },
    "Automotive (DP600 / DP780)": {
        "eff_si_min": 0.88, "chill_limit": 9.5, "rec_var": 2.0,
        "reblow_max": 3.0, "inclusion_max": 0.038, "power_min": 65.0,
        "si_share_max": 0.90,
    },
    "IF Steel (Deep Draw)": {
        "eff_si_min": 0.92, "chill_limit": 9.0, "rec_var": 1.5,
        "reblow_max": 2.5, "inclusion_max": 0.035, "power_min": 70.0,
        "si_share_max": 1.00,
    },
    "Electrical Steel (CRGO / CRNO)": {
        "eff_si_min": 0.95, "chill_limit": 8.5, "rec_var": 1.0,
        "reblow_max": 2.0, "inclusion_max": 0.033, "power_min": 80.0,
        "si_share_max": 1.00,
    },
}

SI_HEAT_SIZE         = 190.0
SI_STEEL_ALLOY_RATIO = 200.0
SI_POWER_RATE        = 6.5
SI_ELECTRODE_RATE    = 240.0
SI_THROUGHPUT_MARGIN = 2800.0
SI_REBLOW_COST       = 15000.0
SI_STEEL_VALUE       = 60000.0


def si_layout(title: str, y_title: str = "Price", height: int = 460) -> dict:
    return dict(
        template="plotly_white", paper_bgcolor="white", plot_bgcolor="#FAFAFA",
        font=dict(family="Inter, sans-serif", size=12, color=SI_C_TEXT),
        title=dict(text=title, font=dict(size=15, color="#111"), x=0.01),
        legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#DDD",
                    borderwidth=1, font=dict(size=11)),
        xaxis=dict(showgrid=True, gridcolor=SI_C_GRID, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=SI_C_GRID, zeroline=False, title=y_title),
        hovermode="x unified", height=height, margin=dict(l=60, r=20, t=55, b=45),
    )


def si_regime_shapes(dates: pd.DatetimeIndex, probs: np.ndarray,
                     high: float = 0.65, med: float = 0.45) -> list:
    shapes = []
    in_high, in_med = False, False
    t0_h, t0_m     = None, None
    for d, p in zip(dates, probs):
        if p >= high:
            if in_med:
                shapes.append(dict(type="rect", xref="x", yref="paper",
                                   x0=str(t0_m), x1=str(d), y0=0, y1=1,
                                   fillcolor=SI_C_REG_M, line_width=0, layer="below"))
                in_med = False
            if not in_high:
                in_high, t0_h = True, d
        elif p >= med:
            if in_high:
                shapes.append(dict(type="rect", xref="x", yref="paper",
                                   x0=str(t0_h), x1=str(d), y0=0, y1=1,
                                   fillcolor=SI_C_REG_H, line_width=0, layer="below"))
                in_high = False
            if not in_med:
                in_med, t0_m = True, d
        else:
            if in_high:
                shapes.append(dict(type="rect", xref="x", yref="paper",
                                   x0=str(t0_h), x1=str(d), y0=0, y1=1,
                                   fillcolor=SI_C_REG_H, line_width=0, layer="below"))
                in_high = False
            if in_med:
                shapes.append(dict(type="rect", xref="x", yref="paper",
                                   x0=str(t0_m), x1=str(d), y0=0, y1=1,
                                   fillcolor=SI_C_REG_M, line_width=0, layer="below"))
                in_med = False
    if in_high:
        shapes.append(dict(type="rect", xref="x", yref="paper",
                           x0=str(t0_h), x1=str(dates[-1]), y0=0, y1=1,
                           fillcolor=SI_C_REG_H, line_width=0, layer="below"))
    if in_med:
        shapes.append(dict(type="rect", xref="x", yref="paper",
                           x0=str(t0_m), x1=str(dates[-1]), y0=0, y1=1,
                           fillcolor=SI_C_REG_M, line_width=0, layer="below"))
    return shapes


@st.cache_data(ttl=5)
def si_load_alloy_data(alloy_code: str, hw: int):
    output_dir = f"./outputs_{alloy_code}"
    hist   = pd.read_csv(f"{output_dir}/historical_predictions.csv",
                         index_col=0, parse_dates=True)
    future = pd.read_csv(f"{output_dir}/future_forecast.csv",
                         index_col=0, parse_dates=True).iloc[:hw]
    fi     = (pd.read_csv(f"{output_dir}/feature_importance.csv")
               .sort_values("importance", ascending=False).head(25))
    with open(f"{output_dir}/model_metadata.json") as f:
        meta = json.load(f)
    return hist, future, fi, meta


def si_get_real_price_series(alloy_code: str):
    try:
        df = pd.read_csv(f"./outputs_{alloy_code}/historical_predictions.csv",
                         index_col=0, parse_dates=True)
        return df["real_price"]
    except Exception:
        return None


def si_get_future_price_series(alloy_code: str):
    try:
        df = pd.read_csv(f"./outputs_{alloy_code}/future_forecast.csv",
                         index_col=0, parse_dates=True)
        return df["real_price"]
    except Exception:
        return None


def si_generate_executive_insights(alloy_code, hist, future, meta, fi) -> dict:
    last_price  = float(hist["real_price"].iloc[-1])
    regime_now  = float(hist["regime_probability"].iloc[-1])
    nxt_price   = float(future["real_price"].iloc[0])
    end_price   = float(future["real_price"].iloc[-1])
    price_trend = (end_price - last_price) / (last_price + 1e-9) * 100

    known_drivers = {
        "al_price", "solar_etf", "semiconductor_etf", "china_etf",
        "bdry_freight", "vix", "thermal_coal_futures", "crude_oil",
        "usd_inr", "silica_quartz_index", "cny_inr",
        "hydrology_rainfall_index", "petcoke_charcoal_index",
        "electrode_consumables_index", "gfex_silicon_futures",
        "electricity_power_index", "steel_etf", "iron_ore",
        "india_steel", "zce_fesi_futures", "carbon_emissions_futures",
        "fx_effect", "shaanxi_semicoke", "magnesium_demand",
    }
    top_driver = fi["feature"].iloc[0]
    for feat in fi["feature"]:
        base = feat.split("_lag")[0].split("_rm")[0].split("_rz")[0].split("_ret")[0]
        if base in known_drivers:
            top_driver = base
            break

    if regime_now > 0.65:
        regime_alert = "🔴 HIGH STRESS: Market in high-volatility regime. Procurement risk elevated."
        regime_color = "error"
    elif regime_now > 0.45:
        regime_alert = "🟡 ELEVATED RISK: Transition regime. Monitor closely."
        regime_color = "warning"
    else:
        regime_alert = "🟢 STABLE REGIME: Low volatility. Favourable procurement window."
        regime_color = "success"

    wk4_idx = min(3, len(future) - 1)
    wk4_chg = (float(future["real_price"].iloc[wk4_idx]) - last_price) / last_price * 100
    if wk4_chg > 3:
        momentum = f"📈 UPWARD: +{wk4_chg:.1f}% forecast over next 4 weeks. Consider forward procurement."
    elif wk4_chg < -3:
        momentum = f"📉 DOWNWARD: {wk4_chg:.1f}% forecast over next 4 weeks. Defer non-urgent orders."
    else:
        momentum = f"➡️ SIDEWAYS: {wk4_chg:+.1f}% over next 4 weeks. Neutral procurement stance."

    if price_trend > 10:
        outlook = f"⚠️ RISING TREND: +{price_trend:.1f}% over forecast horizon. Lock in forward contracts."
    elif price_trend < -10:
        outlook = f"💡 FALLING TREND: {price_trend:.1f}% over forecast horizon. Spot buying preferred."
    else:
        outlook = f"📊 RANGE-BOUND: {price_trend:+.1f}% over forecast horizon. Blend spot and term procurement."

    driver_label    = top_driver.replace("_", " ").title()
    driver_comment  = f"🔧 DOMINANT DRIVER: '{driver_label}' has highest predictive weight. Monitor weekly."

    return dict(
        regime_alert=regime_alert, regime_color=regime_color,
        momentum=momentum, outlook=outlook, driver_comment=driver_comment,
        last_price=last_price, regime_prob=regime_now, price_trend=price_trend,
    )


def si_compute_operational_benefits(
    power_kwh, recovery_pct, slag_red_kg, inclusion_rej,
    reblow_pct, yield_gain_pct, throughput_min, si_price_mt,
) -> dict:
    power_benefit      = power_kwh * SI_POWER_RATE
    electrode_benefit  = power_kwh * 0.00286 * SI_ELECTRODE_RATE
    recovery_benefit   = (recovery_pct / 100) * si_price_mt * 0.50
    scale              = SI_STEEL_ALLOY_RATIO / SI_HEAT_SIZE
    slag_benefit       = slag_red_kg * 600 * SI_HEAT_SIZE * 0.05 * scale
    inclusion_benefit  = (inclusion_rej / 100) * SI_STEEL_VALUE * SI_STEEL_ALLOY_RATIO * 0.40
    reblow_benefit     = (reblow_pct / 100) * SI_REBLOW_COST * scale
    yield_benefit      = (yield_gain_pct / 100) * SI_STEEL_VALUE * SI_STEEL_ALLOY_RATIO * 0.50
    throughput_benefit = (throughput_min / 53.0) * SI_HEAT_SIZE * 0.25 * SI_THROUGHPUT_MARGIN * scale
    return {
        "Power Saving":          round(power_benefit, 2),
        "Electrode Saving":      round(electrode_benefit, 2),
        "Recovery Improvement":  round(recovery_benefit, 2),
        "Slag Reduction":        round(slag_benefit, 2),
        "Inclusion Cleanliness": round(inclusion_benefit, 2),
        "Reblow Reduction":      round(reblow_benefit, 2),
        "Yield Improvement":     round(yield_benefit, 2),
        "Throughput/RH Saving":  round(throughput_benefit, 2),
    }


def si_calc_tco(price_mt, si_pct, fe_pct, recovery, fe_credit_rate, viu_benefits_total) -> dict:
    effective_si = (si_pct / 100) * (recovery / 100)
    fe_credit    = (fe_pct / 100) * fe_credit_rate
    adj_price    = price_mt - fe_credit
    base_viu     = adj_price / (effective_si + 1e-9)
    viu_per_eff  = viu_benefits_total / (effective_si + 1e-9)
    tco          = base_viu - viu_per_eff
    return dict(
        effective_si=effective_si, fe_credit=fe_credit, adj_price=adj_price,
        base_viu=base_viu, viu_benefits_per_eff=viu_per_eff, tco=tco,
    )


def render_silicon():
    """Render the full Silicon dashboard for the selected Si product."""

    alloy_code    = "Si" if "Metal" in product_choice else "FeSi"
    product_label = "Silicon Metal" if alloy_code == "Si" else "FeSi Alloy"
    color         = SI_C_IDX if alloy_code == "Si" else SI_C_FESI

    # ── Data load ─────────────────────────────────────────────────────────────
    try:
        hist, future, fi, meta = si_load_alloy_data(alloy_code, horizon_weeks)
    except FileNotFoundError:
        st.error(
            f"⛔ Pipeline outputs for **{alloy_code}** not found.  \n"
            f"Run the pipeline first:  \n"
            f"```bash\npython pipeline_silicon.py --alloy {alloy_code}\n```"
        )
        st.stop()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f"<h1 style='color:{color}; margin-bottom:4px;'>⚗️ {product_label} Intelligence Platform</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#666; margin-top:0; font-size:14px;'>"
        "Procurement Intelligence · Process Economics · Substitution Solver</p>",
        unsafe_allow_html=True,
    )

    insights = si_generate_executive_insights(alloy_code, hist, future, meta, fi)

    if insights["regime_color"] == "error":
        st.error(insights["regime_alert"])
    elif insights["regime_color"] == "warning":
        st.warning(insights["regime_alert"])
    else:
        st.success(insights["regime_alert"])

    # KPI row
    last_real = float(hist["real_price"].iloc[-1])
    last_idx  = float(hist["actual"].iloc[-1])
    nxt_real  = float(future["real_price"].iloc[0])
    end_real  = float(future["real_price"].iloc[-1])
    pct_1wk   = (nxt_real - last_real) / (last_real + 1e-9) * 100
    pct_end   = (end_real - last_real) / (last_real + 1e-9) * 100
    mape_hist = float(np.mean(np.abs(
        (hist["actual"] - hist["hybrid_prediction"]) / (hist["actual"] + 1e-9)
    )) * 100)

    overlap_rows = hist.dropna(subset=["market_price"]) if "market_price" in hist.columns else pd.DataFrame()
    if len(overlap_rows) > 5:
        mkt_rmse = float(np.sqrt(np.mean(
            (overlap_rows["real_price"] - overlap_rows["market_price"]) ** 2)))
        mkt_mape = float(np.mean(np.abs(
            (overlap_rows["real_price"] - overlap_rows["market_price"]) /
            (overlap_rows["market_price"] + 1e-9)
        )) * 100)
    else:
        mkt_rmse, mkt_mape = None, None

    k1, k2, k3, k4, k5, k6 = st.columns([1, 1.2, 1.5, 1.8, 1, 1])
    k1.metric("📍 Last Index",         f"{last_idx:.1f}")
    k2.metric("💰 Current Price",      f"₹{last_real:.1f}/Kg")
    k3.metric("📅 Next-Week Forecast", f"₹{nxt_real:.1f}/Kg",
              delta=f"{pct_1wk:+.1f}%",
              delta_color="inverse" if alloy_code == "Si" else "normal")
    k4.metric("🎯 Horizon-End Price",  f"₹{end_real:.1f}/Kg",
              delta=f"{pct_end:+.1f}% ({len(future)} wks)", delta_color="off")
    k5.metric("📊 In-Sample MAPE",     f"{mape_hist:.1f}%")
    k6.metric("⚖️ Scale Factor",       f"{meta.get('scaling_factor', 0):.2f}",
              help=f"Anchored: {meta.get('anchor_date')} = ₹{meta.get('anchor_price_kg', 0):.2f}/Kg")

    st.divider()

    # ── Tabs (3 only — VIU & Substitution Solver removed) ────────────────────
    tab1, tab2, tab3 = st.tabs([
        "📉 Price Forecast",
        "📊 Market Comparison",
        "🔀 Regime & Drivers",
    ])

    # ── TAB 1: PRICE FORECAST ─────────────────────────────────────────────────
    with tab1:
        h = hist[hist.index >= hist.index[-1] - pd.DateOffset(weeks=display_window)].copy()

        use_real  = price_mode.startswith("₹")
        hist_vals = h["real_price"]  if use_real else h["actual"]
        fut_col   = "real_price"     if use_real else "predicted_index"
        y_label   = "Price (₹/Kg)"  if use_real else "Price Index"
        hover_fmt = "₹%{y:.2f}/Kg"  if use_real else "Index: %{y:.3f}"

        N = len(h)
        M = len(future)
        full_x = list(h.index) + list(future.index)

        fig1 = go.Figure()

        if show_regime and "regime_probability" in h.columns:
            for s in si_regime_shapes(h.index, h["regime_probability"].values):
                fig1.add_shape(**s)

        fig1.add_trace(go.Scatter(
            x=full_x, y=list(hist_vals) + [None] * M,
            name=f"{product_label} Index", line=dict(color=color, width=2.8),
            hovertemplate=f"<b>%{{x|%d %b %Y}}</b><br>{product_label}: {hover_fmt}<extra></extra>",
        ))

        if show_market and "market_price" in h.columns:
            mkt_vals = h["market_price"]
            if mkt_vals.notna().any():
                fig1.add_trace(go.Scatter(
                    x=full_x, y=list(mkt_vals) + [None] * M,
                    name="Indian Market Price",
                    line=dict(color=SI_C_MARKET, width=2.2, dash="dot"),
                    hovertemplate=f"<b>%{{x|%d %b %Y}}</b><br>Market: {hover_fmt}<extra></extra>",
                ))

        conn_val = float(hist_vals.iloc[-1])
        fp       = future[fut_col]

        # Always compute CI values so they can be shown in the forecast hover tooltip
        idx_arr    = np.arange(1, M + 1)
        base_sigma = float(np.std(fp.values)) if len(fp) > 1 and np.std(fp.values) > 0 else conn_val * 0.03
        sigma      = base_sigma * 0.015 * idx_arr
        ci_up      = list(np.array(fp.values) + 1.96 * sigma)
        ci_dn      = list(np.array(fp.values) - 1.96 * sigma)

        if show_ci and len(fp) > 1:
            ci_x = [h.index[-1]] + list(future.index)
            fig1.add_trace(go.Scatter(
                x=ci_x + ci_x[::-1],
                y=[conn_val] + ci_up + ([conn_val] + ci_dn)[::-1],
                fill="toself", fillcolor=SI_C_CI, line=dict(width=0),
                name="95% CI Band", showlegend=True, hoverinfo="skip",
            ))

        # customdata: [ci_up, ci_dn] aligned to full_x; None for historical points
        ci_up_full = [None] * (N - 1) + [conn_val] + ci_up
        ci_dn_full = [None] * (N - 1) + [conn_val] + ci_dn
        si_forecast_customdata = np.stack([ci_up_full, ci_dn_full], axis=-1)

        price_unit = "₹" if use_real else ""
        price_sfx  = "/Kg" if use_real else ""
        ci_fmt     = f"{price_unit}%{{customdata[0]:.2f}}{price_sfx}" if use_real else "%{customdata[0]:.3f}"
        ci_fmt_dn  = f"{price_unit}%{{customdata[1]:.2f}}{price_sfx}" if use_real else "%{customdata[1]:.3f}"

        fut_y = [None] * (N - 1) + [conn_val] + list(fp.values)
        fig1.add_trace(go.Scatter(
            x=full_x, y=fut_y, name="Future Forecast",
            line=dict(color=SI_C_FUTURE, width=2.8, dash="dash"),
            customdata=si_forecast_customdata,
            hovertemplate=(
                f"<b>%{{x|%d %b %Y}}</b><br>"
                f"Forecast: {hover_fmt}<br>"
                f"95% CI Max: {ci_fmt}<br>"
                f"95% CI Min: {ci_fmt_dn}"
                "<extra></extra>"
            ),
        ))

        x_forecast_start = h.index[-1]
        fig1.add_vline(x=x_forecast_start, line_width=1.5, line_dash="dot", line_color="#999")
        fig1.add_annotation(
            x=x_forecast_start, y=1, yref="paper",
            text="Forecast →", showarrow=False,
            xanchor="left", yanchor="top", font=dict(size=11), xshift=5,
        )

        fig1.update_layout(**si_layout(
            f"{product_label} — Price Trajectory & {horizon_label} Forecast", y_label, 490,
        ))
        st.plotly_chart(fig1, use_container_width=True)

        col_ins1, col_ins2 = st.columns(2)
        col_ins1.info(f"**4-Week Outlook:** {insights['momentum']}")
        col_ins2.info(f"**Horizon Outlook:** {insights['outlook']}")
        st.caption(insights["driver_comment"])

        with st.expander("📊 Show Dual-Axis: Index vs Real Price", expanded=False):
            fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
            fig_dual.add_trace(
                go.Scatter(x=h.index, y=h["actual"],
                           name="Index Value", line=dict(color=color, width=2.5)),
                secondary_y=False,
            )
            fig_dual.add_trace(
                go.Scatter(x=h.index, y=h["real_price"],
                           name="Real Price (₹/Kg)",
                           line=dict(color=SI_C_MARKET, width=2, dash="dash")),
                secondary_y=True,
            )
            fig_dual.update_yaxes(title_text="Price Index", secondary_y=False,
                                   showgrid=True, gridcolor=SI_C_GRID)
            fig_dual.update_yaxes(title_text="₹/Kg", secondary_y=True, showgrid=False)
            fig_dual.update_xaxes(showgrid=True, gridcolor=SI_C_GRID)
            fig_dual.update_layout(
                title=f"{product_label}: Index vs Real Price (Dual Axis)",
                template="plotly_white", height=380,
                legend=dict(orientation="h", y=1.06),
                hovermode="x unified",
            )
            st.plotly_chart(fig_dual, use_container_width=True)

    # ── TAB 2: MARKET COMPARISON ──────────────────────────────────────────────
    with tab2:
        st.markdown("### 📊 Model vs Indian Market Price — Validation Dashboard")
        st.caption(
            "Compares model-generated calibrated index price against actual Indian market prices. "
            "Overlap period only — shows where real data exists."
        )

        if "market_price" not in hist.columns or hist["market_price"].isna().all():
            st.warning(
                "⚠️ No market price data found in pipeline outputs. "
                "Ensure `market_prices_Si_FeSi.xlsx` is in the working directory and re-run pipeline."
            )
        else:
            mkt_overlap = hist.dropna(subset=["market_price"]).copy()
            mkt_overlap = mkt_overlap[
                mkt_overlap.index >= hist.index[-1] - pd.DateOffset(weeks=display_window)
            ]

            if len(mkt_overlap) < 3:
                st.warning(
                    f"Only {len(mkt_overlap)} overlapping data points found in the selected display window. "
                    "Increase history window on the sidebar to view more data."
                )
            else:
                rmse = float(np.sqrt(np.mean(
                    (mkt_overlap["real_price"] - mkt_overlap["market_price"]) ** 2)))
                mae  = float(np.mean(np.abs(
                    mkt_overlap["real_price"] - mkt_overlap["market_price"])))
                mape = float(np.mean(np.abs(
                    (mkt_overlap["real_price"] - mkt_overlap["market_price"]) /
                    (mkt_overlap["market_price"] + 1e-9)
                )) * 100)
                corr = float(np.corrcoef(
                    mkt_overlap["real_price"], mkt_overlap["market_price"])[0, 1])
                bias = float((mkt_overlap["real_price"] - mkt_overlap["market_price"]).mean())

                m1, m2, m3, m4, m5 = st.columns(5)
                m1.metric("RMSE (₹/Kg)", f"₹{rmse:.2f}")
                m2.metric("MAE (₹/Kg)",  f"₹{mae:.2f}")
                m3.metric("MAPE",        f"{mape:.2f}%")
                m4.metric("Correlation", f"{corr:.2f}")
                m5.metric("Mean Bias",   f"₹{bias:+.2f}/Kg",
                          help="Positive = model overestimates market")

                st.divider()

                h_t2 = hist[hist.index >= hist.index[-1] - pd.DateOffset(weeks=display_window)].copy()

                fig_mkt = go.Figure()
                fig_mkt.add_trace(go.Scatter(
                    x=mkt_overlap.index, y=mkt_overlap["market_price"],
                    name="Indian Market Price (Actual)",
                    mode="markers+lines",
                    line=dict(color=SI_C_MARKET, width=2.8),
                    hovertemplate="<b>%{x|%d %b %Y}</b><br>Market: ₹%{y:.2f}/Kg<extra></extra>",
                ))
                fig_mkt.add_trace(go.Scatter(
                    x=h_t2.index, y=h_t2["real_price"],
                    name="Model Index Price",
                    line=dict(color=color, width=2.5, dash="dash"),
                    hovertemplate="<b>%{x|%d %b %Y}</b><br>Model: ₹%{y:.2f}/Kg<extra></extra>",
                ))
                fig_mkt.add_trace(go.Scatter(
                    x=list(mkt_overlap.index) + list(mkt_overlap.index[::-1]),
                    y=list(mkt_overlap["market_price"]) + list(mkt_overlap["real_price"][::-1]),
                    fill="toself", fillcolor="rgba(100,100,200,0.07)",
                    line=dict(width=0), name="Model Error Band", hoverinfo="skip",
                ))
                last_hist_date  = h_t2.index[-1]
                last_hist_price = float(h_t2["real_price"].iloc[-1])
                forecast_x = [last_hist_date] + list(future.index)
                forecast_y = [last_hist_price] + list(future["real_price"])
                fig_mkt.add_trace(go.Scatter(
                    x=forecast_x, y=forecast_y,
                    name="Future Forecast (Model)",
                    line=dict(color=SI_C_FUTURE, width=2.2, dash="dot"),
                    hovertemplate="<b>%{x|%d %b %Y}</b><br>Forecast: ₹%{y:.2f}/Kg<extra></extra>",
                ))
                x_mkt_forecast = mkt_overlap.index[-1]
                fig_mkt.add_vline(x=x_mkt_forecast, line_width=1.5, line_dash="dot", line_color="#999")
                fig_mkt.add_annotation(
                    x=x_mkt_forecast, y=1, yref="paper",
                    text="Forecast Start →", showarrow=False,
                    xanchor="left", yanchor="top", font=dict(size=11), xshift=5,
                )
                fig_mkt.update_layout(**si_layout(
                    f"{product_label}: Indian Market Price vs Model Index Price", "Price (₹/Kg)", 490,
                ))
                st.plotly_chart(fig_mkt, use_container_width=True)

                error_s = mkt_overlap["real_price"] - mkt_overlap["market_price"]
                fig_err = go.Figure()
                fig_err.add_trace(go.Bar(
                    x=mkt_overlap.index, y=error_s,
                    name="Error (Model − Market)",
                    marker=dict(
                        color=np.where(error_s >= 0, SI_C_EP, SI_C_EN),
                        opacity=0.75,
                    ),
                    hovertemplate="<b>%{x|%d %b %Y}</b><br>Error: ₹%{y:.2f}/Kg<extra></extra>",
                ))
                fig_err.add_hline(y=0, line_color="#333", line_width=1)
                fig_err.add_hline(y=bias, line_dash="dot", line_color="#888")
                fig_err.add_annotation(
                    x=1, xref="paper", y=bias,
                    text=f"Mean Bias: ₹{bias:+.2f}", showarrow=False,
                    xanchor="right", yanchor="bottom", yshift=2,
                )
                fig_err.update_layout(**si_layout("Weekly Model Error (₹/Kg)", "Error (₹/Kg)", 300))
                st.plotly_chart(fig_err, use_container_width=True)

                col_s1, col_s2 = st.columns(2)

                fig_scat = go.Figure()
                fig_scat.add_trace(go.Scatter(
                    x=mkt_overlap["market_price"], y=mkt_overlap["real_price"],
                    mode="markers",
                    marker=dict(color=color, size=7, opacity=0.65),
                    hovertemplate="Market: ₹%{x:.2f}<br>Model: ₹%{y:.2f}<extra></extra>",
                    name="Observations",
                ))
                mn2 = mkt_overlap["market_price"].min()
                mx2 = mkt_overlap["market_price"].max()
                fig_scat.add_trace(go.Scatter(
                    x=[mn2, mx2], y=[mn2, mx2], mode="lines", name="Perfect Fit",
                    line=dict(color="#aaa", dash="dash", width=1.5),
                ))
                fig_scat.update_layout(**si_layout(
                    "Calibration Scatter: Model vs Market", "Model Price (₹/Kg)", 380))
                fig_scat.update_xaxes(title="Market Price (₹/Kg)")
                col_s1.plotly_chart(fig_scat, use_container_width=True)

                fig_hist_err = go.Figure(go.Histogram(
                    x=error_s, nbinsx=20,
                    marker_color=color, opacity=0.75, name="Error Dist",
                ))
                fig_hist_err.add_vline(x=0, line_color="#333", line_width=1.5)
                fig_hist_err.add_vline(x=bias, line_dash="dot", line_color=SI_C_MARKET)
                fig_hist_err.add_annotation(
                    x=bias, y=1, yref="paper",
                    text=f"Bias={bias:+.2f}", showarrow=False,
                    xanchor="right", yanchor="top", xshift=-5,
                )
                fig_hist_err.update_layout(**si_layout("Error Distribution", "Frequency", 380))
                col_s2.plotly_chart(fig_hist_err, use_container_width=True)

                with st.expander("📋 View Weekly Comparison Data", expanded=False):
                    tbl = mkt_overlap[["real_price", "market_price"]].copy()
                    tbl.columns = ["Model Price (₹/Kg)", "Market Price (₹/Kg)"]
                    tbl["Error (₹/Kg)"] = (tbl["Model Price (₹/Kg)"] - tbl["Market Price (₹/Kg)"]).round(2)
                    tbl["Error %"] = (tbl["Error (₹/Kg)"] / (tbl["Market Price (₹/Kg)"] + 1e-9) * 100).round(2)
                    st.dataframe(
                        tbl.sort_index(ascending=False).style.format({
                            "Model Price (₹/Kg)":  "₹{:.2f}",
                            "Market Price (₹/Kg)": "₹{:.2f}",
                            "Error (₹/Kg)":        "₹{:+.2f}",
                            "Error %":             "{:+.2f}%",
                        }),
                        use_container_width=True,
                    )

    # ── TAB 3: REGIME & DRIVERS ───────────────────────────────────────────────
    with tab3:
        st.markdown("### 🌍 Macro Driver Analysis & Market Regime")

        h_drv = hist[hist.index >= hist.index[-1] - pd.DateOffset(weeks=display_window)].copy()

        if "regime_probability" in h_drv.columns:
            fig_reg = go.Figure()
            reg_vals = h_drv["regime_probability"].values
            fig_reg.add_trace(go.Scatter(
                x=h_drv.index, y=reg_vals,
                name="P(High Volatility Regime)",
                fill="tozeroy",
                fillcolor="rgba(211, 47, 47, 0.15)",
                line=dict(color="#D32F2F", width=2),
                hovertemplate="<b>%{x|%d %b %Y}</b><br>Regime Prob: %{y:.2%}<extra></extra>",
            ))
            fig_reg.add_hline(y=0.65, line_dash="dot", line_color="#D32F2F")
            fig_reg.add_annotation(
                x=1, xref="paper", y=0.65,
                text="High Stress (0.65)", showarrow=False,
                xanchor="right", yanchor="bottom", yshift=2,
            )
            fig_reg.add_hline(y=0.45, line_dash="dot", line_color="#FF9800")
            fig_reg.add_annotation(
                x=1, xref="paper", y=0.45,
                text="Elevated Risk (0.45)", showarrow=False,
                xanchor="right", yanchor="bottom", yshift=2,
            )
            fig_reg.update_layout(**si_layout(
                f"{product_label}: Market Stress Regime Probability", "Probability", 280))
            st.plotly_chart(fig_reg, use_container_width=True)

        st.divider()

        si_drivers   = [
            "al_price", "solar_etf", "semiconductor_etf", "china_etf",
            "bdry_freight", "vix", "thermal_coal_futures", "crude_oil",
            "usd_inr", "silica_quartz_index", "cny_inr",
            "hydrology_rainfall_index", "petcoke_charcoal_index",
            "electrode_consumables_index", "gfex_silicon_futures",
            "electricity_power_index",
        ]
        fesi_drivers = [
            "steel_etf", "iron_ore", "thermal_coal_futures", "bdry_freight",
            "al_price", "india_steel", "vix", "usd_inr", "silica_quartz_index",
            "cny_inr", "hydrology_rainfall_index", "shaanxi_semicoke",
            "magnesium_demand", "zce_fesi_futures", "carbon_emissions_futures",
            "electricity_power_index", "fx_effect",
        ]
        driver_list = si_drivers if alloy_code == "Si" else fesi_drivers
        avail_drv   = [d for d in driver_list if d in h_drv.columns]

        if avail_drv:
            st.markdown("#### 📈 Relative Driver Movement (Indexed to 100)")
            st.caption("All drivers normalised to 100 at start of history for relative comparison.")
            fig_drv = go.Figure()
            for i, d_col in enumerate(avail_drv):
                s = h_drv[d_col].dropna()
                if s.empty or s.iloc[0] == 0:
                    continue
                norm = (s / s.iloc[0]) * 100
                fig_drv.add_trace(go.Scatter(
                    x=s.index, y=norm,
                    name=SI_DRIVER_LABELS.get(d_col, d_col.replace("_", " ").title()),
                    line=dict(color=SI_DRIVER_PALETTE[i % len(SI_DRIVER_PALETTE)], width=1.8),
                    hovertemplate=(
                        f"<b>%{{x|%d %b %Y}}</b><br>"
                        f"{SI_DRIVER_LABELS.get(d_col, d_col)}: %{{y:.1f}}<extra></extra>"
                    ),
                ))
            fig_drv.update_layout(**si_layout(
                "Relative Driver Movement (Indexed = 100 at start)", "Relative Index", 430))
            st.plotly_chart(fig_drv, use_container_width=True)

        st.divider()

        fc1, fc2 = st.columns([3, 2])

        fig_bar = go.Figure(go.Bar(
            x=fi["importance"].iloc[:15][::-1],
            y=fi["feature"].iloc[:15][::-1],
            orientation="h",
            marker=dict(
                color=fi["importance"].iloc[:15][::-1],
                colorscale="Blues", showscale=False, opacity=0.88,
            ),
            hovertemplate="%{y}: %{x:.1f}<extra></extra>",
        ))
        fig_bar.update_layout(**si_layout(
            f"Top 15 Feature Importances — {product_label}", "Importance Score", 430))
        fc1.plotly_chart(fig_bar, use_container_width=True)

        top7     = fi.head(7).copy()
        rest_imp = fi.iloc[7:]["importance"].sum()
        if rest_imp > 0:
            top7 = pd.concat([
                top7,
                pd.DataFrame([{"feature": "Other Variables", "importance": rest_imp}]),
            ], ignore_index=True)
        fig_pie = go.Figure(go.Pie(
            labels=[SI_DRIVER_LABELS.get(f, f.replace("_", " ").title()) for f in top7["feature"]],
            values=(top7["importance"] / top7["importance"].sum() * 100),
            hole=0.48,
            marker=dict(colors=SI_DRIVER_PALETTE[:len(top7)]),
            textinfo="label+percent", textfont=dict(size=10),
        ))
        fig_pie.update_layout(
            title=dict(text=f"{product_label}: Driver Dependence %",
                       font=dict(size=14), x=0.5),
            template="plotly_white", height=430, showlegend=False,
        )
        fc2.plotly_chart(fig_pie, use_container_width=True)

        with st.expander("⚡ View Historical Shock Event Periods", expanded=False):
            SHOCKS = {
                "covid_disruption":       ("2020-03-01", "2020-08-31"),
                "ukraine_energy_crisis":  ("2022-02-24", "2022-12-31"),
                "logistics_spike":        ("2021-01-01", "2021-12-31"),
                "china_power_curbs_2021": ("2021-08-01", "2021-12-31"),
                "china_export_restrict":  ("2023-07-01", "2024-03-31"),
                "energy_crisis_europe":   ("2022-06-01", "2023-03-31"),
                "steel_downturn_2015":    ("2015-06-01", "2016-06-30"),
                "steel_downturn_2019":    ("2019-01-01", "2019-12-31"),
                "china_steel_curbs":      ("2021-05-01", "2021-12-31"),
                "india_infra_push":       ("2023-01-01", "2024-12-31"),
            }
            shock_df = pd.DataFrame([
                {"Event": k.replace("_", " ").title(), "Start": v[0], "End": v[1]}
                for k, v in SHOCKS.items()
            ])
            st.dataframe(shock_df, use_container_width=True)

            fig_shk = go.Figure()
            fig_shk.add_trace(go.Scatter(
                x=h_drv.index, y=h_drv["actual"],
                name=f"{product_label} Index", line=dict(color=color, width=2),
            ))
            for k, (s_d, e_d) in SHOCKS.items():
                fig_shk.add_vrect(
                    x0=s_d, x1=e_d,
                    fillcolor="rgba(100,100,200,0.08)",
                    layer="below", line_width=0,
                )
                fig_shk.add_annotation(
                    x=s_d, y=1, yref="paper",
                    text=k.replace("_", " ").title()[:18], showarrow=False,
                    xanchor="left", yanchor="top", font=dict(size=8), xshift=2,
                )
            fig_shk.update_layout(**si_layout(
                f"{product_label}: Shock Event Periods vs Index", "Index Value", 380))
            st.plotly_chart(fig_shk, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# ██████████████████████████   ALUMINIUM SECTION   ████████████████████████████
# ══════════════════════════════════════════════════════════════════════════════

# ── Design palette (Al) ───────────────────────────────────────────────────────
AL_C_IDX     = "#1565C0"
AL_C_LME     = "#0288D1"
AL_C_SMM     = "#C62828"
AL_C_MARKET  = "#E65100"
AL_C_FUTURE  = "#2E7D32"
AL_C_CI      = "rgba(46, 125, 50, 0.10)"
AL_C_REG_H   = "rgba(211, 47, 47, 0.12)"
AL_C_REG_M   = "rgba(255, 152, 0, 0.10)"
AL_C_GRID    = "#EEEEEE"
AL_C_TEXT    = "#212121"
AL_C_SILVER  = "#78909C"
AL_C_METAL   = "#546E7A"
AL_C_IPP_POS = "#1565C0"
AL_C_IPP_NEG = "#E65100"

AL_DRIVER_LABELS = {
    "usd_cny":                "USD/CNY FX (China)",
    "usd_inr":                "USD/INR FX (India)",
    "usd_eur":                "USD/EUR FX (Europe)",
    "bdry_freight":           "Baltic Dry Freight (BDRY)",
    "vix":                    "VIX (Risk Regime)",
    "dbb_base_metals_etf":    "Base Metals ETF (DBB)",
    "xme_mining_etf":         "Mining ETF (XME)",
    "crude_oil":              "WTI Crude Oil",
    "ttf_natural_gas":        "TTF Natural Gas (Europe)",
    "bauxite_index":          "Bauxite Spot Index",
    "alumina_index":          "Alumina Price (FOB)",
    "cpc_index":              "Calcined Pet Coke (CPC)",
    "coal_tar_pitch_index":   "Coal Tar Pitch (Anode Binder)",
    "hydrology_index":        "Hydrology / Yunnan Reservoir",
    "lme_3m_benchmark":       "LME 3M Aluminium Benchmark",
    "smm_a00_price":          "SMM A00 Domestic China Price",
    "electricity_power_index":"Electricity Power Cost Index",
    "fx_effect":              "FX Composite (CNY/INR)",
    "crude_oil_csv":          "Crude Oil (CSV)",
    "coal_pci":               "Coal PCI",
    "met_coal_cn":            "Met Coal China",
    "met_coal_ind":           "Met Coal India",
    "al_scrap_zorba_cn":      "Al Scrap Zorba (China)",
    "al_scrap_zorba_ind":     "Al Scrap Zorba (India)",
    "al_tense_scrap":         "Al Tense Scrap",
    "al_alloy_secondary_226": "Al Alloy Secondary 226",
}

AL_DRIVER_PALETTE = [
    "#1565C0", "#C62828", "#2E7D32", "#E65100", "#6A1B9A",
    "#00838F", "#F9A825", "#4A148C", "#1B5E20", "#BF360C",
    "#0277BD", "#D84315", "#558B2F", "#6D4C41", "#546E7A",
    "#F06292", "#BA68C8", "#4DD0E1", "#9575CD", "#7986CB",
    "#81C784", "#FF8A65", "#A1887F", "#90A4AE", "#E57373",
]

AL_SHOCK_EVENTS = {
    "covid_disruption":                   ("2020-03-01", "2020-08-31"),
    "rusal_sanctions_2018":               ("2018-04-06", "2019-12-31"),
    "european_energy_crisis_2022":        ("2022-02-01", "2023-12-31"),
    "china_tax_rebate_cancellation_2024": ("2024-12-01", "2030-12-31"),
    "middle_east_supply_halts":           ("2023-10-01", "2024-06-30"),
    "logistics_spike":                    ("2021-01-01", "2021-12-31"),
    "china_power_curbs_2021":             ("2021-08-01", "2021-12-31"),
    "ukraine_war_onset":                  ("2022-02-24", "2022-12-31"),
    "india_infra_push":                   ("2023-01-01", "2024-12-31"),
}

AL_DISPLAY_DRIVERS = [
    "alumina_index", "electricity_power_index", "lme_3m_benchmark",
    "smm_a00_price", "bauxite_index", "cpc_index", "ttf_natural_gas",
    "crude_oil", "bdry_freight", "usd_cny", "usd_inr", "usd_eur",
    "dbb_base_metals_etf", "xme_mining_etf", "vix",
    "coal_tar_pitch_index", "hydrology_index", "fx_effect",
    "al_tense_scrap", "al_scrap_zorba_cn",
]

PREMIUM_DEFAULTS = {
    "Midwest (US)":    {"min": 150, "max": 350, "default": 225, "currency": "USD/MT"},
    "Rotterdam (NWE)": {"min":  70, "max": 200, "default": 110, "currency": "USD/MT"},
    "MJP (Japan)":     {"min": 100, "max": 250, "default": 155, "currency": "USD/MT"},
    "India (CIF)":     {"min":  80, "max": 180, "default": 120, "currency": "USD/MT"},
    "SE Asia":         {"min":  60, "max": 160, "default":  90, "currency": "USD/MT"},
}

DUTY_DEFAULTS = {
    "Midwest (US)":    {"duty_pct": 10.0, "gst_vat_pct": 0.0,  "other_usd": 15},
    "Rotterdam (NWE)": {"duty_pct":  2.7, "gst_vat_pct": 0.0,  "other_usd":  8},
    "MJP (Japan)":     {"duty_pct":  3.0, "gst_vat_pct": 0.0,  "other_usd": 10},
    "India (CIF)":     {"duty_pct":  7.5, "gst_vat_pct": 18.0, "other_usd": 12},
    "SE Asia":         {"duty_pct":  5.0, "gst_vat_pct": 0.0,  "other_usd":  8},
}


def al_layout(title: str, y_title: str = "Price", height: int = 460) -> dict:
    return dict(
        template="plotly_white", paper_bgcolor="white", plot_bgcolor="#FAFAFA",
        font=dict(family="Inter, sans-serif", size=12, color=AL_C_TEXT),
        title=dict(text=title, font=dict(size=15, color="#111"), x=0.01),
        legend=dict(bgcolor="rgba(255,255,255,0.9)", bordercolor="#DDD",
                    borderwidth=1, font=dict(size=11)),
        xaxis=dict(showgrid=True, gridcolor=AL_C_GRID, zeroline=False),
        yaxis=dict(showgrid=True, gridcolor=AL_C_GRID, zeroline=False, title=y_title),
        hovermode="x unified", height=height, margin=dict(l=60, r=20, t=55, b=45),
    )


def al_regime_shapes(dates: pd.DatetimeIndex, probs: np.ndarray,
                     high: float = 0.65, med: float = 0.45) -> list:
    shapes = []
    in_high, in_med = False, False
    t0_h, t0_m     = None, None
    for d, p in zip(dates, probs):
        if p >= high:
            if in_med:
                shapes.append(dict(type="rect", xref="x", yref="paper",
                                   x0=str(t0_m), x1=str(d), y0=0, y1=1,
                                   fillcolor=AL_C_REG_M, line_width=0, layer="below"))
                in_med = False
            if not in_high:
                in_high, t0_h = True, d
        elif p >= med:
            if in_high:
                shapes.append(dict(type="rect", xref="x", yref="paper",
                                   x0=str(t0_h), x1=str(d), y0=0, y1=1,
                                   fillcolor=AL_C_REG_H, line_width=0, layer="below"))
                in_high = False
            if not in_med:
                in_med, t0_m = True, d
        else:
            if in_high:
                shapes.append(dict(type="rect", xref="x", yref="paper",
                                   x0=str(t0_h), x1=str(d), y0=0, y1=1,
                                   fillcolor=AL_C_REG_H, line_width=0, layer="below"))
                in_high = False
            if in_med:
                shapes.append(dict(type="rect", xref="x", yref="paper",
                                   x0=str(t0_m), x1=str(d), y0=0, y1=1,
                                   fillcolor=AL_C_REG_M, line_width=0, layer="below"))
                in_med = False
    if in_high:
        shapes.append(dict(type="rect", xref="x", yref="paper",
                           x0=str(t0_h), x1=str(dates[-1]), y0=0, y1=1,
                           fillcolor=AL_C_REG_H, line_width=0, layer="below"))
    if in_med:
        shapes.append(dict(type="rect", xref="x", yref="paper",
                           x0=str(t0_m), x1=str(dates[-1]), y0=0, y1=1,
                           fillcolor=AL_C_REG_M, line_width=0, layer="below"))
    return shapes


@st.cache_data(ttl=5)
def al_load_data(hw: int):
    output_dir = "./outputs_Al"
    hist   = pd.read_csv(f"{output_dir}/historical_predictions.csv",
                         index_col=0, parse_dates=True)
    future = pd.read_csv(f"{output_dir}/future_forecast.csv",
                         index_col=0, parse_dates=True).iloc[:hw]
    fi     = (pd.read_csv(f"{output_dir}/feature_importance.csv")
               .sort_values("importance", ascending=False).head(25))
    with open(f"{output_dir}/model_metadata.json") as f:
        meta = json.load(f)
    return hist, future, fi, meta


def al_generate_executive_insights(hist, future, meta, fi) -> dict:
    last_price  = float(hist["real_price"].iloc[-1])
    regime_now  = float(hist["regime_probability"].iloc[-1])
    nxt_price   = float(future["real_price"].iloc[0])
    end_price   = float(future["real_price"].iloc[-1])
    price_trend = (end_price - last_price) / (last_price + 1e-9) * 100

    top_driver  = fi["feature"].iloc[0]
    known_bases = set(AL_DRIVER_LABELS.keys())
    for feat in fi["feature"]:
        base = feat.split("_lag")[0].split("_rm")[0].split("_rz")[0].split("_ret")[0]
        if base in known_bases:
            top_driver = base
            break

    if regime_now > 0.65:
        regime_alert = "🔴 HIGH STRESS: Market in high-volatility regime. Procurement risk elevated."
        regime_color = "error"
    elif regime_now > 0.45:
        regime_alert = "🟡 ELEVATED RISK: Transition regime. Monitor closely."
        regime_color = "warning"
    else:
        regime_alert = "🟢 STABLE REGIME: Low volatility. Favourable procurement window."
        regime_color = "success"

    wk4_idx = min(3, len(future) - 1)
    wk4_chg = (float(future["real_price"].iloc[wk4_idx]) - last_price) / last_price * 100
    if wk4_chg > 3:
        momentum = f"📈 UPWARD: +{wk4_chg:.1f}% forecast over next 4 weeks. Consider forward procurement."
    elif wk4_chg < -3:
        momentum = f"📉 DOWNWARD: {wk4_chg:.1f}% forecast over next 4 weeks. Defer non-urgent orders."
    else:
        momentum = f"➡️ SIDEWAYS: {wk4_chg:+.1f}% over next 4 weeks. Neutral procurement stance."

    if price_trend > 10:
        outlook = f"⚠️ RISING TREND: +{price_trend:.1f}% over forecast horizon. Lock in forward contracts."
    elif price_trend < -10:
        outlook = f"💡 FALLING TREND: {price_trend:.1f}% over forecast horizon. Spot buying preferred."
    else:
        outlook = f"📊 RANGE-BOUND: {price_trend:+.1f}% over forecast horizon. Blend spot and term procurement."

    driver_label   = AL_DRIVER_LABELS.get(top_driver, top_driver.replace("_", " ").title())
    driver_comment = f"🔧 DOMINANT DRIVER: '{driver_label}' has highest predictive weight. Monitor weekly."

    return dict(
        regime_alert=regime_alert, regime_color=regime_color,
        momentum=momentum, outlook=outlook, driver_comment=driver_comment,
        last_price=last_price, regime_prob=regime_now, price_trend=price_trend,
    )


def al_calc_ipp(
    lme_3m_usd, regional_premium, freight_usd,
    duty_pct, gst_vat_pct, other_charges, usd_inr,
) -> dict:
    cif          = lme_3m_usd + regional_premium + freight_usd
    duty         = cif * (duty_pct / 100)
    landed_usd   = cif + duty + other_charges
    gst_amt      = landed_usd * (gst_vat_pct / 100)
    total_usd    = landed_usd + gst_amt
    total_inr_mt = total_usd * usd_inr
    total_inr_kg = total_inr_mt / 1000
    return dict(
        lme_3m=lme_3m_usd, regional_premium=regional_premium, freight=freight_usd,
        cif=cif, duty=duty, other_charges=other_charges,
        landed_usd=landed_usd, gst_amt=gst_amt,
        total_usd=total_usd, total_inr_mt=total_inr_mt, total_inr_kg=total_inr_kg,
    )


def render_aluminium():
    """Render the full Aluminium dashboard."""

    # ── Data load ─────────────────────────────────────────────────────────────
    try:
        hist, future, fi, meta = al_load_data(horizon_weeks)
    except FileNotFoundError:
        st.error(
            "⛔ Pipeline outputs for **Primary Aluminium** not found.  \n"
            "Run the pipeline first:  \n"
            "```bash\npython pipeline_aluminium.py\n```"
        )
        st.stop()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(
        f"<h1 style='color:{AL_C_IDX}; margin-bottom:4px;'>🔩 Primary Aluminium Ingot Intelligence Platform</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='color:#666; margin-top:0; font-size:14px;'>"
        "Procurement Intelligence · Regime Analysis · LME-Premium Spread Calculator</p>",
        unsafe_allow_html=True,
    )

    insights = al_generate_executive_insights(hist, future, meta, fi)

    if insights["regime_color"] == "error":
        st.error(insights["regime_alert"])
    elif insights["regime_color"] == "warning":
        st.warning(insights["regime_alert"])
    else:
        st.success(insights["regime_alert"])

    # KPI row
    last_real = float(hist["real_price"].iloc[-1])
    last_idx  = float(hist["actual"].iloc[-1])
    nxt_real  = float(future["real_price"].iloc[0])
    end_real  = float(future["real_price"].iloc[-1])
    pct_1wk   = (nxt_real - last_real) / (last_real + 1e-9) * 100
    pct_end   = (end_real - last_real) / (last_real + 1e-9) * 100
    mape_hist = float(np.mean(np.abs(
        (hist["actual"] - hist["hybrid_prediction"]) / (hist["actual"] + 1e-9)
    )) * 100)

    lme_last = None
    if "lme_3m_benchmark" in hist.columns:
        s = hist["lme_3m_benchmark"].dropna()
        if not s.empty:
            lme_last = float(s.iloc[-1])

    smm_last = None
    if "smm_a00_price" in hist.columns:
        s = hist["smm_a00_price"].dropna()
        if not s.empty:
            smm_last = float(s.iloc[-1])

    k1, k2, k3, k4, k5, k6 = st.columns([1, 1.2, 1.5, 1.8, 1, 1])
    k1.metric("📍 Last Index",         f"{last_idx:.1f}")
    k2.metric("💰 Current Price",      f"₹{last_real:.1f}/Kg")
    k3.metric("📅 Next-Week Forecast", f"₹{nxt_real:.1f}/Kg",
              delta=f"{pct_1wk:+.1f}%", delta_color="inverse")
    k4.metric("🎯 Horizon-End Price",  f"₹{end_real:.1f}/Kg",
              delta=f"{pct_end:+.1f}% ({len(future)} wks)", delta_color="off")
    k5.metric("📊 In-Sample MAPE",     f"{mape_hist:.1f}%")
    k6.metric("⚖️ Scale Factor",       f"{meta.get('scaling_factor', 0):.4f}")

    st.divider()

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        "📈 Price Forecast",
        "🔀 Regime & Drivers",
        "⚙️ LME vs Premium Spreads",
    ])

    # ── TAB 1: PRICE FORECAST ─────────────────────────────────────────────────
    with tab1:
        h = hist[hist.index >= hist.index[-1] - pd.DateOffset(weeks=display_window)].copy()

        use_real  = price_mode.startswith("₹")
        hist_vals = h["real_price"]  if use_real else h["actual"]
        fut_col   = "real_price"     if use_real else "predicted_index"
        y_label   = "Price (₹/Kg)"  if use_real else "Price Index"
        hover_fmt = "₹%{y:.2f}/Kg"  if use_real else "Index: %{y:.3f}"

        N = len(h)
        M = len(future)
        full_x = list(h.index) + list(future.index)

        fig1 = go.Figure()

        if show_regime and "regime_probability" in h.columns:
            for s in al_regime_shapes(h.index, h["regime_probability"].values):
                fig1.add_shape(**s)

        fig1.add_trace(go.Scatter(
            x=full_x, y=list(hist_vals) + [None] * M,
            name="Primary Al Index", line=dict(color=AL_C_IDX, width=2.8),
            hovertemplate=f"<b>%{{x|%d %b %Y}}</b><br>Al Index: {hover_fmt}<extra></extra>",
        ))

        if show_market and "market_price" in h.columns:
            mkt_vals = h["market_price"]
            if mkt_vals.notna().any():
                fig1.add_trace(go.Scatter(
                    x=full_x, y=list(mkt_vals) + [None] * M,
                    name="Market Price (Actual)",
                    line=dict(color=AL_C_MARKET, width=2.2, dash="dot"),
                    hovertemplate=f"<b>%{{x|%d %b %Y}}</b><br>Market: {hover_fmt}<extra></extra>",
                ))

        if "lme_3m_benchmark" in h.columns:
            lme_s = h["lme_3m_benchmark"].dropna()
            if lme_s.notna().any() and use_real:
                usd_inr_approx = 83.5
                lme_inr = lme_s * usd_inr_approx / 1000
                fig1.add_trace(go.Scatter(
                    x=lme_s.index, y=lme_inr,
                    name="LME 3M (₹/Kg approx.)",
                    line=dict(color=AL_C_LME, width=1.8, dash="dot"),
                    opacity=0.70,
                    hovertemplate="<b>%{x|%d %b %Y}</b><br>LME 3M: ₹%{y:.2f}/Kg<extra></extra>",
                ))

        conn_val = float(hist_vals.iloc[-1])
        fp       = future[fut_col]

        # Always compute CI values so they can be shown in the forecast hover tooltip
        idx_arr    = np.arange(1, M + 1)
        base_sigma = float(np.std(fp.values)) if len(fp) > 1 and np.std(fp.values) > 0 else conn_val * 0.03
        sigma      = base_sigma * 0.015 * idx_arr
        ci_up      = list(np.array(fp.values) + 1.96 * sigma)
        ci_dn      = list(np.array(fp.values) - 1.96 * sigma)

        if show_ci and len(fp) > 1:
            ci_x = [h.index[-1]] + list(future.index)
            fig1.add_trace(go.Scatter(
                x=ci_x + ci_x[::-1],
                y=[conn_val] + ci_up + ([conn_val] + ci_dn)[::-1],
                fill="toself", fillcolor=AL_C_CI, line=dict(width=0),
                name="95% CI Band", showlegend=True, hoverinfo="skip",
            ))

        # customdata: [ci_up, ci_dn] aligned to full_x; None for historical points
        ci_up_full = [None] * (N - 1) + [conn_val] + ci_up
        ci_dn_full = [None] * (N - 1) + [conn_val] + ci_dn
        al_forecast_customdata = np.stack([ci_up_full, ci_dn_full], axis=-1)

        price_unit = "₹" if use_real else ""
        price_sfx  = "/Kg" if use_real else ""
        ci_fmt     = f"{price_unit}%{{customdata[0]:.2f}}{price_sfx}" if use_real else "%{customdata[0]:.3f}"
        ci_fmt_dn  = f"{price_unit}%{{customdata[1]:.2f}}{price_sfx}" if use_real else "%{customdata[1]:.3f}"

        fut_y = [None] * (N - 1) + [conn_val] + list(fp.values)
        fig1.add_trace(go.Scatter(
            x=full_x, y=fut_y, name="Future Forecast",
            line=dict(color=AL_C_FUTURE, width=2.8, dash="dash"),
            customdata=al_forecast_customdata,
            hovertemplate=(
                f"<b>%{{x|%d %b %Y}}</b><br>"
                f"Forecast: {hover_fmt}<br>"
                f"95% CI Max: {ci_fmt}<br>"
                f"95% CI Min: {ci_fmt_dn}"
                "<extra></extra>"
            ),
        ))

        x_forecast_start = h.index[-1]
        fig1.add_vline(x=x_forecast_start, line_width=1.5, line_dash="dot", line_color="#999")
        fig1.add_annotation(
            x=x_forecast_start, y=1, yref="paper",
            text="Forecast →", showarrow=False,
            xanchor="left", yanchor="top", font=dict(size=11), xshift=5,
        )

        fig1.update_layout(**al_layout(
            f"Primary Aluminium Ingot — Price Trajectory & {horizon_label} Forecast",
            y_label, 500,
        ))
        st.plotly_chart(fig1, use_container_width=True)

        col_ins1, col_ins2 = st.columns(2)
        col_ins1.info(f"**4-Week Outlook:** {insights['momentum']}")
        col_ins2.info(f"**Horizon Outlook:** {insights['outlook']}")
        st.caption(insights["driver_comment"])

        with st.expander("📊 Show Dual-Axis: Index vs Real Price", expanded=False):
            fig_dual = make_subplots(specs=[[{"secondary_y": True}]])
            fig_dual.add_trace(
                go.Scatter(x=h.index, y=h["actual"],
                           name="Index Value", line=dict(color=AL_C_IDX, width=2.5)),
                secondary_y=False,
            )
            fig_dual.add_trace(
                go.Scatter(x=h.index, y=h["real_price"],
                           name="Real Price (₹/Kg)",
                           line=dict(color=AL_C_MARKET, width=2, dash="dash")),
                secondary_y=True,
            )
            if "market_price" in h.columns and h["market_price"].notna().any():
                fig_dual.add_trace(
                    go.Scatter(x=h.index, y=h["market_price"],
                               name="Market Price (₹/Kg)",
                               line=dict(color=AL_C_SMM, width=1.8, dash="dot")),
                    secondary_y=True,
                )
            fig_dual.update_yaxes(title_text="Price Index",  secondary_y=False,
                                   showgrid=True, gridcolor=AL_C_GRID)
            fig_dual.update_yaxes(title_text="₹/Kg", secondary_y=True, showgrid=False)
            fig_dual.update_xaxes(showgrid=True, gridcolor=AL_C_GRID)
            fig_dual.update_layout(
                title="Primary Aluminium: Index vs Real Price (Dual Axis)",
                template="plotly_white", height=380,
                legend=dict(orientation="h", y=1.06),
                hovermode="x unified",
            )
            st.plotly_chart(fig_dual, use_container_width=True)

    # ── TAB 2: REGIME & DRIVERS ───────────────────────────────────────────────
    with tab2:
        st.markdown("### 🌍 Macro Driver Analysis & Market Regime")

        h_drv = hist[hist.index >= hist.index[-1] - pd.DateOffset(weeks=display_window)].copy()

        if "regime_probability" in h_drv.columns:
            fig_reg = go.Figure()
            reg_vals = h_drv["regime_probability"].values
            fig_reg.add_trace(go.Scatter(
                x=h_drv.index, y=reg_vals,
                name="P(High Volatility Regime)",
                fill="tozeroy",
                fillcolor="rgba(211, 47, 47, 0.15)",
                line=dict(color="#D32F2F", width=2),
                hovertemplate="<b>%{x|%d %b %Y}</b><br>Regime Prob: %{y:.2%}<extra></extra>",
            ))
            fig_reg.add_hline(y=0.65, line_dash="dot", line_color="#D32F2F")
            fig_reg.add_annotation(
                x=1, xref="paper", y=0.65,
                text="High Stress (0.65)", showarrow=False,
                xanchor="right", yanchor="bottom", yshift=2,
            )
            fig_reg.add_hline(y=0.45, line_dash="dot", line_color="#FF9800")
            fig_reg.add_annotation(
                x=1, xref="paper", y=0.45,
                text="Elevated Risk (0.45)", showarrow=False,
                xanchor="right", yanchor="bottom", yshift=2,
            )
            fig_reg.update_layout(**al_layout(
                "Primary Aluminium: Market Stress Regime Probability", "Probability", 280))
            st.plotly_chart(fig_reg, use_container_width=True)

        st.divider()

        avail_drv = [d for d in AL_DISPLAY_DRIVERS if d in h_drv.columns]

        if avail_drv:
            st.markdown("#### 📈 Relative Driver Movement (Indexed to 100)")
            st.caption(
                "All drivers normalised to 100 at start of history window for relative comparison. "
                "Alumina, LME and SMM A00 are primary signal drivers for aluminium."
            )
            fig_drv = go.Figure()
            for i, d_col in enumerate(avail_drv):
                s = h_drv[d_col].dropna()
                if s.empty or abs(s.iloc[0]) < 1e-9:
                    continue
                norm = (s / s.iloc[0]) * 100
                fig_drv.add_trace(go.Scatter(
                    x=s.index, y=norm,
                    name=AL_DRIVER_LABELS.get(d_col, d_col.replace("_", " ").title()),
                    line=dict(color=AL_DRIVER_PALETTE[i % len(AL_DRIVER_PALETTE)], width=1.8),
                    hovertemplate=(
                        f"<b>%{{x|%d %b %Y}}</b><br>"
                        f"{AL_DRIVER_LABELS.get(d_col, d_col)}: %{{y:.1f}}<extra></extra>"
                    ),
                ))
            fig_drv.update_layout(**al_layout(
                "Relative Driver Movement (Indexed = 100 at start)", "Relative Index", 450))
            st.plotly_chart(fig_drv, use_container_width=True)

        st.divider()

        fc1, fc2 = st.columns([3, 2])

        fig_bar = go.Figure(go.Bar(
            x=fi["importance"].iloc[:15][::-1],
            y=fi["feature"].iloc[:15][::-1],
            orientation="h",
            marker=dict(
                color=fi["importance"].iloc[:15][::-1],
                colorscale="Blues", showscale=False, opacity=0.88,
            ),
            hovertemplate="%{y}: %{x:.1f}<extra></extra>",
        ))
        fig_bar.update_layout(**al_layout(
            "Top 15 LightGBM Feature Importances — Primary Aluminium", "Importance Score", 430))
        fig_bar.update_yaxes(tickfont=dict(size=10))
        fc1.plotly_chart(fig_bar, use_container_width=True)

        top7     = fi.head(7).copy()
        rest_imp = fi.iloc[7:]["importance"].sum()
        if rest_imp > 0:
            top7 = pd.concat([
                top7,
                pd.DataFrame([{"feature": "Other Variables", "importance": rest_imp}]),
            ], ignore_index=True)
        fig_pie = go.Figure(go.Pie(
            labels=[AL_DRIVER_LABELS.get(f, f.replace("_", " ").title()) for f in top7["feature"]],
            values=(top7["importance"] / top7["importance"].sum() * 100),
            hole=0.48,
            marker=dict(colors=AL_DRIVER_PALETTE[:len(top7)]),
            textinfo="label+percent", textfont=dict(size=9),
        ))
        fig_pie.update_layout(
            title=dict(text="Primary Al: Driver Dependence %", font=dict(size=14), x=0.5),
            template="plotly_white", height=430, showlegend=False,
        )
        fc2.plotly_chart(fig_pie, use_container_width=True)

        st.divider()

        with st.expander("⚡ View Historical Shock Event Periods (Aluminium)", expanded=False):
            shock_df = pd.DataFrame([
                {"Event": k.replace("_", " ").title(), "Start": v[0], "End": v[1]}
                for k, v in AL_SHOCK_EVENTS.items()
            ])
            st.dataframe(shock_df, use_container_width=True, hide_index=True)

            fig_shk = go.Figure()
            fig_shk.add_trace(go.Scatter(
                x=h_drv.index, y=h_drv["actual"],
                name="Primary Al Index", line=dict(color=AL_C_IDX, width=2),
            ))
            for k, (s_d, e_d) in AL_SHOCK_EVENTS.items():
                fig_shk.add_vrect(
                    x0=s_d, x1=e_d,
                    fillcolor="rgba(100,100,200,0.08)",
                    layer="below", line_width=0,
                )
                fig_shk.add_annotation(
                    x=s_d, y=1, yref="paper",
                    text=k.replace("_", " ").title()[:20], showarrow=False,
                    xanchor="left", yanchor="top", font=dict(size=8), xshift=2,
                )
            fig_shk.update_layout(**al_layout(
                "Primary Aluminium: Shock Event Periods vs Index", "Index Value", 400))
            st.plotly_chart(fig_shk, use_container_width=True)

            st.markdown("**Key Aluminium Shock Notes:**")
            st.markdown(
                "- **Rusal Sanctions (2018)**: UC Rusal sanctions caused immediate +30% LME spike "
                "before partial reversal. Remains most significant single-event shock in recent history.\n"
                "- **European Energy Crisis (2022)**: Smelter curtailments across NWE due to >€300/MWh power; "
                "capacity shutdowns in Germany, Netherlands, Norway reduced European Al output by ~1.2 MT.\n"
                "- **China Power Curbs (2021)**: Yunnan/Xinjiang hydropower restrictions forced ~2 MT annualised "
                "capacity curtailment; sent LME to 13-year highs at $3,229/MT.\n"
                "- **China Tax Rebate Cancellation (Dec 2024)**: Removal of 13% VAT export rebate on semis "
                "effectively raised Chinese export prices; ongoing structural shift in China's role as net exporter."
            )

    # ── TAB 3: LME VS PREMIUM SPREADS / IPP CALCULATOR ───────────────────────
    with tab3:
        st.markdown("### ⚙️ LME 3M vs Physical Delivery Premium Spread & Import Parity Calculator")
        st.caption(
            "Calculates the all-in Import Parity Price (IPP) by region: LME 3M cash price + "
            "regional delivery premium + freight + duties + GST/VAT. Compares landed cost vs "
            "Indian domestic benchmark."
        )

        # ── 1. Reference Prices ───────────────────────────────────────────────
        st.markdown("#### 1. Reference Prices")
        rp1, rp2, rp3, rp4 = st.columns(4)

        if lme_last is not None and lme_last > 100:
            lme_default = int(lme_last)
        else:
            lme_default = 2450

        lme_3m_inp  = rp1.number_input("LME 3M Price (USD/MT)",       value=lme_default, step=10)
        smm_inp     = rp2.number_input("SMM A00 Domestic (CNY/MT)",    value=19800, step=100)
        usd_inr_inp = rp3.number_input("USD/INR Rate",                 value=83.5, step=0.1, format="%.1f")
        usd_cny_inp = rp4.number_input("USD/CNY Rate",                 value=7.25, step=0.01, format="%.2f")

        lme_inr_kg         = lme_3m_inp * usd_inr_inp / 1000
        smm_usd_mt         = smm_inp / usd_cny_inp
        smm_inr_kg         = smm_usd_mt * usd_inr_inp / 1000
        lme_smm_spread_usd = lme_3m_inp - smm_usd_mt

        sp1, sp2, sp3, sp4 = st.columns(4)
        sp1.metric("LME 3M (₹/Kg equiv.)",   f"₹{lme_inr_kg:.2f}")
        sp2.metric("SMM A00 (USD/MT equiv.)", f"${smm_usd_mt:,.0f}")
        sp3.metric("SMM A00 (₹/Kg equiv.)",  f"₹{smm_inr_kg:.2f}")
        sp4.metric("LME–SMM Spread (USD/MT)", f"${lme_smm_spread_usd:+.0f}",
                   delta_color="normal" if lme_smm_spread_usd > 0 else "inverse",
                   help="Positive = LME trading at premium to China domestic. "
                        "Negative = China price premium → export pressure.")

        if lme_smm_spread_usd > 100:
            st.info("ℹ️ **LME Premium vs China**: Elevated LME-SMM spread may incentivise China exports, "
                    "placing downward pressure on international premiums.")
        elif lme_smm_spread_usd < -100:
            st.warning("⚠️ **SMM Premium vs LME**: China domestic price above LME. "
                       "Import arb window may be open for Chinese buyers; reduced export pressure.")
        else:
            st.success("✅ **LME-SMM Spread**: Within normal ±$100/MT range. No strong arb signal.")

        st.divider()

        # ── 2. Regional IPP Calculator ────────────────────────────────────────
        st.markdown("#### 2. Regional Import Parity Price (IPP) Calculator")

        region_sel = st.selectbox("Select Delivery Region", list(PREMIUM_DEFAULTS.keys()), index=3)
        pdef       = PREMIUM_DEFAULTS[region_sel]
        ddef       = DUTY_DEFAULTS[region_sel]

        rc1, rc2, rc3 = st.columns(3)
        with rc1:
            st.markdown("**Delivery Premium & Freight**")
            reg_premium = st.slider(
                f"Regional Delivery Premium (USD/MT) — {region_sel}",
                min_value=int(pdef["min"]), max_value=int(pdef["max"]),
                value=int(pdef["default"]), step=5,
            )
            freight_usd = st.number_input(
                "Sea Freight (USD/MT)",
                value=35 if "India" in region_sel else 20, step=5,
            )
        with rc2:
            st.markdown("**Duties & Taxes**")
            duty_pct    = st.number_input("Import Duty (%)",        value=ddef["duty_pct"],    step=0.5, format="%.1f")
            gst_vat_pct = st.number_input("GST / VAT (%)",          value=ddef["gst_vat_pct"], step=0.5, format="%.1f")
            other_chg   = st.number_input("Port + Handling (USD/MT)", value=ddef["other_usd"], step=2)
        with rc3:
            st.markdown("**Indian Domestic Benchmark**")
            indian_dom_price = st.number_input(
                "Indian Domestic Al Price (₹/Kg)",
                value=float(last_real), step=1.0, format="%.2f",
                help="Current spot price from Indian market or pipeline model",
            )

        ipp = al_calc_ipp(
            lme_3m_usd=lme_3m_inp,
            regional_premium=reg_premium,
            freight_usd=freight_usd,
            duty_pct=duty_pct,
            gst_vat_pct=gst_vat_pct,
            other_charges=other_chg,
            usd_inr=usd_inr_inp,
        )

        spread_vs_domestic = ipp["total_inr_kg"] - indian_dom_price
        if spread_vs_domestic > 5:
            arb_signal = f"🔴 IMPORT UNECONOMIC: IPP is ₹{spread_vs_domestic:.2f}/Kg ABOVE domestic. Domestic sourcing preferred."
            arb_color  = "error"
        elif spread_vs_domestic < -5:
            arb_signal = f"🟢 IMPORT ARBITRAGE OPEN: IPP is ₹{abs(spread_vs_domestic):.2f}/Kg BELOW domestic. Import window open."
            arb_color  = "success"
        else:
            arb_signal = f"🟡 AT PARITY: IPP within ±₹5/Kg of domestic price. No strong arb signal."
            arb_color  = "warning"

        if arb_color == "error":
            st.error(arb_signal)
        elif arb_color == "success":
            st.success(arb_signal)
        else:
            st.warning(arb_signal)

        im1, im2, im3, im4, im5 = st.columns(5)
        im1.metric("LME 3M Base",        f"${ipp['lme_3m']:,.0f}/MT")
        im2.metric("+ Regional Premium", f"${ipp['regional_premium']:,.0f}/MT")
        im3.metric("+ Freight",          f"${ipp['freight']:,.0f}/MT")
        im4.metric("Total IPP (₹/Kg)",   f"₹{ipp['total_inr_kg']:.2f}",
                   delta=f"vs ₹{indian_dom_price:.2f} domestic",
                   delta_color="inverse" if spread_vs_domestic > 0 else "normal")
        im5.metric("IPP (USD/MT)",        f"${ipp['total_usd']:,.0f}")

        st.divider()

        # ── 3. Waterfall chart — IPP build-up ─────────────────────────────────
        st.markdown("#### 3. IPP Cost Waterfall — Build-up (USD/MT)")

        wf_labels  = ["LME 3M", "Regional Premium", "Freight", "Duty", "Port/Handling", "GST/VAT", "Total IPP (USD/MT)"]
        wf_values  = [
            ipp["lme_3m"], ipp["regional_premium"], ipp["freight"],
            ipp["duty"], ipp["other_charges"], ipp["gst_amt"], ipp["total_usd"],
        ]
        wf_measure = ["absolute", "relative", "relative", "relative", "relative", "relative", "total"]
        wf_text    = [f"${v:,.0f}" for v in wf_values]

        fig_wf = go.Figure(go.Waterfall(
            name="IPP Build-up", orientation="v",
            measure=wf_measure, x=wf_labels, y=wf_values,
            text=wf_text, textposition="outside",
            connector=dict(line=dict(color="rgb(63,63,63)")),
            increasing=dict(marker=dict(color=AL_C_SMM)),
            decreasing=dict(marker=dict(color=AL_C_IDX)),
            totals=dict(marker=dict(color=AL_C_METAL)),
        ))
        fig_wf.update_layout(
            title=f"IPP Cost Waterfall — {region_sel} Delivery (USD/MT)",
            template="plotly_white", height=420,
            yaxis_title="USD/MT", showlegend=False,
            margin=dict(l=60, r=20, t=55, b=45),
        )
        st.plotly_chart(fig_wf, use_container_width=True)

        st.divider()

        # ── 4. Multi-region premium comparison ────────────────────────────────
        st.markdown("#### 4. Cross-Region Premium Spread Comparison")
        st.caption("Calculates all-in IPP for every region simultaneously using default duty structures.")

        region_rows = []
        for reg, pdef_r in PREMIUM_DEFAULTS.items():
            ddef_r = DUTY_DEFAULTS[reg]
            ipp_r  = al_calc_ipp(
                lme_3m_usd=lme_3m_inp,
                regional_premium=pdef_r["default"],
                freight_usd=35 if "India" in reg else 20,
                duty_pct=ddef_r["duty_pct"],
                gst_vat_pct=ddef_r["gst_vat_pct"],
                other_charges=ddef_r["other_usd"],
                usd_inr=usd_inr_inp,
            )
            region_rows.append({
                "Region":             reg,
                "Prem. (USD/MT)":     pdef_r["default"],
                "Duty (%)":           ddef_r["duty_pct"],
                "IPP (USD/MT)":       round(ipp_r["total_usd"], 0),
                "IPP (₹/Kg)":         round(ipp_r["total_inr_kg"], 2),
                "vs India Dom. (₹)":  round(ipp_r["total_inr_kg"] - indian_dom_price, 2),
            })

        reg_df = pd.DataFrame(region_rows)

        fig_reg_bar = go.Figure(go.Bar(
            x=reg_df["IPP (USD/MT)"],
            y=reg_df["Region"],
            orientation="h",
            marker=dict(
                color=[AL_C_SMM if v > ipp["total_usd"] else AL_C_IDX for v in reg_df["IPP (USD/MT)"]],
                opacity=0.85,
            ),
            text=[f"${v:,.0f}" for v in reg_df["IPP (USD/MT)"]],
            textposition="outside",
            hovertemplate="%{y}: $%{x:,.0f}/MT<extra></extra>",
        ))
        fig_reg_bar.add_vline(x=lme_3m_inp, line_dash="dot", line_color="#999")
        fig_reg_bar.add_annotation(
            x=lme_3m_inp, y=1, yref="paper",
            text="LME 3M Base", showarrow=False,
            xanchor="left", yanchor="top", font=dict(size=11), xshift=5,
        )
        fig_reg_bar.update_layout(**al_layout(
            "All-in IPP Comparison by Delivery Region (USD/MT)", "USD/MT", 360))
        st.plotly_chart(fig_reg_bar, use_container_width=True)

        st.dataframe(
            reg_df.style.format({
                "Prem. (USD/MT)":    "${:.0f}",
                "Duty (%)":          "{:.1f}%",
                "IPP (USD/MT)":      "${:,.0f}",
                "IPP (₹/Kg)":        "₹{:.2f}",
                "vs India Dom. (₹)": "₹{:+.2f}",
            }).map(
                lambda v: "color: red;" if isinstance(v, (int, float)) and v > 0
                          else ("color: green;" if isinstance(v, (int, float)) and v < 0 else ""),
                subset=["vs India Dom. (₹)"],
            ),
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        # ── 5. Historical spread: LME vs SMM ──────────────────────────────────
        st.markdown("#### 5. Historical LME 3M vs SMM A00 Spread (Aluminium Benchmark Divergence)")
        st.caption(
            "The LME–SMM spread is a key structural indicator for global aluminium trade flows. "
            "When LME > SMM in USD terms, Chinese aluminium becomes relatively cheap on an export basis."
        )

        h_drv = hist[hist.index >= hist.index[-1] - pd.DateOffset(weeks=display_window)].copy()

        if "lme_3m_benchmark" in h_drv.columns and "smm_a00_price" in h_drv.columns:
            lme_s_hist = h_drv["lme_3m_benchmark"].dropna()
            smm_s_hist = h_drv["smm_a00_price"].dropna()
            common_idx = lme_s_hist.index.intersection(smm_s_hist.index)

            if len(common_idx) > 10:
                lme_hist_usd = lme_s_hist.loc[common_idx]
                smm_hist_usd = smm_s_hist.loc[common_idx] / usd_cny_inp
                spread_hist  = lme_hist_usd - smm_hist_usd

                fig_spread = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                            row_heights=[0.65, 0.35], vertical_spacing=0.05)
                fig_spread.add_trace(go.Scatter(
                    x=lme_hist_usd.index, y=lme_hist_usd,
                    name="LME 3M (USD/MT)", line=dict(color=AL_C_LME, width=2.2),
                    hovertemplate="<b>%{x|%d %b %Y}</b><br>LME 3M: $%{y:,.0f}<extra></extra>",
                ), row=1, col=1)
                fig_spread.add_trace(go.Scatter(
                    x=smm_hist_usd.index, y=smm_hist_usd,
                    name="SMM A00 (USD/MT)", line=dict(color=AL_C_SMM, width=2.2),
                    hovertemplate="<b>%{x|%d %b %Y}</b><br>SMM A00: $%{y:,.0f}<extra></extra>",
                ), row=1, col=1)
                colors_spread = [AL_C_IPP_POS if v >= 0 else AL_C_IPP_NEG for v in spread_hist.values]
                fig_spread.add_trace(go.Bar(
                    x=spread_hist.index, y=spread_hist.values,
                    name="LME – SMM Spread",
                    marker=dict(color=colors_spread, opacity=0.75),
                    hovertemplate="<b>%{x|%d %b %Y}</b><br>Spread: $%{y:+.0f}/MT<extra></extra>",
                ), row=2, col=1)
                fig_spread.add_hline(y=0, line_color="#333", line_width=1, row=2, col=1)
                fig_spread.update_layout(
                    title="LME 3M vs SMM A00: Historical Benchmark Spread",
                    template="plotly_white", height=500,
                    hovermode="x unified",
                    legend=dict(orientation="h", y=1.04),
                    margin=dict(l=60, r=20, t=55, b=45),
                )
                fig_spread.update_yaxes(title_text="USD/MT", row=1, col=1,
                                         showgrid=True, gridcolor=AL_C_GRID)
                fig_spread.update_yaxes(title_text="Spread (USD/MT)", row=2, col=1,
                                         showgrid=True, gridcolor=AL_C_GRID)
                st.plotly_chart(fig_spread, use_container_width=True)
            else:
                st.info("📂 LME 3M and/or SMM A00 data series too short for spread chart. "
                        "Ensure `industrial_drivers_Al.xlsx` contains these sheets.")
        else:
            st.info("📂 LME 3M benchmark and/or SMM A00 columns not present in pipeline outputs. "
                    "Run pipeline with full `industrial_drivers_Al.xlsx` to enable this chart.")

        # ── 6. Forward IPP projections using model forecast ───────────────────
        st.divider()
        st.markdown("#### 6. Forward IPP Projection — Model-Based")
        st.caption(
            "Projects the Import Parity Price over the forecast horizon using the pipeline's "
            "future real price forecast. Assumes flat FX and static delivery premium."
        )

        fut_inr_kg        = future["real_price"]
        fut_ipp_usd       = fut_inr_kg * 1000 / usd_inr_inp
        fut_ipp_total     = fut_ipp_usd + reg_premium + (35 if "India" in region_sel else 20)
        fut_ipp_duty      = fut_ipp_total * (duty_pct / 100)
        fut_ipp_final_usd = fut_ipp_total + fut_ipp_duty + other_chg
        fut_ipp_inr_kg    = fut_ipp_final_usd * usd_inr_inp / 1000

        fig_fut_ipp = go.Figure()
        fig_fut_ipp.add_trace(go.Scatter(
            x=future.index, y=fut_inr_kg,
            name="Model Forecast Price (₹/Kg)",
            line=dict(color=AL_C_FUTURE, width=2.5),
            hovertemplate="<b>%{x|%d %b %Y}</b><br>Model: ₹%{y:.2f}/Kg<extra></extra>",
        ))
        fig_fut_ipp.add_trace(go.Scatter(
            x=future.index, y=fut_ipp_inr_kg,
            name=f"Forward IPP — {region_sel} (₹/Kg)",
            line=dict(color=AL_C_SMM, width=2.5, dash="dash"),
            hovertemplate="<b>%{x|%d %b %Y}</b><br>IPP: ₹%{y:.2f}/Kg<extra></extra>",
        ))
        fig_fut_ipp.add_trace(go.Scatter(
            x=list(future.index) + list(future.index[::-1]),
            y=list(fut_inr_kg) + list(fut_ipp_inr_kg[::-1]),
            fill="toself", fillcolor="rgba(100,100,200,0.06)",
            line=dict(width=0), name="Model vs IPP Band", hoverinfo="skip",
        ))
        fig_fut_ipp.add_hline(y=indian_dom_price, line_dash="dot", line_color=AL_C_SILVER)
        fig_fut_ipp.add_annotation(
            x=1, xref="paper", y=indian_dom_price,
            text=f"Indian Dom. ₹{indian_dom_price:.2f}", showarrow=False,
            xanchor="right", yanchor="bottom", yshift=2,
        )
        fig_fut_ipp.update_layout(**al_layout(
            f"Forward Price vs IPP ({region_sel}) — {horizon_label}", "Price (₹/Kg)", 430,
        ))
        st.plotly_chart(fig_fut_ipp, use_container_width=True)

        pct_ipp_above = (fut_ipp_inr_kg > fut_inr_kg).mean() * 100
        if pct_ipp_above > 70:
            st.info(f"📊 **Import Economics**: IPP above model price in **{pct_ipp_above:.0f}%** of forecast. "
                    f"Domestic sourcing favoured for {region_sel} buyers.")
        elif pct_ipp_above < 30:
            st.success(f"📊 **Import Arbitrage**: Model price above IPP in **{100 - pct_ipp_above:.0f}%** of forecast. "
                       f"Import window likely to remain open over horizon.")
        else:
            st.warning(f"📊 **Mixed Signals**: IPP and model price cross in forecast. "
                       "Monitor LME–premium dynamics closely.")


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ROUTER — Dispatch to the correct dashboard
# ══════════════════════════════════════════════════════════════════════════════

if is_manganese():
    render_manganese()
elif is_silicon():
    render_silicon()
elif is_aluminium():
    render_aluminium()

# ══════════════════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════════════════
st.divider()
if is_manganese():
    footer_text = (
        "Manganese Forecasting Engine | "
        "Products: Mn Briquette (97%) · LC FeMn (80%) · MC FeMn (70%) | "
        "Model: LightGBM Hybrid Engine"
    )
elif is_silicon():
    footer_text = (
        "Silicon Procurement Intelligence & Process Economics Platform | "
        "Anchors: Si Metal ₹187.50/Kg · FeSi ₹107.75/Kg (08-Jan-2024) | "
        "Model: LightGBM Hybrid Engine | Indian Market Data Integrated"
    )
else:
    footer_text = (
        "Primary Aluminium Ingot Intelligence Platform | "
        "Model: LightGBM Hybrid Engine · 2026 Industrial Framework | "
        "Drivers: Alumina, Electricity, LME, SMM A00, Bauxite, CPC, TTF Gas"
    )

st.markdown(
    f"<div style='text-align:center; color:#999; font-size:11px;'>{footer_text}</div>",
    unsafe_allow_html=True,
)
