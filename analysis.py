"""Compute the numbers and tables for the four business questions.

Writes CSV tables and ``metrics.json`` to ``results/``.
"""

import json

import numpy as np
import pandas as pd

from northwind import (BASE_YEAR, CURRENT_YEAR, RESULTS, load_tables,
                       order_lines, window, window_label)

MIN_LINES_PER_LEVEL = 10
DISCOUNT_CAP = 0.10
REORDER_DAYS = 90


def growth_drivers(lines):
    """Decompose Jan–Apr revenue growth into its drivers.

    Revenue is split into active customers x orders per customer x
    average order value. Average order value is split further into a
    quantity-weighted price index over products sold in both windows
    and a volume & mix remainder.

    Args:
        lines (pandas.DataFrame): Order lines from ``order_lines``.

    Returns:
        tuple: Four elements:
            - pandas.DataFrame: Revenue, customers, orders, orders per
              customer and average order value per window.
            - pandas.DataFrame: Ratio, % change and share of log growth
              per driver.
            - pandas.DataFrame: Customers per quarter of first recorded
              order.
            - dict: Headline numbers for the webpage.
    """
    base, cur = window(lines, BASE_YEAR), window(lines, CURRENT_YEAR)
    stats = {}
    for year, w in ((BASE_YEAR, base), (CURRENT_YEAR, cur)):
        order_value = w.groupby("OrderID")["Revenue"].sum()
        customers = w["CustomerID"].nunique()
        stats[year] = {
            "revenue": w["Revenue"].sum(),
            "active_customers": customers,
            "orders": len(order_value),
            "orders_per_customer": len(order_value) / customers,
            "avg_order_value": order_value.mean(),
        }

    # Price index: this year's basket valued at this year's vs last year's
    # quantity-weighted average unit price. Only products sold in both
    # windows have a comparable price; the rest are excluded from the index
    # and their effect ends up in the volume & mix factor.
    p0 = base.groupby("ProductID")["ListValue"].sum() / base.groupby("ProductID")["Quantity"].sum()
    p1 = cur.groupby("ProductID")["ListValue"].sum() / cur.groupby("ProductID")["Quantity"].sum()
    q1 = cur.groupby("ProductID")["Quantity"].sum()
    common = p0.index.intersection(p1.index)
    price_ratio = (p1[common] * q1[common]).sum() / (p0[common] * q1[common]).sum()
    no_base_price = p1.index.difference(p0.index)

    s0, s1 = stats[BASE_YEAR], stats[CURRENT_YEAR]
    aov_ratio = s1["avg_order_value"] / s0["avg_order_value"]
    drivers = pd.DataFrame([
        ("Active customers", s1["active_customers"] / s0["active_customers"], "level1"),
        ("Orders per customer", s1["orders_per_customer"] / s0["orders_per_customer"], "level1"),
        ("Average order value", aov_ratio, "level1"),
        ("of which: unit prices", price_ratio, "level2"),
        ("of which: volume & mix per order", aov_ratio / price_ratio, "level2"),
    ], columns=["driver", "ratio", "level"])
    drivers["change_pct"] = (drivers["ratio"] - 1) * 100
    # The three level-1 ratios multiply exactly to the revenue ratio, so their
    # logs add up to log(revenue ratio); each log's share is its contribution.
    level1 = drivers[drivers["level"] == "level1"]
    drivers["share_of_log_growth_pct"] = np.where(
        drivers["level"] == "level1",
        np.log(drivers["ratio"]) / np.log(level1["ratio"]).sum() * 100, np.nan)

    summary = pd.DataFrame(stats).T
    summary.index = [window_label(y) for y in summary.index]

    first_order = lines.groupby("CustomerID")["OrderDate"].min()
    new_by_quarter = (first_order.dt.to_period("Q").value_counts().sort_index()
                      .reindex(pd.period_range("1996Q3", "1998Q2", freq="Q"),
                               fill_value=0))
    new_customers = pd.DataFrame({"quarter": new_by_quarter.index.astype(str),
                                  "new_customers": new_by_quarter.values})

    base_custs, cur_custs = set(base["CustomerID"]), set(cur["CustomerID"])
    metrics = {
        "revenue_base": s0["revenue"],
        "revenue_current": s1["revenue"],
        "revenue_growth_pct": (s1["revenue"] / s0["revenue"] - 1) * 100,
        "customers_base": s0["active_customers"],
        "customers_current": s1["active_customers"],
        "customers_retained": len(base_custs & cur_custs),
        "customers_first_recorded_1998": int((first_order >= f"{CURRENT_YEAR}-01-01").sum()),
        "customers_first_recorded_1997H2_onward": int((first_order >= "1997-07-01").sum()),
        "revenue_from_retained_pct":
            cur.loc[cur["CustomerID"].isin(base_custs), "Revenue"].sum() / s1["revenue"] * 100,
        "price_change_pct": (price_ratio - 1) * 100,
        "price_products_compared": len(common),
        "price_products_excluded": len(no_base_price),
        "price_excluded_revenue_share_pct":
            cur.loc[cur["ProductID"].isin(no_base_price), "Revenue"].sum() / s1["revenue"] * 100,
        "opc_change_pct": drivers.loc[1, "change_pct"],
        "customers_share_of_growth_pct": drivers.loc[0, "share_of_log_growth_pct"],
        "opc_share_of_growth_pct": drivers.loc[1, "share_of_log_growth_pct"],
        "aov_share_of_growth_pct": drivers.loc[2, "share_of_log_growth_pct"],
    }
    return summary, drivers, new_customers, metrics


def markets(lines):
    """Compare revenue by customer country and estimate revenue at risk.

    Args:
        lines (pandas.DataFrame): Order lines from ``order_lines``.

    Returns:
        tuple: Three elements:
            - pandas.DataFrame: Per-country revenue in both windows,
              change, customer counts and full base-year revenue,
              sorted by change.
            - pandas.DataFrame: Per-account revenue and last order date
              in countries whose revenue fell, sorted by change.
            - dict: Headline numbers, including annual revenue at risk
              and the account split of growth in the top 3 countries.
    """
    base, cur = window(lines, BASE_YEAR), window(lines, CURRENT_YEAR)
    full_base_year = lines[lines["OrderDate"].dt.year == BASE_YEAR]
    t = pd.DataFrame({
        "revenue_base": base.groupby("Country")["Revenue"].sum(),
        "revenue_current": cur.groupby("Country")["Revenue"].sum(),
    }).fillna(0)
    t["change"] = t["revenue_current"] - t["revenue_base"]
    t["change_pct"] = np.where(t["revenue_base"] > 0,
                               t["change"] / t["revenue_base"] * 100, np.nan)
    t["customers_on_file"] = lines.drop_duplicates("CustomerID").groupby("Country").size()
    t["customers_active_current"] = cur.groupby("Country")["CustomerID"].nunique()
    t["revenue_full_base_year"] = full_base_year.groupby("Country")["Revenue"].sum()
    t = t.fillna({"customers_active_current": 0, "revenue_full_base_year": 0})
    t = t.sort_values("change").reset_index().rename(columns={"index": "Country"})

    declining = t[t["change"] < 0]
    decline_rate = 1 - declining["revenue_current"].sum() / declining["revenue_base"].sum()
    at_risk = declining["revenue_full_base_year"].sum() * decline_rate

    end = lines["OrderDate"].max()
    acc = lines[lines["Country"].isin(declining["Country"])]
    accounts = acc.groupby(["Country", "CompanyName"]).apply(
        lambda g: pd.Series({
            "revenue_base_year": g.loc[g["OrderDate"].dt.year == BASE_YEAR, "Revenue"].sum(),
            "revenue_base_window": window(g, BASE_YEAR)["Revenue"].sum(),
            "revenue_current_window": window(g, CURRENT_YEAR)["Revenue"].sum(),
            "last_order": g["OrderDate"].max().date().isoformat(),
            "days_since_last_order": (end - g["OrderDate"].max()).days,
        }), include_groups=False).reset_index()
    accounts["change"] = accounts["revenue_current_window"] - accounts["revenue_base_window"]
    accounts = accounts.sort_values("change").reset_index(drop=True)

    growth = t["change"].sum()
    top3 = t.nlargest(3, "change")

    # How much of each leading country's growth comes from its largest accounts.
    leaders = []
    for country in top3["Country"]:
        by_cust = (window(lines[lines["Country"] == country], CURRENT_YEAR)
                   .groupby("CompanyName")["Revenue"].sum()
                   .sub(window(lines[lines["Country"] == country], BASE_YEAR)
                        .groupby("CompanyName")["Revenue"].sum(), fill_value=0)
                   .sort_values(ascending=False))
        leaders.append({
            "country": country,
            "growth": by_cust.sum(),
            "top_account": by_cust.index[0],
            "top_account_share_pct": by_cust.iloc[0] / by_cust.sum() * 100,
            "top2_share_pct": by_cust.iloc[:2].sum() / by_cust.sum() * 100,
        })

    metrics = {
        "n_countries": len(t),
        "n_declining": len(declining),
        "declining_countries": declining["Country"].tolist(),
        "declining_share_base_year_pct":
            declining["revenue_full_base_year"].sum() / full_base_year["Revenue"].sum() * 100,
        "declining_decline_rate_pct": decline_rate * 100,
        "revenue_at_risk_annual": at_risk,
        "declining_customers_on_file": int(declining["customers_on_file"].sum()),
        "top3_growth_countries": top3["Country"].tolist(),
        "top3_share_of_growth_pct": top3["change"].sum() / growth * 100,
        "growth_leaders": leaders,
        "biggest_account_drop": accounts.iloc[0][["CompanyName", "Country", "change",
                                                  "last_order"]].to_dict(),
    }
    return t, accounts, metrics


def top_share(revenue_by_customer, share=0.10):
    """Return the revenue share of the largest customers.

    Args:
        revenue_by_customer (pandas.Series): Revenue per customer.
        share (float): Fraction of customers counted as top; the count
            is rounded up to a whole customer.

    Returns:
        tuple: Share of revenue in percent (float), number of top
        customers (int), and total number of customers (int).
    """
    s = revenue_by_customer.sort_values(ascending=False)
    k = int(np.ceil(len(s) * share))
    return s.head(k).sum() / s.sum() * 100, k, len(s)


def concentration(lines):
    """Measure dependence on the largest customers over time.

    Args:
        lines (pandas.DataFrame): Order lines from ``order_lines``.

    Returns:
        tuple: Three elements:
            - pandas.DataFrame: Top-10% and top-3 revenue share for each
              rolling 4-month window.
            - pandas.DataFrame: Ten largest customers by all-time
              revenue, with revenue in both Jan–Apr windows.
            - dict: Headline numbers, including growth of the base
              window's top customers vs all other customers.
    """
    # Rolling 4-month windows keep the period length constant, because
    # shorter periods look more concentrated simply because fewer customers order.
    months = pd.period_range("1996-07", "1998-04", freq="M")
    period = lines["OrderDate"].dt.to_period("M")
    rows = []
    for i in range(3, len(months)):
        span = months[i - 3:i + 1]
        w = lines[period.isin(span)]
        top10, k, n = top_share(w.groupby("CustomerID")["Revenue"].sum())
        top3 = (w.groupby("CustomerID")["Revenue"].sum().nlargest(3).sum()
                / w["Revenue"].sum() * 100)
        rows.append({"window_end": str(span[-1]),
                     "window": f"{span[0].strftime('%b %Y')} – {span[-1].strftime('%b %Y')}",
                     "top10_share_pct": top10, "top3_share_pct": top3,
                     "customers": n, "top10_count": k})
    rolling = pd.DataFrame(rows)

    base, cur = window(lines, BASE_YEAR), window(lines, CURRENT_YEAR)
    rb = base.groupby("CustomerID")["Revenue"].sum()
    rc = cur.groupby("CustomerID")["Revenue"].sum()
    total = lines.groupby(["CustomerID", "CompanyName", "Country"])["Revenue"].sum()
    top = total.sort_values(ascending=False).head(10).reset_index()
    top["share_all_time_pct"] = top["Revenue"] / lines["Revenue"].sum() * 100
    top["revenue_base_window"] = top["CustomerID"].map(rb).fillna(0)
    top["revenue_current_window"] = top["CustomerID"].map(rc).fillna(0)
    top["growth_pct"] = (top["revenue_current_window"] / top["revenue_base_window"] - 1) * 100

    b_share, b_k, b_n = top_share(rb)
    c_share, c_k, c_n = top_share(rc)
    top3_ids = rc.nlargest(3).index
    hanari = lines[lines["CompanyName"] == "Hanari Carnes"]
    metrics = {
        "hanari_first_order": hanari["OrderDate"].min().date().isoformat(),
        "hanari_revenue_base_year": hanari.loc[hanari["OrderDate"].dt.year == BASE_YEAR,
                                               "Revenue"].sum(),
        "hanari_revenue_current_window": window(hanari, CURRENT_YEAR)["Revenue"].sum(),
        "rolling_min_since_1997": rolling.loc[rolling["window_end"] >= "1997-04",
                                              "top10_share_pct"].min(),
        "rolling_max_since_1997": rolling.loc[rolling["window_end"] >= "1997-04",
                                              "top10_share_pct"].max(),
        "top10_share_base_pct": b_share, "top10_count_base": b_k,
        "top10_share_current_pct": c_share, "top10_count_current": c_k,
        "top3_share_current_pct": rc[top3_ids].sum() / rc.sum() * 100,
        "top3_current": top.set_index("CustomerID").reindex(top3_ids)["CompanyName"].tolist(),
        "rolling_first": rolling.iloc[0]["top10_share_pct"],
        "rolling_last": rolling.iloc[-1]["top10_share_pct"],
        "top_customers_growth_pct": (rc[rc.index.isin(rb.nlargest(b_k).index)].sum()
                                     / rb.nlargest(b_k).sum() - 1) * 100,
        "other_customers_growth_pct": (rc[~rc.index.isin(rb.nlargest(b_k).index)].sum()
                                       / rb[~rb.index.isin(rb.nlargest(b_k).index)].sum() - 1) * 100,
    }
    return rolling, top, metrics


def discounts(lines):
    """Relate discounts to order quantity, employees and repeat orders.

    Args:
        lines (pandas.DataFrame): Order lines from ``order_lines``;
            not modified.

    Returns:
        tuple: Three elements:
            - pandas.DataFrame: Mean quantity relative to the same
              product at full price, with 95% CI, for each discount
              level with at least ``MIN_LINES_PER_LEVEL`` lines.
            - pandas.DataFrame: Discount dollars and rates per employee.
            - dict: Headline numbers, including discounts above
              ``DISCOUNT_CAP`` and censoring-adjusted reorder rates
              within ``REORDER_DAYS``.
    """
    lines = lines.copy()
    lines["Discounted"] = lines["Discount"] > 0
    # Compare each line with the same product's average undiscounted quantity,
    # so the result is not driven by which products tend to get discounts.
    baseline = lines[~lines["Discounted"]].groupby("ProductID")["Quantity"].mean()
    lines["RelQty"] = lines["Quantity"] / lines["ProductID"].map(baseline)
    lines = lines.dropna(subset=["RelQty"])

    lvl = lines.groupby("Discount")["RelQty"].agg(["mean", "std", "size"]).reset_index()
    dropped = int(lvl.loc[lvl["size"] < MIN_LINES_PER_LEVEL, "size"].sum())
    lvl = lvl[lvl["size"] >= MIN_LINES_PER_LEVEL].copy()
    lvl["ci95"] = 1.96 * lvl["std"] / np.sqrt(lvl["size"])
    lvl["extra_units_pct"] = (lvl["mean"] - 1) * 100
    lvl["discount_label"] = (lvl["Discount"] * 100).round().astype(int).astype(str) + "%"
    lvl = lvl.rename(columns={"mean": "relative_quantity", "size": "order_lines"})

    # Value-weighted rate: total discount dollars / total list value of the
    # employee's order lines. The unweighted mean of line discounts is kept
    # for comparison.
    emp = lines.groupby("Employee").apply(lambda g: pd.Series({
        "discount_given": (g["ListValue"] - g["Revenue"]).sum(),
        "avg_discount_pct": (g["ListValue"] - g["Revenue"]).sum() / g["ListValue"].sum() * 100,
        "mean_line_discount_pct": g["Discount"].mean() * 100,
        "lines_discounted_pct": g["Discounted"].mean() * 100,
        "lines_over_cap_pct": (g["Discount"] > DISCOUNT_CAP).mean() * 100,
        "revenue": g["Revenue"].sum(),
    }), include_groups=False).sort_values("avg_discount_pct").reset_index()

    # Historical discount dollars above a hypothetical cap, holding quantities
    # fixed. Not a forecast of recoverable revenue.
    over = lines[lines["Discount"] > DISCOUNT_CAP]
    above_cap = (over["ListValue"] * (over["Discount"] - DISCOUNT_CAP)).sum()

    end = lines["OrderDate"].max()
    orders = (lines.groupby("OrderID")
              .agg(CustomerID=("CustomerID", "first"), OrderDate=("OrderDate", "first"),
                   Discounted=("Discounted", "any"))
              .sort_values("OrderDate"))
    orders["next"] = orders.groupby("CustomerID")["OrderDate"].shift(-1)
    # Right-censoring: keep only orders with a full follow-up window
    # before the data ends.
    orders = orders[orders["OrderDate"] <= end - pd.Timedelta(days=REORDER_DAYS)]
    orders["reordered"] = (orders["next"] - orders["OrderDate"]).dt.days <= REORDER_DAYS
    reorder = orders.groupby("Discounted")["reordered"].agg(["mean", "size"])

    discounted_lvls = lvl[lvl["Discount"] > 0]
    metrics = {
        "discount_total": (lines["ListValue"] - lines["Revenue"]).sum(),
        "discount_pct_of_list": (lines["ListValue"] - lines["Revenue"]).sum()
                                / lines["ListValue"].sum() * 100,
        "lines_discounted_pct": lines["Discounted"].mean() * 100,
        "extra_units_min_pct": discounted_lvls["extra_units_pct"].min(),
        "extra_units_max_pct": discounted_lvls["extra_units_pct"].max(),
        "extra_units_5_pct": lvl.loc[lvl["Discount"] == 0.05, "extra_units_pct"].item(),
        "extra_units_25_pct": lvl.loc[lvl["Discount"] == 0.25, "extra_units_pct"].item(),
        "lines_dropped_rare_levels": dropped,
        "discount_above_cap": above_cap,
        "discount_on_lines_over_cap": (over["ListValue"] - over["Revenue"]).sum(),
        "cap_pct": DISCOUNT_CAP * 100,
        "lines_over_cap_pct": (lines["Discount"] > DISCOUNT_CAP).mean() * 100,
        "emp_max": emp.iloc[-1][["Employee", "avg_discount_pct",
                                 "mean_line_discount_pct"]].to_dict(),
        "emp_min": emp.iloc[0][["Employee", "avg_discount_pct"]].to_dict(),
        "reorder_discounted_pct": reorder.loc[True, "mean"] * 100,
        "reorder_full_price_pct": reorder.loc[False, "mean"] * 100,
        "reorder_n_discounted": int(reorder.loc[True, "size"]),
        "reorder_n_full_price": int(reorder.loc[False, "size"]),
        "reorder_last_eligible_date":
            (end - pd.Timedelta(days=REORDER_DAYS)).date().isoformat(),
        "reorder_days": REORDER_DAYS,
    }
    return lvl, emp, metrics


def to_builtin(value):
    """Convert numpy values to JSON-serialisable Python types.

    Args:
        value (Any): Scalar, list, tuple or dict, possibly nested.

    Returns:
        Any: Same structure with tuples as lists, numpy integers as
        ``int`` and floats rounded to 2 decimals; other values are
        unchanged.
    """
    if isinstance(value, dict):
        return {k: to_builtin(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_builtin(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return round(float(value), 2)
    return value


def main():
    """Run all analyses and write the results files.

    Args:
        None.

    Returns:
        None. Writes CSV tables and ``metrics.json`` to ``results/``
        and prints the metrics.
    """
    RESULTS.mkdir(exist_ok=True)
    tables = load_tables()
    lines = order_lines(tables)

    summary, drivers, new_customers, m_growth = growth_drivers(lines)
    countries, accounts, m_markets = markets(lines)
    rolling, top, m_conc = concentration(lines)
    levels, employees, m_disc = discounts(lines)

    outputs = {
        "q1_growth_summary.csv": summary,
        "q1_growth_drivers.csv": drivers,
        "q1_new_customers_by_quarter.csv": new_customers,
        "q2_country_change.csv": countries,
        "q2_accounts_in_declining_countries.csv": accounts,
        "q3_rolling_concentration.csv": rolling,
        "q3_top_customers.csv": top,
        "q4_quantity_by_discount.csv": levels,
        "q4_discount_by_employee.csv": employees,
    }
    for name, df in outputs.items():
        df.to_csv(RESULTS / name, index=(name == "q1_growth_summary.csv"),
                  float_format="%.4f")

    metrics = {
        "data": {
            "first_order": lines["OrderDate"].min().date().isoformat(),
            "last_order": lines["OrderDate"].max().date().isoformat(),
            "orders": int(lines["OrderID"].nunique()),
            "order_lines": len(lines),
            "customers_with_orders": int(lines["CustomerID"].nunique()),
            "total_revenue": lines["Revenue"].sum(),
            "base_window": window_label(BASE_YEAR),
            "current_window": window_label(CURRENT_YEAR),
        },
        "q1": m_growth, "q2": m_markets, "q3": m_conc, "q4": m_disc,
    }
    with open(RESULTS / "metrics.json", "w") as f:
        json.dump(to_builtin(metrics), f, indent=2, ensure_ascii=False)
    print(json.dumps(to_builtin(metrics), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
