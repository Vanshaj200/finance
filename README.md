# Equity Valuation & Analytics Engine: Paytm vs fintech peers

Compares Paytm (One 97 Communications) with Angel One, CAMS and PB Fintech using
Screener.in exports, estimates what Paytm is worth two ways, and shows everything in an
interactive Streamlit dashboard.

## Setup

```powershell
pip install -r requirements.txt
python -m src.refresh      # run the pipeline, print results, write data/processed/
streamlit run app.py       # dashboard
```

## Data

Four Screener.in Excel exports live in `data/raw/`. The visible P&L / Balance Sheet / Cash
Flow tabs are blank formula views, so `ingest.py` reads the hidden **Data Sheet** tab.
Figures are consolidated, in Rs Crore, FY2017 to FY2026, plus a quarterly block.

To update: replace a file in `data/raw/` with a newer export (same filename) and press
**Refresh data** in the sidebar. This re-reads a downloaded export; it is not live scraping.

## Pipeline (`src/`)

| Module | Job |
|---|---|
| `ingest.py` | Read each Data Sheet into clean tables |
| `clean.py` | Fill gaps, fix share counts after stock splits, run data checks |
| `analytics.py` | Growth, 3 and 5 year growth, profit margin, P/E, price-to-sales |
| `valuation.py` | Simple 5-year cash-flow valuation (DCF) with a what-if grid |
| `comps.py` | Peer table, and Paytm's value at its peers' price-to-sales |
| `refresh.py` | Runs everything; `python -m src.refresh` prints the results |

## Data checks

Each check is logged as PASS / WARN / FAIL and shown in the dashboard's *Data checks* tab:
missing values, stock splits, sudden share-count jumps, profit statement adding up,
balance sheet balancing, quarters adding up to the year, and a test for whether a
company's revenue is the whole group or just the parent company. **PB Fintech fails the
last one** (its other income is bigger than its sales), so it is shown but left out of the
peer median.

## Valuation, in plain words

1. **Cash-flow model (DCF).** Forecast 5 years of the cash Paytm keeps from its sales, add a
   long-run value for the years after, and bring it all back to today's money using the
   return investors expect. Add cash minus debt, divide by the number of shares.
   Settings are in `config.yaml` and as sliders in the dashboard: year-1 growth (fades by
   1.5 points a year), cash kept per Rs 100 of sales by year 5, expected return (13.5%) and
   growth after year 5 (5%). Default result: about Rs 267 per share.
2. **Peer check.** What Paytm would be worth at the price-to-sales of Angel One and CAMS:
   about Rs 498 to Rs 1,099 per share (median Rs 798).

The market price is Rs 1,675. Both views come out well below it. The margins are
assumptions, not forecasts, and most of the cash-flow value comes from the years after year 5.
