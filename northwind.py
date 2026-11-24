"""Load the Northwind workbook and build shared analysis tables."""

import pathlib

import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parent
DATA = ROOT / "data" / "northwind.xlsx"
RESULTS = ROOT / "results"
SITE = ROOT / "docs"

BASE_YEAR, CURRENT_YEAR = 1997, 1998
WINDOW_LAST_MONTH = 4  # data ends 6 May 1998, so Jan-Apr is the latest full span


def load_tables(path=DATA):
    """Read every sheet of the Northwind workbook.

    Args:
        path (pathlib.Path): Excel workbook to read; defaults to
            ``data/northwind.xlsx``.

    Returns:
        dict[str, pandas.DataFrame]: One DataFrame per sheet, keyed by
        sheet name.
    """
    return pd.read_excel(path, sheet_name=None)


def order_lines(tables):
    """Build one row per order line with revenue, customer and employee.

    Args:
        tables (dict[str, pandas.DataFrame]): Sheets from
            ``load_tables``.

    Returns:
        pandas.DataFrame: Order Details joined with Orders, plus
        ``ListValue``, ``Revenue`` (after discount), ``CompanyName``,
        ``Country`` and ``Employee``. Discounts are rounded to two
        decimals.
    """
    lines = tables["Orders Details"].copy()
    # Discounts are stored as floats like 0.0500000007; round to whole percents.
    lines["Discount"] = lines["Discount"].round(2)
    lines["ListValue"] = lines["UnitPrice"] * lines["Quantity"]
    lines["Revenue"] = lines["ListValue"] * (1 - lines["Discount"])

    lines = lines.merge(tables["Orders"], on="OrderID", validate="many_to_one")
    customers = tables["Customers"][["CustomerID", "CompanyName", "Country"]]
    lines = lines.merge(customers, on="CustomerID", how="left",
                        validate="many_to_one")

    emp = tables["Employees"]
    names = dict(zip(emp["EmployeeID"], emp["FirstName"] + " " + emp["LastName"]))
    lines["Employee"] = lines["EmployeeID"].map(names)
    return lines


def window(lines, year, last_month=WINDOW_LAST_MONTH):
    """Select order lines from January through a given month of a year.

    Args:
        lines (pandas.DataFrame): Rows with an ``OrderDate`` column.
        year (int): Calendar year to keep.
        last_month (int): Last month included, 1-12; default 4 (April).

    Returns:
        pandas.DataFrame: Rows dated 1 January to the end of
        ``last_month`` in ``year``.
    """
    dates = lines["OrderDate"]
    return lines[(dates.dt.year == year) & (dates.dt.month <= last_month)]


def window_label(year):
    """Format the comparison window label for a year.

    Args:
        year (int): Calendar year.

    Returns:
        str: Label such as ``"Jan–Apr 1997"``.
    """
    return f"Jan–Apr {year}"
