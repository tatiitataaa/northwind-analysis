"""Build the analysis webpage ``docs/index.html`` from ``results/``."""

import html
import json

import pandas as pd
import plotly.graph_objects as go

from northwind import RESULTS, SITE

REPO_URL = "https://github.com/tatiitataaa/northwind-analysis"

BLUE, BLUE_LIGHT, RED, GRAY = "#2a78d6", "#86b6ef", "#e34948", "#8a8984"
INK, INK2, INK3, GRID, SURFACE = "#0b0b0b", "#52514e", "#7a7974", "#e4e3df", "#fcfcfb"
FONT = "Inter, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif"


def money(x, k=False):
    """Format a dollar amount.

    Args:
        x (float): Amount in dollars.
        k (bool): If True, show thousands with one decimal, e.g.
            ``$38.0k``.

    Returns:
        str: Formatted amount, e.g. ``$38,043``.
    """
    if k:
        return f"${x / 1000:,.1f}k"
    return f"${x:,.0f}"


def pct(x, sign=False, digits=0):
    """Format a number as a percentage.

    Args:
        x (float): Value already in percent, e.g. 12.5 for 12.5%.
        sign (bool): If True, always show a leading + or -.
        digits (int): Decimal places.

    Returns:
        str: Formatted percentage, e.g. ``+121%``.
    """
    return f"{x:+.{digits}f}%" if sign else f"{x:.{digits}f}%"


def base_layout(fig, title, height=380, **kw):
    """Apply the shared chart style to a Plotly figure.

    Args:
        fig (plotly.graph_objects.Figure): Figure to style; modified
            in place.
        title (str): Chart title.
        height (int): Chart height in pixels.
        **kw: Extra ``fig.update_layout`` arguments, e.g. ``legend``.

    Returns:
        plotly.graph_objects.Figure: The same figure.
    """
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15, color=INK)),
        font=dict(family=FONT, size=12, color=INK2),
        paper_bgcolor=SURFACE, plot_bgcolor=SURFACE, height=height,
        margin=dict(l=10, r=20, t=50, b=40),
        hoverlabel=dict(bgcolor="white", font=dict(family=FONT, color=INK)),
        **kw)
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    return fig


def growth_drivers_fig(drivers, growth_pct):
    """Plot the % change of each revenue growth driver.

    Args:
        drivers (pandas.DataFrame): Contents of
            ``q1_growth_drivers.csv``.
        growth_pct (float): Total revenue growth in percent, shown in
            the title.

    Returns:
        plotly.graph_objects.Figure: Horizontal bar chart.
    """
    d = drivers.iloc[::-1]
    labels = [r.driver.replace("of which: ", "↳ ") for r in d.itertuples()]
    colors = [BLUE if r.level == "level1" else
              (BLUE_LIGHT if r.change_pct >= 0 else RED) for r in d.itertuples()]
    fig = go.Figure(go.Bar(
        x=d["change_pct"], y=labels, orientation="h", marker_color=colors,
        text=[pct(v, sign=True) for v in d["change_pct"]], textposition="outside",
        cliponaxis=False,
        hovertemplate="%{y}: %{x:+.1f}%<br>ratio 1998/1997: %{customdata:.2f}<extra></extra>",
        customdata=d["ratio"]))
    base_layout(fig, f"Revenue grew {pct(growth_pct, sign=True)}: what changed, Jan–Apr 1997 → 1998",
                height=330)
    fig.update_xaxes(title="Change vs. Jan–Apr 1997", ticksuffix="%", range=[-30, 85])
    fig.update_yaxes(showgrid=False, ticksuffix="  ")
    return fig


def new_customers_fig(new):
    """Plot customers by quarter of first recorded order.

    Args:
        new (pandas.DataFrame): Contents of
            ``q1_new_customers_by_quarter.csv``.

    Returns:
        plotly.graph_objects.Figure: Bar chart.
    """
    labels = new["quarter"].str.replace("Q", " Q")
    notes = {"1996 Q3": "data starts", "1998 Q2": "partial"}
    fig = go.Figure(go.Bar(
        x=labels, y=new["new_customers"], marker_color=BLUE, width=0.6,
        text=new["new_customers"], textposition="outside", cliponaxis=False,
        hovertemplate="%{x}: %{y} customers with their first recorded order<extra></extra>"))
    for q, note in notes.items():
        fig.add_annotation(x=q, y=0, text=note, showarrow=False, yshift=-38,
                           font=dict(size=10, color=INK3))
    base_layout(fig, "Customers by quarter of first recorded order", height=330)
    fig.update_yaxes(title="Customers", range=[0, new["new_customers"].max() * 1.15])
    fig.update_xaxes(showgrid=False)
    fig.update_layout(margin=dict(b=60))
    return fig


def country_fig(countries):
    """Plot the revenue change by customer country.

    Args:
        countries (pandas.DataFrame): Contents of
            ``q2_country_change.csv``.

    Returns:
        plotly.graph_objects.Figure: Horizontal bar chart; declines
        are red.
    """
    c = countries.sort_values("change")
    colors = [RED if v < 0 else BLUE for v in c["change"]]
    fig = go.Figure(go.Bar(
        x=c["change"] / 1000, y=c["Country"], orientation="h", marker_color=colors,
        customdata=c[["revenue_base", "revenue_current", "customers_active_current",
                      "customers_on_file"]],
        hovertemplate=("<b>%{y}</b><br>Jan–Apr 1997: $%{customdata[0]:,.0f}"
                       "<br>Jan–Apr 1998: $%{customdata[1]:,.0f}"
                       "<br>Change: %{x:+,.1f}k"
                       "<br>Customers active 1998 / on file: %{customdata[2]:.0f} / %{customdata[3]:.0f}"
                       "<extra></extra>")))
    base_layout(fig, "Change in revenue by customer country, Jan–Apr 1998 vs 1997",
                height=560)
    fig.update_xaxes(title="Change in revenue (thousand $)", tickprefix="$", ticksuffix="k")
    fig.update_yaxes(showgrid=False, dtick=1)
    return fig


def concentration_fig(rolling):
    """Plot top-10% and top-3 revenue shares over rolling windows.

    Args:
        rolling (pandas.DataFrame): Contents of
            ``q3_rolling_concentration.csv``.

    Returns:
        plotly.graph_objects.Figure: Line chart with one point per
        window, placed at the window's last month.
    """
    x = pd.to_datetime(rolling["window_end"])
    fig = go.Figure()
    for col, name, color in (("top10_share_pct", "Top 10% of customers", BLUE),
                             ("top3_share_pct", "Top 3 customers", "#eb6834")):
        fig.add_trace(go.Scatter(
            x=x, y=rolling[col], name=name, mode="lines+markers",
            line=dict(color=color, width=2), marker=dict(size=8),
            customdata=rolling[["customers", "top10_count", "window"]],
            hovertemplate=(f"<b>{name}</b><br>%{{customdata[2]}}<br>%{{y:.1f}}% of revenue"
                           "<br>(%{customdata[1]} of %{customdata[0]} active customers in top 10%)"
                           "<extra></extra>")))
        fig.add_annotation(x=x.iloc[-1], y=rolling[col].iloc[-1], text=name,
                           xanchor="left", xshift=8, showarrow=False,
                           font=dict(color=INK2, size=11))
    base_layout(fig, "Share of revenue from the largest customers, rolling 4-month windows",
                height=380, legend=dict(orientation="h", y=-0.25, x=0))
    fig.update_yaxes(title="Share of revenue", ticksuffix="%", range=[0, 60])
    fig.update_xaxes(title="Last month of the 4-month window", showgrid=False,
                     tickformat="%b %Y", dtick="M3",
                     range=["1996-09-15", "1998-05-15"])
    fig.update_layout(margin=dict(r=150, b=60))
    return fig


def discount_qty_fig(levels):
    """Plot extra units per order line by discount level.

    Args:
        levels (pandas.DataFrame): Contents of
            ``q4_quantity_by_discount.csv``; the 0% row is skipped.

    Returns:
        plotly.graph_objects.Figure: Bar chart with 95% CI error bars.
    """
    lv = levels[levels["Discount"] > 0]
    fig = go.Figure(go.Bar(
        x=lv["discount_label"], y=lv["extra_units_pct"], marker_color=BLUE, width=0.55,
        error_y=dict(type="data", array=lv["ci95"] * 100, color=INK3, thickness=1.2, width=5),
        customdata=lv[["order_lines", "ci95"]],
        hovertemplate=("Discount %{x}: %{y:+.0f}% more units than the same product at full price"
                       "<br>95% CI ± %{customdata[1]:.2f} × baseline · %{customdata[0]} order lines"
                       "<extra></extra>")))
    base_layout(fig, "Extra units per order line vs. the same product at full price",
                height=360)
    fig.update_yaxes(title="Extra units vs. full price", ticksuffix="%", range=[0, 70])
    fig.update_xaxes(title="Discount level", showgrid=False)
    return fig


def discount_emp_fig(emp):
    """Plot each employee's discount rate.

    Args:
        emp (pandas.DataFrame): Contents of
            ``q4_discount_by_employee.csv``.

    Returns:
        plotly.graph_objects.Figure: Horizontal bar chart of discount
        dollars as a share of list value.
    """
    e = emp.sort_values("avg_discount_pct")
    fig = go.Figure(go.Bar(
        x=e["avg_discount_pct"], y=e["Employee"], orientation="h", marker_color=BLUE,
        text=[pct(v, digits=1) for v in e["avg_discount_pct"]], textposition="outside",
        cliponaxis=False,
        customdata=e[["discount_given", "lines_discounted_pct", "lines_over_cap_pct",
                      "mean_line_discount_pct"]],
        hovertemplate=("<b>%{y}</b><br>Discount $ ÷ list value: %{x:.1f}%"
                       "<br>Discount given: $%{customdata[0]:,.0f}"
                       "<br>Unweighted mean line discount: %{customdata[3]:.1f}%"
                       "<br>Lines discounted: %{customdata[1]:.0f}%"
                       "<br>Lines above 10%: %{customdata[2]:.0f}%<extra></extra>")))
    base_layout(fig, "Discount rate by sales employee (discount $ ÷ list value)", height=360)
    fig.update_xaxes(title="Discount as % of list value", ticksuffix="%", range=[0, 14])
    fig.update_yaxes(showgrid=False)
    return fig


def table(df, columns, formats, align=None):
    """Render DataFrame columns as an HTML table.

    Args:
        df (pandas.DataFrame): Rows to show.
        columns (dict[str, str]): Column name to header text, in
            display order.
        formats (dict[str, Callable]): Column name to formatting
            function; unlisted columns use ``str``.
        align (dict[str, str] | None): Column name to CSS class,
            ``"txt"`` or ``"num"``; unlisted columns use ``"num"``.

    Returns:
        str: HTML for a horizontally scrollable table, with escaped
        cell text.
    """
    align = align or {}
    head = "".join(f'<th class="{align.get(c, "num")}">{html.escape(h)}</th>'
                   for c, h in columns.items())
    rows = []
    for _, r in df.iterrows():
        cells = "".join(f'<td class="{align.get(c, "num")}">{html.escape(formats.get(c, str)(r[c]))}</td>'
                        for c in columns)
        rows.append(f"<tr>{cells}</tr>")
    return (f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def chart(fig, first=False):
    """Convert a Plotly figure to an embeddable HTML snippet.

    Args:
        fig (plotly.graph_objects.Figure): Figure to embed.
        first (bool): If True, include the Plotly.js CDN script tag;
            use it for the first chart on the page only.

    Returns:
        str: HTML ``div`` for the chart.
    """
    return fig.to_html(full_html=False, include_plotlyjs="cdn" if first else False,
                       config={"displayModeBar": False, "responsive": True})


def section(num, question, why, approach, visuals, finding, implication):
    """Assemble the HTML section for one business question.

    Args:
        num (int): Question number, used for the anchor ``#q{num}``.
        question (str): Question text for the heading.
        why (str): HTML for "Why it matters".
        approach (str): HTML for "Approach".
        visuals (str): HTML for the charts and tables.
        finding (str): HTML for "Main finding".
        implication (str): HTML for "Business implication".

    Returns:
        str: HTML ``section`` element.
    """
    return f"""
<section id="q{num}">
  <p class="eyebrow">Question {num}</p>
  <h2>{question}</h2>
  <div class="grid2">
    <div><h3>Why it matters</h3>{why}</div>
    <div><h3>Approach</h3>{approach}</div>
  </div>
  {visuals}
  <div class="finding"><h3>Main finding</h3>{finding}</div>
  <div class="implication"><h3>Business implication</h3>{implication}</div>
</section>"""


def build():
    """Generate the webpage from the files in ``results/``.

    Args:
        None.

    Returns:
        None. Writes ``docs/index.html``.
    """
    m = json.loads((RESULTS / "metrics.json").read_text())
    d, q1, q2, q3, q4 = m["data"], m["q1"], m["q2"], m["q3"], m["q4"]
    drivers = pd.read_csv(RESULTS / "q1_growth_drivers.csv")
    new = pd.read_csv(RESULTS / "q1_new_customers_by_quarter.csv")
    countries = pd.read_csv(RESULTS / "q2_country_change.csv")
    accounts = pd.read_csv(RESULTS / "q2_accounts_in_declining_countries.csv")
    rolling = pd.read_csv(RESULTS / "q3_rolling_concentration.csv")
    top = pd.read_csv(RESULTS / "q3_top_customers.csv")
    levels = pd.read_csv(RESULTS / "q4_quantity_by_discount.csv")
    emp = pd.read_csv(RESULTS / "q4_discount_by_employee.csv")
    dr = drivers.set_index("driver")["change_pct"]

    acc = accounts[accounts["change"].abs() >= 500].copy()
    acc_table = table(
        acc,
        {"CompanyName": "Customer", "Country": "Country",
         "revenue_base_year": "Revenue 1997", "revenue_base_window": "Jan–Apr 1997",
         "revenue_current_window": "Jan–Apr 1998", "last_order": "Last order"},
        {"revenue_base_year": money, "revenue_base_window": money,
         "revenue_current_window": money},
        {"CompanyName": "txt", "Country": "txt", "last_order": "txt"})

    top_table = table(
        top,
        {"CompanyName": "Customer", "Country": "Country", "Revenue": "All-time revenue",
         "share_all_time_pct": "Share", "revenue_base_window": "Jan–Apr 1997",
         "revenue_current_window": "Jan–Apr 1998"},
        {"Revenue": money, "share_all_time_pct": lambda v: pct(v, digits=1),
         "revenue_base_window": money, "revenue_current_window": money},
        {"CompanyName": "txt", "Country": "txt"})

    big = q2["biggest_account_drop"]
    merep = accounts.set_index("CompanyName").loc["Mère Paillarde"]

    s1 = section(
        1, "Where is revenue growth coming from: new customers, more frequent orders, "
           "bigger orders, or higher prices?",
        "<p>Revenue more than doubled. Whether that came from winning new customers, "
        "from existing customers buying more often, or from raising prices decides where "
        "the next dollar of sales effort should go and whether the growth can last.</p>",
        "<p>Revenue is split exactly into <em>active customers × orders per customer × "
        "average order value</em>, comparing Jan–Apr 1997 with Jan–Apr 1998. Because the "
        "three factors multiply, each one's share of growth is its share of the log of total "
        "growth: ln(1.69) ÷ ln(2.21) ≈ 66% for orders per customer.</p>"
        f"<p>Average order value is further split into a price index and the remaining volume "
        f"and product-mix effect. The price index values the 1998 basket at each product's "
        f"quantity-weighted average price in both windows. It covers the "
        f"{q1['price_products_compared']} products sold in both windows; "
        f"{q1['price_products_excluded']} products sold only in 1998 "
        f"({pct(q1['price_excluded_revenue_share_pct'], digits=1)} of 1998 revenue) have no "
        f"1997 price and are left out of the index, so their effect falls into "
        f"the volume and mix factor. Customers are also counted by the quarter of their first "
        f"recorded order.</p>",
        f'<div class="charts2">{chart(growth_drivers_fig(drivers, q1["revenue_growth_pct"]), first=True)}'
        f'{chart(new_customers_fig(new))}</div>',
        f"<p>Revenue rose from {money(q1['revenue_base'])} to {money(q1['revenue_current'])} "
        f"({pct(q1['revenue_growth_pct'], sign=True)}). The main driver is <strong>existing "
        f"customers ordering more often</strong>: orders per customer rose "
        f"{pct(q1['opc_change_pct'], sign=True)}, about {pct(q1['opc_share_of_growth_pct'])} of "
        f"the growth (active customers {pct(q1['customers_share_of_growth_pct'])}, average order "
        f"value {pct(q1['aov_share_of_growth_pct'])}). Unit prices rose "
        f"{pct(q1['price_change_pct'], sign=True)}, but orders contained fewer units or cheaper "
        f"products, so the average order grew only {pct(dr['Average order value'], sign=True)}.</p>"
        f"<p>{pct(q1['revenue_from_retained_pct'])} of Jan–Apr 1998 revenue came from customers "
        f"who were already buying in Jan–Apr 1997. Few customers appear for the first time: "
        f"only {q1['customers_first_recorded_1997H2_onward']} customers have their first "
        f"recorded order after June 1997, and {q1['customers_first_recorded_1998']} in 1998. "
        f"The extra active customers are mostly earlier customers ordering again.</p>"
        f'<p class="note">"First recorded order" means the first order in this dataset. '
        f"Customers may have bought before July 1996, which is why the 1996 Q3 bar is so "
        f"high.</p>",
        "<p>Northwind is growing by selling more to the same customers, while very few "
        "customers are appearing for the first time. Frequency gains cannot grow forever, so "
        "the manager should (1) invest in winning new customers; (2) protect the "
        "higher order frequency with standing orders and reorder reminders; and (3) watch "
        "whether the price increase is shrinking basket sizes.</p>")

    s2 = section(
        2, "Which customer markets are growing or shrinking, and how much revenue is at risk?",
        "<p>Sales attention is limited. Knowing which markets carry the growth and which are "
        "slipping tells the manager where to put salespeople and where to intervene before "
        "revenue is lost.</p>",
        "<p>Revenue by customer country, Jan–Apr 1998 vs the same months of 1997 (comparing "
        "the same months avoids mixing growth with seasonality). Revenue at risk is the "
        "shrinking countries' full-year 1997 revenue multiplied by their combined rate of "
        "decline, i.e. the annual loss if the decline continues. Because each shrinking "
        "country has only a few customers, the individual accounts are examined too.</p>",
        chart(country_fig(countries)) +
        "<h3 class=\"table-title\">Largest account changes in the shrinking countries</h3>" + acc_table,
        f"<p>{q2['n_countries'] - q2['n_declining']} of {q2['n_countries']} countries grew. "
        f"{', '.join(q2['top3_growth_countries'])} delivered {pct(q2['top3_share_of_growth_pct'])} "
        f"of all growth. Four countries shrank: {', '.join(q2['declining_countries'])}, together "
        f"{pct(q2['declining_decline_rate_pct'], sign=False)} down. They were "
        f"{pct(q2['declining_share_base_year_pct'], digits=1)} of 1997 revenue, so about "
        f"<strong>{money(q2['revenue_at_risk_annual'])} a year is at risk</strong> if the trend "
        f"continues.</p>"
        f"<p>These four countries have only {q2['declining_customers_on_file']} customers between "
        f"them, so the decline is really about single accounts. {big['CompanyName']} "
        f"({big['Country']}) placed one unusually large order in January 1997 and is still "
        f"ordering. The real warning sign is <strong>Mère Paillarde</strong> (Canada): "
        f"{money(merep['revenue_base_year'])} in 1997, but no order since "
        f"{merep['last_order']} ({int(merep['days_since_last_order'])} days).</p>"
        "<p>Growth in the leading countries is also driven by a few accounts: "
        + "; ".join(f"{g['country']}: {g['top_account']} {pct(g['top_account_share_pct'])} of the "
                    f"country's growth, top two accounts {pct(g['top2_share_pct'])}"
                    for g in q2["growth_leaders"]) + ".</p>",
        "<p>Manage key accounts, not countries. Contact Mère Paillarde now to find out why it "
        "stopped ordering, and set an alert for any top-30 customer that has not ordered in "
        "90 days. The USA, Germany and Brazil deserve continued attention, but their growth "
        "depends on a handful of accounts (most of all Hanari Carnes in Brazil), so "
        "relationships with those accounts should be secured before the growth is treated "
        "as a market-wide trend.</p>")

    s3 = section(
        3, "How dependent is Northwind on its largest customers, and is that dependence rising?",
        "<p>If a few customers bring in most of the revenue, losing one of them hurts "
        "badly. The answer affects whether the company needs dedicated key-account "
        "management and how urgently it must broaden its customer base.</p>",
        "<p>Share of revenue from the top 10% of customers and from the top 3, in rolling "
        "4-month windows. All windows have the same length because a shorter period looks "
        "more concentrated simply because fewer customers order in it. The growth of the "
        "largest customers is also compared with that of all others.</p>",
        chart(concentration_fig(rolling)) +
        "<h3 class=\"table-title\">Ten largest customers</h3>" + top_table,
        f"<p>Dependence is high and has <strong>stayed in a similar range since early "
        f"1997</strong>, with no clear upward trend. The top 10% of customers "
        f"({q3['top10_count_current']} companies) brought in {pct(q3['top10_share_current_pct'])} "
        f"of revenue in Jan–Apr 1998, compared with {pct(q3['top10_share_base_pct'])} a year "
        f"earlier, a small increase. The share rose from {pct(q3['rolling_first'])} in late 1996 "
        f"and has moved between {pct(q3['rolling_min_since_1997'])} and "
        f"{pct(q3['rolling_max_since_1997'])} since April 1997. The three largest customers "
        f"({', '.join(q3['top3_current'])}) are about {pct(q3['top3_share_current_pct'])} of "
        f"revenue.</p>"
        f"<p>The largest customers of early 1997 grew {pct(q3['top_customers_growth_pct'], sign=True)}, "
        f"while all other customers grew {pct(q3['other_customers_growth_pct'], sign=True)}. "
        f"The list of top accounts is changing. For example, Hanari Carnes (Brazil) has been a "
        f"customer since {q3['hanari_first_order']}, but grew from "
        f"{money(q3['hanari_revenue_base_year'])} in all of 1997 to "
        f"{money(q3['hanari_revenue_current_window'])} in Jan–Apr 1998 alone.</p>"
        f'<p class="note">Comparing whole calendar years instead (1996 H2, 1997, Jan–Apr 1998) '
        f"would wrongly suggest a steady rise from 37% to 52%, because those periods have "
        f"different lengths.</p>",
        "<p>No emergency, but real exposure: losing one of the top three would remove about "
        "8% of revenue. Give the top three customers named account managers and regular "
        "business reviews. The Mère Paillarde case (the #9 customer of all time) shows that "
        "large accounts can go quiet without anyone noticing.</p>")

    s4 = section(
        4, "Does discounting buy more volume, or does it just give away revenue?",
        f"<p>Discounts reduced revenue by {money(q4['discount_total'])} "
        f"({pct(q4['discount_pct_of_list'], digits=1)} of list value) on "
        f"{pct(q4['lines_discounted_pct'])} of order lines. If larger discounts do not come "
        f"with larger orders, part of that revenue may be given up for little in return.</p>",
        "<p>Each order line's quantity is compared with the average full-price quantity of "
        "the <em>same product</em>, so the result is not driven by which products get "
        "discounts. Error bars show 95% confidence intervals. An employee's discount rate is "
        "total discount dollars divided by the total list value (price × quantity) of the "
        "order lines they handled, so large lines count more than small ones. The discount "
        f"dollars above a hypothetical {pct(q4['cap_pct'])} cap are also calculated.</p>",
        f'<div class="charts2">{chart(discount_qty_fig(levels))}{chart(discount_emp_fig(emp))}</div>',
        f"<p>Discounted lines are {pct(q4['extra_units_min_pct'])}–{pct(q4['extra_units_max_pct'])} "
        f"larger than full-price lines of the same product, but <strong>larger discounts are "
        f"not associated with clearly larger quantities</strong>: lines at 5% off are "
        f"{pct(q4['extra_units_5_pct'], sign=True)} larger, lines at 25% off "
        f"{pct(q4['extra_units_25_pct'], sign=True)}, and the confidence intervals overlap. "
        f"Discounts above {pct(q4['cap_pct'])} appear on {pct(q4['lines_over_cap_pct'], digits=1)} "
        f"of lines. The part of those discounts above a hypothetical {pct(q4['cap_pct'])} cap "
        f"was <strong>{money(q4['discount_above_cap'])}</strong>. This is a historical amount "
        f"at unchanged quantities, not revenue that a cap would be guaranteed to recover, "
        f"because some customers might have bought less without the larger discount. "
        f"Discount rates also differ widely between salespeople, from "
        f"{pct(q4['emp_min']['avg_discount_pct'], digits=1)} ({q4['emp_min']['Employee']}) to "
        f"{pct(q4['emp_max']['avg_discount_pct'], digits=1)} ({q4['emp_max']['Employee']}). "
        f"{q4['emp_max']['Employee']} also has the highest rate when every line counts "
        f"equally ({pct(q4['emp_max']['mean_line_discount_pct'], digits=1)}).</p>"
        f'<p class="note">Repeat purchases: {pct(q4["reorder_discounted_pct"])} of discounted '
        f"orders were followed by another order from the same customer within "
        f"{q4['reorder_days']} days, versus {pct(q4['reorder_full_price_pct'])} for full-price "
        f"orders. To avoid right-censoring, only orders placed on or before "
        f"{q4['reorder_last_eligible_date']} are counted, so each one has a full "
        f"{q4['reorder_days']}-day follow-up period in the data "
        f"({q4['reorder_n_discounted']} discounted and {q4['reorder_n_full_price']} full-price "
        f"orders). This is an association: frequent buyers may simply be the customers who "
        f"receive discounts. {q4['lines_dropped_rare_levels']} lines with rare discount levels "
        f"(1–4% and 6%) are left out of the chart.</p>",
        f"<p>The data does not show that discounts above {pct(q4['cap_pct'])} come with "
        f"extra volume compared with smaller discounts. Northwind could test a "
        f"{pct(q4['cap_pct'])} standard cap with manager approval above it, and agree on "
        f"common discount guidelines for the sales team. Because this is observational data, "
        f"the cap should first be piloted for one quarter with some sales reps or customers, "
        f"checking whether order volumes and repeat purchases hold.</p>")

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Northwind Growth Analysis</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
:root {{ color-scheme: light; --ink:{INK}; --ink2:{INK2}; --ink3:{INK3}; --grid:{GRID};
  --surface:{SURFACE}; --bg:#f4f3ef; --blue:{BLUE}; --red:{RED}; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; background:var(--bg); color:var(--ink); font-family:{FONT};
  line-height:1.6; font-size:16px; }}
header {{ background:var(--ink); color:#fff; padding:56px 16px 48px; }}
.wrap {{ max-width:1080px; margin:0 auto; padding:0 16px; }}
header .wrap {{ padding:0; }}
header h1 {{ font-size:clamp(28px,4vw,42px); line-height:1.15; margin:0 0 12px; max-width:820px; }}
header p {{ color:#c3c2b7; max-width:760px; margin:0; }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(min(200px,100%),1fr)); gap:12px;
  margin:-28px auto 0; }}
.stat {{ background:var(--surface); border:1px solid var(--grid); border-radius:10px; padding:16px 18px; }}
.stat b {{ display:block; font-size:28px; line-height:1.2; }}
.stat span {{ color:var(--ink2); font-size:14px; }}
nav {{ margin:28px 0 8px; display:flex; flex-wrap:wrap; gap:8px; }}
nav a {{ color:var(--ink2); text-decoration:none; border:1px solid var(--grid); background:var(--surface);
  border-radius:999px; padding:4px 12px; font-size:14px; }}
nav a:hover {{ color:var(--blue); border-color:var(--blue); }}
section, .box {{ background:var(--surface); border:1px solid var(--grid); border-radius:12px;
  padding:28px; margin:24px 0; }}
.eyebrow {{ color:var(--blue); font-weight:600; text-transform:uppercase; letter-spacing:.06em;
  font-size:13px; margin:0; }}
h2 {{ font-size:clamp(22px,2.6vw,28px); line-height:1.25; margin:6px 0 18px; }}
h3 {{ font-size:15px; margin:0 0 6px; }}
.grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:28px; margin-bottom:12px; }}
.grid2 p, .finding p, .implication p {{ margin:0 0 10px; color:var(--ink2); }}
.charts2 {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
.charts2 > div, section > div.plotly-graph-div {{ min-width:0; }}
.finding {{ border-left:4px solid var(--blue); padding:4px 0 4px 18px; margin:20px 0; }}
.implication {{ background:#eef4fc; border-radius:10px; padding:18px 20px; }}
.implication p {{ color:var(--ink); }}
.note {{ font-size:14px; color:var(--ink3) !important; }}
.table-title {{ margin-top:20px; }}
.table-wrap {{ overflow-x:auto; }}
table {{ border-collapse:collapse; width:100%; font-size:14px; }}
th, td {{ padding:8px 10px; border-bottom:1px solid var(--grid); white-space:nowrap; }}
th {{ color:var(--ink2); font-weight:600; }}
.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
.txt {{ text-align:left; }}
.box ul {{ color:var(--ink2); padding-left:20px; }}
code {{ background:#efeee9; padding:1px 5px; border-radius:4px; font-size:14px; }}
pre {{ background:#efeee9; padding:14px; border-radius:8px; overflow-x:auto; font-size:14px; }}
a {{ color:var(--blue); }}
footer {{ color:var(--ink3); font-size:14px; padding:8px 0 48px; }}
@media (max-width: 760px) {{
  .grid2, .charts2 {{ grid-template-columns:1fr; gap:12px; }}
  section, .box {{ padding:20px 16px; }}
}}
</style>
</head>
<body>
<header><div class="wrap">
  <h1>Northwind Traders: growth is strong, but it rests on existing customers</h1>
  <p>An analysis of {d['orders']} orders ({d['order_lines']:,} order lines) from
  {d['customers_with_orders']} customers between {d['first_order']} and {d['last_order']},
  prepared for Northwind's management.</p>
</div></header>
<main class="wrap">
  <div class="stats">
    <div class="stat"><b>{pct(q1['revenue_growth_pct'], sign=True)}</b><span>revenue, Jan–Apr 1998 vs 1997</span></div>
    <div class="stat"><b>{q1['customers_first_recorded_1998']}</b><span>customer with a first recorded order in 1998</span></div>
    <div class="stat"><b>{money(q2['revenue_at_risk_annual'], k=True)}</b><span>annual revenue at risk in shrinking markets</span></div>
    <div class="stat"><b>{money(q4['discount_above_cap'], k=True)}</b><span>historical discounts above a hypothetical 10% cap</span></div>
  </div>
  <nav>
    <a href="#q1">1 · Growth drivers</a><a href="#q2">2 · Markets</a>
    <a href="#q3">3 · Customer dependence</a><a href="#q4">4 · Discounts</a>
    <a href="#method">Data &amp; method</a>
  </nav>
  {s1}{s2}{s3}{s4}
  <div class="box" id="method">
    <h2>Data, method and limitations</h2>
    <ul>
      <li><strong>Data:</strong> the Northwind Database workbook provided for the course
      (Orders, Order Details, Customers, Products, Employees). Revenue = unit price × quantity
      × (1 − discount), using the price actually charged on each order.</li>
      <li><strong>Like-for-like comparison:</strong> the data runs from {d['first_order']} to
      {d['last_order']}. Year-over-year comparisons use {d['base_window']} vs
      {d['current_window']}, so seasonality and partial months do not distort them.</li>
      <li><strong>No cost data:</strong> the dataset has no purchase costs, so profit and
      margin cannot be measured. All findings are about revenue.</li>
      <li><strong>Small groups:</strong> many countries have only 1–5 customers, so
      country-level changes can come from a single order.</li>
      <li><strong>Observational data:</strong> discount effects are associations, not proven
      causes. The recommended cap should be tested before it is rolled out.</li>
    </ul>
    <h3>Reproduce these results</h3>
    <p>All numbers, charts and tables on this page are generated by Python code in the
    <a href="{REPO_URL}">GitHub repository</a>:</p>
<pre>pip install -r requirements.txt
python analysis.py     # writes results/*.csv and results/metrics.json
python build_site.py   # writes docs/index.html</pre>
  </div>
  <footer>Analysis built with Python (pandas, Plotly) for 15.561 HW 3.</footer>
</main>
</body>
</html>"""
    SITE.mkdir(exist_ok=True)
    (SITE / "index.html").write_text(page, encoding="utf-8")
    print("Wrote", SITE / "index.html")


if __name__ == "__main__":
    build()
