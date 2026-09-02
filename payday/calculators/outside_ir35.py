from payday.annual_allowance import (
    calc_annual_allowance,
    find_max_pension_for_funcs,
)
from payday.constants import (
    EMPLOYMENT_ALLOWANCE,
    MAX_SALARY_SACRIFICE,
    PERSONAL_ALLOWANCE,
    VAT_FLAT_RATE_DEFAULT,
    VAT_STANDARD_RATE,
)
from payday.hicbc import apply_hicbc_inputs, hicbc_result_and_steps
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
        vat_registered: bool = False,
        vat_scheme: str | None = None,
        vat_flat_rate: float | None = None,
        region: str | None = None,
        student_loan_plan: str | None = None,
        postgraduate_loan: bool = False,
        has_child_benefit: bool = False,
        num_children: int = 1,
        ni_category: str = "A",
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
        VAT Flat Rate Scheme: https://www.gov.uk/vat-flat-rate-scheme
        VAT Flat Rate — how much you pay: https://www.gov.uk/vat-flat-rate-scheme/how-much-you-pay
        VAT Notice 733 (Flat Rate Scheme): https://www.gov.uk/guidance/flat-rate-scheme-for-small-businesses-vat-notice-733--2
        BIM31585 (Computation of trading profits — flat rate): https://www.gov.uk/hmrc-internal-manuals/business-income-manual/bim31585

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
        *vat_registered* when True enables VAT modelling. *vat_scheme* is
        ``"standard"`` (cash-neutral, no profit effect), ``"flat_rate"``
        (charges 20% VAT to client, pays *vat_flat_rate* on VAT-inclusive
        turnover to HMRC, keeps the difference as taxable trading income —
        see BIM31585), or ``"none"`` (default, not VAT-registered). When
        *vat_scheme* is ``"flat_rate"``, *vat_flat_rate* is the flat-rate
        % as a decimal (default 0.165 = 16.5% limited cost trader since
        1 Apr 2017 per VAT Notice 733 ¶4.4; sector rates 4%–14.5% otherwise).
        The flat-rate surplus is taxable for Corporation Tax and flows into
        Company Profit before CT (BIM31585).
        *region* is ``"scotland"`` for Scottish Income Tax on the salary
        slice; dividends always use UK rates.
        *existing_income* is income already earned in this tax year. It reduces
        the remaining Personal Allowance, rate bands and student loan threshold
        available for dividends.
        *existing_dividends* is dividends already received this tax year.
        *effective_days* if provided, overrides the pro-rated working_days count.
        *student_loan_plan* is ``"plan1"/"plan2"/"plan4"/"plan5"`` or ``None``.
        *postgraduate_loan* stacks a 6% Postgraduate Loan (Plan 3) repayment on top
        (England & Wales only).
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
        if vat_scheme is not None and vat_scheme not in (
            "standard",
            "flat_rate",
            "none",
        ):
            raise ValueError("vat_scheme must be 'standard', 'flat_rate', or 'none'")
        if vat_flat_rate is not None and not (0 < float(vat_flat_rate) < 1):
            raise ValueError("vat_flat_rate must be between 0 and 1")

        months, prorated_days, period_label = pro_rate_contract(
            working_days, start_month
        )
        if effective_days is None:
            effective_days = prorated_days

        revenue = day_rate * effective_days

        # VAT Flat Rate Scheme — profit from keeping the difference between
        # 20% VAT charged to client and the lower flat-rate % paid to HMRC
        # on VAT-inclusive turnover (gross = revenue × 1.2).
        # Only when vat_registered + flat_rate; standard scheme is cash-neutral.
        # Surplus = VAT charged (revenue × 20%) − flat payment (gross × flat_rate)
        #         = revenue × 0.20 − revenue × 1.2 × flat_rate
        #         = gross × (1/6 − flat_rate). Taxable as trading income
        # per BIM31585 (turnover = net + surplus; e.g. gross 84k, VAT 14k,
        # flat 6% → payment 5,040, turnover 78,960 = 70k net + 8,960 surplus).
        # See https://www.gov.uk/vat-flat-rate-scheme/how-much-you-pay
        # and BIM31585 (flat_rate VAT is taxable trading income).
        flat_rate = (
            VAT_FLAT_RATE_DEFAULT if vat_flat_rate is None else float(vat_flat_rate)
        )
        if vat_registered and vat_scheme == "flat_rate":
            vat_profit = round(
                revenue * VAT_STANDARD_RATE
                - revenue * (1 + VAT_STANDARD_RATE) * flat_rate
            )
            # Surplus can be small (e.g. 16.5% limited cost → £240 on £120k)
            # or even negative if flat_rate > 16.666%; negative reduces profit.
        else:
            vat_profit = 0

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
        # company profit (and therefore CT). Capped at the tapered Annual
        # Allowance (£60k standard, £10k floor when threshold>£200k and
        # adjusted>£260k). Use binary search with correct threshold/
        # adjusted functions since dividends (and thus threshold) depend
        # on the pension.
        pension_requested = min(director_pension, MAX_SALARY_SACRIFICE)
        if pension_requested and not _aa_recursed:
            thr_cache: dict[int, int] = {}

            def _thr_out(p: int) -> int:
                cached = thr_cache.get(p)
                if cached is not None:
                    return cached
                prof = (
                    revenue + vat_profit - salary - er_ni_total - p - company_expenses
                )
                if prof <= 0:
                    divs = 0
                else:
                    ct = calc_corporation_tax(prof).total_ct
                    divs = max(0, prof - ct - min(retained_profit, max(0, prof - ct)))
                thr = round(
                    salary + divs + other_income + existing_income + existing_dividends
                )
                thr_cache[p] = thr
                return thr

            def _adj_out(p: int) -> int:
                return _thr_out(p) + p

            max_allowed = find_max_pension_for_funcs(
                _thr_out, _adj_out, cap=pension_requested
            )
            if pension_requested > max_allowed:
                return OutsideIR35Calculator.calculate(
                    day_rate=day_rate,
                    working_days=working_days,
                    start_month=start_month,
                    existing_income=existing_income,
                    existing_dividends=existing_dividends,
                    other_income=other_income,
                    effective_days=effective_days,
                    director_salary=director_salary,
                    director_pension=max_allowed,
                    company_expenses=company_expenses,
                    retained_profit=retained_profit,
                    employment_allowance=employment_allowance,
                    vat_registered=vat_registered,
                    vat_scheme=vat_scheme,
                    vat_flat_rate=flat_rate,
                    region=region,
                    student_loan_plan=student_loan_plan,
                    postgraduate_loan=postgraduate_loan,
                    has_child_benefit=has_child_benefit,
                    num_children=num_children,
                    ni_category=ni_category,
                    _aa_recursed=True,
                )
            pension = pension_requested
        else:
            pension = pension_requested

        # Company running costs (accountancy, insurance, software, etc.)
        # are allowable expenses reducing profit before Corporation Tax.
        expenses = company_expenses

        profit = revenue + vat_profit - salary - er_ni_total - pension - expenses
        ct_result = calc_corporation_tax(profit)

        post_tax_profit = profit - ct_result.total_ct

        # Retained profit — clamped to distributable profit (cannot retain more
        # than is available; loss-making companies retain nothing extra beyond
        # the fact that dividends already clamp to 0).
        retained = min(retained_profit, max(0, post_tax_profit))

        # Assume all remaining distributable profit distributed as dividends
        # (clamped to zero if loss-making / fully retained).
        dividends = max(0, post_tax_profit - retained)

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
        ee_ni_result = calc_employee_ni(salary, ni_category)

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
        if vat_profit:
            steps.append(
                StepLine(
                    f"Flat Rate VAT Surplus ({flat_rate:.1%})", vat_profit, indent=1
                )
            )
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
            steps.append(
                StepLine("Postgraduate Loan (Plan 3)", -pgl_result.repayment, indent=1)
            )
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
        if ni_category.upper() != "A":
            inputs["ni_category"] = ni_category.upper()
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
        if vat_registered:
            inputs["vat_registered"] = True
            inputs["vat_scheme"] = vat_scheme or "none"
            if vat_scheme == "flat_rate":
                inputs["vat_flat_rate"] = flat_rate
                inputs["vat_profit"] = vat_profit
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
        apply_hicbc_inputs(inputs, hicbc_result, has_child_benefit)

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
            hicbc=hicbc_result,
        )
