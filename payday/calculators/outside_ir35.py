from payday.annual_allowance import calc_annual_allowance
from payday.constants import (
    EMPLOYMENT_ALLOWANCE,
    MAX_SALARY_SACRIFICE,
    PERSONAL_ALLOWANCE,
)
from payday.income_tax import (
    calc_adjusted_net_income,
    calc_income_tax,
    calc_personal_allowance,
)
from payday.national_insurance import calc_employee_ni, calc_employer_ni
from payday.corporation_tax import calc_corporation_tax
from payday.dividend_tax import calc_dividend_tax
from payday.models import SalaryBreakdown, StepLine
from payday.student_loan import calc_postgraduate_loan, calc_student_loan
from payday.tax_year import pro_rate_contract


class OutsideIR35Calculator:
    @staticmethod
    def calculate(
        day_rate: int,
        working_days: int,
        start_month: int | None = None,
        existing_income: float = 0,
        existing_dividends: float = 0,
        other_income: float = 0,
        effective_days: int | None = None,
        director_salary: int | None = None,
        director_pension: int = 0,
        company_expenses: int = 0,
        retained_profit: int = 0,
        employment_allowance: bool = False,
        region: str | None = None,
        student_loan_plan: str | None = None,
        postgraduate_loan: bool = False,
        _aa_recursed: bool = False,
    ) -> SalaryBreakdown:
        """Outside IR35: Revenue → CT → dividends → tax → Student Loan → 20-day.
        IR35 context: https://www.gov.uk/guidance/understanding-off-payroll-working-ir35
        Income Tax: https://www.gov.uk/income-tax-rates
        Scottish Income Tax: https://www.gov.uk/scottish-income-tax
        Employer NI: https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027
        Employment Allowance: https://www.gov.uk/claim-employment-allowance
        Detailed guidance: https://www.gov.uk/government/publications/employment-allowance-more-detailed-guidance/single-director-companies-and-employment-allowance-further-employer-guidance
        HMRC manual: https://www.gov.uk/hmrc-internal-manuals/national-insurance-manual/nim06545
        Corporation Tax: https://www.gov.uk/corporation-tax-rates
        Dividend Tax: https://www.gov.uk/tax-on-dividends
        Student Loan: https://www.gov.uk/repaying-your-student-loan/what-you-pay

        *director_salary* is the annual director salary (default £12,570 —
        the Primary Threshold). Values above the threshold incur Income Tax
        and Employee NI on the salary itself (Scottish rates apply when
        *region* is ``"scotland"``). Values below £5,000 incur zero Employer NI.
        *company_expenses* are annual allowable company running costs
        (accountancy, insurance, software, etc.) deducted before Corporation Tax.
        See https://www.gov.uk/expenses-if-youre-self-employed and
        https://www.gov.uk/limited-company-expenses
        *retained_profit* is profit retained in the company and not
        distributed as dividends (subject to CT, defers dividend tax).
        *employment_allowance* when True reduces Employer NI by up to
        £10,500 (2026/27). Single-director companies (sole director as only
        employee) cannot claim. See single-director guidance above.
        *region* is ``"scotland"`` for Scottish Income Tax on the salary
        slice; dividends always use UK rates.
        *existing_income* is income already earned in this tax year. It reduces
        the remaining Personal Allowance, rate bands and student loan threshold
        available for dividends.
        *existing_dividends* is dividends already received this tax year.
        *effective_days* if provided, overrides the pro-rated working_days count.
        *student_loan_plan* is ``"plan1"/"plan2"/"plan4"/"plan5"`` or ``None``.
        *postgraduate_loan* stacks a 6% Postgraduate Loan repayment on top.
        Outside IR35 repayments are modelled as Self Assessment on total
        personal income (salary + dividends); the repayment base includes
        existing income/dividends already earned this tax year.
        """
        if working_days <= 0:
            raise ValueError("working_days must be > 0")
        if director_salary is not None and director_salary < 0:
            raise ValueError("director_salary must be >= 0")
        if company_expenses < 0:
            raise ValueError("company_expenses must be >= 0")
        if retained_profit < 0:
            raise ValueError("retained_profit must be >= 0")

        months, prorated_days, period_label = pro_rate_contract(
            working_days, start_month
        )
        if effective_days is None:
            effective_days = prorated_days

        revenue = day_rate * effective_days

        # Director salary — default is £12,570 (Primary Threshold / Personal Allowance),
        # the tax-optimal salary for a single-director Ltd. Configurable via
        # director_salary. See https://www.gov.uk/guidance/rates-and-thresholds-for-employers-2026-to-2027
        salary = PERSONAL_ALLOWANCE if director_salary is None else director_salary
        er_ni_gross_result = calc_employer_ni(salary)

        # Employment Allowance — £10,500 for 2026/27, opt-in.
        # Single-director companies (sole director as only employee) cannot claim:
        # https://www.gov.uk/government/publications/employment-allowance-more-detailed-guidance/single-director-companies-and-employment-allowance-further-employer-guidance
        er_ni_total = er_ni_gross_result.total_er_ni
        ea_used = 0
        if employment_allowance:
            ea_used = min(er_ni_total, EMPLOYMENT_ALLOWANCE)
            er_ni_total = er_ni_total - ea_used

        # Director pension contributions are an allowable expense that reduces
        # company profit (and therefore CT). Capped at the standard Annual
        # Allowance (£60k); tapered AA is enforced below after profit is known.
        pension = min(director_pension, MAX_SALARY_SACRIFICE)

        # Company running costs (accountancy, insurance, software, etc.)
        # are allowable expenses reducing profit before Corporation Tax.
        expenses = company_expenses

        profit = revenue - salary - er_ni_total - pension - expenses
        ct_result = calc_corporation_tax(profit)

        post_tax_profit = profit - ct_result.total_ct

        # Retained profit — clamped to distributable profit (cannot retain more
        # than is available; loss-making companies retain nothing extra beyond
        # the fact that dividends already clamp to 0).
        retained = min(retained_profit, max(0, post_tax_profit))

        # Assume all remaining distributable profit distributed as dividends
        # (clamped to zero if loss-making / fully retained).
        dividends = max(0, post_tax_profit - retained)

        # Annual Allowance taper — when threshold/adjusted income triggers
        # the taper, cap the pension. Need dividends to compute threshold
        # so we check here; recurse once with the tapered allowance when
        # the requested pension exceeds it (per-mode isolation).
        if pension and not _aa_recursed:
            threshold_income = round(
                salary + dividends + other_income + existing_income + existing_dividends
            )
            adjusted_income = round(threshold_income + pension)
            aa_check = calc_annual_allowance(threshold_income, adjusted_income)
            if pension > aa_check.annual_allowance:
                return OutsideIR35Calculator.calculate(
                    day_rate=day_rate,
                    working_days=working_days,
                    start_month=start_month,
                    existing_income=existing_income,
                    existing_dividends=existing_dividends,
                    other_income=other_income,
                    effective_days=effective_days,
                    director_salary=director_salary,
                    director_pension=aa_check.annual_allowance,
                    company_expenses=company_expenses,
                    retained_profit=retained_profit,
                    employment_allowance=employment_allowance,
                    region=region,
                    student_loan_plan=student_loan_plan,
                    postgraduate_loan=postgraduate_loan,
                    _aa_recursed=True,
                )

        # Personal Allowance depends on total adjusted net income (salary +
        # dividends + existing + other). Computed here for the salary income-tax
        # slice and to keep stacking consistent with dividend_tax (which
        # recomputes it internally from the same inputs).
        ani = calc_adjusted_net_income(
            employment_income=round(salary + existing_income + other_income),
            dividend_income=dividends + existing_dividends,
        )
        pa, _tapered = calc_personal_allowance(ani)

        # Income Tax + Employee NI on the salary slice (zero when <= PA / PT).
        # Mirrors inside_ir35.py which computes IT + EE NI on gross salary.
        it_result = calc_income_tax(
            salary,
            pa,
            existing_income=round(existing_income + other_income),
            region=region,
        )
        ee_ni_result = calc_employee_ni(salary)

        div_tax_result = calc_dividend_tax(
            dividends,
            salary,
            existing_income=round(existing_income + other_income),
            existing_dividends=existing_dividends,
        )

        # Annual Allowance (for display) — threshold is total income
        # (salary + dividends + other + existing), adjusted adds pension.
        threshold_income = round(
            salary + dividends + other_income + existing_income + existing_dividends
        )
        adjusted_income = round(threshold_income + pension)
        aa_result = calc_annual_allowance(threshold_income, adjusted_income)

        # Take-home = salary (net of IT + EE NI) + net dividends - Student Loan.
        # Student loan via Self Assessment is on total income (salary + dividends).
        net_dividends = dividends - div_tax_result.total_tax
        total_personal_income = salary + dividends
        existing_total = existing_income + existing_dividends

        sl_result = (
            calc_student_loan(total_personal_income, student_loan_plan, existing_total)
            if student_loan_plan
            else None
        )
        pgl_result = (
            calc_postgraduate_loan(total_personal_income, existing_total)
            if postgraduate_loan
            else None
        )
        sl_total = (sl_result.repayment if sl_result else 0) + (
            pgl_result.repayment if pgl_result else 0
        )

        take_home = (
            salary
            - it_result.total_tax
            - ee_ni_result.total_ni
            + net_dividends
            - sl_total
        )

        take_home_20_day = (
            round(take_home / effective_days * 20) if effective_days else 0
        )

        year_taxable_income = round(
            salary + dividends + existing_income + existing_dividends + other_income
        )

        steps = [
            StepLine("Company Revenue", revenue),
            StepLine("Director Salary", -salary, indent=1),
            StepLine("Employer NI (15%)", -er_ni_gross_result.total_er_ni, indent=1),
        ]
        if ea_used:
            steps.append(StepLine("Employment Allowance", ea_used, indent=1))
        if expenses:
            steps.append(StepLine("Company Expenses", -expenses, indent=1))
        if pension:
            steps.append(StepLine("Director Pension", -pension, indent=1))
        steps += [
            StepLine("Company Profit", profit, is_subtotal=True),
            StepLine("Corporation Tax", -ct_result.total_ct, indent=1),
            StepLine("Distributable Profit", post_tax_profit, is_subtotal=True),
        ]
        if retained:
            steps.append(StepLine("Retained in Company", -retained, indent=1))
        # Salary income tax / NI only shown when non-zero (preserves existing output when salary = £12,570)
        if it_result.total_tax:
            steps.append(StepLine("Income Tax", -it_result.total_tax, indent=1))
        if ee_ni_result.total_ni:
            steps.append(StepLine("Employee NI", -ee_ni_result.total_ni, indent=1))
        steps.append(StepLine("Dividend Tax", -div_tax_result.total_tax, indent=1))
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
            StepLine("Take-Home", take_home, is_subtotal=True),
            StepLine("20-Day Take-Home", take_home_20_day),
            StepLine("Year Taxable Income", year_taxable_income, is_subtotal=True),
        ]

        inputs: dict = {
            "day_rate": day_rate,
            "working_days": working_days,
            "effective_working_days": effective_days,
            "salary": salary,
            "net_dividends": net_dividends,
        }
        if other_income:
            inputs["other_income"] = other_income
        if aa_result and aa_result.tapered:
            inputs["annual_allowance"] = aa_result.annual_allowance
            inputs["threshold_income"] = aa_result.threshold_income
            inputs["adjusted_income"] = aa_result.adjusted_income
        if pension:
            inputs["director_pension"] = pension
        if expenses:
            inputs["company_expenses"] = expenses
        if retained:
            inputs["retained_profit"] = retained
        if employment_allowance:
            inputs["employment_allowance"] = True
            if ea_used:
                inputs["employment_allowance_used"] = ea_used
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
        if student_loan_plan:
            inputs["student_loan_plan"] = student_loan_plan
        if postgraduate_loan:
            inputs["postgraduate_loan"] = True

        return SalaryBreakdown(
            mode="Outside IR35",
            inputs=inputs,
            steps=steps,
            annual_take_home=take_home,
            display_take_home=take_home_20_day,
            year_taxable_income=year_taxable_income,
            income_tax=it_result,
            employee_ni=ee_ni_result,
            employer_ni=er_ni_gross_result,
            corporation_tax=ct_result,
            dividend_tax=div_tax_result,
            annual_allowance=aa_result,
            student_loan=sl_result,
            postgraduate_loan=pgl_result,
        )
