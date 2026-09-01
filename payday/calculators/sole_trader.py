from payday.constants import MAX_SALARY_SACRIFICE
from payday.income_tax import (
    calc_adjusted_net_income,
    calc_personal_allowance,
    calc_income_tax,
)
from payday.national_insurance import calc_class4_ni
from payday.models import SalaryBreakdown, StepLine
from payday.student_loan import calc_postgraduate_loan, calc_student_loan
from payday.tax_year import pro_rate_contract


class SoleTraderCalculator:
    @staticmethod
    def calculate(
        day_rate: int,
        working_days: int,
        start_month: int | None = None,
        existing_income: float = 0,
        existing_self_employment: float = 0,
        business_expenses: int = 0,
        personal_pension: int = 0,
        effective_days: int | None = None,
        region: str | None = None,
        student_loan_plan: str | None = None,
        postgraduate_loan: bool = False,
    ) -> SalaryBreakdown:
        """Sole Trader (self-employed): Turnover → expenses → profit → IT + Class 4 NI → 20-day.
        Sole trader setup: https://www.gov.uk/set-up-sole-trader
        Self-employed National Insurance: https://www.gov.uk/self-employed-national-insurance-rates
        Rates and allowances: https://www.gov.uk/government/publications/rates-and-allowances-national-insurance-contributions/rates-and-allowances-national-insurance-contributions
        Income Tax: https://www.gov.uk/income-tax-rates
        Scottish Income Tax: https://www.gov.uk/scottish-income-tax
        Allowable expenses: https://www.gov.uk/expenses-if-youre-self-employed
        Pension tax relief: https://www.gov.uk/tax-on-your-private-pension/pension-tax-relief
        Annual allowance: https://www.gov.uk/tax-on-your-private-pension/annual-allowance
        Student Loan: https://www.gov.uk/repaying-your-student-loan/what-you-pay

        *existing_income* is employment income already earned this tax year.
        It reduces the remaining Personal Allowance and rate bands.
        *existing_self_employment* is self-employment profit already earned
        this tax year. It reduces PA/rate bands AND remaining Class 4 NI bands.
        *business_expenses* are allowable expenses deducted from turnover
        before profit (https://www.gov.uk/expenses-if-youre-self-employed).
        *personal_pension* is a net personal pension contribution (relief at
        source). Basic-rate relief (20%) is claimed by the provider; higher-rate
        relief is via the extended basic-rate band — modelled here as a
        straight deduction from taxable profit for income tax (not for Class 4,
        since Class 4 is on trading profit before pension).
        Annual allowance £60,000 (https://www.gov.uk/tax-on-your-private-pension/annual-allowance).
        *effective_days* if provided, overrides the pro-rated working_days count.
        *region* is ``"scotland"`` for Scottish rates, anything else for rUK.
        *student_loan_plan* is ``"plan1"/"plan2"/"plan4"/"plan5"`` or ``None``.
        *postgraduate_loan* stacks a 6% Postgraduate Loan repayment on top.
        Sole-trader student-loan repayments are via Self Assessment on total
        income (trading profit + existing income + existing self-employment).
        Class 2 NI is treated as paid above £7,105 (no compulsory charge
        since 6 Apr 2024) — only Class 4 (6%/2%) is deducted in take-home.
        """
        if working_days <= 0:
            raise ValueError("working_days must be > 0")
        if business_expenses < 0:
            raise ValueError("business_expenses must be >= 0")
        if personal_pension < 0:
            raise ValueError("personal_pension must be >= 0")

        months, prorated_days, period_label = pro_rate_contract(
            working_days, start_month
        )
        if effective_days is None:
            effective_days = prorated_days

        turnover = day_rate * effective_days
        trading_profit = max(0, turnover - business_expenses)

        # Personal pension: capped at annual allowance (£60k gross).
        # Input is treated as gross-equivalent for the cap; take-home
        # deducts the gross amount (pension provider claims 20% separately,
        # but from take-home perspective the full gross leaves your pocket
        # via net pay + reclaimed relief — model as straight deduction).
        pension = min(personal_pension, MAX_SALARY_SACRIFICE) if personal_pension else 0

        # Income Tax is on taxable profit (trading profit less pension).
        # Class 4 NI is on trading profit (pension is NOT an allowable
        # trading expense for NI — https://www.gov.uk/self-employed-national-insurance-rates).
        taxable_profit = max(0, trading_profit - pension)

        # ANI for PA taper: self-employment + employment, less relief-at-source
        # gross-up (pension net × 1.25). Use calc_adjusted_net_income helper.
        ani = calc_adjusted_net_income(
            employment_income=existing_income,
            self_employment_income=round(trading_profit + existing_self_employment),
            relief_at_source_pension=pension,
        )
        pa, tapered = calc_personal_allowance(ani)

        # Existing income for income tax bands: employment + prior self-employment
        existing_for_it = existing_income + existing_self_employment
        it_result = calc_income_tax(
            taxable_profit, pa, existing_income=existing_for_it, region=region
        )

        class4_result = calc_class4_ni(
            trading_profit, existing_self_employment=existing_self_employment
        )

        # Student loan via Self Assessment on total income (profit + existing).
        # Use taxable_profit as the current-year income for repayment calc
        # (pension already deducted), plus total existing.
        total_income_for_sl = taxable_profit
        existing_total = existing_income + existing_self_employment

        sl_result = (
            calc_student_loan(total_income_for_sl, student_loan_plan, existing_total)
            if student_loan_plan
            else None
        )
        pgl_result = (
            calc_postgraduate_loan(total_income_for_sl, existing_total)
            if postgraduate_loan
            else None
        )
        sl_total = (sl_result.repayment if sl_result else 0) + (
            pgl_result.repayment if pgl_result else 0
        )

        annual_take_home = (
            trading_profit
            - it_result.total_tax
            - class4_result.total_ni
            - sl_total
            - pension
        )
        # Clamp to 0 if loss-making after expenses/pension/tax?
        # Allow negative? Use max(0, ...) for display? Keep actual.
        take_home_20_day = (
            round(annual_take_home / effective_days * 20) if effective_days else 0
        )

        year_taxable_income = round(
            taxable_profit + existing_income + existing_self_employment
        )

        remaining_pa = max(0, pa - existing_for_it)
        pa_label = "Personal Allowance" + (" (tapered)" if tapered else "")

        steps = [
            StepLine("Turnover", turnover),
        ]
        if business_expenses:
            steps.append(StepLine("Business Expenses", -business_expenses, indent=1))
        steps.append(StepLine("Trading Profit", trading_profit, is_subtotal=True))
        if pension:
            steps.append(StepLine("Personal Pension", -pension, indent=1))
            steps.append(StepLine("Taxable Profit", taxable_profit, is_subtotal=True))
        steps += [
            StepLine(pa_label, -remaining_pa, indent=1),
            StepLine("Taxable Income", it_result.taxable_income, indent=1),
            StepLine("Income Tax", -it_result.total_tax, indent=1),
            StepLine("Class 4 NI", -class4_result.total_ni, indent=1),
        ]
        if sl_result:
            steps.append(StepLine("Student Loan", -sl_result.repayment, indent=1))
        if pgl_result:
            steps.append(StepLine("Postgraduate Loan", -pgl_result.repayment, indent=1))
        steps += [
            StepLine("Annual Take-Home", annual_take_home, is_subtotal=True),
            StepLine("20-Day Take-Home", take_home_20_day),
            StepLine("Year Taxable Income", year_taxable_income, is_subtotal=True),
        ]

        inputs: dict = {
            "day_rate": day_rate,
            "working_days": working_days,
            "effective_working_days": effective_days,
        }
        if business_expenses:
            inputs["business_expenses"] = business_expenses
        if pension:
            inputs["personal_pension"] = pension
        if region == "scotland":
            inputs["region"] = "scotland"
        if period_label:
            inputs["start_month"] = start_month
            inputs["contract_months"] = months
            inputs["contract_period"] = period_label
        if existing_income:
            inputs["existing_income"] = existing_income
        if existing_self_employment:
            inputs["existing_self_employment"] = existing_self_employment
        if student_loan_plan:
            inputs["student_loan_plan"] = student_loan_plan
        if postgraduate_loan:
            inputs["postgraduate_loan"] = True

        return SalaryBreakdown(
            mode="Sole Trader",
            inputs=inputs,
            steps=steps,
            annual_take_home=annual_take_home,
            display_take_home=take_home_20_day,
            year_taxable_income=year_taxable_income,
            income_tax=it_result,
            class4_ni=class4_result,
            student_loan=sl_result,
            postgraduate_loan=pgl_result,
        )
