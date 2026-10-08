"""
DEFINED BENEFIT PENSION FUNDING & LONGEVITY RISK MODEL  -  complete project in ONE file
=====================================================================================
Question answered: can an illustrative defined benefit (DB) pension scheme afford its
promised pensions, and how likely is it to be underfunded after 10 years?

HOW TO RUN
  Colab : upload this file, then run a cell with   !python db_pension_full.py
          (or paste the whole file into one cell and run it)
  PC    : pip install numpy pandas matplotlib openpyxl   then   python db_pension_full.py
Needs: numpy, pandas, matplotlib, openpyxl (all already installed on Colab).

WHAT YOU GET (saved in a folder called  pension_outputs):
  chart1_funding_fan.png, chart2_year10_distribution.png, chart3_contributions.png
  DB_Pension_Reperformance_Check.xlsx   (one member worked out with live Excel formulas)
  members.csv                           (the 500 synthetic members)

MAP OF THE CODE
  1. ASSUMPTIONS      every number you can change
  2. MORTALITY        Indian Individual Annuitant's Mortality Table (2012-15), Institute of Actuaries of India
  3. MEMBERS          500 synthetic active members
  4. LIABILITIES      expected pensions per year, discounted to today
  5. ASSET SIMULATION 10,000 random 10-year paths of investment returns
  6. RESULTS          funding level, longevity shock, contribution test, discount-rate test
  7. CHARTS
  8. EXCEL CHECK      reperformance of one member's liability
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = "pension_outputs"
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ 1. ASSUMPTIONS
SEED = 42
N_MEMBERS = 500
RET_AGE = 60            # normal retirement age
MAX_AGE = 115           # last age in the IAI table
ACCRUAL = 1 / 60        # pension earned per year of service = 1/60 of final salary
SAL_GROWTH = 0.06       # salary growth per year
DISC = 0.07             # discount rate used to value liabilities
PEN_INC = 0.00          # yearly increase in pensions in payment
START_FL = 0.90         # starting funding level (assets / liabilities)
HORIZON = 10            # years simulated
N_SIMS = 10_000         # Monte Carlo paths
RET_MEAN = 0.08         # expected yearly asset return
RET_VOL = 0.12          # yearly asset volatility
CONTRIB_RATE = 0.15     # employer contribution as % of payroll (base case)
LONGEVITY_SHIFT = 2     # longevity shock: members die like people 2 years younger

# ------------------------------------------------------------------ 2. MORTALITY
# q(x) = chance a person aged x dies within a year, ages 20 to 115 (age last birthday).
QX = [
    0.000284, 0.000305, 0.000328, 0.000353, 0.000379, 0.000407, 0.000438, 0.000471,
    0.000507, 0.000545, 0.000586, 0.000631, 0.000679, 0.000731, 0.000787, 0.000847,
    0.000913, 0.000984, 0.001061, 0.001144, 0.001234, 0.001332, 0.001438, 0.001553,
    0.001679, 0.001815, 0.001964, 0.002125, 0.002302, 0.002495, 0.002705, 0.002936,
    0.003188, 0.003464, 0.003768, 0.004101, 0.004468, 0.004871, 0.005316, 0.005807,
    0.006349, 0.006948, 0.007612, 0.008347, 0.009163, 0.010070, 0.011077, 0.012198,
    0.013447, 0.014840, 0.016393, 0.018128, 0.020067, 0.022236, 0.024662, 0.027379,
    0.030422, 0.033830, 0.037651, 0.041932, 0.046730, 0.052106, 0.058127, 0.064868,
    0.072410, 0.080840, 0.090252, 0.100746, 0.112428, 0.125408, 0.139798, 0.155712,
    0.173260, 0.192548, 0.213673, 0.236719, 0.261749, 0.288807, 0.317906, 0.349031,
    0.382129, 0.417111, 0.453851, 0.492190, 0.531933, 0.572866, 0.614755, 0.657357,
    0.700435, 0.743762, 0.787136, 0.830382, 0.873364, 0.915987, 0.958198, 0.999990,
]
TBL_MIN = 20
assert len(QX) == 96
_l = np.concatenate([[1.0], np.cumprod(1 - np.array(QX))])   # l[0] = age 20 ... l[96] = age 116


def survival(age, t, shift=0):
    """Probability that someone aged `age` is alive `t` years later = l(age+t) / l(age).
    shift=2 means they follow the mortality of someone 2 years younger (longevity shock)."""
    x = np.asarray(age) - shift - TBL_MIN
    t = np.asarray(t)
    end = x + t
    out = _l[np.minimum(end, len(_l) - 1)] / _l[x]
    return np.where(end > len(_l) - 1, 0.0, out)


# ------------------------------------------------------------------ 3. MEMBERS
def build_members(rng):
    ages = rng.integers(30, 60, N_MEMBERS)                       # ages 30..59
    salary = np.clip(rng.lognormal(np.log(1_200_000), 0.4, N_MEMBERS), 400_000, 5_000_000)
    service = np.maximum(ages - 22, 1)                           # joined at 22
    yrs_to_ret = RET_AGE - ages
    final_salary = salary * (1 + SAL_GROWTH) ** yrs_to_ret
    pension = ACCRUAL * final_salary * (service + yrs_to_ret)    # yearly pension at retirement
    return pd.DataFrame(dict(age=ages, salary=salary, service=service,
                             yrs_to_ret=yrs_to_ret, pension=pension))


# ------------------------------------------------------------------ 4. LIABILITIES
def cashflows(m, shift=0):
    """Expected pension paid in each future year s (end of year), all members added up."""
    S = MAX_AGE - m.age.min()
    s = np.arange(0, S + 1)
    cf = np.zeros(S + 1)
    for age, R, pen in zip(m.age.values, m.yrs_to_ret.values, m.pension.values):
        yrs = s[(s >= R) & (s <= MAX_AGE - age)]
        cf[yrs] += pen * (1 + PEN_INC) ** (yrs - R) * survival(age, yrs, shift)
    return cf


def liability_at(cf, t, disc=None):
    """Value at time t of all expected payments after t, discounted at `disc`."""
    disc = DISC if disc is None else disc
    s = np.arange(len(cf))
    mask = s > t
    return float((cf[mask] / (1 + disc) ** (s[mask] - t)).sum())


def payroll(m, t):
    """Expected salary bill in year t: active members who are alive and not yet retired."""
    active = t < m.yrs_to_ret.values
    return float((m.salary.values * (1 + SAL_GROWTH) ** t * active
                  * survival(m.age.values, t)).sum())


# ------------------------------------------------------------------ 5. ASSET SIMULATION
def simulate(m, cf, a0, contrib_rate, rng, n_sims=N_SIMS):
    """Roll assets forward:  A(t+1) = A(t) * (1 + return) + contributions - pensions paid.
    Returns the funding level (assets / liabilities) at t = 0..HORIZON for every path."""
    mu_log = np.log(1 + RET_MEAN) - 0.5 * RET_VOL ** 2           # so that the average return = RET_MEAN
    gross = np.exp(rng.normal(mu_log, RET_VOL, (n_sims, HORIZON)))
    liab = np.array([liability_at(cf, t) for t in range(HORIZON + 1)])
    contrib = np.array([contrib_rate * payroll(m, t) for t in range(HORIZON)])
    assets = np.empty((n_sims, HORIZON + 1))
    assets[:, 0] = a0
    for t in range(HORIZON):
        assets[:, t + 1] = assets[:, t] * gross[:, t] + contrib[t] - cf[t + 1]
    return assets / liab, liab


# ------------------------------------------------------------------ 6. RESULTS
def summary(fl):
    end = fl[:, -1]
    return dict(median=float(np.median(end)), p5=float(np.percentile(end, 5)),
                p95=float(np.percentile(end, 95)), prob_deficit=float((end < 1).mean()))


def run_model():
    rng = np.random.default_rng(SEED)
    m = build_members(rng)
    cf = cashflows(m)
    L0 = liability_at(cf, 0)
    A0 = START_FL * L0
    res = dict(liability_0=L0, assets_0=A0, payroll_0=payroll(m, 0),
               life_exp_60=float(survival(60, np.arange(1, 56)).sum() + 0.5))

    fl, _ = simulate(m, cf, A0, CONTRIB_RATE, np.random.default_rng(1))          # base case
    res["base"] = summary(fl)
    res["base_pctiles"] = {p: np.percentile(fl, p, axis=0) * 100 for p in (5, 25, 50, 75, 95)}
    res["base_end"] = fl[:, -1] * 100

    cf_l = cashflows(m, shift=LONGEVITY_SHIFT)                                    # longevity shock
    L0_l = liability_at(cf_l, 0)
    fl_l, _ = simulate(m, cf_l, A0, CONTRIB_RATE, np.random.default_rng(1))
    res["longevity"] = dict(liability_increase=L0_l / L0 - 1, **summary(fl_l))

    res["contrib"] = {}                                                           # contribution test
    for rate in (0.10, 0.15, 0.20, 0.25, 0.30):
        f, _ = simulate(m, cf, A0, rate, np.random.default_rng(1))
        res["contrib"][rate] = summary(f)

    res["disc_sens"] = {d: liability_at(cf, 0, d) / L0 - 1 for d in (0.06, 0.07, 0.08)}

    chk = pd.DataFrame(dict(age=[45], salary=[1_200_000], service=[23], yrs_to_ret=[15],     # Excel check member
                            pension=[ACCRUAL * 1_200_000 * (1 + SAL_GROWTH) ** 15 * (23 + 15)]))
    res["check_liability"] = liability_at(cashflows(chk), 0)
    m.to_csv(f"{OUT}/members.csv", index=False)
    return res


def print_results(r):
    print(f"Liability today        : Rs {r['liability_0']/1e7:,.1f} crore")
    print(f"Assets today (90%)     : Rs {r['assets_0']/1e7:,.1f} crore")
    print(f"Payroll today          : Rs {r['payroll_0']/1e7:,.1f} crore  (liability = {r['liability_0']/r['payroll_0']:.1f}x payroll)")
    print(f"Life expectancy at 60  : {r['life_exp_60']:.1f} years")
    b = r["base"]
    print(f"\nBASE (15% contributions): median FL {b['median']:.1%}, 5th pct {b['p5']:.1%}, P(FL<100%) {b['prob_deficit']:.1%}")
    l = r["longevity"]
    print(f"LONGEVITY +2 yrs: liability +{l['liability_increase']:.1%}, median FL {l['median']:.1%}, 5th pct {l['p5']:.1%}, P(FL<100%) {l['prob_deficit']:.1%}")
    print("\nContribution test:")
    for k, v in r["contrib"].items():
        print(f"  {k:.0%} of payroll -> median FL {v['median']:.1%}, 5th pct {v['p5']:.1%}, P(deficit) {v['prob_deficit']:.1%}")
    print("\nDiscount-rate sensitivity (liability change vs 7%):", {k: f"{v:+.1%}" for k, v in r["disc_sens"].items()})
    print(f"Excel-check member liability (age 45): Rs {r['check_liability']:,.2f}")


# ------------------------------------------------------------------ 7. CHARTS
def make_charts(r):
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    NAVY, GREY, RED = "#1f3b73", "#9aa5b8", "#c0392b"

    fig, ax = plt.subplots(figsize=(7, 4)); yrs = np.arange(HORIZON + 1); p = r["base_pctiles"]
    ax.fill_between(yrs, p[5], p[95], color=GREY, alpha=0.35, label="5th-95th percentile")
    ax.fill_between(yrs, p[25], p[75], color=GREY, alpha=0.7, label="25th-75th percentile")
    ax.plot(yrs, p[50], color=NAVY, lw=2.2, label="Median")
    ax.axhline(100, color=RED, ls="--", lw=1.2); ax.text(0.1, 101.5, "Fully funded (100%)", color=RED, fontsize=9)
    ax.set_xlabel("Years from today"); ax.set_ylabel("Funding level (%)")
    ax.set_title("Funding level over 10 years (10,000 simulations)", loc="left", fontweight="bold")
    ax.legend(frameon=False, loc="upper left", bbox_to_anchor=(0, 0.93)); fig.tight_layout()
    fig.savefig(f"{OUT}/chart1_funding_fan.png", dpi=200); plt.close(fig)

    end = r["base_end"]; bins = np.arange(0, 305, 5)
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.hist(end[end < 100], bins=bins, color=RED, alpha=0.85, label="Underfunded")
    ax.hist(end[end >= 100], bins=bins, color=NAVY, alpha=0.85, label="Fully funded")
    ax.axvline(100, color="black", lw=1); ax.set_xlim(0, 300)
    ax.set_xlabel("Funding level at year 10 (%)"); ax.set_ylabel("Number of simulations")
    ax.set_title(f"Chance of a deficit after 10 years: {r['base']['prob_deficit']:.0%}", loc="left", fontweight="bold")
    ax.legend(frameon=False); fig.tight_layout()
    fig.savefig(f"{OUT}/chart2_year10_distribution.png", dpi=200); plt.close(fig)

    rates = sorted(r["contrib"]); vals = [r["contrib"][k]["prob_deficit"] * 100 for k in rates]
    fig, ax = plt.subplots(figsize=(7, 4))
    bars = ax.bar([f"{k:.0%}" for k in rates], vals, color=NAVY, width=0.55)
    for b_, v in zip(bars, vals):
        ax.text(b_.get_x() + b_.get_width() / 2, v + 1, f"{v:.0f}%", ha="center")
    ax.set_xlabel("Employer contribution (% of payroll)"); ax.set_ylabel("Chance of deficit at year 10 (%)")
    ax.set_ylim(0, max(vals) + 10)
    ax.set_title("Higher contributions cut the chance of a deficit", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(f"{OUT}/chart3_contributions.png", dpi=200); plt.close(fig)


# ------------------------------------------------------------------ 8. EXCEL CHECK
def make_excel(r):
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    wb = Workbook(); ws = wb.active; ws.title = "Member check"
    b = Font(bold=True); blue = Font(color="0000FF"); hdr = PatternFill("solid", fgColor="DDDDDD")

    tb = wb.create_sheet("IIAMT 2012-15")                       # the IAI table, survivors built by formula
    for j, h in enumerate(["Age", "q(x): chance of dying within a year", "l(x): survivors out of 1.0 at age 20"], 1):
        c = tb.cell(1, j, h); c.font = b; c.fill = hdr; c.alignment = Alignment(wrap_text=True)
    for i, (age, qx) in enumerate(zip(range(20, 116), QX), start=2):
        tb.cell(i, 1, age); tb.cell(i, 2, qx).font = blue
        tb.cell(i, 3, 1 if i == 2 else f"=C{i-1}*(1-B{i-1})")
    last_tbl = 1 + len(QX)
    tb.cell(last_tbl + 1, 1, 116); tb.cell(last_tbl + 1, 3, f"=C{last_tbl}*(1-B{last_tbl})")
    for col, w in zip("ABC", (8, 26, 26)): tb.column_dimensions[col].width = w
    tb.row_dimensions[1].height = 45
    AGES = f"'IIAMT 2012-15'!$A$2:$A${last_tbl+1}"; LX = f"'IIAMT 2012-15'!$C$2:$C${last_tbl+1}"

    ws["A1"] = "Reperformance check: liability for ONE member (must match Python)"; ws["A1"].font = Font(bold=True, size=12)
    inputs = [("Age today", 45), ("Salary today (Rs)", 1200000), ("Years of service today", 23),
              ("Retirement age", 60), ("Pension accrual per year of service", "=1/60"),
              ("Salary growth", SAL_GROWTH), ("Discount rate", DISC), ("Pension increase", PEN_INC), ("Last age in table", MAX_AGE)]
    for i, (k, v) in enumerate(inputs, start=3):
        ws.cell(i, 1, k); ws.cell(i, 2, v).font = blue
    ws["A14"] = "Years to retirement";               ws["B14"] = "=B6-B3"
    ws["A15"] = "Final salary (Rs)";                 ws["B15"] = "=B4*(1+B8)^B14"
    ws["A16"] = "Yearly pension at retirement (Rs)"; ws["B16"] = "=B7*B15*(B5+B14)"
    ws["A18"] = "Blue = inputs you can change. Everything else is a live formula."
    for rr in (14, 15, 16): ws.cell(rr, 1).font = b
    heads = ["Years from now (s)", "Age at s", "Pension payable? (1/0)", "Chance alive at s (from IAI table)",
             "Expected pension paid (Rs)", "Discount factor", "Present value (Rs)"]
    for j, h in enumerate(heads, 1):
        c = ws.cell(20, j, h); c.font = b; c.fill = hdr; c.alignment = Alignment(wrap_text=True)
    S = 80
    for s in range(S + 1):
        rr = 21 + s
        ws.cell(rr, 1, s); ws.cell(rr, 2, f"=$B$3+A{rr}")
        ws.cell(rr, 3, f"=IF(AND(A{rr}>=$B$14,B{rr}<=$B$11),1,0)")
        ws.cell(rr, 4, f"=IFERROR(INDEX({LX},MATCH(B{rr},{AGES},0))/INDEX({LX},MATCH($B$3,{AGES},0)),0)")
        ws.cell(rr, 5, f"=C{rr}*$B$16*(1+$B$10)^(A{rr}-$B$14)*D{rr}")
        ws.cell(rr, 6, f"=(1+$B$9)^(-A{rr})"); ws.cell(rr, 7, f"=E{rr}*F{rr}")
        ws.cell(rr, 4).number_format = "0.0000"; ws.cell(rr, 6).number_format = "0.0000"
        for c in (5, 7): ws.cell(rr, c).number_format = "#,##0"
    ws["I3"] = "Liability, Excel (Rs)";  ws["J3"] = f"=SUM(G21:G{21+S})"
    ws["I4"] = "Liability, Python (Rs)"; ws["J4"] = round(r["check_liability"], 2)
    ws["I5"] = "Difference (Rs)";        ws["J5"] = "=J3-J4"
    ws["I6"] = "Match?";                 ws["J6"] = '=IF(ABS(J5)<1,"YES","NO")'
    for rr in range(3, 7): ws.cell(rr, 9).font = b
    for rr in (3, 4, 5): ws.cell(rr, 10).number_format = "#,##0.00"
    for col, w in zip("ABCDEFGHIJ", (36, 14, 14, 18, 20, 14, 18, 3, 24, 18)): ws.column_dimensions[col].width = w
    ws.row_dimensions[20].height = 45
    wb.save(f"{OUT}/DB_Pension_Reperformance_Check.xlsx")


if __name__ == "__main__":
    results = run_model()
    print_results(results)
    make_charts(results)
    make_excel(results)
    print(f"\nDone. Charts, Excel check and members.csv saved in the folder: {OUT}")
