"""Streamlit dashboard: Paytm turnaround, peer comps, DCF, data checks.

Run:  streamlit run app.py
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src import refresh, valuation

st.set_page_config(page_title="Equity Valuation Engine", page_icon="📈", layout="wide")

# ---- palette (dark-mode steps; one fixed colour per company) --------------------
COLORS = {"Paytm": "#4f9cff", "Angel One": "#ff8a4c", "CAMS": "#2dd4a7", "PB Fintech": "#f08cb4"}
POS, NEG, MUTED, ACCENT = "#4f9cff", "#ff6b6b", "#64748b", "#5eead4"
INK, INK2, GRID = "#e6edf7", "#94a3b8", "rgba(148,163,184,0.12)"

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"], .stApp { font-family: 'Inter', sans-serif; }
.stApp { background: radial-gradient(1200px 500px at 10% -10%, #16224a 0%, transparent 60%),
                     radial-gradient(900px 400px at 100% 0%, #0f3b3a 0%, transparent 55%), #0a0f1e; }
header[data-testid="stHeader"], #MainMenu, footer { visibility: hidden; height: 0; }
.block-container { padding-top: 1.6rem; max-width: 1280px; }

.hero { padding: 28px 32px; border-radius: 22px; margin-bottom: 18px;
  background: linear-gradient(135deg, rgba(79,156,255,.18), rgba(94,234,212,.10) 60%, rgba(17,26,46,.6));
  border: 1px solid rgba(148,163,184,.18); box-shadow: 0 20px 60px rgba(0,0,0,.35); }
.eyebrow { letter-spacing: .18em; font-size: 11px; font-weight: 700; color: #5eead4; text-transform: uppercase; }
.hero h1 { font-size: 40px; line-height: 1.1; font-weight: 800; margin: 8px 0 6px;
  background: linear-gradient(90deg, #fff, #9fd0ff 55%, #5eead4); -webkit-background-clip: text;
  -webkit-text-fill-color: transparent; }
.hero p { color: #94a3b8; margin: 0; font-size: 15px; max-width: 760px; }
.chips { display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px; }
.chip { padding: 6px 12px; border-radius: 999px; font-size: 12px; font-weight: 600;
  background: rgba(148,163,184,.12); color: #cbd5e1; border: 1px solid rgba(148,163,184,.2); }
.chip.warn { background: rgba(255,107,107,.12); color: #ffb0b0; border-color: rgba(255,107,107,.35); }
.chip.good { background: rgba(45,212,167,.12); color: #7ff0cd; border-color: rgba(45,212,167,.35); }

.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 14px; margin: 6px 0 18px; }
.kpi { padding: 16px 18px; border-radius: 16px; background: rgba(17,26,46,.85);
  border: 1px solid rgba(148,163,184,.16); position: relative; overflow: hidden; }
.kpi:before { content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 3px; background: var(--c, #4f9cff); }
.kpi .l { font-size: 11px; letter-spacing: .1em; text-transform: uppercase; color: #94a3b8; font-weight: 600; }
.kpi .v { font-size: 26px; font-weight: 800; margin-top: 4px; color: #f1f5f9; }
.kpi .s { font-size: 12px; color: #94a3b8; margin-top: 2px; }

.stTabs [data-baseweb="tab-list"] { gap: 6px; background: rgba(17,26,46,.7); padding: 6px; border-radius: 14px;
  border: 1px solid rgba(148,163,184,.14); width: fit-content; }
.stTabs [data-baseweb="tab"] { height: 38px; border-radius: 10px; padding: 0 16px; color: #94a3b8; font-weight: 600; }
.stTabs [aria-selected="true"] { background: linear-gradient(90deg, rgba(79,156,255,.28), rgba(94,234,212,.2));
  color: #fff !important; }
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] { display: none; }

.section { font-size: 13px; letter-spacing: .12em; text-transform: uppercase; color: #94a3b8;
  font-weight: 700; margin: 22px 0 6px; }
.note { color: #94a3b8; font-size: 12.5px; }
[data-testid="stPlotlyChart"] { background: rgba(17,26,46,.55); border: 1px solid rgba(148,163,184,.12);
  border-radius: 16px; padding: 6px; }
[data-testid="stSidebar"] { background: #0c1326; border-right: 1px solid rgba(148,163,184,.12); }
div[data-testid="stAlert"] { border-radius: 14px; }
.stButton > button { border-radius: 12px; font-weight: 700; }
.stButton > button[kind="primary"] { color: #06231f; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner="Running pipeline...")
def load(signature, cfg_mtime):
    """Cached pipeline run; the cache key changes when any export or config changes."""
    return refresh.run_pipeline()


def style(fig, title=None, height=360, legend=False, **kw):
    fig.update_layout(
        height=height, margin=dict(l=14, r=14, t=54 if title else 20, b=14),
        title=dict(text=title, x=0.02, font=dict(size=14, color=INK)) if title else None,
        font=dict(family="Inter, sans-serif", color=INK2, size=12),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", showlegend=legend,
        hoverlabel=dict(bgcolor="#0a0f1e", font_color=INK, bordercolor="#334155"), **kw)
    fig.update_xaxes(showgrid=False, linecolor=GRID, tickfont=dict(color=INK2))
    fig.update_yaxes(gridcolor=GRID, zeroline=True, zerolinecolor="rgba(148,163,184,.35)",
                     tickfont=dict(color=INK2))
    return fig


def kpis(items):
    """items: (label, value, sub, accent colour)."""
    html = "".join(f'<div class="kpi" style="--c:{c}"><div class="l">{l}</div>'
                   f'<div class="v">{v}</div><div class="s">{s}</div></div>' for l, v, s, c in items)
    st.markdown(f'<div class="kpis">{html}</div>', unsafe_allow_html=True)


def section(text):
    st.markdown(f'<div class="section">{text}</div>', unsafe_allow_html=True)


def pct(v):
    return "n/a" if pd.isna(v) else f"{v:.1%}"


# ---- sidebar ------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### Data")
    st.caption("Drop a newer Screener export into `data/raw/` (same filename), then refresh.")
    if st.button("Refresh data", type="primary", width="stretch"):
        st.cache_data.clear()
        st.session_state.pop("dcf_init", None)
        st.rerun()
    st.divider()
    st.caption("FILES IN data/raw/")
    for name, mtime in refresh.raw_signature():
        st.caption(f"{name}  \n{pd.Timestamp(mtime, unit='s'):%d %b %Y %H:%M}")

R = load(refresh.raw_signature(), refresh.CONFIG_PATH.stat().st_mtime)
cfg, target = R["config"], R["config"]["target"]
ann, qtr, yr = R["annual"][target], R["quarterly"][target], R["yearly"][target]
fy0, fy1 = ann.index[0], ann.index[-1]
D0 = R["dcf"]
n_warn = int((R["checks"]["status"] != "PASS").sum())
flagged = [c for c, m in R["meta"].items() if m["standalone_suspect"]]

# ---- hero -----------------------------------------------------------------------------
gap = D0["upside"]
chips = (f'<span class="chip {"warn" if gap < 0 else "good"}">DCF Rs {D0["value_per_share"]:,.0f} vs market '
         f'Rs {D0["market_price"]:,.0f} ({gap:+.0%})</span>'
         f'<span class="chip">{len(R["annual"])} companies · FY{fy0}-FY{fy1}</span>'
         f'<span class="chip">Consolidated · Rs Cr</span>'
         f'<span class="chip warn">{n_warn} data checks need attention</span>')
st.markdown(f"""<div class="hero"><div class="eyebrow">Equity valuation &amp; analytics engine</div>
<h1>{target} vs fintech peers</h1>
<p>From a Rs {abs(yr['net_profit'].min()):,.0f} Cr loss year to first profits: what the numbers say about turnaround,
peer standing and what a forward DCF can justify.</p><div class="chips">{chips}</div></div>""",
            unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Turnaround", "Peer benchmarking", "DCF valuation", "Data checks"])

# ---- tab 1: turnaround ----------------------------------------------------------------
with tab1:
    burned = -yr["net_profit"][yr["net_profit"] < 0].sum()
    last8 = int((qtr["net_profit"].iloc[-8:] > 0).sum())
    kpis([(f"FY{fy1} revenue", f"Rs {yr['sales'].iloc[-1]:,.0f} Cr", f"{pct(yr['rev_growth'].iloc[-1])} YoY", POS),
          (f"FY{fy1} net profit", f"Rs {yr['net_profit'].iloc[-1]:,.0f} Cr", f"margin {pct(yr['net_margin'].iloc[-1])}", ACCENT),
          ("Cumulative losses", f"Rs {burned:,.0f} Cr", f"FY{fy0}-FY{fy1}, loss years only", NEG),
          ("Profitable quarters", f"{last8} of 8", f"latest quarter {qtr.index[-1]:%b-%y}", "#fbbf24")])
    c1, c2 = st.columns(2)
    fig = go.Figure(go.Bar(x=ann.index, y=ann["sales"], marker=dict(color=POS, cornerradius=6),
                           hovertemplate="FY%{x}: Rs %{y:,.0f} Cr<extra></extra>"))
    fig.update_xaxes(type="category")
    c1.plotly_chart(style(fig, "Revenue (Rs Cr)"), width="stretch")
    fig = go.Figure(go.Bar(x=ann.index, y=ann["net_profit"],
                           marker=dict(color=[POS if v >= 0 else NEG for v in ann["net_profit"]], cornerradius=6),
                           hovertemplate="FY%{x}: Rs %{y:,.0f} Cr<extra></extra>"))
    fig.update_xaxes(type="category")
    best = ann["net_profit"].idxmin()
    fig.add_annotation(x=best, y=ann["net_profit"].min(), text=f"Trough Rs {ann['net_profit'].min():,.0f} Cr",
                       showarrow=True, arrowcolor=NEG, font=dict(color="#ffb0b0", size=11), ay=-34)
    c2.plotly_chart(style(fig, "Net profit (Rs Cr): blue profit, red loss"), width="stretch")
    labels = [f"{t:%b-%y}" for t in qtr.index]
    fig = go.Figure(go.Bar(x=labels, y=qtr["net_profit"],
                           marker=dict(color=[POS if v >= 0 else NEG for v in qtr["net_profit"]], cornerradius=5),
                           hovertemplate="%{x}: Rs %{y:,.0f} Cr<extra></extra>"))
    st.plotly_chart(style(fig, "Quarterly net profit (Rs Cr)", height=320), width="stretch")
    # margin trajectory (own chart, own axis)
    fig = go.Figure(go.Scatter(x=yr.index, y=yr["net_margin"] * 100, mode="lines+markers",
                               line=dict(color=ACCENT, width=2.5), marker=dict(size=8, line=dict(color="#0a0f1e", width=2)),
                               fill="tozeroy", fillcolor="rgba(94,234,212,.08)",
                               hovertemplate="FY%{x}: %{y:.0f}%<extra></extra>"))
    fig.update_xaxes(type="category")
    fig.update_yaxes(range=[-200, 20], ticksuffix="%")
    st.plotly_chart(style(fig, "Net margin (%)  -  from -141% of revenue in FY2017 to +1.2% in FY2026", height=300),
                    width="stretch")

# ---- tab 2: peers -----------------------------------------------------------------------
with tab2:
    C = R["comps"]
    P = C[C["company"].isin(R["annual"])].copy()
    for c in flagged:
        st.warning(f"**{c}**: revenue looks standalone / holding-company ({'; '.join(R['meta'][c]['flags'])}). "
                   "Shown but excluded from the peer median.")
    med = C[C["company"] == "Peer median"].iloc[0]
    kpis([("Peer median rev CAGR 3y", pct(med["rev_cagr_3y"]), "comparable peers, ex-Paytm", POS),
          ("Peer median net margin", pct(med["net_margin"]), f"{target}: {pct(P.set_index('company').at[target, 'net_margin'])}", ACCENT),
          ("Peer median ROE", pct(med["roe"]), f"{target}: {pct(P.set_index('company').at[target, 'roe'])}", "#fbbf24"),
          ("Peer median P/E", f"{med['pe']:,.0f}x", f"{target}: {P.set_index('company').at[target, 'pe']:,.0f}x (n.m.)", NEG)])
    show = pd.concat([P, C[C["company"] == "Peer median"]])[
        ["company", "price", "market_cap", "revenue", "rev_growth", "rev_cagr_3y", "rev_cagr_5y",
         "net_margin", "roe", "pe", "pb", "comparable"]].copy()
    for c in ["price", "market_cap", "revenue"]:
        show[c] = show[c].map(lambda v: "-" if pd.isna(v) else f"{v:,.0f}")
    show["comparable"] = show["comparable"].map({True: "Yes", False: "No: standalone?"})
    st.dataframe(show, hide_index=True, width="stretch", column_config={
        "company": "Company", "price": st.column_config.TextColumn("Price (Rs)"),
        "market_cap": st.column_config.TextColumn("Mkt cap (Rs Cr)"),
        "revenue": st.column_config.TextColumn("Revenue (Rs Cr)"),
        "rev_growth": st.column_config.NumberColumn("Rev growth", format="percent"),
        "rev_cagr_3y": st.column_config.NumberColumn("CAGR 3y", format="percent"),
        "rev_cagr_5y": st.column_config.NumberColumn("CAGR 5y", format="percent"),
        "net_margin": st.column_config.ProgressColumn("Net margin", format="percent", min_value=0, max_value=0.4),
        "roe": st.column_config.ProgressColumn("ROE", format="percent", min_value=0, max_value=0.4),
        "pe": st.column_config.NumberColumn("P/E", format="%.1fx"),
        "pb": st.column_config.NumberColumn("P/B", format="%.1fx"), "comparable": "Comparable"})
    st.markdown('<div class="note">P/E uses latest-FY net profit. Values above 200x are not meaningful and are '
                'left out of the median.</div>', unsafe_allow_html=True)
    section("Head to head")
    metrics = [("rev_cagr_3y", "Revenue CAGR, 3 years", True), ("net_margin", "Net margin", True),
               ("roe", "Return on equity", True), ("pe", "P/E (x)", False)]
    cols = st.columns(2)
    for i, (m, title, is_pct) in enumerate(metrics):
        d = P.sort_values(m, ascending=True, na_position="first")
        vals = d[m]
        fig = go.Figure(go.Bar(
            y=d["company"], x=vals.clip(upper=120) if m == "pe" else vals, orientation="h",
            marker=dict(color=[COLORS.get(c, MUTED) for c in d["company"]], cornerradius=6),
            text=[("n/a" if pd.isna(v) else f"{v:.1%}" if is_pct else f"{v:,.0f}x") for v in vals],
            textposition="outside", textfont=dict(color=INK), cliponaxis=False,
            hovertemplate="%{y}: %{text}<extra></extra>"))
        if m == "pe":
            fig.update_xaxes(range=[0, 150])
            title += "  -  axis capped at 120x"
        fig.update_xaxes(showgrid=True, gridcolor=GRID)
        if is_pct:
            lo = min(0, float(vals.min())) * 1.8
            fig.update_xaxes(tickformat=".0%", range=[lo, float(vals.max()) * 1.25])
        fig.update_yaxes(showgrid=False, zeroline=False, ticklabelstandoff=10)
        cols[i % 2].plotly_chart(style(fig, title, height=290), width="stretch")

# ---- tab 3: DCF ---------------------------------------------------------------------------
with tab3:
    base = cfg["dcf"]
    if "dcf_init" not in st.session_state:
        st.session_state["dcf_init"] = True
        st.session_state["wacc"] = base["wacc"] * 100
        st.session_state["tg"] = base["terminal_growth"] * 100
        st.session_state["inv"] = base["include_investments"]
        for i in range(5):
            st.session_state[f"g{i}"] = base["revenue_growth"][i] * 100
            st.session_state[f"m{i}"] = base["fcf_margin"][i] * 100
    left, right = st.columns([1, 2.2])
    with left:
        section("Assumptions")
        wacc = st.slider("WACC (%)", 8.0, 20.0, step=0.1, key="wacc")
        tg = st.slider("Terminal growth (%)", 2.0, 8.0, step=0.1, key="tg")
        inv = st.checkbox("Add balance-sheet investments to net cash", key="inv")
        with st.expander("Yearly revenue growth and FCF margin"):
            g = [st.slider(f"Year {i + 1} revenue growth (%)", 0.0, 40.0, step=0.5, key=f"g{i}") for i in range(5)]
            mg = [st.slider(f"Year {i + 1} FCF margin (%)", 0.0, 30.0, step=0.5, key=f"m{i}") for i in range(5)]
        b1, b2 = st.columns(2)
        if b1.button("Save to config", width="stretch"):
            cfg["dcf"] = {"revenue_growth": [round(x / 100, 4) for x in g],
                          "fcf_margin": [round(x / 100, 4) for x in mg],
                          "wacc": round(wacc / 100, 4), "terminal_growth": round(tg / 100, 4),
                          "include_investments": bool(inv)}
            refresh.save_config(cfg)
            st.cache_data.clear()
            st.success("Saved.")
        if b2.button("Reset", width="stretch"):
            st.session_state.pop("dcf_init", None)
            st.rerun()

    if wacc <= tg:
        right.error("WACC must be above terminal growth.")
    else:
        a = {"revenue_growth": [x / 100 for x in g], "fcf_margin": [x / 100 for x in mg],
             "wacc": wacc / 100, "terminal_growth": tg / 100, "include_investments": inv}
        sens = {"wacc": [w / 100 for w in (wacc - 1.5, wacc, wacc + 1.5)],
                "terminal_growth": [t / 100 for t in (tg - 1, tg, tg + 1)]}
        d = valuation.value_company(ann, R["meta"][target], a, sens)
        with right:
            tv_share = d["pv_terminal"] / d["enterprise_value"]
            kpis([("DCF value / share", f"Rs {d['value_per_share']:,.0f}", f"{d['upside']:+.0%} vs market", ACCENT),
                  ("Market price", f"Rs {d['market_price']:,.0f}", "latest close in export", MUTED),
                  ("Enterprise value", f"Rs {d['enterprise_value']:,.0f} Cr", f"equity Rs {d['equity_value']:,.0f} Cr", POS),
                  ("Terminal value share", f"{tv_share:.0%}", "of enterprise value", "#fbbf24")])
            fig = go.Figure(go.Waterfall(
                x=["PV of FCF (5y)", "PV of terminal value", "Enterprise value", "Net cash", "Equity value"],
                y=[d["pv_fcf"], d["pv_terminal"], 0, d["net_cash"], 0],
                measure=["relative", "relative", "total", "relative", "total"],
                connector=dict(line=dict(color=GRID)),
                increasing=dict(marker=dict(color=POS)), totals=dict(marker=dict(color=ACCENT)),
                text=[f"{v:,.0f}" for v in (d["pv_fcf"], d["pv_terminal"], d["enterprise_value"],
                                            d["net_cash"], d["equity_value"])],
                textposition="outside", textfont=dict(color=INK),
                hovertemplate="%{x}: Rs %{y:,.0f} Cr<extra></extra>"))
            st.plotly_chart(style(fig, "Equity bridge (Rs Cr)", height=320), width="stretch")
            c1, c2 = st.columns([1, 1.4])
            fig = go.Figure(go.Bar(x=["DCF value", "Market price"], y=[d["value_per_share"], d["market_price"]],
                                   marker=dict(color=[ACCENT, MUTED], cornerradius=8),
                                   text=[f"Rs {d['value_per_share']:,.0f}", f"Rs {d['market_price']:,.0f}"],
                                   textposition="outside", textfont=dict(color=INK), cliponaxis=False,
                                   hovertemplate="%{x}: %{text}<extra></extra>"))
            c1.plotly_chart(style(fig, "Value per share vs market (Rs)", height=330), width="stretch")
            grid = d["sensitivity"]
            fig = go.Figure(go.Heatmap(
                z=grid.values, x=list(grid.columns), y=list(grid.index),
                colorscale=[[0, "#16315a"], [1, "#5eead4"]], xgap=3, ygap=3,
                text=np.round(grid.values, 0), texttemplate="Rs %{text:.0f}", showscale=False,
                textfont=dict(color="#0a0f1e", size=13),
                hovertemplate="WACC %{y}, growth %{x}: Rs %{z:.0f}<extra></extra>"))
            fig.update_xaxes(title="Terminal growth", type="category")
            fig.update_yaxes(title="WACC", autorange="reversed", type="category")
            c2.plotly_chart(style(fig, "Sensitivity: value per share", height=330), width="stretch")
            with st.expander("Projection table"):
                p = d["projection"].round(1)
                p.insert(0, "FY", [fy1 + t for t in p["year"]])
                st.dataframe(p.drop(columns="year"), hide_index=True, width="stretch")
    st.markdown('<div class="note">Illustrative model. FCF margins are assumptions, not guidance; Paytm\'s '
                'historical free cash flow is near zero, so most of the value sits in the terminal value.</div>',
                unsafe_allow_html=True)

# ---- tab 4: data checks -------------------------------------------------------------------
with tab4:
    log = R["checks"]
    counts = log["status"].value_counts()
    kpis([("Checks run", f"{len(log)}", "across 4 companies", POS),
          ("Pass", f"{counts.get('PASS', 0)}", "clean", ACCENT),
          ("Warn", f"{counts.get('WARN', 0)}", "worth knowing", "#fbbf24"),
          ("Fail", f"{counts.get('FAIL', 0)}", "breaks comparability", NEG)])
    sel = st.multiselect("Status", ["FAIL", "WARN", "PASS"], default=["FAIL", "WARN"])
    st.dataframe(log[log["status"].isin(sel)], hide_index=True, width="stretch", column_config={
        "company": "Company", "check": "Check", "status": "Status", "detail": st.column_config.TextColumn("Detail", width="large")})
