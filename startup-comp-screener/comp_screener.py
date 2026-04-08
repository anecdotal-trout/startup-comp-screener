"""
Startup Comparable Company Screener
====================================
Screens and ranks startups/companies on key operating and financial metrics.
Useful for:
- VC analysts evaluating deal flow against the market
- Growth/strategy teams benchmarking against competitors
- Anyone trying to answer "how does company X compare?"

Calculates derived metrics (runway, efficiency score, revenue multiples)
and ranks companies on a composite score.
"""

import sqlite3
import pandas as pd
import os

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_data():
    """Load company data into pandas and SQLite."""
    df = pd.read_csv(os.path.join(DATA_DIR, "companies.csv"))
    conn = sqlite3.connect(":memory:")
    df.to_sql("companies", conn, if_exists="replace", index=False)
    return conn, df


# ---------------------------------------------------------------------------
# DERIVED METRICS
# ---------------------------------------------------------------------------

def calculate_derived_metrics(df):
    """Add calculated columns: runway, multiples, efficiency."""
    df = df.copy()

    # Runway in months
    df["runway_months"] = (
        df["cash_on_hand_usd"] / df["burn_rate_monthly_usd"]
    ).round(1)

    # Revenue multiple (valuation / ARR)
    df["revenue_multiple"] = (
        df["valuation_usd"] / df["revenue_arr_usd"]
    ).round(1)

    # Burn multiple (net burn / net new ARR)
    # Approximation: annual burn / (ARR * growth rate)
    annual_burn = df["burn_rate_monthly_usd"] * 12
    net_new_arr = df["revenue_arr_usd"] * df["revenue_growth_yoy_pct"] / 100
    df["burn_multiple"] = (annual_burn / net_new_arr.replace(0, pd.NA)).round(2)

    # Magic number proxy: net new ARR / (annual burn as sales+marketing proxy)
    # Simplified — in practice you'd use actual S&M spend
    df["magic_number"] = (net_new_arr / annual_burn).round(2)

    # Hype ratio: valuation per employee
    df["valuation_per_employee"] = (
        df["valuation_usd"] / df["employees"]
    ).round(0)

    # Efficiency score: revenue * gross margin / burn
    df["efficiency_score"] = (
        (df["revenue_arr_usd"] * df["gross_margin_pct"] / 100)
        / (df["burn_rate_monthly_usd"] * 12)
    ).round(2)

    return df


# ---------------------------------------------------------------------------
# COMPOSITE SCORING
# ---------------------------------------------------------------------------

def score_companies(df):
    """
    Rank companies on a composite score using normalised percentile ranks.
    Weights reflect what matters for a growth-stage VC evaluation:
    - Revenue growth (25%)
    - Gross margin (15%)
    - Net revenue retention (20%)
    - Efficiency score (20%)
    - Runway (10%)
    - Payback period (10%, inverted — lower is better)
    """
    df = df.copy()
    weights = {
        "revenue_growth_yoy_pct": 0.25,
        "gross_margin_pct": 0.15,
        "nrr_pct": 0.20,
        "efficiency_score": 0.20,
        "runway_months": 0.10,
    }

    # Percentile rank each metric (0-100)
    for col, weight in weights.items():
        df[f"{col}_rank"] = df[col].rank(pct=True) * 100

    # Payback: lower is better, so invert
    df["payback_rank"] = (1 - df["payback_months"].rank(pct=True)) * 100

    # Weighted composite
    df["composite_score"] = (
        sum(df[f"{col}_rank"] * w for col, w in weights.items())
        + df["payback_rank"] * 0.10
    ).round(1)

    return df.sort_values("composite_score", ascending=False)


# ---------------------------------------------------------------------------
# SQL QUERIES
# ---------------------------------------------------------------------------

SECTOR_BENCHMARKS_SQL = """
    SELECT
        sector,
        COUNT(*)                                                AS companies,
        ROUND(AVG(revenue_arr_usd / 1e6), 1)                   AS avg_arr_mm,
        ROUND(AVG(revenue_growth_yoy_pct), 0)                   AS avg_growth_pct,
        ROUND(AVG(gross_margin_pct), 0)                         AS avg_gm_pct,
        ROUND(AVG(nrr_pct), 0)                                  AS avg_nrr_pct,
        ROUND(AVG(CAST(valuation_usd AS REAL) / revenue_arr_usd), 1)
                                                                AS avg_rev_multiple
    FROM companies
    GROUP BY sector
    ORDER BY avg_growth_pct DESC
"""

STAGE_COMPARISON_SQL = """
    SELECT
        stage,
        COUNT(*)                                                AS companies,
        ROUND(AVG(revenue_arr_usd / 1e6), 1)                   AS avg_arr_mm,
        ROUND(AVG(last_round_usd / 1e6), 0)                    AS avg_round_mm,
        ROUND(AVG(employees), 0)                                AS avg_headcount,
        ROUND(AVG(burn_rate_monthly_usd / 1e6), 1)             AS avg_monthly_burn_mm
    FROM companies
    GROUP BY stage
    ORDER BY avg_arr_mm DESC
"""


# ---------------------------------------------------------------------------
# REPORT
# ---------------------------------------------------------------------------

def print_section(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}")


def main():
    conn, raw_df = load_data()
    df = calculate_derived_metrics(raw_df)
    df = score_companies(df)

    print("\n" + "="*80)
    print("  STARTUP COMPARABLE COMPANY SCREENER")
    print("="*80)

    # --- Ranked Leaderboard ---
    print_section("COMPOSITE RANKING")
    leaderboard_cols = [
        "company", "sector", "stage", "composite_score",
        "revenue_growth_yoy_pct", "gross_margin_pct", "nrr_pct",
        "efficiency_score", "runway_months"
    ]
    print(df[leaderboard_cols].to_string(index=False))

    # --- Key Multiples ---
    print_section("VALUATION & EFFICIENCY METRICS")
    multiples_cols = [
        "company", "valuation_usd", "revenue_arr_usd",
        "revenue_multiple", "burn_multiple", "magic_number",
        "valuation_per_employee"
    ]
    fmt_df = df[multiples_cols].copy()
    fmt_df["valuation_usd"] = fmt_df["valuation_usd"].apply(lambda x: f"${x/1e9:.1f}B")
    fmt_df["revenue_arr_usd"] = fmt_df["revenue_arr_usd"].apply(lambda x: f"${x/1e6:.0f}M")
    fmt_df["valuation_per_employee"] = fmt_df["valuation_per_employee"].apply(lambda x: f"${x/1e6:.1f}M")
    print(fmt_df.to_string(index=False))

    # --- Sector Benchmarks ---
    print_section("SECTOR BENCHMARKS")
    sector_df = pd.read_sql(SECTOR_BENCHMARKS_SQL, conn)
    print(sector_df.to_string(index=False))

    # --- Stage Comparison ---
    print_section("STAGE COMPARISON")
    stage_df = pd.read_sql(STAGE_COMPARISON_SQL, conn)
    print(stage_df.to_string(index=False))

    # --- Outlier Analysis ---
    print_section("NOTABLE OUTLIERS")
    fastest = df.nlargest(3, "revenue_growth_yoy_pct")[["company", "revenue_growth_yoy_pct"]]
    most_efficient = df.nlargest(3, "efficiency_score")[["company", "efficiency_score"]]
    highest_nrr = df.nlargest(3, "nrr_pct")[["company", "nrr_pct"]]
    shortest_payback = df.nsmallest(3, "payback_months")[["company", "payback_months"]]

    print("\n  Fastest growing:")
    for _, r in fastest.iterrows():
        print(f"    {r['company']:20s}  {r['revenue_growth_yoy_pct']:.0f}% YoY")
    print("\n  Most capital efficient:")
    for _, r in most_efficient.iterrows():
        print(f"    {r['company']:20s}  {r['efficiency_score']:.2f}x")
    print("\n  Highest net retention:")
    for _, r in highest_nrr.iterrows():
        print(f"    {r['company']:20s}  {r['nrr_pct']:.0f}%")
    print("\n  Fastest payback:")
    for _, r in shortest_payback.iterrows():
        print(f"    {r['company']:20s}  {r['payback_months']} months")

    conn.close()
    print(f"\n{'='*80}")
    print("  Screening complete.")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    main()
