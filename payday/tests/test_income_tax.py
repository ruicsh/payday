import unittest
from payday.income_tax import (
    calc_adjusted_net_income,
    calc_personal_allowance,
    calc_income_tax,
)


class TestIncomeTax(unittest.TestCase):
    def test_personal_allowance_standard(self):
        pa, tapered = calc_personal_allowance(50000)
        self.assertEqual(pa, 12570)
        self.assertFalse(tapered)

    def test_personal_allowance_taper_start(self):
        pa, tapered = calc_personal_allowance(100000)
        self.assertEqual(pa, 12570)
        self.assertFalse(tapered)

    def test_personal_allowance_tapered(self):
        pa, tapered = calc_personal_allowance(110000)
        self.assertEqual(pa, 7570)
        self.assertTrue(tapered)

    def test_personal_allowance_zeroed(self):
        pa, tapered = calc_personal_allowance(125140)
        self.assertEqual(pa, 0)
        self.assertTrue(tapered)

    def test_personal_allowance_highly_tapered(self):
        pa, tapered = calc_personal_allowance(200000)
        self.assertEqual(pa, 0)
        self.assertTrue(tapered)

    def test_income_tax_basic_rate(self):
        # Salary 50k, PA 12570 -> Taxable 37430
        # 37430 * 0.20 = 7486
        res = calc_income_tax(50000, 12570)
        self.assertEqual(res.total_tax, 7486)
        self.assertEqual(res.basic_tax, 7486)
        self.assertEqual(res.higher_tax, 0)

    def test_income_tax_higher_rate(self):
        # Salary 80k, PA 12570 -> Taxable 67430
        # Basic: 37700 * 0.20 = 7540
        # Higher: (67430 - 37700) * 0.40 = 29730 * 0.40 = 11892
        # Total: 7540 + 11892 = 19432
        res = calc_income_tax(80000, 12570)
        self.assertEqual(res.total_tax, 19432)

    def test_income_tax_additional_rate(self):
        # Salary 150k, PA 0 -> Taxable 150000
        # Basic (20%):  37700 * 0.20 =  7540
        # Higher (40%): (125140 - 37700) * 0.40 = 87440 * 0.40 = 34976
        # Additional (45%): (150000 - 125140) * 0.45 = 24860 * 0.45 = 11187
        # Total: 7540 + 34976 + 11187 = 53703
        res = calc_income_tax(150000, 0)
        self.assertEqual(res.total_tax, 53703)


class TestAdjustedNetIncome(unittest.TestCase):
    def test_all_defaults(self):
        ani = calc_adjusted_net_income()
        self.assertEqual(ani, 0)

    def test_single_income_source(self):
        ani = calc_adjusted_net_income(employment_income=50000)
        self.assertEqual(ani, 50000)

    def test_multiple_income_sources(self):
        ani = calc_adjusted_net_income(
            employment_income=40000,
            dividend_income=5000,
            savings_interest=2000,
        )
        self.assertEqual(ani, 47000)

    def test_bill_hmrc_example(self):
        # Bill: income £115k (85k SE + 20k property + 10k interest)
        #        gross pension £10k -> ANI = £105,000
        ani = calc_adjusted_net_income(
            self_employment_income=85000,
            property_income=20000,
            savings_interest=10000,
            gross_pension_contributions=10000,
        )
        self.assertEqual(ani, 105000)

    def test_clara_hmrc_example(self):
        # Clara: income £70k (65k emp + 5k interest)
        #         gross pension £4,750, Gift Aid £1,000 -> ANI = £64,000
        ani = calc_adjusted_net_income(
            employment_income=65000,
            savings_interest=5000,
            gross_pension_contributions=4750,
            gift_aid_donations=1000,
        )
        self.assertEqual(ani, 64000)

    def test_gift_aid_grossed_up(self):
        ani = calc_adjusted_net_income(
            employment_income=50000,
            gift_aid_donations=2000,
        )
        # 2000 * 1.25 = 2500 deducted
        self.assertEqual(ani, 47500)

    def test_relief_at_source_pension_grossed_up(self):
        ani = calc_adjusted_net_income(
            employment_income=50000,
            relief_at_source_pension=4000,
        )
        # 4000 * 1.25 = 5000 deducted
        self.assertEqual(ani, 45000)

    def test_trading_losses_deducted(self):
        ani = calc_adjusted_net_income(
            employment_income=50000,
            self_employment_income=30000,
            trading_losses=10000,
        )
        self.assertEqual(ani, 70000)

    def test_ani_with_pa_taper(self):
        # ANI = 110,000 should taper PA to 7,570
        pa, tapered = calc_personal_allowance(110000)
        self.assertEqual(pa, 7570)
        self.assertTrue(tapered)

    def test_ani_below_taper_threshold(self):
        pa, tapered = calc_personal_allowance(50000)
        self.assertEqual(pa, 12570)
        self.assertFalse(tapered)

    def test_ani_zeroes_pa(self):
        pa, tapered = calc_personal_allowance(125140)
        self.assertEqual(pa, 0)
        self.assertTrue(tapered)


if __name__ == "__main__":
    unittest.main()
