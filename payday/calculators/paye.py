from payday.income_tax import (
    calc_adjusted_net_income,
    calc_personal_allowance,
    calc_income_tax,
)
from payday.national_insurance import calc_employee_ni
from payday.pension import calc_pension
from payday.student_loan import calc_postgraduate_loan, calc_student_loan
from payday.models import SalaryBreakdown, StepLine, PensionResult


class PAYECalculator:
    @staticmethod
    def calculate(
        salary: int,
        salary_sacrifice: int = 0,
        region: str | None = None,
        student_loan_plan: str | None = None,
        postgraduate_loan: bool = False,
    ) -> SalaryBreakdown:
        """PAYE: Gross → IT + EE NI + Pension + Student Loan → take-home (monthly).
        Income Tax: https://www.gov.uk/income-tax-rates
        Scottish Income Tax: https://www.gov.uk/scottish-income-tax
        Employee NI: https://www.gov.uk/government/publications/rates-and-allowances-national-insurance-contributions/rates-and-allowances-national-insurance-contributions
        Pension: https://www.gov.uk/workplace-pensions/what-you-your-employer-and-the-government-pay
        Student Loan: https://www.gov.uk/repaying-your-student-loan/what-you-pay

        *region* is ``"scotland"`` for Scottish rates, anything else for rUK.
        *student_loan_plan* is ``"plan1"/"plan2"/"plan4"/"plan5"`` or ``None``.
        *postgraduate_loan* stacks a 6% Postgraduate Loan repayment on top.
        """
        effective_gross = salary - salary_sacrifice

        ani = calc_adjusted_net_income(employment_income=effective_gross)
        pa, tapered = calc_personal_allowance(ani)
        it_result = calc_income_tax(effective_gross, pa, region=region)
        ni_result = calc_employee_ni(effective_gross)
        if salary_sacrifice:
            pension_result = PensionResult(False, 0, 0, 0)
        else:
            pension_result = calc_pension(effective_gross)

        sl_result = (
            calc_student_loan(effective_gross, student_loan_plan)
            if student_loan_plan
            else None
        )
        pgl_result = (
            calc_postgraduate_loan(effective_gross) if postgraduate_loan else None
        )
        sl_total = (sl_result.repayment if sl_result else 0) + (
            pgl_result.repayment if pgl_result else 0
        )

        annual_take_home = (
            effective_gross
            - it_result.total_tax
            - ni_result.total_ni
            - pension_result.employee_contribution
            - sl_total
        )
        monthly_take_home = annual_take_home // 12

        pa_label = "Personal Allowance" + (" (tapered)" if tapered else "")

        steps = [
            StepLine("Annual Gross Salary", salary),
        ]

        if salary_sacrifice:
            steps.append(StepLine("Salary Sacrifice", -salary_sacrifice, indent=1))
            steps.append(
                StepLine("Monthly Sacrifice", -(salary_sacrifice // 12), indent=2)
            )
            steps.append(
                StepLine("Adjusted Gross Salary", effective_gross, is_subtotal=True)
            )

        steps += [
            StepLine(pa_label, -pa, indent=1),
            StepLine("Taxable Income", it_result.taxable_income, indent=1),
            StepLine("Income Tax", -it_result.total_tax, indent=1),
            StepLine("National Insurance", -ni_result.total_ni, indent=1),
        ]

        if not salary_sacrifice:
            steps.append(
                StepLine(
                    "Pension Contribution",
                    -pension_result.employee_contribution,
                    indent=1,
                )
            )

        if sl_result:
            steps.append(StepLine("Student Loan", -sl_result.repayment, indent=1))
        if pgl_result:
            steps.append(StepLine("Postgraduate Loan", -pgl_result.repayment, indent=1))

        steps += [
            StepLine("Annual Take-Home", annual_take_home, is_subtotal=True),
            StepLine("Monthly Take-Home", monthly_take_home),
        ]

        inputs: dict = {"salary": salary}
        if region == "scotland":
            inputs["region"] = "scotland"
        if salary_sacrifice:
            inputs["salary_sacrifice"] = salary_sacrifice
        if student_loan_plan:
            inputs["student_loan_plan"] = student_loan_plan
        if postgraduate_loan:
            inputs["postgraduate_loan"] = True

        return SalaryBreakdown(
            mode="PAYE",
            inputs=inputs,
            steps=steps,
            annual_take_home=annual_take_home,
            display_take_home=monthly_take_home,
            income_tax=it_result,
            employee_ni=ni_result,
            pension=pension_result,
            student_loan=sl_result,
            postgraduate_loan=pgl_result,
        )
