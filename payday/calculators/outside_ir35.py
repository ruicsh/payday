from payday.constants import MAX_SALARY_SACRIFICE, PERSONAL_ALLOWANCE
from payday.national_insurance import calc_employer_ni
from payday.corporation_tax import calc_corporation_tax
from payday.dividend_tax import calc_dividend_tax
from payday.models import SalaryBreakdown, StepLine
from payday.tax_year import pro_rate_contract


class OutsideIR35Calculator:
    @staticmethod
    def calculate(
        day_rate: int,
        working_days: int,
        start_month: int | None = None,
        existing_income: float = 0,
        existing_dividends: float = 0,
        effective_days: int | None = None,
        director_pension: int = 0,
    ) -> SalaryBreakdown:
        """Outside IR35: Revenue → CT → dividends → tax → 20-day.
        IR35 context: https://www.gov.uk/guidance/understanding-off-payroll-working-ir35
        Income Tax: https://www.gov.uk/income-tax-rates
        Employer NI: https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027
        Corporation Tax: https://www.gov.uk/corporation-tax-rates
        Dividend Tax: https://www.gov.uk/tax-on-dividends

        *existing_income* is income already earned in this tax year. It reduces
        the remaining Personal Allowance and rate bands available for dividends.
        *existing_dividends* is dividends already received this tax year.
        *effective_days* if provided, overrides the pro-rated working_days count.
        """
        if working_days <= 0:
            raise ValueError("working_days must be > 0")

        months, prorated_days, period_label = pro_rate_contract(
            working_days, start_month
        )
        if effective_days is None:
            effective_days = prorated_days

        revenue = day_rate * effective_days

        # Tax-optimal salary for Outside IR35 is £12,570 (Primary Threshold)
        # 2026/27 Secondary Threshold is £5,000, so Employer NI will be due.
        salary = PERSONAL_ALLOWANCE
        er_ni_result = calc_employer_ni(salary)

        # Director pension contributions are an allowable expense that reduces
        # company profit (and therefore CT). Capped at £60k annual allowance.
        pension = min(director_pension, MAX_SALARY_SACRIFICE) if director_pension else 0

        profit = revenue - salary - er_ni_result.total_er_ni - pension
        ct_result = calc_corporation_tax(profit)

        post_tax_profit = profit - ct_result.total_ct

        # Assume all distributed as dividends (clamped to zero if loss-making)
        dividends = max(0, post_tax_profit)
        div_tax_result = calc_dividend_tax(
            dividends, salary, existing_income=existing_income
        )

        # Take-home = Salary + (Dividends - Dividend Tax)
        # Note: at £12,570 salary, Income Tax and EE NI are both zero.
        net_dividends = dividends - div_tax_result.total_tax
        take_home = salary + net_dividends

        take_home_20_day = round(take_home / effective_days * 20)

        year_taxable_income = round(
            salary + dividends + existing_income + existing_dividends
        )

        steps = [
            StepLine("Company Revenue", revenue),
            StepLine("Director Salary", -salary, indent=1),
            StepLine("Employer NI (15%)", -er_ni_result.total_er_ni, indent=1),
        ]
        if pension:
            steps.append(StepLine("Director Pension", -pension, indent=1))
        steps += [
            StepLine("Company Profit", profit, is_subtotal=True),
            StepLine("Corporation Tax", -ct_result.total_ct, indent=1),
            StepLine("Distributable Profit", post_tax_profit, is_subtotal=True),
            StepLine("Dividend Tax", -div_tax_result.total_tax, indent=1),
            StepLine("Take-Home", take_home, is_subtotal=True),
            StepLine("20-Day Take-Home", take_home_20_day),
            StepLine("Year Taxable Income", year_taxable_income, is_subtotal=True),
        ]

        inputs: dict = {
            "day_rate": day_rate,
            "working_days": working_days,
            "effective_working_days": effective_days,
        }
        if pension:
            inputs["director_pension"] = pension
        if period_label:
            inputs["start_month"] = start_month
            inputs["contract_months"] = months
            inputs["contract_period"] = period_label
        if existing_income:
            inputs["existing_income"] = existing_income
        if existing_dividends:
            inputs["existing_dividends"] = existing_dividends

        return SalaryBreakdown(
            mode="Outside IR35",
            inputs=inputs,
            steps=steps,
            annual_take_home=take_home,
            display_take_home=take_home_20_day,
            year_taxable_income=year_taxable_income,
            employer_ni=er_ni_result,
            corporation_tax=ct_result,
            dividend_tax=div_tax_result,
        )
