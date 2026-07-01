from payday.constants import (
    APPRENTICESHIP_LEVY_RATE,
    NI_EMPLOYER_RATE,
    PENSION_EMPLOYER_RATE,
)
from payday.income_tax import (
    calc_adjusted_net_income,
    calc_personal_allowance,
    calc_income_tax,
)
from payday.national_insurance import calc_employee_ni, calc_employer_ni
from payday.pension import calc_pension
from payday.models import SalaryBreakdown, StepLine, PensionResult
from payday.tax_year import pro_rate_contract


class InsideIR35Calculator:
    @staticmethod
    def calculate(
        day_rate: int,
        working_days: int,
        umbrella_margin_weekly: int = 25,
        start_month: int | None = None,
        existing_income: int = 0,
        salary_sacrifice: int = 0,
    ) -> SalaryBreakdown:
        """Inside IR35: Assignment → Er costs → gross → IT + EE NI + Pension → 20-day.
        IR35 context: https://www.gov.uk/guidance/understanding-off-payroll-working-ir35
        Umbrella company guidance: https://www.gov.uk/guidance/working-through-an-umbrella-company

        *existing_income* is income already earned in this tax year. It reduces
        the remaining Personal Allowance and rate bands available to this contract.
        """
        if working_days <= 0:
            raise ValueError("working_days must be > 0")

        months, effective_days, period_label = pro_rate_contract(
            working_days, start_month
        )

        annual_assignment = day_rate * effective_days

        # Calculate annual margin
        # Assuming 5 working days per week, so weeks = effective_days / 5
        weeks = effective_days / 5
        annual_margin = round(umbrella_margin_weekly * weeks)

        budget = annual_assignment - annual_margin

        if salary_sacrifice >= budget:
            raise ValueError("salary_sacrifice exceeds available budget")

        if salary_sacrifice:
            # Budget after sacrifice and margin: this must cover gross + ER NI + Levy
            sac_budget = annual_assignment - salary_sacrifice - annual_margin
            gross = InsideIR35Calculator.solve_gross_salary(
                sac_budget, include_er_pension=False
            )

            effective_gross = gross
            er_ni_result = calc_employer_ni(gross)
            levy = round(gross * APPRENTICESHIP_LEVY_RATE)
            er_pension_contribution = 0
            pension_result = PensionResult(False, 0, 0, 0)

            # Informational: ER NI saving compared to what would have been paid
            baseline_gross = InsideIR35Calculator.solve_gross_salary(budget)
            baseline_er_ni = calc_employer_ni(baseline_gross).total_er_ni
            er_ni_saving = baseline_er_ni - er_ni_result.total_er_ni
        else:
            gross = InsideIR35Calculator.solve_gross_salary(budget)
            effective_gross = gross
            er_ni_result = calc_employer_ni(gross)
            levy = round(gross * APPRENTICESHIP_LEVY_RATE)
            er_pension = calc_pension(gross)
            ee_pension = calc_pension(effective_gross)
            er_pension_contribution = er_pension.employer_contribution
            pension_result = PensionResult(
                eligible=ee_pension.eligible,
                qualifying_earnings=ee_pension.qualifying_earnings,
                employee_contribution=ee_pension.employee_contribution,
                employer_contribution=er_pension.employer_contribution,
            )

        # ANI includes existing income for correct PA tapering
        ani = calc_adjusted_net_income(employment_income=effective_gross + existing_income)
        pa, tapered = calc_personal_allowance(ani)
        it_result = calc_income_tax(effective_gross, pa, existing_income=existing_income)
        ee_ni_result = calc_employee_ni(effective_gross)

        annual_take_home = effective_gross - it_result.total_tax - ee_ni_result.total_ni

        take_home_20_day = round(annual_take_home / effective_days * 20)

        remaining_pa = max(0, pa - existing_income)
        pa_label = "Personal Allowance" + (" (tapered)" if tapered else "")

        if salary_sacrifice:
            steps = [
                StepLine("Assignment Rate", annual_assignment),
                StepLine("Salary Sacrifice", -salary_sacrifice, indent=1),
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
                StepLine("Gross Salary", gross, is_subtotal=True),
            ]
        else:
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
                    -er_pension_contribution,
                    indent=1,
                ),
                StepLine("Gross Salary", gross, is_subtotal=True),
            ]

        steps += [
            StepLine(pa_label, -remaining_pa, indent=1),
            StepLine("Taxable Income", it_result.taxable_income, indent=1),
            StepLine("Income Tax", -it_result.total_tax, indent=1),
            StepLine("Employee NI", -ee_ni_result.total_ni, indent=1),
        ]

        if not salary_sacrifice:
            steps.append(
                StepLine(
                    "Pension Contribution",
                    -pension_result.employee_contribution,
                    indent=1,
                )
            )

        steps += [
            StepLine("Annual Take-Home", annual_take_home, is_subtotal=True),
            StepLine("20-Day Take-Home", take_home_20_day),
        ]

        inputs: dict = {
            "day_rate": day_rate,
            "working_days": working_days,
            "margin_weekly": umbrella_margin_weekly,
        }
        if period_label:
            inputs["start_month"] = start_month
            inputs["contract_months"] = months
            inputs["effective_working_days"] = effective_days
            inputs["contract_period"] = period_label
        if existing_income:
            inputs["existing_income"] = existing_income
        if salary_sacrifice:
            inputs["salary_sacrifice"] = salary_sacrifice
            inputs["er_ni_saving"] = er_ni_saving

        return SalaryBreakdown(
            mode="Inside IR35",
            inputs=inputs,
            steps=steps,
            annual_take_home=annual_take_home,
            display_take_home=take_home_20_day,
            income_tax=it_result,
            employee_ni=ee_ni_result,
            employer_ni=er_ni_result,
            pension=pension_result,
        )

    @staticmethod
    def solve_gross_salary(budget: int, include_er_pension: bool = True) -> int:
        """Closed-form solution for umbrella gross salary.
        Budget = Gross + Er NI + Levy (+ Er Pension, optional).

        Case A: Gross <= 5000 (No Er NI, No Er Pension)
        Budget = Gross + Gross * 0.005 = 1.005 * Gross
        Limit: Budget <= 5000 * 1.005 = 5025

        Case B: Gross > 5000 (Er NI, No Er Pension)
        Budget = Gross + 0.15*(Gross - 5000) + 0.005*Gross = 1.155*Gross - 750

        When include_er_pension=True, Case B is split further:

        Case C: 10000 < Gross <= 50270 (Er NI, Er Pension 3% of qualifying)
        Budget = Gross + 0.15*(Gross - 5000) + 0.005*Gross + 0.03*(Gross - 6240)
        Budget = 1.155*Gross - 750 + 0.03*Gross - 187.20 = 1.185*Gross - 937.20
        Limit: Budget <= 1.185*50270 - 937.20 = 58632.75

        Case D: Gross > 50270 (Er NI, Er Pension capped)
        Budget = Gross + 0.15*(Gross - 5000) + 0.005*Gross + 0.03*(50270 - 6240)
        Budget = 1.155*Gross - 750 + 1320.90 = 1.155*Gross + 570.90
        """
        if budget <= 5025:
            return round(budget / 1.005)

        if not include_er_pension:
            return round((budget + 750) / 1.155)

        # include_er_pension=True
        if budget <= 10800:
            return round((budget + 750) / 1.155)

        if budget <= 58633:
            return round((budget + 937.20) / 1.185)

        return round((budget - 570.90) / 1.155)
