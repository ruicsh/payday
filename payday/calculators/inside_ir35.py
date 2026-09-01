from payday.annual_allowance import (
    calc_annual_allowance,
    find_max_pension_for_threshold,
)
from payday.constants import (
    APPRENTICESHIP_LEVY_RATE,
    NI_EMPLOYER_RATE,
    PENSION_EMPLOYER_RATE,
    PAYSTREAM_ADMIN_CHARGE_WEEKLY,
)
from payday.income_tax import (
    calc_adjusted_net_income,
    calc_personal_allowance,
    calc_income_tax,
)
from payday.national_insurance import calc_employee_ni, calc_employer_ni
from payday.pension import calc_pension
from payday.student_loan import calc_postgraduate_loan, calc_student_loan
from payday.models import SalaryBreakdown, StepLine, PensionResult
from payday.tax_year import pro_rate_contract


class InsideIR35Calculator:
    @staticmethod
    def calculate(
        day_rate: int,
        working_days: int,
        umbrella_margin_weekly: int = 25,
        start_month: int | None = None,
        existing_income: float = 0,
        existing_dividends: float = 0,
        other_income: float = 0,
        salary_sacrifice: int = 0,
        is_paystream: bool = False,
        sacrifice_frequency: str = "monthly",
        effective_days: int | None = None,
        region: str | None = None,
        student_loan_plan: str | None = None,
        postgraduate_loan: bool = False,
    ) -> SalaryBreakdown:
        """Inside IR35: Assignment → Er costs → gross → IT + EE NI + Pension + Student Loan → 20-day.
        IR35 context: https://www.gov.uk/guidance/understanding-off-payroll-working-ir35
        Umbrella company guidance: https://www.gov.uk/guidance/working-through-an-umbrella-company
        Scottish Income Tax: https://www.gov.uk/scottish-income-tax
        Student Loan: https://www.gov.uk/repaying-your-student-loan/what-you-pay

        *existing_income* is income already earned in this tax year. It reduces
        the remaining Personal Allowance, rate bands and student loan threshold
        available to this contract.
        *existing_dividends* is dividends already received this tax year.
        *effective_days* if provided, overrides the pro-rated working_days count.
        *is_paystream* selects the PayStream umbrella salary-sacrifice model
        (net-pay pot, employer-NI saving passed back as additional gross, plus
        a weekly admin charge). Otherwise a generic umbrella applies a direct
        gross reduction and retains the employer-cost saving.
        *sacrifice_frequency* is ``"monthly"`` (default) or ``"daily"`` and only
        affects the per-period breakdown line.
        *region* is ``"scotland"`` for Scottish rates, anything else for rUK.
        *student_loan_plan* is ``"plan1"/"plan2"/"plan4"/"plan5"`` or ``None``.
        *postgraduate_loan* stacks a 6% Postgraduate Loan repayment on top.
        """
        if working_days <= 0:
            raise ValueError("working_days must be > 0")

        months, prorated_days, period_label = pro_rate_contract(
            working_days, start_month
        )
        if effective_days is None:
            effective_days = prorated_days

        annual_assignment = day_rate * effective_days

        # Calculate annual margin
        # Assuming 5 working days per week, so weeks = effective_days / 5
        weeks = effective_days / 5
        annual_margin = round(umbrella_margin_weekly * weeks)

        budget = annual_assignment - annual_margin

        # Preserve original sacrifice for budget-exceed check, then cap
        # to the tapered Annual Allowance before solving gross.
        original_sacrifice = salary_sacrifice
        original_admin = (
            round(PAYSTREAM_ADMIN_CHARGE_WEEKLY * weeks)
            if is_paystream and original_sacrifice
            else 0
        )
        if original_sacrifice >= budget - original_admin:
            raise ValueError("salary_sacrifice exceeds available budget")

        # Annual Allowance taper — cap salary sacrifice when threshold/
        # adjusted income triggers the taper. Estimate threshold via gross
        # without sacrifice (per-mode isolation). For generic umbrellas
        # threshold = ref_gross + other + existing, which is exact; for
        # PayStream it is a close estimate (gross solved from sac_budget).
        if salary_sacrifice:
            ref_gross_estimate = InsideIR35Calculator.solve_gross_salary(budget)
            threshold_estimate = round(
                ref_gross_estimate + other_income + existing_income + existing_dividends
            )
            max_allowed = find_max_pension_for_threshold(threshold_estimate)
            if salary_sacrifice > max_allowed:
                salary_sacrifice = max_allowed

        # PayStream salary-sacrifice administration charge (weekly, incl. VAT).
        # Charged only when sacrificing through PayStream.
        admin_charge = 0
        if is_paystream and salary_sacrifice:
            admin_charge = round(PAYSTREAM_ADMIN_CHARGE_WEEKLY * weeks)

        er_ni_saving = 0
        ref_gross = 0

        if salary_sacrifice:
            if is_paystream:
                # Net-pay pot: the sacrifice (and admin charge) come off the
                # assignment before employer costs, so the employer NI reduction
                # is passed back to the contractor as additional gross pay.
                # G solves: A - S - M - admin = G + ER NI + Levy.
                sac_budget = (
                    annual_assignment - salary_sacrifice - annual_margin - admin_charge
                )
                gross = InsideIR35Calculator.solve_gross_salary(
                    sac_budget, include_er_pension=False
                )
                # Reference gross (no sacrifice) so the passed-back ER NI saving
                # can be shown as an explicit line.
                ref_budget = annual_assignment - annual_margin - admin_charge
                ref_gross = InsideIR35Calculator.solve_gross_salary(
                    ref_budget, include_er_pension=False
                )
                er_ni_saving = (
                    calc_employer_ni(ref_gross).total_er_ni
                    - calc_employer_ni(gross).total_er_ni
                )
            else:
                # Generic umbrella: a direct gross reduction. The employer NI
                # (and levy) saving is retained by the umbrella, not passed back.
                ref_gross = InsideIR35Calculator.solve_gross_salary(budget)
                gross = max(0, ref_gross - salary_sacrifice)

            effective_gross = gross
            er_ni_result = calc_employer_ni(gross)
            levy = round(gross * APPRENTICESHIP_LEVY_RATE)
            er_pension_contribution = 0
            pension_result = PensionResult(False, 0, 0, 0)
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

        # ANI includes all income for correct PA tapering; dividends don't consume rate bands.
        # Other income is treated as additional taxable income for ANI/PA purposes.
        ani = calc_adjusted_net_income(
            employment_income=round(effective_gross + existing_income + other_income),
            dividend_income=existing_dividends,
        )
        pa, tapered = calc_personal_allowance(ani)
        total_existing_for_pa = round(existing_income + other_income)
        it_result = calc_income_tax(
            effective_gross,
            pa,
            existing_income=total_existing_for_pa,
            region=region,
        )
        ee_ni_result = calc_employee_ni(effective_gross)

        sl_result = (
            calc_student_loan(effective_gross, student_loan_plan, existing_income)
            if student_loan_plan
            else None
        )
        pgl_result = (
            calc_postgraduate_loan(effective_gross, existing_income)
            if postgraduate_loan
            else None
        )
        sl_total = (sl_result.repayment if sl_result else 0) + (
            pgl_result.repayment if pgl_result else 0
        )

        # Annual Allowance result for display (per-mode isolation).
        if salary_sacrifice:
            threshold_income = round(
                effective_gross
                + salary_sacrifice
                + other_income
                + existing_income
                + existing_dividends
            )
            adjusted_income = round(threshold_income + salary_sacrifice)
            aa_result = calc_annual_allowance(threshold_income, adjusted_income)
        else:
            threshold_income = round(
                effective_gross + other_income + existing_income + existing_dividends
            )
            pension_input = (
                pension_result.employee_contribution
                + pension_result.employer_contribution
            )
            adjusted_income = round(threshold_income + pension_input)
            aa_result = calc_annual_allowance(threshold_income, adjusted_income)

        annual_take_home = (
            effective_gross - it_result.total_tax - ee_ni_result.total_ni - sl_total
        )

        year_taxable_income = round(
            effective_gross + existing_income + existing_dividends + other_income
        )
        take_home_20_day = round(annual_take_home / effective_days * 20)

        remaining_pa = max(0, pa - round(existing_income + other_income))
        pa_label = "Personal Allowance" + (" (tapered)" if tapered else "")

        if sacrifice_frequency == "daily":
            sacrifice_label = "Daily Sacrifice"
            sacrifice_divisor = effective_days
        else:
            sacrifice_label = "Monthly Sacrifice"
            sacrifice_divisor = months

        if salary_sacrifice:
            if is_paystream:
                steps = [
                    StepLine("Assignment Rate", annual_assignment),
                    StepLine("Salary Sacrifice", -salary_sacrifice, indent=1),
                    StepLine(
                        sacrifice_label,
                        -(salary_sacrifice // sacrifice_divisor),
                        indent=2,
                    ),
                    StepLine("Umbrella Margin", -annual_margin, indent=1),
                    StepLine("PayStream Admin Charge", -admin_charge, indent=1),
                    StepLine(
                        f"Employer NI ({int(NI_EMPLOYER_RATE * 100)}%)",
                        -calc_employer_ni(ref_gross).total_er_ni,
                        indent=1,
                    ),
                    StepLine(
                        "Employer NI saving (passed back)",
                        er_ni_saving,
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
                    StepLine("Salary Sacrifice", -salary_sacrifice, indent=1),
                    StepLine(
                        sacrifice_label,
                        -(salary_sacrifice // sacrifice_divisor),
                        indent=2,
                    ),
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

        if sl_result:
            steps.append(StepLine("Student Loan", -sl_result.repayment, indent=1))
        if pgl_result:
            steps.append(StepLine("Postgraduate Loan", -pgl_result.repayment, indent=1))

        if aa_result and aa_result.tapered:
            steps.append(
                StepLine(
                    f"Annual Allowance (tapered to £{aa_result.annual_allowance:,})",
                    0,
                    indent=1,
                )
            )

        steps += [
            StepLine("Annual Take-Home", annual_take_home, is_subtotal=True),
            StepLine("20-Day Take-Home", take_home_20_day),
            StepLine("Year Taxable Income", year_taxable_income, is_subtotal=True),
        ]

        inputs: dict = {
            "day_rate": day_rate,
            "working_days": working_days,
            "margin_weekly": umbrella_margin_weekly,
            "effective_working_days": effective_days,
        }
        if other_income:
            inputs["other_income"] = other_income
        if aa_result and aa_result.tapered:
            inputs["annual_allowance"] = aa_result.annual_allowance
            inputs["threshold_income"] = aa_result.threshold_income
            inputs["adjusted_income"] = aa_result.adjusted_income
        if region == "scotland":
            inputs["region"] = "scotland"
        if period_label:
            inputs["start_month"] = start_month
            inputs["contract_months"] = months
            inputs["contract_period"] = period_label
        if existing_income:
            inputs["existing_income"] = existing_income
        if existing_dividends:
            inputs["existing_dividends"] = existing_dividends
        if is_paystream:
            inputs["is_paystream"] = True
        if admin_charge:
            inputs["admin_charge"] = admin_charge
        if salary_sacrifice:
            inputs["salary_sacrifice"] = salary_sacrifice
            if is_paystream:
                inputs["er_ni_saving"] = er_ni_saving
        if student_loan_plan:
            inputs["student_loan_plan"] = student_loan_plan
        if postgraduate_loan:
            inputs["postgraduate_loan"] = True

        return SalaryBreakdown(
            mode="Inside IR35",
            inputs=inputs,
            steps=steps,
            annual_take_home=annual_take_home,
            display_take_home=take_home_20_day,
            year_taxable_income=year_taxable_income,
            income_tax=it_result,
            employee_ni=ee_ni_result,
            employer_ni=er_ni_result,
            pension=pension_result,
            annual_allowance=aa_result,
            student_loan=sl_result,
            postgraduate_loan=pgl_result,
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
