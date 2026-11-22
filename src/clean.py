"""Cleaning, share-count normalisation and data due-diligence checks.

Every check appends a row to a log: company, check, status (PASS/WARN/FAIL),
detail. The log is the "data due-diligence" output shown in the dashboard.
"""
import numpy as np
import pandas as pd

EXPENSE_LINES = ["raw_material", "power_fuel", "other_mfr", "employee_cost",
                 "selling_admin", "other_expenses"]
CORE = ["sales", "net_profit", "pbt", "reserves", "equity_capital", "shares"]


def clean_company(name, parsed, cfg):
    """Clean one company. Returns (annual df, quarterly df, meta dict, log rows)."""
    log = []

    def add(check, status, detail):
        log.append({"company": name, "check": check, "status": status, "detail": detail})

    ann = parsed["annual"].copy()
    qtr = parsed["quarterly"].copy()
    meta = dict(parsed["meta"])
    chk = cfg["checks"]

    # ---- missing values ---------------------------------------------------
    missing = {c: int(ann[c].isna().sum()) for c in CORE if c in ann}
    bad = {c: n for c, n in missing.items() if n}
    add("Missing core fields", "WARN" if bad else "PASS",
        f"NaNs in {bad}; not imputed" if bad else "No gaps in sales, profit, equity, shares")
    for col in ["borrowings", "investments", "cash", "other_income", "interest", "depreciation"]:
        n = int(ann[col].isna().sum())
        if n:
            ann[col] = ann[col].fillna(0.0)
            add(f"Imputed {col}", "PASS", f"{n} blank year(s) set to 0 (line item not reported)")
    n = int(ann["tax"].isna().sum())
    if n:
        ann["tax"] = ann["tax"].fillna(ann["pbt"] - ann["net_profit"])
        add("Imputed tax", "PASS", f"{n} blank year(s) derived as PBT - net profit")

    # ---- face-value / split normalisation ----------------------------------
    fv_now = ann["face_value"].dropna().iloc[-1]
    ann["share_factor"] = ann["face_value"] / fv_now
    ann["shares_adj_cr"] = ann["shares"] * ann["share_factor"] / 1e7
    fv_chg = ann["face_value"].diff().fillna(0) != 0
    if fv_chg.any():
        yrs = ", ".join(f"FY{y} ({ann.face_value.shift().loc[y]:g}->{ann.face_value.loc[y]:g})"
                        for y in ann.index[fv_chg])
        add("Face-value change", "WARN",
            f"Split detected at {yrs}; historical shares rescaled to FV {fv_now:g}")
    else:
        add("Face-value change", "PASS", "No split in the period")

    ratio = ann["shares_adj_cr"] / ann["shares_adj_cr"].shift()
    jumps = ratio[(ratio > chk["share_jump_ratio"]) | (ratio < 1 / chk["share_jump_ratio"])]
    if len(jumps):
        add("Share-count jump", "WARN",
            "Adjusted shares jump " + ", ".join(f"FY{y} x{r:.0f}" for y, r in jumps.items())
            + " with no matching split (bonus / preference-share conversion); "
            "per-share history before this is not comparable")
    else:
        add("Share-count jump", "PASS", "Adjusted share count moves smoothly")

    ref = ann["screener_adj_shares_cr"]
    dev = ((ann["shares_adj_cr"] - ref) / ref).abs()
    off = dev[dev > 0.05]
    add("Shares vs Screener adjusted", "WARN" if len(off) else "PASS",
        f"Differs >5% in FY{', FY'.join(map(str, off.index))}" if len(off)
        else "Within 5% of Screener's own adjusted share count")

    # ---- reconciliation ----------------------------------------------------
    tol = chk["reconcile_tolerance"]
    exp = ann[[c for c in EXPENSE_LINES if c in ann]].fillna(0).sum(axis=1)
    implied_pbt = ann["sales"] + ann["other_income"] - exp - ann["depreciation"] - ann["interest"]
    err = (implied_pbt - ann["pbt"]).abs() / ann["sales"].abs().clip(lower=1)
    add("Profit statement adds up", "PASS" if (err <= tol).all() else "FAIL",
        "Sales + other income - costs = profit before tax in every year" if (err <= tol).all()
        else f"Gap >{tol:.0%} of sales in FY{', FY'.join(map(str, err[err > tol].index))}")

    err = ((ann["pbt"] - ann["tax"]) - ann["net_profit"]).abs() / ann["sales"].abs().clip(lower=1)
    add("Profit before tax - tax = net profit", "PASS" if (err <= tol).all() else "WARN",
        "Ties out" if (err <= tol).all()
        else f"Gap in FY{', FY'.join(map(str, err[err > tol].index))} (minorities / exceptionals)")

    err = (ann["total_liabilities"] - ann["total_assets"]).abs() / ann["total_assets"]
    add("Balance sheet balances", "PASS" if (err <= tol).all() else "FAIL",
        "Liabilities = assets every year" if (err <= tol).all()
        else f"Imbalance in FY{', FY'.join(map(str, err[err > tol].index))}")

    # ---- quarterly vs annual ----------------------------------------------
    qtol = chk["quarterly_tolerance"]
    issues = []
    for fy in ann.index:
        quarters = qtr[[(t.year if t.month <= 3 else t.year + 1) == fy for t in qtr.index]]
        if len(quarters) == 4:
            for col in ["sales", "net_profit"]:
                a, q = ann.at[fy, col], quarters[col].sum()
                if abs(a) > 1 and abs(q - a) / abs(a) > qtol:
                    issues.append(f"FY{fy} {col}: annual {a:,.0f} vs 4Q {q:,.0f}")
    add("Quarters sum to annual", "WARN" if issues else "PASS",
        "; ".join(issues) if issues else "Sum of 4 quarters matches annual sales and profit")

    # ---- price / market cap -----------------------------------------------
    price, mcap = meta.get("Current Price"), meta.get("Market Capitalization")
    last_shares = ann["shares_adj_cr"].dropna().iloc[-1]
    meta["shares_cr"] = last_shares
    if price and mcap:
        implied = mcap / price
        d = abs(implied - last_shares) / last_shares
        add("Market cap = price x shares", "PASS" if d < 0.03 else "WARN",
            f"Implied {implied:.2f} Cr shares vs balance-sheet {last_shares:.2f} Cr ({d:.1%} gap)")

    # ---- standalone vs consolidated flag -----------------------------------
    triggers = []
    last = ann.iloc[-1]
    if last["other_income"] > last["sales"]:
        triggers.append(f"other income ({last['other_income']:,.0f}) exceeds sales ({last['sales']:,.0f})")
    if mcap and last["sales"] > 0 and mcap / last["sales"] > chk["mcap_to_sales_standalone"]:
        triggers.append(f"market cap is {mcap / last['sales']:.0f}x sales")
    if len(qtr) >= 5:
        prior = qtr["sales"].iloc[-5:-1].mean()
        if prior > 0 and qtr["sales"].iloc[-1] / prior > chk["quarter_break_ratio"]:
            triggers.append(f"latest quarter sales {qtr['sales'].iloc[-1]:,.0f} is "
                            f"{qtr['sales'].iloc[-1] / prior:.1f}x the prior 4Q average (basis change)")
    flagged = len(triggers) >= 2
    meta["standalone_suspect"] = flagged
    meta["flags"] = triggers
    add("Revenue basis (standalone vs consolidated)", "FAIL" if flagged else "PASS",
        "Revenue looks like a standalone / holding-company basis: " + "; ".join(triggers)
        if flagged else "Revenue consistent with a consolidated operating business")

    return ann, qtr, meta, log


def clean_all(parsed_all, cfg):
    """Clean every company. Returns (annual dict, quarterly dict, meta dict, log DataFrame)."""
    annual, quarterly, meta, rows = {}, {}, {}, []
    for name, parsed in parsed_all.items():
        annual[name], quarterly[name], meta[name], log = clean_company(name, parsed, cfg)
        rows += log
    return annual, quarterly, meta, pd.DataFrame(rows)
