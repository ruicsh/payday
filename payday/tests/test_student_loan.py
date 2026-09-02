import unittest
from payday.constants import (
    STUDENT_LOAN_PLAN1_THRESHOLD,
    STUDENT_LOAN_PLAN2_THRESHOLD,
    STUDENT_LOAN_PLAN4_THRESHOLD,
    STUDENT_LOAN_PLAN5_THRESHOLD,
    STUDENT_LOAN_POSTGRADUATE_THRESHOLD,
)
from payday.student_loan import (
    VALID_STUDENT_LOAN_PLANS,
    calc_postgraduate_loan,
    calc_student_loan,
)
from payday.calculators.inside_ir35 import InsideIR35Calculator
from payday.calculators.outside_ir35 import OutsideIR35Calculator
from payday.calculators.paye import PAYECalculator


class TestConstants(unittest.TestCase):
    def test_thresholds_2026_27(self):
        self.assertEqual(STUDENT_LOAN_PLAN1_THRESHOLD, 26_900)
        self.assertEqual(STUDENT_LOAN_PLAN2_THRESHOLD, 29_385)
        self.assertEqual(STUDENT_LOAN_PLAN4_THRESHOLD, 33_795)
        self.assertEqual(STUDENT_LOAN_PLAN5_THRESHOLD, 25_000)
        self.assertEqual(STUDENT_LOAN_POSTGRADUATE_THRESHOLD, 21_000)

    def test_valid_plans(self):
        self.assertEqual(VALID_STUDENT_LOAN_PLANS, {"plan1", "plan2", "plan4", "plan5"})


class TestCalcStudentLoan(unittest.TestCase):
    def test_below_threshold_no_repayment(self):
        res = calc_student_loan(20000, "plan2")
        self.assertEqual(res.repayment, 0)
        self.assertEqual(res.income_above_threshold, 0)

    def test_at_threshold_no_repayment(self):
        res = calc_student_loan(29_385, "plan2")
        self.assertEqual(res.repayment, 0)

    def test_just_above_threshold(self):
        # £1 above plan2 threshold → 9% × 1 = 0 (rounded)
        res = calc_student_loan(29_386, "plan2")
        self.assertEqual(res.income_above_threshold, 1)
        self.assertEqual(res.repayment, 0)

    def test_plan2_35k_known_answer(self):
        # 35000 - 29385 = 5615, 9% = 505.35 → 505
        res = calc_student_loan(35000, "plan2")
        self.assertEqual(res.income_above_threshold, 5615)
        self.assertEqual(res.repayment, 505)
        self.assertEqual(res.threshold, 29_385)
        self.assertEqual(res.rate, 0.09)

    def test_plan1_30k(self):
        # 30000 - 26900 = 3100, 9% = 279
        res = calc_student_loan(30000, "plan1")
        self.assertEqual(res.repayment, 279)

    def test_plan4_50k(self):
        # 50000 - 33795 = 16205, 9% = 1458.45 → 1458
        res = calc_student_loan(50000, "plan4")
        self.assertEqual(res.repayment, 1458)

    def test_plan5_50k(self):
        # 50000 - 25000 = 25000, 9% = 2250
        res = calc_student_loan(50000, "plan5")
        self.assertEqual(res.repayment, 2250)

    def test_each_plan_threshold_and_rate(self):
        for plan in ("plan1", "plan2", "plan4", "plan5"):
            res = calc_student_loan(100_000, plan)
            self.assertEqual(res.plan, plan)
            self.assertEqual(res.rate, 0.09)
            self.assertGreater(res.repayment, 0)

    def test_invalid_plan_raises(self):
        with self.assertRaises(ValueError):
            calc_student_loan(50000, "plan3")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            calc_student_loan(50000, "postgraduate")  # type: ignore[arg-type]

    def test_zero_income(self):
        res = calc_student_loan(0, "plan1")
        self.assertEqual(res.repayment, 0)

    # ── existing_income (partial year) ───────────────────────────────

    def test_existing_income_below_threshold_reduces_remaining(self):
        # threshold 26900, existing 10000, income 20000
        # remaining = 16900, above = 3100, 9% = 279
        res = calc_student_loan(20000, "plan1", existing_income=10000)
        self.assertEqual(res.income_above_threshold, 3100)
        self.assertEqual(res.repayment, 279)

    def test_existing_income_above_threshold_all_income_repays(self):
        # threshold 26900, existing 30000, income 20000
        # remaining = 0, above = 20000, 9% = 1800
        res = calc_student_loan(20000, "plan1", existing_income=30000)
        self.assertEqual(res.income_above_threshold, 20000)
        self.assertEqual(res.repayment, 1800)

    def test_existing_income_exactly_at_threshold(self):
        # threshold 26900, existing 26900, income 1000 → above 1000
        res = calc_student_loan(1000, "plan1", existing_income=26900)
        self.assertEqual(res.income_above_threshold, 1000)
        self.assertEqual(res.repayment, 90)

    def test_existing_income_straddles_threshold(self):
        # plan2 threshold 29385, existing 25000, income 10000
        # remaining = 4385, above = 5615, 9% = 505
        res = calc_student_loan(10000, "plan2", existing_income=25000)
        self.assertEqual(res.income_above_threshold, 5615)
        self.assertEqual(res.repayment, 505)

    def test_existing_income_zero_same_as_no_arg(self):
        a = calc_student_loan(40000, "plan2", existing_income=0)
        b = calc_student_loan(40000, "plan2")
        self.assertEqual(a.repayment, b.repayment)


class TestCalcPostgraduateLoan(unittest.TestCase):
    def test_below_threshold(self):
        res = calc_postgraduate_loan(20000)
        self.assertEqual(res.repayment, 0)

    def test_at_threshold(self):
        res = calc_postgraduate_loan(21000)
        self.assertEqual(res.repayment, 0)

    def test_30k_known_answer(self):
        # 30000 - 21000 = 9000, 6% = 540
        res = calc_postgraduate_loan(30000)
        self.assertEqual(res.repayment, 540)
        self.assertEqual(res.threshold, 21_000)
        self.assertEqual(res.rate, 0.06)
        self.assertEqual(res.plan, "postgraduate")

    def test_50k(self):
        # 50000 - 21000 = 29000, 6% = 1740
        res = calc_postgraduate_loan(50000)
        self.assertEqual(res.repayment, 1740)

    def test_existing_income(self):
        # threshold 21000, existing 15000, income 15000
        # remaining = 6000, above = 9000, 6% = 540
        res = calc_postgraduate_loan(15000, existing_income=15000)
        self.assertEqual(res.income_above_threshold, 9000)
        self.assertEqual(res.repayment, 540)

    def test_existing_income_above_threshold(self):
        res = calc_postgraduate_loan(10000, existing_income=25000)
        self.assertEqual(res.income_above_threshold, 10000)
        self.assertEqual(res.repayment, 600)

    def test_stacking_with_undergrad(self):
        # Plan 2 (9%) + PGL (6%) on £50k should stack
        sl = calc_student_loan(50000, "plan2")
        pgl = calc_postgraduate_loan(50000)
        # plan2: 50000-29385=20615 * 0.09 = 1855
        # pgl: 50000-21000=29000 * 0.06 = 1740
        self.assertEqual(sl.repayment, 1855)
        self.assertEqual(pgl.repayment, 1740)
        self.assertEqual(sl.repayment + pgl.repayment, 3595)


class TestPAYEWithStudentLoan(unittest.TestCase):
    def _find_step(self, breakdown, label):
        for step in breakdown.steps:
            if step.label == label:
                return step
        self.fail(f"Step '{label}' not found")

    def test_no_loan_backward_compatible(self):
        default = PAYECalculator.calculate(50000)
        explicit = PAYECalculator.calculate(
            50000, student_loan_plan=None, postgraduate_loan=False
        )
        self.assertEqual(default.annual_take_home, explicit.annual_take_home)
        self.assertEqual(default.steps, explicit.steps)
        self.assertIsNone(explicit.student_loan)
        self.assertIsNone(explicit.postgraduate_loan)

    def test_plan2_reduces_take_home(self):
        no_loan = PAYECalculator.calculate(50000)
        with_loan = PAYECalculator.calculate(50000, student_loan_plan="plan2")
        assert with_loan.student_loan is not None
        self.assertEqual(with_loan.student_loan.repayment, 1855)
        self.assertEqual(no_loan.annual_take_home - with_loan.annual_take_home, 1855)

    def test_plan1_exact(self):
        breakdown = PAYECalculator.calculate(50000, student_loan_plan="plan1")
        assert breakdown.student_loan is not None
        # 50000 - 26900 = 23100 * 0.09 = 2079
        self.assertEqual(breakdown.student_loan.repayment, 2079)
        self._find_step(breakdown, "Student Loan")

    def test_postgraduate_only(self):
        breakdown = PAYECalculator.calculate(50000, postgraduate_loan=True)
        assert breakdown.postgraduate_loan is not None
        self.assertEqual(breakdown.postgraduate_loan.repayment, 1740)
        self._find_step(breakdown, "Postgraduate Loan (Plan 3)")
        self.assertIsNone(breakdown.student_loan)
        labels = {s.label for s in breakdown.steps}
        self.assertNotIn("Student Loan", labels)

    def test_stacked_plan_and_postgraduate(self):
        breakdown = PAYECalculator.calculate(
            50000, student_loan_plan="plan2", postgraduate_loan=True
        )
        assert breakdown.student_loan is not None
        assert breakdown.postgraduate_loan is not None
        self.assertEqual(breakdown.student_loan.repayment, 1855)
        self.assertEqual(breakdown.postgraduate_loan.repayment, 1740)
        total = 1855 + 1740
        no_loan = PAYECalculator.calculate(50000)
        self.assertEqual(no_loan.annual_take_home - breakdown.annual_take_home, total)
        self._find_step(breakdown, "Student Loan")
        self._find_step(breakdown, "Postgraduate Loan (Plan 3)")

    def test_below_threshold_no_deduction(self):
        breakdown = PAYECalculator.calculate(20000, student_loan_plan="plan2")
        assert breakdown.student_loan is not None
        self.assertEqual(breakdown.student_loan.repayment, 0)
        # Repayment 0 still creates the result object but step is still added
        # (amount 0) — verify it exists
        self._find_step(breakdown, "Student Loan")

    def test_salary_sacrifice_reduces_loan_base(self):
        # £50k salary, £10k sacrifice → effective £40k
        # Plan2 on 40k: 40000-29385=10615 * 0.09 = 955
        # vs 50k no sacrifice: 1855
        with_sac = PAYECalculator.calculate(
            50000, salary_sacrifice=10000, student_loan_plan="plan2"
        )
        no_sac = PAYECalculator.calculate(50000, student_loan_plan="plan2")
        assert with_sac.student_loan is not None
        assert no_sac.student_loan is not None
        self.assertEqual(with_sac.student_loan.repayment, 955)
        self.assertLess(with_sac.student_loan.repayment, no_sac.student_loan.repayment)

    def test_inputs_stored(self):
        breakdown = PAYECalculator.calculate(
            50000, student_loan_plan="plan5", postgraduate_loan=True
        )
        self.assertEqual(breakdown.inputs.get("student_loan_plan"), "plan5")
        self.assertTrue(breakdown.inputs.get("postgraduate_loan"))

    def test_low_salary_inputs_not_stored_when_none(self):
        breakdown = PAYECalculator.calculate(30000)
        self.assertIsNone(breakdown.inputs.get("student_loan_plan"))
        self.assertIsNone(breakdown.inputs.get("postgraduate_loan"))


class TestInsideIR35WithStudentLoan(unittest.TestCase):
    def _find_step(self, breakdown, label):
        for step in breakdown.steps:
            if step.label == label:
                return step
        self.fail(f"Step '{label}' not found")

    def test_no_loan_backward_compatible(self):
        default = InsideIR35Calculator.calculate(600, 227)
        explicit = InsideIR35Calculator.calculate(
            600, 227, student_loan_plan=None, postgraduate_loan=False
        )
        self.assertEqual(default.annual_take_home, explicit.annual_take_home)

    def test_plan2_deducted_from_gross(self):
        no_loan = InsideIR35Calculator.calculate(600, 227)
        with_loan = InsideIR35Calculator.calculate(600, 227, student_loan_plan="plan2")
        assert with_loan.student_loan is not None
        self.assertGreater(with_loan.student_loan.repayment, 0)
        self.assertLess(with_loan.annual_take_home, no_loan.annual_take_home)
        self._find_step(with_loan, "Student Loan")

    def test_existing_income_prorated(self):
        # existing 25k, gross ~100k+, repayment should account for remaining threshold
        no_existing = InsideIR35Calculator.calculate(
            600, 227, student_loan_plan="plan2", existing_income=0
        )
        with_existing = InsideIR35Calculator.calculate(
            600, 227, student_loan_plan="plan2", existing_income=25000
        )
        assert no_existing.student_loan is not None
        assert with_existing.student_loan is not None
        # With existing 25k below threshold, repayment is higher (less remaining threshold)
        # 25k consumes 25k of the 29385 threshold, leaving only 4385 before this contract repays
        self.assertGreater(
            with_existing.student_loan.repayment, no_existing.student_loan.repayment
        )

    def test_stacked_loans_inside_ir35(self):
        breakdown = InsideIR35Calculator.calculate(
            600, 227, student_loan_plan="plan1", postgraduate_loan=True
        )
        assert breakdown.student_loan is not None
        assert breakdown.postgraduate_loan is not None
        self._find_step(breakdown, "Student Loan")
        self._find_step(breakdown, "Postgraduate Loan (Plan 3)")
        no_loan = InsideIR35Calculator.calculate(600, 227)
        expected_diff = (
            breakdown.student_loan.repayment + breakdown.postgraduate_loan.repayment
        )
        self.assertEqual(
            no_loan.annual_take_home - breakdown.annual_take_home, expected_diff
        )

    def test_postgraduate_only_inside_ir35(self):
        breakdown = InsideIR35Calculator.calculate(600, 227, postgraduate_loan=True)
        assert breakdown.postgraduate_loan is not None
        self.assertIsNone(breakdown.student_loan)
        self._find_step(breakdown, "Postgraduate Loan (Plan 3)")


class TestOutsideIR35WithStudentLoan(unittest.TestCase):
    def _find_step(self, breakdown, label):
        for step in breakdown.steps:
            if step.label == label:
                return step
        self.fail(f"Step '{label}' not found")

    def test_no_loan_backward_compatible(self):
        default = OutsideIR35Calculator.calculate(600, 227)
        explicit = OutsideIR35Calculator.calculate(
            600, 227, student_loan_plan=None, postgraduate_loan=False
        )
        self.assertEqual(default.annual_take_home, explicit.annual_take_home)
        self.assertEqual(default.steps, explicit.steps)

    def test_plan2_on_salary_plus_dividends(self):
        # Outside IR35: repayment base is salary (12570) + dividends.
        # Plan 2 threshold 29385, so for a profitable contract the repayment
        # should be well above zero.
        no_loan = OutsideIR35Calculator.calculate(600, 227)
        with_loan = OutsideIR35Calculator.calculate(600, 227, student_loan_plan="plan2")
        assert with_loan.student_loan is not None
        self.assertGreater(with_loan.student_loan.repayment, 0)
        self.assertLess(with_loan.annual_take_home, no_loan.annual_take_home)
        self._find_step(with_loan, "Student Loan")

    def test_postgraduate_only(self):
        breakdown = OutsideIR35Calculator.calculate(600, 227, postgraduate_loan=True)
        assert breakdown.postgraduate_loan is not None
        self.assertIsNone(breakdown.student_loan)
        self._find_step(breakdown, "Postgraduate Loan (Plan 3)")

    def test_stacked_loans(self):
        no_loan = OutsideIR35Calculator.calculate(600, 227)
        stacked = OutsideIR35Calculator.calculate(
            600, 227, student_loan_plan="plan1", postgraduate_loan=True
        )
        assert stacked.student_loan is not None
        assert stacked.postgraduate_loan is not None
        self._find_step(stacked, "Student Loan")
        self._find_step(stacked, "Postgraduate Loan (Plan 3)")
        self.assertEqual(
            no_loan.annual_take_home - stacked.annual_take_home,
            stacked.student_loan.repayment + stacked.postgraduate_loan.repayment,
        )

    def test_existing_dividends_consume_threshold(self):
        no_existing = OutsideIR35Calculator.calculate(
            600, 227, student_loan_plan="plan2", existing_income=0, existing_dividends=0
        )
        with_existing = OutsideIR35Calculator.calculate(
            600, 227, student_loan_plan="plan2", existing_dividends=25000
        )
        assert no_existing.student_loan is not None
        assert with_existing.student_loan is not None
        # Existing 25k dividends consume most of the 29385 threshold.
        self.assertGreater(
            with_existing.student_loan.repayment, no_existing.student_loan.repayment
        )

    def test_not_deducted_from_company_profit(self):
        # Student loan is a personal Self Assessment deduction — it must not
        # affect company profit or corporation tax.
        no_loan = OutsideIR35Calculator.calculate(600, 227)
        with_loan = OutsideIR35Calculator.calculate(600, 227, student_loan_plan="plan5")
        assert no_loan.corporation_tax is not None
        assert with_loan.corporation_tax is not None
        assert no_loan.dividend_tax is not None
        assert with_loan.dividend_tax is not None
        self.assertEqual(
            no_loan.corporation_tax.total_ct, with_loan.corporation_tax.total_ct
        )
        self.assertEqual(
            no_loan.dividend_tax.total_tax, with_loan.dividend_tax.total_tax
        )

    def test_inputs_stored(self):
        b = OutsideIR35Calculator.calculate(
            500, 200, student_loan_plan="plan4", postgraduate_loan=True
        )
        self.assertEqual(b.inputs.get("student_loan_plan"), "plan4")
        self.assertTrue(b.inputs.get("postgraduate_loan"))


if __name__ == "__main__":
    unittest.main()
