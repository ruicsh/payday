from payday.constants import (
    APPRENTICESHIP_LEVY_RATE,
    NI_EMPLOYER_RATE,
    PENSION_EMPLOYER_RATE,
)
from payday.income_tax import calc_adjusted_net_income, calc_personal_allowance, calc_income_tax
from payday.national_insurance import calc_employee_ni, calc_employer_ni
from payday.pension import calc_pension
from payday.models import SalaryBreakdown, StepLine


class InsideIR35Calculator:
    @staticmethod
    def calculate(
        day_rate: int, working_days: int, umbrella_margin_weekly: int = 25
    ) -> SalaryBreakdown:
        """Inside IR35: Assignment → Er costs → gross → IT + EE NI + Pension → 20-day.
        IR35 context: https://www.gov.uk/guidance/understanding-off-payroll-working-ir35
        Umbrella company guidance: https://www.gov.uk/guidance/working-through-an-umbrella-company
        """
        if working_days <= 0:
            raise ValueError("working_days must be > 0")

        annual_assignment = day_rate * working_days

        # Calculate annual margin
        # Assuming 5 working days per week, so weeks = working_days / 5
        weeks = working_days / 5
        annual_margin = round(umbrella_margin_weekly * weeks)

        budget = annual_assignment - annual_margin

        # Solve for gross salary including Er NI, Levy, and Er Pension
        gross = InsideIR35Calculator.solve_gross_salary(budget)

        er_ni_result = calc_employer_ni(gross)
        levy = round(gross * APPRENTICESHIP_LEVY_RATE)
        pension_result = calc_pension(gross)

        ani = calc_adjusted_net_income(employment_income=gross)
        pa, tapered = calc_personal_allowance(ani)
        it_result = calc_income_tax(gross, pa)
        ee_ni_result = calc_employee_ni(gross)

        annual_take_home = (
            gross
            - it_result.total_tax
            - ee_ni_result.total_ni
            - pension_result.employee_contribution
        )
        take_home_20_day = round(annual_take_home / working_days * 20)

        pa_label = "Personal Allowance" + (" (tapered)" if tapered else "")

        steps = [
            StepLine("Assignment Rate", annual_assignment),
            StepLine("Umbrella Margin", -annual_margin, indent=1),
            StepLine(
                f"Employer NI ({int(NI_EMPLOYER_RATE * 100)}%)",
                -er_ni_result.total_er_ni,
                indent=1,
            ),
            StepLine(
                f"Apprenticeship Levy ({APPRENTICESHIP_LEVY_RATE * 100}%)",
                -levy,
                indent=1,
            ),
            StepLine(
                f"Employer Pension ({int(PENSION_EMPLOYER_RATE * 100)}%)",
                -pension_result.employer_contribution,
                indent=1,
            ),
            StepLine("Gross Salary", gross, is_subtotal=True),
            StepLine(pa_label, -pa, indent=1),
            StepLine("Taxable Income", it_result.taxable_income, indent=1),
            StepLine("Income Tax", -it_result.total_tax, indent=1),
            StepLine("Employee NI", -ee_ni_result.total_ni, indent=1),
            StepLine(
                "Pension Contribution", -pension_result.employee_contribution, indent=1
            ),
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
            pension=pension_result,
        )

    @staticmethod
    def solve_gross_salary(budget: int) -> int:
        """Closed-form solution for umbrella gross salary including pension.
        Budget = Gross + Er NI + Levy + Er Pension

        Case A: Gross <= 5000 (No Er NI, No Er Pension)
        Budget = Gross + Gross * 0.005 = 1.005 * Gross
        Limit: Budget <= 5000 * 1.005 = 5025

        Case B: 5000 < Gross <= 10000 (Er NI, No Er Pension)
        Budget = Gross + 0.15*(Gross - 5000) + 0.005*Gross = 1.155*Gross - 750
        Limit: Budget <= 1.155*10000 - 750 = 10800

        Case C: 10000 < Gross <= 50270 (Er NI, Er Pension 3% of qualifying)
        Budget = Gross + 0.15*(Gross - 5000) + 0.005*Gross + 0.03*(Gross - 6240)
        Budget = 1.155*Gross - 750 + 0.03*Gross - 187.20 = 1.185*Gross - 937.20
        Limit: Budget <= 1.185*50270 - 937.20 = 58632.75

        Case D: Gross > 50270 (Er NI, Er Pension capped)
        Budget = Gross + 0.15*(Gross - 5000) + 0.005*Gross + 0.03*(50270 - 6240)
        Budget = 1.155*Gross - 750 + 1320.90 = 1.155*Gross + 570.90
        """
        # Thresholds in terms of Budget
        if budget <= 5025:
            return round(budget / 1.005)

        if budget <= 10800:
            return round((budget + 750) / 1.155)

        if budget <= 58633:
            return round((budget + 937.20) / 1.185)

        return round((budget - 570.90) / 1.155)
