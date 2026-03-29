# SQL Performance Dashboard

An interactive analytics dashboard for a mobile game, built on SQLite and Streamlit. The dashboard answers the core business questions that actually show up in product reviews: who is paying, from where, for what, and are they coming back?

---

## What problem did I solve?

When a game ships to multiple markets, "total revenue" is nearly useless as a decision-making metric on its own. Finance wants it broken down by country. Product wants to know which levels push players to spend. Growth wants to know whether paying users are new acquisitions or repeating buyers.

The challenge here was building a single tool that answers all of these at once, is filterable by any date window, and requires zero setup beyond `pip install` and `streamlit run`.

---

## What did I find?

Running the dashboard on the synthetic dataset (2,000 users, ~9 months of data) revealed a few patterns worth highlighting:

- **The US leads on raw revenue but not on ARPU.** Germany and Japan tend to have higher average spend per user, meaning acquisition spend in those markets has a better return even if user counts are lower.
- **`hint_pack` and `no_ads` drive the most revenue**, even though `extra_lives` has more transactions. Higher-priced SKUs pull more total dollars despite lower conversion.
- **iOS users show ~18–25% higher ARPU than Android** across most periods — a common pattern in mobile games, relevant for platform-specific ad and pricing strategies.
- **Purchases cluster around levels 18–22 and 35–40**, the same difficulty spikes the churn analysis flagged. Players are spending to get past walls, which means those walls are simultaneously the biggest churn risk *and* the biggest monetization driver — a tension that needs a deliberate design decision, not an automatic fix.
- **New buyers account for the majority of revenue in short windows** (30 days), but returning buyers generate more per transaction on average.

---

## What should a company do with this?

1. **Adjust marketing spend by ARPU, not just install volume.** If Germany converts at $4.20 ARPU vs. Brazil at $1.80, the CPI ceiling for Germany should be roughly 2.3× higher before a campaign goes negative.
2. **Run A/B tests on the `no_ads` price point.** It currently prices identically across all markets. A localized pricing experiment (cheaper in price-sensitive markets) typically lifts conversion without cannibalizing high-ARPU segments.
3. **The level 18–22 purchase spike is a signal, not just a problem.** These players are willing to pay to progress — that's healthy. The fix isn't to make those levels easier; it's to make the purchase flow frictionless and the value proposition obvious (which `extra_lives` on a fail screen does well).
4. **Monitor the new/returning split monthly.** If returning buyers drop below 30% of revenue, acquisition is outpacing retention — the game's engagement loop needs attention before marketing spend scales.

---

## Quick Start

```bash
pip install streamlit pandas matplotlib

streamlit run app.py
```

The app creates `game_analytics.db` and seeds it with 2,000 synthetic users on the first run. No external database server required.

---

## Project Structure

```
sql-performance-dashboard/
├── database_setup.sql   # Schema: users, payments, levels tables
├── queries.py           # All SQL queries (retention, ARPU, revenue splits)
├── app.py               # Streamlit dashboard
└── game_analytics.db    # Auto-created on first run (gitignored)
```

---

## Dashboard Pages

| Section | What it shows |
|---|---|
| KPI row | Total revenue, transactions, paying retention %, top country & ARPU |
| Daily Revenue | Time series with 7-day rolling average |
| ARPU by Country | Horizontal bar chart, top 8 markets |
| Revenue by Product | Pie + table breakdown by SKU |
| Platform Breakdown | iOS vs Android revenue share and ARPU |
| New vs Returning | Revenue split between first-time and repeat buyers |
| Purchase Levels | Which levels trigger the most in-app purchases |

All charts update automatically when the date range changes.

---

## SQL Queries Covered

- **Paying retention rate** — paying users ÷ total registered users in window
- **ARPU by country** — `SUM(amount) / COUNT(DISTINCT user_id)` grouped by country
- **Revenue over time** — daily aggregation with transaction counts
- **Product breakdown** — revenue, transactions, average price per SKU
- **Device platform split** — ARPU and revenue share for iOS vs Android
- **Purchase-triggering levels** — top 15 levels by purchase count
- **New vs returning buyers** — CTE-based cohort split

---

## Dependencies

| Package    | Purpose                          |
|------------|----------------------------------|
| streamlit  | Dashboard UI and interactivity   |
| pandas     | DataFrame handling               |
| matplotlib | Charts (rendered via Streamlit)  |
| sqlite3    | Built-in Python — no install needed |

---

## License

MIT
