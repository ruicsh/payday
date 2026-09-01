from payday.annual_allowance import (
    calc_annual_allowance,
    find_max_pension_for_threshold,
)
from payday.income_tax import (
    calc_adjusted_net_income,
    calc_personal_allowance,
    calc_income_tax,
)
from payday.national_insurance import calc_employee_ni
from payday.pension import calc_pension
from payday.student_loan import calc_postgraduate_loan, calc_student_loan
from payday.hicbc import apply_hicbc_inputs, hicbc_result_and_steps
from payday.models import PensionResult, SalaryBreakdown, StepLine


class PAYECalculator:
    @staticmethod
    def calculate(
        salary: int,
        salary_sacrifice: int = 0,
        other_income: float = 0,
        region: str | None = None,
        student_loan_plan: str | None = None,
        postgraduate_loan: bool = False,
        has_child_benefit: bool = False,
        num_children: int = 1,
    ) -> SalaryBreakdown:
        """PAYE: Gross → IT + EE NI + Pension + Student Loan → take-home (monthly).
        Income Tax: https://www.gov.uk/income-tax-rates
        Scottish Income Tax: https://www.gov.uk/scottish-income-tax
        Employee NI: https://www.gov.uk/government/publications/rates-and-allowances-national-insurance-contributions/rates-and-allowances-national-insurance-contributions
        Pension: https://www.gov.uk/workplace-pensions/what-you-your-employer-and-the-government-pay
        Pension Annual Allowance: https://www.gov.uk/tax-on-your-private-pension/annual-allowance
        Tapered Annual Allowance: https://www.gov.uk/guidance/pension-schemes-work-out-your-tapered-annual-allowance
        Student Loan: https://www.gov.uk/repaying-your-student-loan/what-you-pay

        *other_income* is all other taxable income (savings, property, etc.)
        for the tax year. It reduces the remaining Personal Allowance /
        rate bands and feeds the Annual Allowance taper.
        *region* is ``"scotland"`` for Scottish rates, anything else for rUK.
        *student_loan_plan* is ``"plan1"/"plan2"/"plan4"/"plan5"`` or ``None``.
        *postgraduate_loan* stacks a 6% Postgraduate Loan repayment on top.
        """
        # Annual Allowance taper — cap salary sacrifice when threshold/
        # adjusted income triggers the taper. Per-mode isolation: threshold
        # is salary + other_income (add-back cancels), adjusted = threshold
        # + sacrifice. See annual_allowance.py for HMRC definitions.
        aa_result = None
        if salary_sacrifice:
            threshold_income = round(salary + other_income)
            max_allowed = find_max_pension_for_threshold(threshold_income)
            if salary_sacrifice > max_allowed:
                salary_sacrifice = max_allowed
            adjusted_income = threshold_income + salary_sacrifice
            aa_result = calc_annual_allowance(threshold_income, adjusted_income)
        else:
            # No sacrifice: still compute AA for display when tapered (auto-enrolment).
            threshold_income = round(salary + other_income)
            # Pension input for AA when no sacrifice is the auto-enrolment amount.
            _tmp_pension = calc_pension(salary)
            pension_input = (
                _tmp_pension.employee_contribution + _tmp_pension.employer_contribution
            )
            adjusted_income = threshold_income + pension_input
            aa_result = calc_annual_allowance(threshold_income, adjusted_income)
            # Auto-enrolment is only ~£3.5k so it never exceeds AA; no capping needed.

        effective_gross = salary - salary_sacrifice

        ani = calc_adjusted_net_income(
            employment_income=round(effective_gross + other_income),
        )
        pa, tapered = calc_personal_allowance(ani)
        it_result = calc_income_tax(
            effective_gross, pa, existing_income=round(other_income), region=region
        )
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

        # Annual Allowance taper note — only when the allowance is tapered
        # below the standard £60k.
        if aa_result and aa_result.tapered:
            steps.append(
                StepLine(
                    f"Annual Allowance (tapered to £{aa_result.annual_allowance:,})",
                    0,
                    indent=1,
                )
            )

        # HICBC advisory (shared helper).
        hicbc_result, hicbc_steps = hicbc_result_and_steps(
            ani, has_child_benefit=has_child_benefit, num_children=num_children
        )
        steps.extend(hicbc_steps)

        year_taxable_income = round(effective_gross + other_income)

        steps += [
            StepLine("Annual Take-Home", annual_take_home, is_subtotal=True),
            StepLine("Monthly Take-Home", monthly_take_home),
            StepLine("Year Taxable Income", year_taxable_income, is_subtotal=True),
        ]

        inputs: dict = {"salary": salary}
        if other_income:
            inputs["other_income"] = other_income
        if aa_result and aa_result.tapered:
            inputs["annual_allowance"] = aa_result.annual_allowance
            inputs["threshold_income"] = aa_result.threshold_income
            inputs["adjusted_income"] = aa_result.adjusted_income
        if region == "scotland":
            inputs["region"] = "scotland"
        if salary_sacrifice:
            inputs["salary_sacrifice"] = salary_sacrifice
        if student_loan_plan:
            inputs["student_loan_plan"] = student_loan_plan
        if postgraduate_loan:
            inputs["postgraduate_loan"] = True
        apply_hicbc_inputs(inputs, hicbc_result, has_child_benefit)

        return SalaryBreakdown(
            mode="PAYE",
            inputs=inputs,
            steps=steps,
            annual_take_home=annual_take_home,
            display_take_home=monthly_take_home,
            year_taxable_income=year_taxable_income,
            income_tax=it_result,
            employee_ni=ni_result,
            pension=pension_result,
            annual_allowance=aa_result,
            student_loan=sl_result,
            postgraduate_loan=pgl_result,
            hicbc=hicbc_result,
        )
