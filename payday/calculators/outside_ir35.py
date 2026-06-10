from payday.constants import PERSONAL_ALLOWANCE
from payday.national_insurance import calc_employer_ni
from payday.corporation_tax import calc_corporation_tax
from payday.dividend_tax import calc_dividend_tax
from payday.models import SalaryBreakdown, StepLine


class OutsideIR35Calculator:
    @staticmethod
    def calculate(day_rate: int, working_days: int) -> SalaryBreakdown:
        """Outside IR35: Revenue → CT → dividends → tax → 20-day.
        IR35 context: https://www.gov.uk/guidance/understanding-off-payroll-working-ir35
        """
        revenue = day_rate * working_days

        # Tax-optimal salary for Outside IR35 is £12,570 (Primary Threshold)
        # 2026/27 Secondary Threshold is £5,000, so Employer NI will be due.
        # Income Tax: https://www.gov.uk/income-tax-rates
        # Employer NI: https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027
        salary = PERSONAL_ALLOWANCE
        er_ni_result = calc_employer_ni(salary)

        profit = revenue - salary - er_ni_result.total_er_ni
        ct_result = calc_corporation_tax(
            profit
        )  # https://www.gov.uk/corporation-tax-rates

        post_tax_profit = profit - ct_result.total_ct

        # Assume all distributed as dividends (clamped to zero if loss-making)
        dividends = max(0, post_tax_profit)
        div_tax_result = calc_dividend_tax(
            dividends, salary
        )  # https://www.gov.uk/tax-on-dividends

        # Take-home = Salary + (Dividends - Dividend Tax)
        # Note: at £12,570 salary, Income Tax and EE NI are both zero.
        net_dividends = dividends - div_tax_result.total_tax
        take_home = salary + net_dividends

        take_home_20_day = round(take_home / working_days * 20)

        steps = [
            StepLine("Company Revenue", revenue),
            StepLine(
                "Director Salary", -salary, indent=1
            ),  # https://www.gov.uk/income-tax-rates
            StepLine(
                "Employer NI (15%)", -er_ni_result.total_er_ni, indent=1
            ),  # https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027
            StepLine("Company Profit", profit, is_subtotal=True),
            StepLine(
                "Corporation Tax", -ct_result.total_ct, indent=1
            ),  # https://www.gov.uk/corporation-tax-rates
            StepLine("Distributable Profit", post_tax_profit, is_subtotal=True),
            StepLine(
                "Dividend Tax", -div_tax_result.total_tax, indent=1
            ),  # https://www.gov.uk/tax-on-dividends
            StepLine("Take-Home", take_home, is_subtotal=True),
            StepLine("20-Day Take-Home", take_home_20_day),
        ]

        return SalaryBreakdown(
            mode="Outside IR35",
            inputs={"day_rate": day_rate, "working_days": working_days},
            steps=steps,
            annual_take_home=take_home,
            display_take_home=take_home_20_day,
            employer_ni=er_ni_result,
            corporation_tax=ct_result,
            dividend_tax=div_tax_result,
        )
