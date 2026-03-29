"""
Analytics query library.

All functions accept a sqlite3.Connection and optional date range parameters,
and return a pandas DataFrame. Keeping SQL separate from the Streamlit app
makes it straightforward to unit-test queries or point them at a different DB.
"""

import sqlite3
import textwrap
import numpy as np
import pandas as pd
from pathlib import Path

DB_PATH = "game_analytics.db"

# ── Connection helper ──────────────────────────────────────────────────────────

def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


# ── Seed data (called once by app.py on startup) ───────────────────────────────

def seed_database(conn: sqlite3.Connection, n_users: int = 2_000, seed: int = 42):
    """
    Populates the database with synthetic users and payments if the users table
    is empty. Safe to call multiple times.
    """
    cur = conn.cursor()
    if cur.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        return  # already seeded

    rng = np.random.default_rng(seed)

    countries = {
        "US": 0.28, "TR": 0.15, "DE": 0.10, "BR": 0.10,
        "GB": 0.08, "FR": 0.07, "IN": 0.07, "JP": 0.05,
        "MX": 0.05, "PL": 0.05,
    }
    country_list  = list(countries.keys())
    country_probs = list(countries.values())
    devices = ["ios", "android"]

    base_date = pd.Timestamp("2024-07-01")
    products  = ["extra_lives", "hint_pack", "no_ads", "level_skip", "coin_pack"]
    prices    = [0.99, 1.99, 2.99, 4.99, 9.99]

    # ── Users ──
    user_rows = []
    for i in range(1, n_users + 1):
        country = rng.choice(country_list, p=country_probs)
        device  = rng.choice(devices, p=[0.45, 0.55])
        days    = int(rng.integers(0, 270))
        reg_dt  = (base_date + pd.Timedelta(days=days)).date().isoformat()
        user_rows.append((f"U{i:05d}", country, device, reg_dt))

    cur.executemany("INSERT OR IGNORE INTO users VALUES (?,?,?,?)", user_rows)

    # ── Payments ──
    # ~35% of users make at least one purchase; heavy spenders make more
    payment_rows = []
    for uid, country, _, reg_dt in user_rows:
        if rng.random() > 0.35:
            continue
        n_purchases = int(rng.integers(1, 8))
        reg_ts = pd.Timestamp(reg_dt)
        for _ in range(n_purchases):
            days_after = int(rng.integers(0, 270))
            pay_dt = (reg_ts + pd.Timedelta(days=days_after)).date().isoformat()
            product = rng.choice(products)
            amount  = float(rng.choice(prices))
            level   = int(rng.integers(1, 51))
            payment_rows.append((uid, amount, pay_dt, level, product))

    cur.executemany(
        "INSERT INTO payments (user_id, amount_usd, payment_dt, level_id, product) VALUES (?,?,?,?,?)",
        payment_rows,
    )
    conn.commit()
    print(f"[DB] Seeded {n_users} users, {len(payment_rows)} payments")


# ── Analytics queries ─────────────────────────────────────────────────────────

def retention_rate(conn: sqlite3.Connection, start: str, end: str) -> pd.DataFrame:
    """
    30-day paying retention: what share of registered users made a payment
    within the selected date window?
    """
    sql = """
        SELECT
            COUNT(DISTINCT p.user_id)  AS paying_users,
            COUNT(DISTINCT u.user_id)  AS total_users,
            ROUND(
                100.0 * COUNT(DISTINCT p.user_id) / COUNT(DISTINCT u.user_id),
                2
            ) AS retention_pct
        FROM users u
        LEFT JOIN payments p
            ON p.user_id = u.user_id
            AND p.payment_dt BETWEEN :start AND :end
        WHERE u.registration_dt <= :end
    """
    return pd.read_sql(textwrap.dedent(sql), conn, params={"start": start, "end": end})


def arpu_by_country(conn: sqlite3.Connection, start: str, end: str) -> pd.DataFrame:
    """Average revenue per user, broken down by country."""
    sql = """
        SELECT
            u.country,
            COUNT(DISTINCT u.user_id)            AS total_users,
            COALESCE(SUM(p.amount_usd), 0)        AS total_revenue,
            ROUND(
                COALESCE(SUM(p.amount_usd), 0) /
                COUNT(DISTINCT u.user_id),
                2
            ) AS arpu
        FROM users u
        LEFT JOIN payments p
            ON p.user_id = u.user_id
            AND p.payment_dt BETWEEN :start AND :end
        GROUP BY u.country
        ORDER BY arpu DESC
    """
    return pd.read_sql(textwrap.dedent(sql), conn, params={"start": start, "end": end})


def revenue_over_time(conn: sqlite3.Connection, start: str, end: str) -> pd.DataFrame:
    """Daily revenue totals within the selected period."""
    sql = """
        SELECT
            payment_dt         AS date,
            SUM(amount_usd)    AS revenue,
            COUNT(payment_id)  AS transactions,
            COUNT(DISTINCT user_id) AS unique_buyers
        FROM payments
        WHERE payment_dt BETWEEN :start AND :end
        GROUP BY payment_dt
        ORDER BY payment_dt
    """
    df = pd.read_sql(textwrap.dedent(sql), conn, params={"start": start, "end": end})
    df["date"] = pd.to_datetime(df["date"])
    return df


def top_products(conn: sqlite3.Connection, start: str, end: str) -> pd.DataFrame:
    """Revenue and transaction count by product SKU."""
    sql = """
        SELECT
            product,
            COUNT(payment_id)       AS transactions,
            ROUND(SUM(amount_usd), 2) AS revenue,
            ROUND(AVG(amount_usd), 2) AS avg_price
        FROM payments
        WHERE payment_dt BETWEEN :start AND :end
        GROUP BY product
        ORDER BY revenue DESC
    """
    return pd.read_sql(textwrap.dedent(sql), conn, params={"start": start, "end": end})


def revenue_by_device(conn: sqlite3.Connection, start: str, end: str) -> pd.DataFrame:
    """ARPU split by device platform."""
    sql = """
        SELECT
            u.device_type,
            COUNT(DISTINCT u.user_id)             AS users,
            ROUND(COALESCE(SUM(p.amount_usd),0), 2) AS revenue,
            ROUND(
                COALESCE(SUM(p.amount_usd),0) /
                COUNT(DISTINCT u.user_id),
                2
            ) AS arpu
        FROM users u
        LEFT JOIN payments p
            ON p.user_id = u.user_id
            AND p.payment_dt BETWEEN :start AND :end
        GROUP BY u.device_type
        ORDER BY arpu DESC
    """
    return pd.read_sql(textwrap.dedent(sql), conn, params={"start": start, "end": end})


def paying_levels(conn: sqlite3.Connection, start: str, end: str) -> pd.DataFrame:
    """Which game levels trigger the most purchases?"""
    sql = """
        SELECT
            p.level_id,
            l.difficulty,
            COUNT(p.payment_id)        AS purchases,
            ROUND(SUM(p.amount_usd),2) AS revenue
        FROM payments p
        JOIN levels l ON l.level_id = p.level_id
        WHERE p.payment_dt BETWEEN :start AND :end
        GROUP BY p.level_id, l.difficulty
        ORDER BY purchases DESC
        LIMIT 15
    """
    return pd.read_sql(textwrap.dedent(sql), conn, params={"start": start, "end": end})


def new_vs_returning(conn: sqlite3.Connection, start: str, end: str) -> pd.DataFrame:
    """
    Splits revenue between new buyers (first purchase ever in the window)
    and returning buyers (had a purchase before the window start).
    """
    sql = """
        WITH first_purchase AS (
            SELECT user_id, MIN(payment_dt) AS first_dt
            FROM payments
            GROUP BY user_id
        )
        SELECT
            CASE
                WHEN fp.first_dt BETWEEN :start AND :end THEN 'New'
                ELSE 'Returning'
            END AS buyer_type,
            COUNT(DISTINCT p.user_id)        AS buyers,
            ROUND(SUM(p.amount_usd), 2)      AS revenue
        FROM payments p
        JOIN first_purchase fp ON fp.user_id = p.user_id
        WHERE p.payment_dt BETWEEN :start AND :end
        GROUP BY buyer_type
    """
    return pd.read_sql(textwrap.dedent(sql), conn, params={"start": start, "end": end})
