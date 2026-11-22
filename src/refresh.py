"""Run the whole pipeline: ingest -> clean -> analytics -> valuation -> comps.

Standalone:  python -m src.refresh
Dashboard:   app.py calls run_pipeline() (the Refresh button re-runs it).
"""
from pathlib import Path

import pandas as pd
import yaml

from . import analytics, clean, comps, ingest, valuation

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.yaml"
RAW_DIR = ROOT / "data" / "raw"
OUT_DIR = ROOT / "data" / "processed"


def load_config(path=CONFIG_PATH):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_config(cfg, path=CONFIG_PATH):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f, sort_keys=False)


def raw_signature():
    """(filename, mtime) of every export, used to detect a newly dropped file."""
    return tuple((p.name, p.stat().st_mtime) for p in sorted(RAW_DIR.glob("*.xlsx")))


def run_pipeline(cfg=None, save=True):
    """Execute every stage and return all results in one dict."""
    cfg = cfg or load_config()
    parsed = ingest.ingest_all(cfg["companies"], RAW_DIR)
    annual, quarterly, meta, checks = clean.clean_all(parsed, cfg)
    yearly, snapshot = analytics.analyse_all(annual, quarterly, meta)
    target = cfg["target"]
    peers = comps.build_comps(snapshot, meta, target)
    dcf = valuation.value_company(annual[target], meta[target], cfg["dcf"], cfg["sensitivity"])
    pv = comps.peer_value(snapshot, meta, target, dcf["shares_cr"])
    result = {"config": cfg, "peer_value": pv, "annual": annual, "quarterly": quarterly, "meta": meta,
              "checks": checks, "yearly": yearly, "snapshot": snapshot,
              "comps": peers, "dcf": dcf}
    if save:
        save_outputs(result)
    return result


def save_outputs(result):
    """Write cleaned tables to data/processed/ (parquet + csv)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    ann = pd.concat(result["annual"], names=["company", "fy"]).reset_index()
    qtr = pd.concat(result["quarterly"], names=["company", "quarter_end"]).reset_index()
    yr = pd.concat(result["yearly"], names=["company", "fy"]).reset_index()
    for name, df in [("annual_clean", ann), ("quarterly_clean", qtr), ("yearly_metrics", yr),
                     ("comps", result["comps"]), ("checks", result["checks"])]:
        df.to_parquet(OUT_DIR / f"{name}.parquet", index=False)
        df.to_csv(OUT_DIR / f"{name}.csv", index=False)
    result["dcf"]["projection"].to_csv(OUT_DIR / "dcf_projection.csv", index=False)
    result["dcf"]["sensitivity"].to_csv(OUT_DIR / "dcf_sensitivity.csv")


def main():
    r = run_pipeline()
    d, target = r["dcf"], r["config"]["target"]
    pd.set_option("display.width", 220, "display.max_columns", 30)
    print("\n=== Data due-diligence (non-PASS) ===")
    print(r["checks"][r["checks"]["status"] != "PASS"].to_string(index=False, max_colwidth=110))
    print(f"\n=== {target} DCF ===")
    print(f"Base revenue (FY{r['annual'][target].index[-1]}): Rs {d['base_revenue']:,.0f} Cr")
    print(f"Enterprise value : Rs {d['enterprise_value']:,.0f} Cr")
    print(f"Net cash         : Rs {d['net_cash']:,.0f} Cr")
    print(f"Equity value     : Rs {d['equity_value']:,.0f} Cr")
    print(f"Value per share  : Rs {d['value_per_share']:,.0f}  (market Rs {d['market_price']:,.0f}, "
          f"{d['upside']:+.0%})")
    pv = r["peer_value"]
    print(f"\nAt peers' price-to-sales (Paytm now {pv['target_ps']:.1f}x): "
          f"Rs {pv['low']:,.0f} to Rs {pv['high']:,.0f} per share, median Rs {pv['median']:,.0f}")
    print("\nValue per share (Rs) if expected return and long-term growth change:")
    print(d["sensitivity"].round(0).to_string())
    print("\n=== Peer comps ===")
    print(comps.format_comps(r["comps"]).to_string(index=False))
    print(f"\nProcessed files written to {OUT_DIR}")


if __name__ == "__main__":
    main()
