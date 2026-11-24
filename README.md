# Northwind Traders: Business Data Analysis

A Python analysis of the Northwind Database for 15.561, Homework 3. The findings are presented as an interactive webpage for a manager who wants to understand where the business is growing and where it is exposed.

- **Webpage:** https://tatiitataaa.github.io/northwind-analysis/
- **Repository:** https://github.com/tatiitataaa/northwind-analysis

## Business questions

| # | Question | Main finding |
|---|---|---|
| 1 | Where is revenue growth coming from: new customers, more frequent orders, bigger orders, or higher prices? | Revenue grew 121% (Jan–Apr 1998 vs 1997). About two thirds of that comes from existing customers ordering more often. Very few customers appear for the first time. |
| 2 | Which customer markets are growing or shrinking, and how much revenue is at risk? | 17 of 21 countries grew. The four shrinking countries put about $38k a year at risk. Changes in both directions are driven by a few individual accounts. |
| 3 | How dependent is Northwind on its largest customers, and is that dependence rising? | The top 10% of customers bring in about 48% of revenue. That share has stayed between 41% and 51% since April 1997, with no clear upward trend. |
| 4 | Does discounting buy more volume, or does it just give away revenue? | Discounted order lines are larger, but larger discounts are not associated with clearly larger quantities. Discount rates differ widely between salespeople. |

## Repository structure

```
northwind-analysis/
├── data/northwind.xlsx        # Northwind Database workbook provided on Canvas (unchanged)
├── northwind.py               # Loads the workbook, builds the order-line table, defines time windows
├── analysis.py                # Computes every number and table -> results/
├── build_site.py              # Builds the webpage from results/ -> docs/index.html
├── explore.py                 # Exploratory charts used to choose the questions -> figures/explore/
├── results/                   # CSV tables and metrics.json behind every number on the webpage
├── docs/index.html            # The published webpage (served by GitHub Pages)
├── figures/explore/           # Static exploratory charts (PNG)
├── .claude/skills/python-docstrings/SKILL.md   # Skill used to document the Python code
├── requirements.txt
└── README.md
```

## Reproduce the results

Requires Python 3.11 or newer.

```bash
git clone https://github.com/tatiitataaa/northwind-analysis.git
cd northwind-analysis
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python analysis.py      # computes every number and table -> results/
python build_site.py    # builds the webpage from results/ -> docs/index.html
python explore.py       # optional: exploratory charts -> figures/explore/
```

Open `docs/index.html` in a browser to view the page locally. The page loads Plotly from its CDN, so it needs an internet connection. Running the two main scripts on the unchanged workbook reproduces the files in `results/` and the webpage exactly.

### Where each number on the webpage comes from

| Webpage element | Source file in `results/` |
|---|---|
| Headline numbers and all figures quoted in the text | `metrics.json` |
| Q1 growth-driver chart | `q1_growth_drivers.csv`, `q1_growth_summary.csv` |
| Q1 first-recorded-order chart | `q1_new_customers_by_quarter.csv` |
| Q2 country chart | `q2_country_change.csv` |
| Q2 account table | `q2_accounts_in_declining_countries.csv` |
| Q3 concentration chart | `q3_rolling_concentration.csv` |
| Q3 top-customer table | `q3_top_customers.csv` |
| Q4 discount-quantity chart | `q4_quantity_by_discount.csv` |
| Q4 employee chart | `q4_discount_by_employee.csv` |

## Definitions and analytical choices

- **Revenue** = `UnitPrice × Quantity × (1 − Discount)` from Order Details. This uses the price actually charged, which differs from the current catalog price for many 1996–97 orders.
- **Discounts** are rounded to two decimals, because the workbook stores values such as `0.0500000007`.
- **Country** is the customer's country from the Customers table. It matches the ship-to country on 99.5% of order lines.
- **Year-over-year comparison** is Jan–Apr 1997 vs Jan–Apr 1998. The data runs from 4 July 1996 to 6 May 1998, so this is the latest stretch of complete months that can be compared with the same months a year earlier.
- **Growth decomposition**: revenue = active customers × orders per customer × average order value. The three ratios (1998 ÷ 1997) multiply exactly to the revenue ratio. Each factor's share of growth is `ln(factor ratio) ÷ ln(revenue ratio)`; for orders per customer this is ln(1.69) ÷ ln(2.21) ≈ 66%.
- **Price index**: the Jan–Apr 1998 basket (quantity per product) valued at each product's quantity-weighted average price in Jan–Apr 1998 vs Jan–Apr 1997. Only the 71 products sold in both windows are included. The 3 products sold only in 1998 (2.1% of 1998 revenue) have no 1997 price, so their effect ends up in the "volume & mix" factor (average order value ÷ price index).
- **First recorded order**: a customer's earliest order in this dataset. Customers may have ordered before July 1996, so this does not prove that a customer is genuinely new.
- **Revenue at risk**: the shrinking countries' full-year 1997 revenue × their combined rate of decline (Jan–Apr 1998 vs 1997). It is the annual loss if that decline continues, not a forecast.
- **Customer concentration** is measured in rolling 4-month windows of equal length, because comparing periods of different length would bias the result.
- **Discount effect**: each order line's quantity is divided by the average full-price quantity of the same product. 8 lines with rare discount levels (1–4% and 6%) are left out of the chart. The results are associations, not causal effects.
- **Employee discount rate**: total discount dollars ÷ total list value (`UnitPrice × Quantity`) of the order lines in that employee's orders. Large lines count more than small ones. The unweighted mean of line discounts is also saved in `q4_discount_by_employee.csv`.
- **Discounts above a 10% cap**: for lines with a discount above 10%, `list value × (discount − 10%)`, summed. This is a historical amount at unchanged quantities, not a forecast of recoverable revenue.
- **Repeat purchases**: an order counts as repeated if the same customer ordered again within 90 days. To avoid right-censoring, only orders placed at least 90 days before the last order date (6 May 1998) are counted.
- **No cost data**: the workbook contains no purchase costs, so profit and margin are not analysed.

## Code documentation with SKILL.md

All Python code in this repository is documented with docstrings generated by the `python-docstrings` skill provided for this homework. The skill file is included at [`.claude/skills/python-docstrings/SKILL.md`](.claude/skills/python-docstrings/SKILL.md).

**What the skill is.** A skill is a Markdown file with instructions that a coding agent (here, Claude Code) loads when a task matches it. The header (`name`, `description`) tells the agent when to use the skill. The body describes the workflow and the rules to follow. Because the file is stored in `.claude/skills/` inside the project folder, it is available to Claude Code in this project.

**What it does.** The skill writes PEP 8 / PEP 257 compliant docstrings in a single pass, without asking questions first:

- It reads each function's full body, and the functions it calls, before writing.
- It edits only docstrings, never code.
- Every function gets a summary line in the imperative mood, one line per parameter, and a `Returns:` section (also `None.` when nothing is returned). Lines are at most 72 characters. Google style is the default when a project has no existing style.
- When the meaning of a parameter is ambiguous, it picks the most defensible reading (code behaviour first, then callers, names and conventions) and records that choice.
- Afterwards it reports every docstring written, a numbered list of **assumptions to check**, and anything else it noticed (possible bugs, misleading names), so the user can accept the result or send numbered corrections.

**How it was called.** After the analysis code was final, the skill was invoked in Claude Code on all four Python files, equivalent to typing:

```
/python-docstrings northwind.py analysis.py build_site.py explore.py
```

It added a module docstring to each file and Google-style docstrings to all 37 functions. Its self-check confirmed that every parameter is documented exactly once and in order, and that every docstring has a `Returns:` section. The analysis was re-run afterwards, and `results/` and the webpage were byte-for-byte identical, which confirms that only documentation changed. Among the issues the skill flagged for review: `window_label` always returns "Jan–Apr" even if the window constant changes, and two customer names (Mère Paillarde, Hanari Carnes) are referenced directly in the code, so the scripts assume the provided dataset.

## Tools

Python 3 with pandas, NumPy, openpyxl, Plotly (interactive webpage charts) and matplotlib (exploratory charts). The analysis was carried out with the help of Claude Code, an AI coding agent. Questions, analytical choices and conclusions were reviewed and verified by the author against the original dataset.
