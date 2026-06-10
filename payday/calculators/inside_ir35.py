from payday.constants import APPRENTICESHIP_LEVY_RATE
from payday.income_tax import calc_personal_allowance, calc_income_tax
from payday.national_insurance import calc_employee_ni, calc_employer_ni
from payday.models import SalaryBreakdown, StepLine


class InsideIR35Calculator:
    @staticmethod
    def calculate(
        day_rate: int, working_days: int, umbrella_margin_weekly: int = 25
    ) -> SalaryBreakdown:
        """Inside IR35: Assignment → Er costs → gross → IT + EE NI → 20-day.
        # IR35 context: https://www.gov.uk/guidance/understanding-off-payroll-working-ir35
        # Umbrella company guidance: https://www.gov.uk/guidance/working-through-an-umbrella-company
        """
        annual_assignment = day_rate * working_days

        # Calculate annual margin
        # Assuming 5 working days per week, so weeks = working_days / 5
        weeks = working_days / 5
        annual_margin = round(umbrella_margin_weekly * weeks)

        budget = annual_assignment - annual_margin

        # Solve for gross salary
        # Employer NI 15% above £5k ST: https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027
        # Apprenticeship Levy 0.5%: https://www.gov.uk/guidance/pay-apprenticeship-levy
        gross = InsideIR35Calculator.solve_gross_salary(budget)

        er_ni_result = calc_employer_ni(gross)  # https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027
        levy = round(gross * APPRENTICESHIP_LEVY_RATE)  # https://www.gov.uk/guidance/pay-apprenticeship-levy

        pa, _ = calc_personal_allowance(gross)  # https://www.gov.uk/income-tax-rates
        it_result = calc_income_tax(gross, pa)  # https://www.gov.uk/income-tax-rates
        ee_ni_result = calc_employee_ni(gross)  # https://www.gov.uk/government/publications/rates-and-allowances-national-insurance-contributions/rates-and-allowances-national-insurance-contributions

        annual_take_home = gross - it_result.total_tax - ee_ni_result.total_ni
        take_home_20_day = round(annual_take_home / working_days * 20)

        steps = [
            StepLine("Assignment Rate", annual_assignment),
            StepLine("Umbrella Margin", -annual_margin, indent=1),
            StepLine("Employer NI (15%)", -er_ni_result.total_er_ni, indent=1),  # https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027
            StepLine("Apprenticeship Levy", -levy, indent=1),  # https://www.gov.uk/guidance/pay-apprenticeship-levy
            StepLine("Gross Salary", gross, is_subtotal=True),
            StepLine("Income Tax", -it_result.total_tax, indent=1),  # https://www.gov.uk/income-tax-rates
            StepLine("Employee NI", -ee_ni_result.total_ni, indent=1),  # https://www.gov.uk/government/publications/rates-and-allowances-national-insurance-contributions/rates-and-allowances-national-insurance-contributions
            StepLine("Annual Take-Home", annual_take_home, is_subtotal=True),
            StepLine("20-Day Take-Home", take_home_20_day),
        ]

        return SalaryBreakdown(
            mode="Inside IR35",
            inputs={
                "day_rate": day_rate,
                "working_days": working_days,
                "margin_weekly": umbrella_margin_weekly,
            },
            steps=steps,
            annual_take_home=annual_take_home,
            display_take_home=take_home_20_day,
            income_tax=it_result,
            employee_ni=ee_ni_result,
            employer_ni=er_ni_result,
        )

    @staticmethod
    def solve_gross_salary(budget: int) -> int:
        """Closed-form solution for umbrella gross salary.
        Source: https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027 (ER NI 15%, ST £5,000)
        Source: https://www.gov.uk/guidance/pay-apprenticeship-levy (Levy 0.5%)

        Budget = Gross + Employer NI + Apprenticeship Levy
        Employer NI = (Gross - 5000) * 0.15  (if Gross > 5000)
        Levy = Gross * 0.005

        If Gross > 5000:
        Budget = Gross + (Gross - 5000) * 0.15 + Gross * 0.005
        Budget = Gross + 0.15 * Gross - 750 + 0.005 * Gross
        Budget = Gross * (1 + 0.15 + 0.005) - 750
        Budget = Gross * 1.155 - 750
        Gross = (Budget + 750) / 1.155

        If Gross <= 5000:
        Budget = Gross + Gross * 0.005 = Gross * 1.005
        Gross = Budget / 1.005
        """
        # Threshold for budget where Gross would be 5000:
        # Budget = 5000 * 1.005 = 5025
        if budget <= 5025:
            return round(budget / 1.005)

        return round((budget + 750) / 1.155)
