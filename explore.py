"""Draw exploratory charts used to choose the business questions.

Saves PNG files to ``figures/explore/``.
"""

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import pandas as pd

DATA = pathlib.Path(__file__).parent / "data" / "northwind.xlsx"
OUT = pathlib.Path(__file__).parent / "figures" / "explore"

BLUE, ORANGE, RED, GRAY = "#2a78d6", "#eb6834", "#e34948", "#8a8984"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def style():
    """Set the shared matplotlib style for the exploratory charts.

    Args:
        None.

    Returns:
        None. Updates ``matplotlib.rcParams`` globally.
    """
    plt.rcParams.update({
        "figure.facecolor": "#fcfcfb", "axes.facecolor": "#fcfcfb",
        "axes.edgecolor": GRID, "axes.labelcolor": INK2,
        "axes.titlesize": 13, "axes.titleweight": "bold",
        "axes.titlecolor": INK, "axes.titlelocation": "left",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
        "xtick.color": INK2, "ytick.color": INK2,
        "font.size": 10, "legend.frameon": False,
    })


def load():
    """Load the workbook and join order lines with lookup tables.

    Args:
        None.

    Returns:
        tuple: Three elements:
            - pandas.DataFrame: Order lines with ``Revenue``,
              ``ListValue``, ``ProductName``, ``CategoryName``,
              ``Name`` (employee) and ``Shipper``.
            - pandas.DataFrame: The Orders sheet.
            - pandas.DataFrame: Products with category names.
    """
    x = pd.read_excel(DATA, sheet_name=None)
    orders = x["Orders"]
    lines = x["Orders Details"].copy()
    lines["Discount"] = lines["Discount"].round(2)
    lines["Revenue"] = lines.UnitPrice * lines.Quantity * (1 - lines.Discount)
    lines["ListValue"] = lines.UnitPrice * lines.Quantity
    products = x["Product"].merge(x["Categories"][["CategoryID", "CategoryName"]])
    lines = (lines.merge(orders, on="OrderID")
                  .merge(products[["ProductID", "ProductName", "CategoryName"]]))
    emp = x["Employees"]
    emp["Name"] = emp.FirstName + " " + emp.LastName
    lines = lines.merge(emp[["EmployeeID", "Name"]])
    lines = lines.merge(x["Shippers"].rename(
        columns={"ShipperID": "ShipVia", "CompanyName": "Shipper"})[["ShipVia", "Shipper"]])
    return lines, orders, products


def same_window(df):
    """Keep Jan–Apr rows of 1997 and 1998 and label the period.

    Args:
        df (pandas.DataFrame): Rows with an ``OrderDate`` column.

    Returns:
        pandas.DataFrame: Filtered rows with a ``Period`` column such
        as ``"1997 Jan–Apr"``.
    """
    m = df.OrderDate.dt.month <= 4
    y = df.OrderDate.dt.year
    return df[m & y.isin([1997, 1998])].assign(Period=y.astype(str) + " Jan–Apr")


def save(fig, name):
    """Save a figure as PNG in the exploration folder and close it.

    Args:
        fig (matplotlib.figure.Figure): Figure to save.
        name (str): File name inside ``figures/explore/``.

    Returns:
        None.
    """
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=150)
    plt.close(fig)


def monthly_revenue(lines):
    """Chart total revenue per month, marking partial months.

    Args:
        lines (pandas.DataFrame): Order lines from ``load``.

    Returns:
        None. Saves ``01_monthly_revenue.png``.
    """
    s = lines.groupby(lines.OrderDate.dt.to_period("M")).Revenue.sum()
    fig, ax = plt.subplots(figsize=(9, 4))
    x = s.index.to_timestamp()
    ax.plot(x, s.values / 1000, color=BLUE, lw=2, marker="o", ms=4)
    for p in (s.index[0], s.index[-1]):
        ax.annotate("partial month", (p.to_timestamp(), s[p] / 1000),
                    textcoords="offset points", xytext=(0, 10),
                    ha="center", color=INK2, fontsize=8)
    ax.set_title("Monthly revenue, Jul 1996 – May 1998")
    ax.set_ylabel("Revenue (thousand $)")
    save(fig, "01_monthly_revenue.png")


def country_growth(lines):
    """Chart revenue by ship-to country, Jan–Apr 1997 vs 1998.

    Args:
        lines (pandas.DataFrame): Order lines from ``load``.

    Returns:
        None. Saves ``02_country_growth.png``.
    """
    w = same_window(lines)
    t = w.pivot_table(index="ShipCountry", columns="Period",
                      values="Revenue", aggfunc="sum", fill_value=0)
    t = t.sort_values("1998 Jan–Apr")
    fig, ax = plt.subplots(figsize=(9, 7))
    y = range(len(t))
    ax.barh([i + 0.2 for i in y], t.iloc[:, 0] / 1000, 0.4, color=GRAY, label=t.columns[0])
    ax.barh([i - 0.2 for i in y], t.iloc[:, 1] / 1000, 0.4, color=BLUE, label=t.columns[1])
    ax.set_yticks(list(y), t.index)
    ax.set_xlabel("Revenue (thousand $)")
    ax.set_title("Revenue by country, same four months in 1997 vs 1998")
    ax.legend(loc="lower right")
    ax.grid(axis="y", visible=False)
    save(fig, "02_country_growth.png")


def customer_concentration(lines):
    """Chart cumulative revenue share by customer rank.

    Args:
        lines (pandas.DataFrame): Order lines from ``load``.

    Returns:
        None. Saves ``03_customer_concentration.png``.
    """
    c = lines.groupby("CustomerID").Revenue.sum()
    c = c.sort_values(ascending=False)
    cum = c.cumsum() / c.sum() * 100
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(range(1, len(cum) + 1), cum.values, color=BLUE, lw=2)
    for k in (10, 20):
        ax.axvline(k, color=GRAY, lw=1, ls="--")
        ax.annotate(f"top {k}: {cum.iloc[k - 1]:.0f}%", (k, cum.iloc[k - 1]),
                    textcoords="offset points", xytext=(6, -14), color=INK)
    ax.set_title("Customer concentration: cumulative share of revenue")
    ax.set_xlabel("Customers ranked by revenue")
    ax.set_ylabel("Cumulative share of revenue")
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())
    save(fig, "03_customer_concentration.png")


def customer_recency(lines, orders):
    """Chart customer revenue against days since last order.

    Customers above median revenue with no order in 120+ days are
    highlighted.

    Args:
        lines (pandas.DataFrame): Order lines from ``load``.
        orders (pandas.DataFrame): Orders sheet; its latest
            ``OrderDate`` is the reference date.

    Returns:
        None. Saves ``04_customer_recency.png``.
    """
    end = orders.OrderDate.max()
    g = lines.groupby("CustomerID").agg(Revenue=("Revenue", "sum"),
                                         Last=("OrderDate", "max"))
    g["DaysSince"] = (end - g.Last).dt.days
    fig, ax = plt.subplots(figsize=(8, 4.5))
    risky = (g.DaysSince > 120) & (g.Revenue > g.Revenue.median())
    ax.scatter(g.DaysSince[~risky], g.Revenue[~risky] / 1000, s=30, color=BLUE,
               label="Other customers")
    ax.scatter(g.DaysSince[risky], g.Revenue[risky] / 1000, s=40, color=ORANGE,
               label="Above-median revenue, no order in 120+ days")
    for cid, r in g[risky].iterrows():
        ax.annotate(cid, (r.DaysSince, r.Revenue / 1000), fontsize=7,
                    textcoords="offset points", xytext=(4, 3), color=INK2)
    ax.set_title("Customer value vs. days since last order")
    ax.set_xlabel(f"Days since last order (as of {end:%d %b %Y})")
    ax.set_ylabel("Lifetime revenue (thousand $)")
    ax.legend(loc="upper right")
    save(fig, "04_customer_recency.png")


def discounts(lines):
    """Chart mean units per order line by discount band.

    Args:
        lines (pandas.DataFrame): Order lines from ``load``.

    Returns:
        None. Saves ``05_discounts.png``.
    """
    b = pd.cut(lines.Discount, [-0.001, 0, 0.07, 0.10, 0.15, 0.20, 0.25],
               labels=["0%", "1–6%", "10%", "15%", "20%", "25%"])
    g = lines.groupby(b, observed=True).agg(Qty=("Quantity", "mean"),
                                             N=("Quantity", "size"))
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.bar(g.index.astype(str), g.Qty, color=BLUE, width=0.6)
    for i, (q, n) in enumerate(zip(g.Qty, g.N)):
        ax.text(i, q + 0.5, f"{q:.1f}\n(n={n})", ha="center", va="bottom",
                fontsize=8, color=INK2)
    ax.set_title("Average quantity per order line by discount level")
    ax.set_xlabel("Discount")
    ax.set_ylabel("Units per order line")
    ax.set_ylim(0, g.Qty.max() * 1.25)
    ax.grid(axis="x", visible=False)
    given = (lines.ListValue - lines.Revenue).sum()
    ax.text(0.99, 0.98, f"Total discount given: ${given:,.0f}",
            transform=ax.transAxes, ha="right", va="top", color=INK)
    save(fig, "05_discounts.png")


def shipping(orders, lines):
    """Chart late-shipment rates by shipper and by employee.

    An order is late if shipped after its required date; unshipped
    orders are excluded.

    Args:
        orders (pandas.DataFrame): Orders sheet.
        lines (pandas.DataFrame): Order lines from ``load``, used to
            look up each order's shipper and employee name.

    Returns:
        None. Saves ``06_late_shipments.png``.
    """
    o = orders.copy()
    o["Late"] = o.ShippedDate > o.RequiredDate
    o["DaysToShip"] = (o.ShippedDate - o.OrderDate).dt.days
    names = lines.drop_duplicates("OrderID").set_index("OrderID")
    o["Shipper"] = o.OrderID.map(names.Shipper)
    o["Employee"] = o.OrderID.map(names.Name)
    shipped = o[o.ShippedDate.notna()]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, col in zip(axes, ["Shipper", "Employee"]):
        r = shipped.groupby(col).Late.mean().sort_values() * 100
        ax.barh(r.index, r.values, color=BLUE, height=0.6)
        for i, v in enumerate(r.values):
            ax.text(v + 0.2, i, f"{v:.1f}%", va="center", fontsize=8, color=INK2)
        ax.set_title(f"Late shipments by {col.lower()}")
        ax.set_xlabel("Share of shipped orders that were late")
        ax.xaxis.set_major_formatter(mtick.PercentFormatter())
        ax.grid(axis="y", visible=False)
    save(fig, "06_late_shipments.png")


def employees(lines):
    """Chart revenue per employee, Jan–Apr 1997 vs 1998.

    Args:
        lines (pandas.DataFrame): Order lines from ``load``.

    Returns:
        None. Saves ``07_employees.png``.
    """
    w = same_window(lines)
    t = w.pivot_table(index="Name", columns="Period", values="Revenue",
                      aggfunc="sum", fill_value=0).sort_values("1998 Jan–Apr")
    fig, ax = plt.subplots(figsize=(9, 5))
    y = range(len(t))
    ax.barh([i + 0.2 for i in y], t.iloc[:, 0] / 1000, 0.4, color=GRAY, label=t.columns[0])
    ax.barh([i - 0.2 for i in y], t.iloc[:, 1] / 1000, 0.4, color=BLUE, label=t.columns[1])
    ax.set_yticks(list(y), t.index)
    ax.set_xlabel("Revenue (thousand $)")
    ax.set_title("Revenue by sales employee, Jan–Apr 1997 vs 1998")
    ax.legend(loc="lower right")
    ax.grid(axis="y", visible=False)
    save(fig, "07_employees.png")


def categories(lines):
    """Chart revenue growth by category, Jan–Apr 1998 vs 1997.

    Args:
        lines (pandas.DataFrame): Order lines from ``load``.

    Returns:
        None. Saves ``08_category_growth.png``.
    """
    w = same_window(lines)
    t = w.pivot_table(index="CategoryName", columns="Period", values="Revenue",
                      aggfunc="sum").sort_values("1998 Jan–Apr")
    growth = (t.iloc[:, 1] / t.iloc[:, 0] - 1) * 100
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(growth.index, growth.values, color=BLUE, height=0.6)
    for i, v in enumerate(growth.values):
        ax.text(v + 2, i, f"{v:+.0f}%", va="center", fontsize=8, color=INK2)
    ax.set_title("Revenue growth by category, Jan–Apr 1998 vs 1997")
    ax.set_xlabel("Change in revenue")
    ax.xaxis.set_major_formatter(mtick.PercentFormatter())
    ax.grid(axis="y", visible=False)
    save(fig, "08_category_growth.png")


def stock(lines, products):
    """Chart stock on hand against recent demand for active products.

    Recent demand is units sold in the 90 days before the last order.

    Args:
        lines (pandas.DataFrame): Order lines from ``load``.
        products (pandas.DataFrame): Products from ``load``;
            discontinued products are skipped.

    Returns:
        None. Saves ``09_stock_vs_demand.png``.
    """
    end = lines.OrderDate.max()
    recent = lines[lines.OrderDate > end - pd.Timedelta(days=90)]
    demand = recent.groupby("ProductID").Quantity.sum()
    p = products[~products.Discontinued].set_index("ProductID")
    p["Demand90"] = demand.reindex(p.index).fillna(0)
    low = p.UnitsInStock + p.UnitsOnOrder <= p.ReorderLevel
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.scatter(p.Demand90[~low], p.UnitsInStock[~low], s=30, color=BLUE,
               label="Stock + on order above reorder level")
    ax.scatter(p.Demand90[low], p.UnitsInStock[low], s=40, color=RED,
               label="Stock + on order at or below reorder level")
    for _, r in p[low].iterrows():
        ax.annotate(r.ProductName, (r.Demand90, r.UnitsInStock), fontsize=7,
                    textcoords="offset points", xytext=(4, 3), color=INK2)
    ax.set_title("Active products: stock vs. recent demand")
    ax.set_xlabel("Units sold in last 90 days")
    ax.set_ylabel("Units in stock")
    ax.legend(loc="upper right")
    save(fig, "09_stock_vs_demand.png")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    style()
    lines, orders, products = load()
    monthly_revenue(lines)
    country_growth(lines)
    customer_concentration(lines)
    customer_recency(lines, orders)
    discounts(lines)
    shipping(orders, lines)
    employees(lines)
    categories(lines)
    stock(lines, products)
    print("Saved charts to", OUT)
