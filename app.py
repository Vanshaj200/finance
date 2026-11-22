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

tab1, tab2, tab3, tab4 = st.tabs(["Turnaround", "Peer benchmarking", "Valuation", "Data checks"])

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
        st.warning(f"**{c}**: its revenue looks like the parent company only ({'; '.join(R['meta'][c]['flags'])}). "
                   "It is shown but left out of the peer median.")
    med = C[C["company"] == "Peer median"].iloc[0]
    me = P.set_index("company").loc[target]
    kpis([("Revenue growth (3-yr avg)", pct(me["rev_cagr_3y"]), f"peer median {pct(med['rev_cagr_3y'])}", POS),
          ("Net margin", pct(me["net_margin"]), f"peer median {pct(med['net_margin'])}", ACCENT),
          ("P/E", f"{me['pe']:,.0f}x", f"peer median {med['pe']:,.0f}x", NEG),
          ("Price-to-sales", f"{me['ps']:.1f}x", f"peer median {med['ps']:.1f}x", "#fbbf24")])
    show = pd.concat([P, C[C["company"] == "Peer median"]])[
        ["company", "price", "market_cap", "revenue", "rev_growth", "rev_cagr_3y", "net_margin", "pe", "ps",
         "comparable"]].copy()
    for c in ["price", "market_cap", "revenue"]:
        show[c] = show[c].map(lambda v: "-" if pd.isna(v) else f"{v:,.0f}")
    show["comparable"] = show["comparable"].map({True: "Yes", False: "No"})
    st.dataframe(show, hide_index=True, width="stretch", column_config={
        "company": "Company", "price": st.column_config.TextColumn("Price (Rs)"),
        "market_cap": st.column_config.TextColumn("Market cap (Rs Cr)"),
        "revenue": st.column_config.TextColumn("Revenue (Rs Cr)"),
        "rev_growth": st.column_config.NumberColumn("Growth last year", format="percent"),
        "rev_cagr_3y": st.column_config.NumberColumn("Growth, 3-yr avg", format="percent"),
        "net_margin": st.column_config.ProgressColumn("Net margin", format="percent", min_value=0, max_value=0.4),
        "pe": st.column_config.NumberColumn("P/E", format="%.1fx"),
        "ps": st.column_config.NumberColumn("Price-to-sales", format="%.1fx"),
        "comparable": "Fair to compare?"})
    st.markdown('<div class="note"><b>Net margin</b> = profit kept from each Rs 100 of sales. '
                '<b>P/E</b> = share price relative to profit per share (how many years of profit you pay for). '
                '<b>Price-to-sales</b> = market value relative to yearly sales. '
                'P/E above 200x is not meaningful and is left out of the median.</div>', unsafe_allow_html=True)
    section("Head to head")
    metrics = [("rev_cagr_3y", "Revenue growth, 3-year average", "pct"), ("net_margin", "Net margin", "pct"),
               ("pe", "P/E (x)", "x"), ("ps", "Price-to-sales (x)", "x")]
    cols = st.columns(2)
    for i, (m, title, kind) in enumerate(metrics):
        d = P.sort_values(m, ascending=True, na_position="first")
        vals = d[m]
        fig = go.Figure(go.Bar(
            y=d["company"], x=vals.clip(upper=120) if m == "pe" else vals, orientation="h",
            marker=dict(color=[COLORS.get(c, MUTED) for c in d["company"]], cornerradius=6),
            text=[("n/a" if pd.isna(v) else f"{v:.1%}" if kind == "pct" else f"{v:,.0f}x" if m == "pe" else f"{v:.1f}x")
                  for v in vals],
            textposition="outside", textfont=dict(color=INK), cliponaxis=False,
            hovertemplate="%{y}: %{text}<extra></extra>"))
        fig.update_xaxes(showgrid=True, gridcolor=GRID)
        if kind == "pct":
            lo = min(0, float(vals.min())) * 1.8
            fig.update_xaxes(tickformat=".0%", range=[lo, float(vals.max()) * 1.25])
        if m == "pe":
            fig.update_xaxes(range=[0, 150])
            title += "  -  axis capped at 120x"
        fig.update_yaxes(showgrid=False, zeroline=False, ticklabelstandoff=10)
        cols[i % 2].plotly_chart(style(fig, title, height=290), width="stretch")

# ---- tab 3: valuation ---------------------------------------------------------------------
with tab3:
    base = cfg["dcf"]
    KEYS = {"sg": base["start_growth"] * 100, "em": base["end_margin"] * 100,
            "er": base["expected_return"] * 100, "lg": base["long_term_growth"] * 100,
            "inv": base["include_investments"]}
    if "dcf_init" not in st.session_state:
        st.session_state["dcf_init"] = True
        for k, v in KEYS.items():
            st.session_state[k] = v
    left, right = st.columns([1, 2.2])
    with left:
        section("Your assumptions")
        sg = st.slider("Revenue growth in year 1 (%)", 5.0, 30.0, step=0.5, key="sg",
                       help="Growth then falls by 1.5 points every year.")
        em = st.slider("Cash kept from each Rs 100 of sales by year 5 (Rs)", 5.0, 30.0, step=0.5, key="em",
                       help="Starts at Rs 4 in year 1 and rises in a straight line.")
        er = st.slider("Return investors expect (%)", 8.0, 20.0, step=0.1, key="er",
                       help="Future cash is worth less today, so it is discounted at this rate.")
        lg = st.slider("Growth after year 5 (%)", 2.0, 8.0, step=0.1, key="lg",
                       help="Long-run growth forever after the 5 forecast years.")
        inv = st.checkbox("Also count the company's investments as spare cash", key="inv")
        b1, b2 = st.columns(2)
        if b1.button("Save to config", width="stretch"):
            cfg["dcf"] = {**base, "start_growth": round(sg / 100, 4), "end_margin": round(em / 100, 4),
                          "expected_return": round(er / 100, 4), "long_term_growth": round(lg / 100, 4),
                          "include_investments": bool(inv)}
            refresh.save_config(cfg)
            st.cache_data.clear()
            st.success("Saved.")
        if b2.button("Reset", width="stretch"):
            st.session_state.pop("dcf_init", None)
            st.rerun()

    if er <= lg:
        right.error("Expected return must be higher than long-term growth.")
    else:
        a = {**base, "start_growth": sg / 100, "end_margin": em / 100, "expected_return": er / 100,
             "long_term_growth": lg / 100, "include_investments": inv}
        sens = {"expected_return": [x / 100 for x in (er - 1.5, er, er + 1.5)],
                "long_term_growth": [x / 100 for x in (lg - 1, lg, lg + 1)]}
        d = valuation.value_company(ann, R["meta"][target], a, sens)
        pv = R["peer_value"]
        with right:
            kpis([("Value from cash-flow model", f"Rs {d['value_per_share']:,.0f}", "per share (DCF)", ACCENT),
                  ("Value at peer price-to-sales", f"Rs {pv['median']:,.0f}", f"range Rs {pv['low']:,.0f} to {pv['high']:,.0f}", POS),
                  ("Market price", f"Rs {d['market_price']:,.0f}", f"DCF is {abs(d['upside']):.0%} {'below' if d['upside'] < 0 else 'above'} it", MUTED)])
            names = ["Cash-flow model (DCF)", "Peers, low", "Peers, median", "Peers, high", "Market price"]
            vals = [d["value_per_share"], pv["low"], pv["median"], pv["high"], d["market_price"]]
            fig = go.Figure(go.Bar(
                y=names, x=vals, orientation="h",
                marker=dict(color=[ACCENT, POS, POS, POS, MUTED], cornerradius=6),
                text=[f"Rs {v:,.0f}" for v in vals], textposition="outside", textfont=dict(color=INK),
                cliponaxis=False, hovertemplate="%{y}: %{text}<extra></extra>"))
            fig.update_yaxes(autorange="reversed", showgrid=False, zeroline=False, ticklabelstandoff=10)
            fig.update_xaxes(range=[0, max(vals) * 1.2])
            st.plotly_chart(style(fig, "Value per share: three ways to look at it (Rs)", height=300), width="stretch")
            grid = d["sensitivity"]
            fig = go.Figure(go.Heatmap(
                z=grid.values, x=list(grid.columns), y=list(grid.index),
                colorscale=[[0, "#16315a"], [1, "#5eead4"]], xgap=3, ygap=3,
                text=np.round(grid.values, 0), texttemplate="Rs %{text:.0f}", showscale=False,
                textfont=dict(color="#0a0f1e", size=13),
                hovertemplate="Expected return %{y}, long-term growth %{x}: Rs %{z:.0f}<extra></extra>"))
            fig.update_xaxes(title="Growth after year 5", type="category")
            fig.update_yaxes(title="Expected return", autorange="reversed", type="category")
            st.plotly_chart(style(fig, "What if the two big assumptions change? (value per share)", height=300),
                            width="stretch")
            with st.expander("Year-by-year numbers"):
                p = d["projection"].copy()
                p.insert(0, "FY", [fy1 + t for t in p["year"]])
                p["growth"] = d["growth"]
                p["cash_margin"] = d["margin"]
                p = p[["FY", "growth", "revenue", "cash_margin", "fcf", "pv_fcf"]]
                st.dataframe(p, hide_index=True, width="stretch", column_config={
                    "growth": st.column_config.NumberColumn("Revenue growth", format="percent"),
                    "revenue": st.column_config.NumberColumn("Revenue (Rs Cr)", format="%.0f"),
                    "cash_margin": st.column_config.NumberColumn("Cash kept", format="percent"),
                    "fcf": st.column_config.NumberColumn("Free cash (Rs Cr)", format="%.0f"),
                    "pv_fcf": st.column_config.NumberColumn("Worth today (Rs Cr)", format="%.0f")})
                st.write(f"Cash and bank minus borrowings: Rs {d['net_cash']:,.0f} Cr is added on top. "
                         f"Divided by {d['shares_cr']:.1f} Cr shares.")
    st.markdown('<div class="note">How to read this: the <b>cash-flow model</b> adds up the cash Paytm could '
                'generate over 5 years plus a long-run value after that, brought back to today at the return investors '
                'expect. The <b>peer view</b> asks what Paytm would be worth if it traded at the same price-to-sales '
                'as Angel One and CAMS. Both are rough: the margins are assumptions, not forecasts, and the peers earn '
                'far higher profits than Paytm today.</div>', unsafe_allow_html=True)

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
