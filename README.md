# Defined-Benefit-Pension-Funding-Longevity-Risk-Model
A Monte Carlo model that estimates whether a defined benefit (DB) pension scheme can afford its promised pensions, and how likely it is to be underfunded after 10 years. It values the scheme's liabilities with the Indian Individual Annuitant's Mortality Table (2012-15), simulates 10,000 paths of investment returns, and tests how longevity risk and employer contributions change the answer.
# 1. The question
A DB scheme promises each member a fixed pension for life, so the employer carries the risk if the money runs short. Three things drive that risk:
Investment returns are uncertain. Assets may grow less than expected.
Members may live longer than expected. Pensions are then paid for more years.
Contributions can be raised. The question is how much extra funding is needed.

The model answers: what is the probability that the scheme's funding level (assets divided by liabilities) is below 100% after 10 years, and how does that change with longevity and contributions?


## 2. Key results (base assumptions)

| Measure | Result |
|---|---|
| Liabilities today | ₹392.0 crore (6.1 times the yearly salary bill) |
| Starting funding level | 90% (assets ₹352.8 crore) |
| Life expectancy at 60 (IAI annuitant table) | 24.0 years |
| Median funding level after 10 years | 111.7% |
| Worst 5% of cases | 60.3% |
| **Probability of a funding deficit after 10 years** | **38.5%** |
| Liabilities if members live 2 years longer | +3.6% |
| Deficit probability with that longevity shock | 42.8% |
| Liabilities if the discount rate falls from 7% to 6% | +25.3% |
| Liabilities if the discount rate rises from 7% to 8% | -19.1% |

### Deficit probability by employer contribution rate

| Employer contribution (% of payroll) | Chance of a deficit after 10 years |
|---|---|
| 10% | 45.8% |
| 15% (base) | 38.5% |
| 20% | 31.6% |
| 25% | 24.9% |
| 30% | 19.7% |

Under these assumptions the scheme has about a 4 in 10 chance of being underfunded after 10 years, longer lives push that to about 43%, and contributions of around 30% of payroll reduce it to about 1 in 5.

### Charts

![Funding level over 10 years](chart1_funding_fan.png)

![Funding level at year 10](chart2_year10_distribution.png)

![Deficit probability by contribution rate](chart3_contributions.png)

## 3. How the model works

1. **Members.** 500 synthetic active members aged 30 to 59, with salaries around ₹12 lakh and service from age 22. Each earns a pension of 1/60 of final salary per year of service, payable from age 60.
2. **Mortality.** Annual death probabilities q(x) come from the Indian Individual Annuitant's Mortality Table (2012-15), ages 20 to 115. The chance of surviving t years is built from these rates.
3. **Liabilities.** The expected pension in each future year is the pension amount multiplied by the chance the member is alive. These are added across members and discounted at 7% to give today's liability.
4. **Asset simulation.** Each of 10,000 paths rolls assets forward: `assets(next year) = assets × (1 + random return) + contributions − pensions paid`. Returns are lognormal with 8% mean and 12% volatility.
5. **Funding level.** Assets divided by liabilities, recorded each year. The share of paths ending below 100% is the deficit probability.
6. **Longevity shock.** Members follow the mortality of people 2 years younger, which means they live longer. Liabilities and pension payments are recalculated.
7. **Contribution test.** The simulation is repeated at contribution rates from 10% to 30% of payroll.

## 4. Assumptions 

| Assumption | Value |
|---|---|
| Members | 500 (synthetic) |
| Retirement age | 60 |
| Pension accrual | 1/60 of final salary per year of service |
| Salary growth | 6% a year |
| Discount rate | 7% |
| Pension increases | 0% |
| Starting funding level | 90% |
| Asset return / volatility | 8% / 12% a year |
| Base employer contribution | 15% of payroll |
| Horizon / simulations | 10 years / 10,000 |
| Longevity shock | Mortality of people 2 years younger |
| Mortality table | Indian Individual Annuitant's Mortality Table (2012-15), Institute of Actuaries of India |




## 5. Validation

- **Reperformance in Excel.** One member (age 45, salary ₹12 lakh, 23 years of service) is valued in `DB_Pension_Reperformance_Check.xlsx` using live formulas and the IAI table. The Excel liability matches the Python result to the paisa: **₹73,15,529.96**.
- **Independent survival check.** The 15-year survival probability for the same member was recomputed directly from the table as a product of (1 − q), and agrees with the model to 13 decimal places.
- **Sensible outputs.** Life expectancy at 60 of 24.0 years, a longevity shock that raises liabilities, and a deficit probability that falls as contributions rise all move in the expected direction.

# 6. How to run
pip install numpy pandas matplotlib openpyxl
python db_pension_full.py

On Google Colab, upload db_pension_full.py and run !python db_pension_full.py.

**Outputs** are saved in a folder called `pension_outputs`:

| File | What it is |
|---|---|
| `chart1_funding_fan.png` | Funding level over 10 years, with percentile bands |
| `chart2_year10_distribution.png` | Distribution of funding levels at year 10 |
| `chart3_contributions.png` | Deficit probability against contribution rate |
| `DB_Pension_Reperformance_Check.xlsx` | One member's liability worked out with live Excel formulas |
| `members.csv` | The 500 synthetic members |

## 7. Limitations

- **Liabilities are an expected value.** Only asset returns are random. Interest rates, inflation and salary growth are fixed, so interest rate risk appears only as the discount-rate sensitivity.
- **Liabilities include future service.** Each member's full projected pension is valued, so contributions fund part of the liability. A real valuation would separate benefits already earned from those still to be earned.
- **The scheme is closed.** There are no new joiners, leavers, early retirements, death-in-service benefits or spouse pensions.
- **Mortality is fixed.** There is no future improvement in longevity beyond the 2-year shock, and no uncertainty in the mortality table itself.
- **Pensions are not indexed.** Increases in payment are set to 0%.
- **Returns are lognormal.** Real markets have fatter tails and volatility that changes over time.
- **The members are synthetic**, so results are illustrative and should not be read as a valuation of any real scheme.

## 8. Possible extensions

- Add stochastic interest rates and inflation, and value liabilities on a market-consistent basis.
- Add future mortality improvement, for example with a Lee-Carter model.
- Model an asset-liability matching strategy and its effect on funding-level volatility.
- Replace the lognormal returns with a GARCH model to capture changing volatility.


# 9. Data source

Mortality rates: Indian Individual Annuitant's Mortality Table (2012-15), published by the Institute of Actuaries of India (IAI), effective 1 April 2021. All other data (members, salaries, assets) are synthetic.
