"""Peer benchmarking table."""
import numpy as np
import pandas as pd

METRICS = ["rev_growth", "rev_cagr_3y", "rev_cagr_5y", "net_margin", "roe", "pe", "pb", "ps"]
# P/E above this is shown but treated as not meaningful for medians
PE_CAP = 200


def build_comps(snapshot, meta, target=None):
    """One row per company plus a peer-median row.

    The median covers peers only: the target company and any company whose
    revenue basis was flagged standalone are shown but excluded from it.
    """
    df = snapshot.copy()
    df["comparable"] = [not meta[c]["standalone_suspect"] for c in df["company"]]
    df["pe_meaningful"] = df["pe"].where(df["pe"] <= PE_CAP)
    base = df[df["comparable"] & (df["company"] != target)]
    median = {"company": "Peer median", "comparable": True}
    for m in METRICS:
        col = "pe_meaningful" if m == "pe" else m
        median[m] = base[col].median()
    return pd.concat([df, pd.DataFrame([median])], ignore_index=True)


def format_comps(comps):
    """Console-friendly copy of the comps table."""
    d = comps.copy()
    pct = ["rev_growth", "rev_cagr_3y", "rev_cagr_5y", "net_margin", "roe"]
    for c in pct:
        d[c] = d[c].map(lambda v: "n/a" if pd.isna(v) else f"{v:.1%}")
    for c in ["pe", "pe_ttm", "pb", "ps"]:
        d[c] = d[c].map(lambda v: "n/m" if pd.isna(v) else f"{v:,.1f}x")
    d["comparable"] = d["comparable"].map({True: "yes", False: "NO (standalone?)"})
    keep = ["company", "price", "market_cap", "revenue", "rev_growth", "rev_cagr_3y",
            "rev_cagr_5y", "net_margin", "roe", "pe", "pb", "comparable"]
    return d[keep]


def peer_value(snapshot, meta, target, shares_cr):
    """What Paytm would be worth per share at its peers' price-to-sales (P/S).

    P/S = market cap / sales. Uses only comparable peers (not the target, not
    companies flagged as standalone). Returns low / median / high Rs per share.
    """
    t = snapshot.set_index("company")
    peers = [c for c in t.index if c != target and not meta[c]["standalone_suspect"]]
    ps = t.loc[peers, "ps"].dropna()
    revenue = t.at[target, "revenue"]
    to_price = lambda multiple: multiple * revenue / shares_cr
    return {"peers": ps.to_dict(), "target_ps": t.at[target, "ps"],
            "low": to_price(ps.min()), "median": to_price(ps.median()), "high": to_price(ps.max())}
