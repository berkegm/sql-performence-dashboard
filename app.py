"""
Mobile Game Performance Dashboard — Streamlit app

Run:
    streamlit run app.py

The database is created and seeded automatically on first launch.
"""

import sqlite3
from pathlib import Path
from datetime import date, timedelta

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import streamlit as st

import queries

# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Game Analytics Dashboard",
    page_icon="🎮",
    layout="wide",
)

# ── DB bootstrap ──────────────────────────────────────────────────────────────

@st.cache_resource
def get_conn() -> sqlite3.Connection:
    db_path = "game_analytics.db"
    conn = queries.get_connection(db_path)

    schema = Path("database_setup.sql").read_text()
    conn.executescript(schema)
    queries.seed_database(conn)
    return conn

conn = get_conn()

# ── Sidebar — date range ──────────────────────────────────────────────────────

st.sidebar.header("Filters")

today     = date(2025, 3, 31)   # last date in synthetic data
min_date  = date(2024, 7, 1)

preset = st.sidebar.radio(
    "Date range",
    ["Last 30 days", "Last 90 days", "Last 6 months", "All time", "Custom"],
    index=1,
)

if preset == "Last 30 days":
    start_dt, end_dt = today - timedelta(days=30), today
elif preset == "Last 90 days":
    start_dt, end_dt = today - timedelta(days=90), today
elif preset == "Last 6 months":
    start_dt, end_dt = today - timedelta(days=180), today
elif preset == "All time":
    start_dt, end_dt = min_date, today
else:
    start_dt = st.sidebar.date_input("From", today - timedelta(days=90), min_value=min_date, max_value=today)
    end_dt   = st.sidebar.date_input("To",   today,                      min_value=min_date, max_value=today)
    if start_dt > end_dt:
        st.sidebar.error("Start date must be before end date.")
        st.stop()

start_str = start_dt.isoformat()
end_str   = end_dt.isoformat()

# ── Header ────────────────────────────────────────────────────────────────────

st.title("Game Performance Dashboard")
st.caption(f"Showing data from **{start_str}** to **{end_str}**")
st.divider()

# ── KPI row ───────────────────────────────────────────────────────────────────

rev_df      = queries.revenue_over_time(conn, start_str, end_str)
retention   = queries.retention_rate(conn, start_str, end_str)
arpu_df     = queries.arpu_by_country(conn, start_str, end_str)

total_rev   = rev_df["revenue"].sum() if not rev_df.empty else 0
total_txn   = rev_df["transactions"].sum() if not rev_df.empty else 0
ret_pct     = retention["retention_pct"].iloc[0] if not retention.empty else 0
top_country = arpu_df.iloc[0]["country"] if not arpu_df.empty else "—"
top_arpu    = arpu_df.iloc[0]["arpu"] if not arpu_df.empty else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Total Revenue",    f"${total_rev:,.2f}")
k2.metric("Transactions",     f"{int(total_txn):,}")
k3.metric("Paying Retention", f"{ret_pct:.1f}%")
k4.metric("Top Country",      top_country)
k5.metric("Top Country ARPU", f"${top_arpu:.2f}")

st.divider()

# ── Row 1: Revenue over time + ARPU by country ────────────────────────────────

col1, col2 = st.columns([3, 2])

with col1:
    st.subheader("Daily Revenue")
    if rev_df.empty:
        st.info("No payment data in this range.")
    else:
        fig, ax = plt.subplots(figsize=(8, 3.5))
        ax.fill_between(rev_df["date"], rev_df["revenue"], alpha=0.25, color="#3498db")
        ax.plot(rev_df["date"], rev_df["revenue"], color="#3498db", linewidth=1.8)

        # 7-day rolling average
        if len(rev_df) >= 7:
            rolling = rev_df.set_index("date")["revenue"].rolling(7).mean()
            ax.plot(rolling.index, rolling.values, color="#e74c3c",
                    linewidth=1.4, linestyle="--", label="7-day avg")
            ax.legend(fontsize=9)

        ax.set_xlabel("")
        ax.set_ylabel("USD")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        ax.grid(axis="y", alpha=0.3)
        fig.autofmt_xdate()
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

with col2:
    st.subheader("ARPU by Country")
    if arpu_df.empty:
        st.info("No data.")
    else:
        top_n = arpu_df.head(8)
        fig, ax = plt.subplots(figsize=(5, 3.5))
        bars = ax.barh(top_n["country"][::-1], top_n["arpu"][::-1],
                       color="#2ecc71", edgecolor="white")
        for bar, val in zip(bars, top_n["arpu"][::-1]):
            ax.text(bar.get_width() + 0.05, bar.get_y() + bar.get_height() / 2,
                    f"${val:.2f}", va="center", fontsize=8)
        ax.set_xlabel("ARPU (USD)")
        ax.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.0f}"))
        ax.grid(axis="x", alpha=0.3)
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

st.divider()

# ── Row 2: Products + Device split ───────────────────────────────────────────

col3, col4 = st.columns(2)

with col3:
    st.subheader("Revenue by Product")
    prod_df = queries.top_products(conn, start_str, end_str)
    if prod_df.empty:
        st.info("No data.")
    else:
        fig, ax = plt.subplots(figsize=(5, 3.5))
        colors = plt.cm.Set2.colors[:len(prod_df)]
        ax.pie(prod_df["revenue"], labels=prod_df["product"],
               autopct="%1.1f%%", colors=colors, startangle=140,
               textprops={"fontsize": 9})
        ax.set_title("")
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

        st.dataframe(
            prod_df.rename(columns={
                "product": "Product", "transactions": "Transactions",
                "revenue": "Revenue ($)", "avg_price": "Avg Price ($)"
            }),
            hide_index=True, use_container_width=True
        )

with col4:
    st.subheader("Platform Breakdown")
    dev_df = queries.revenue_by_device(conn, start_str, end_str)
    if dev_df.empty:
        st.info("No data.")
    else:
        fig, axes = plt.subplots(1, 2, figsize=(5, 3))
        axes[0].pie(dev_df["revenue"], labels=dev_df["device_type"],
                    autopct="%1.1f%%", colors=["#3498db", "#e74c3c"],
                    textprops={"fontsize": 9})
        axes[0].set_title("Revenue Share", fontsize=9)

        axes[1].bar(dev_df["device_type"], dev_df["arpu"],
                    color=["#3498db", "#e74c3c"], edgecolor="white")
        axes[1].set_title("ARPU", fontsize=9)
        axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:.2f}"))
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

    st.subheader("New vs Returning Buyers")
    nvr = queries.new_vs_returning(conn, start_str, end_str)
    if not nvr.empty:
        fig, ax = plt.subplots(figsize=(4, 2.5))
        ax.bar(nvr["buyer_type"], nvr["revenue"],
               color=["#2ecc71", "#3498db"], edgecolor="white")
        ax.set_ylabel("Revenue ($)")
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        plt.tight_layout()
        st.pyplot(fig)
        plt.close()

st.divider()

# ── Row 3: Purchase trigger levels ───────────────────────────────────────────

st.subheader("Top Purchase-Triggering Levels")
lvl_df = queries.paying_levels(conn, start_str, end_str)
if lvl_df.empty:
    st.info("No payment data linked to levels in this range.")
else:
    fig, ax = plt.subplots(figsize=(12, 3.5))
    diff_colors = {"easy": "#2ecc71", "medium": "#e67e22", "hard": "#e74c3c"}
    bar_colors  = [diff_colors.get(d, "#95a5a6") for d in lvl_df["difficulty"]]
    ax.bar(lvl_df["level_id"].astype(str), lvl_df["purchases"],
           color=bar_colors, edgecolor="white")
    ax.set_xlabel("Level")
    ax.set_ylabel("Purchases")

    from matplotlib.patches import Patch
    legend_items = [Patch(facecolor=c, label=k) for k, c in diff_colors.items()]
    ax.legend(handles=legend_items, fontsize=9)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close()

    st.dataframe(
        lvl_df.rename(columns={
            "level_id": "Level", "difficulty": "Difficulty",
            "purchases": "Purchases", "revenue": "Revenue ($)"
        }),
        hide_index=True, use_container_width=True
    )

# ── Footer ────────────────────────────────────────────────────────────────────

st.divider()
st.caption("Data is synthetic. Built with SQLite + Streamlit + Matplotlib.")
