from payday.income_tax import (
    calc_adjusted_net_income,
    calc_personal_allowance,
    calc_income_tax,
)
from payday.national_insurance import calc_employee_ni
from payday.pension import calc_pension
from payday.models import SalaryBreakdown, StepLine


class PAYECalculator:
    @staticmethod
    def calculate(salary: int, salary_sacrifice: int = 0) -> SalaryBreakdown:
        """PAYE: Gross → IT + EE NI + Pension → take-home (monthly).
        Income Tax: https://www.gov.uk/income-tax-rates
        Employee NI: https://www.gov.uk/government/publications/rates-and-allowances-national-insurance-contributions/rates-and-allowances-national-insurance-contributions
        Pension: https://www.gov.uk/workplace-pensions/what-you-your-employer-and-the-government-pay
        """
        effective_gross = salary - salary_sacrifice

        ani = calc_adjusted_net_income(employment_income=effective_gross)
        pa, tapered = calc_personal_allowance(ani)
        it_result = calc_income_tax(effective_gross, pa)
        ni_result = calc_employee_ni(effective_gross)
        pension_result = calc_pension(effective_gross)

        annual_take_home = (
            effective_gross
            - it_result.total_tax
            - ni_result.total_ni
            - pension_result.employee_contribution
        )
        monthly_take_home = annual_take_home // 12

        pa_label = "Personal Allowance" + (" (tapered)" if tapered else "")

        steps = [
            StepLine("Annual Gross Salary", salary),
        ]

        if salary_sacrifice:
            steps.append(StepLine("Salary Sacrifice", -salary_sacrifice, indent=1))
            steps.append(
                StepLine("Adjusted Gross Salary", effective_gross, is_subtotal=True)
            )

        steps += [
            StepLine(pa_label, -pa, indent=1),
            StepLine("Taxable Income", it_result.taxable_income, indent=1),
            StepLine("Income Tax", -it_result.total_tax, indent=1),
            StepLine("National Insurance", -ni_result.total_ni, indent=1),
            StepLine(
                "Pension Contribution", -pension_result.employee_contribution, indent=1
            ),
            StepLine("Annual Take-Home", annual_take_home, is_subtotal=True),
            StepLine("Monthly Take-Home", monthly_take_home),
        ]

        inputs: dict = {"salary": salary}
        if salary_sacrifice:
            inputs["salary_sacrifice"] = salary_sacrifice

        return SalaryBreakdown(
            mode="PAYE",
            inputs=inputs,
            steps=steps,
            annual_take_home=annual_take_home,
            display_take_home=monthly_take_home,
            income_tax=it_result,
            employee_ni=ni_result,
            pension=pension_result,
        )
