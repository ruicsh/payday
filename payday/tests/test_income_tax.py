import unittest
from payday.income_tax import (
    calc_adjusted_net_income,
    calc_personal_allowance,
    calc_income_tax,
)
from payday.models import IncomeTaxResult


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

    # ── existing_income tests ──────────────────────────────────────────

    def test_income_tax_existing_backward_compatible(self):
        res_default = calc_income_tax(50000, 12570)
        res_explicit = calc_income_tax(50000, 12570, existing_income=0)
        self.assertEqual(res_default.total_tax, res_explicit.total_tax)
        self.assertEqual(res_default.taxable_income, res_explicit.taxable_income)
        self.assertEqual(res_default.basic_band, res_explicit.basic_band)

    def test_income_tax_existing_consumes_pa(self):
        # Existing £30k consumes £12,570 PA + £17,430 of basic band.
        # New £20k has no remaining PA, all taxed at 20%.
        res = calc_income_tax(20000, 12570, existing_income=30000)
        self.assertEqual(res.total_tax, 4000)
        self.assertEqual(res.taxable_income, 20000)
        self.assertEqual(res.basic_band, 20000)
        self.assertEqual(res.higher_band, 0)

    def test_income_tax_existing_pushes_into_higher(self):
        # Existing £50k consumes PA + £37,430 of basic band.
        # Remaining basic: £37,700 - £37,430 = £270.
        # New £40k: £270 at 20%, £39,730 at 40%.
        res = calc_income_tax(40000, 12570, existing_income=50000)
        self.assertEqual(res.total_tax, 15946)
        self.assertEqual(res.taxable_income, 40000)
        self.assertEqual(res.basic_band, 270)
        self.assertEqual(res.higher_band, 39730)

    def test_income_tax_existing_into_additional(self):
        # Existing £120k + new £80k, PA tapered to 0.
        # Combined taxable: 200,000
        # Existing taxable: 120,000
        pa, _ = calc_personal_allowance(200000)
        self.assertEqual(pa, 0)
        res = calc_income_tax(80000, pa, existing_income=120000)
        # Combined tax on 200k:
        #   basic:  37,700 * 0.20 =  7,540
        #   higher: 87,440 * 0.40 = 34,976
        #   addl:   (200k-125140) * 0.45 = 74,860*0.45 = 33,687
        #   total: 76,203
        # Existing tax on 120k:
        #   basic:  37,700 * 0.20 =  7,540
        #   higher: (120k-37,700) * 0.40 = 82,300*0.40 = 32,920
        #   addl:   max(0, 120k-125140) = 0
        #   total: 40,460
        # New tax: 76,203 - 40,460 = 35,743
        self.assertEqual(res.total_tax, 35743)
        # New salary bands:
        #   basic:   37,700 - 37,700 = 0
        #   higher:  87,440 - 82,300 = 5,140
        #   addl:    74,860 - 0 = 74,860
        self.assertEqual(res.basic_band, 0)
        self.assertEqual(res.higher_band, 5140)
        self.assertEqual(res.additional_band, 74860)

    def test_income_tax_existing_consumes_all_bands(self):
        # Existing £200k (all bands consumed), new £50k all at additional rate.
        pa, _ = calc_personal_allowance(250000)
        self.assertEqual(pa, 0)
        res = calc_income_tax(50000, pa, existing_income=200000)
        # Combined taxable: 250k
        #   basic:  37,700 * 0.20 =  7,540
        #   higher: 87,440 * 0.40 = 34,976
        #   addl:   124,860 * 0.45 = 56,187
        #   total: 98,703
        # Existing taxable: 200k
        #   basic:  37,700 * 0.20 =  7,540
        #   higher: 87,440 * 0.40 = 34,976
        #   addl:   74,860 * 0.45 = 33,687
        #   total: 76,203
        # New tax: 98,703 - 76,203 = 22,500
        self.assertEqual(res.total_tax, 22500)
        # New bands: all additional
        self.assertEqual(res.basic_band, 0)
        self.assertEqual(res.higher_band, 0)
        self.assertEqual(res.additional_band, 50000)

    def test_existing_income_float_accepted(self):
        """Float existing_income should be accepted and produce valid results."""
        res = calc_income_tax(20000, 12570, existing_income=30000.50)
        self.assertIsInstance(res, IncomeTaxResult)
        self.assertEqual(res.total_tax, 4000)
        self.assertEqual(res.taxable_income, 20000)
        self.assertEqual(res.basic_band, 20000)

    def test_existing_income_float_precision(self):
        """Float values near band boundaries should still produce valid results."""
        res = calc_income_tax(40000, 12570, existing_income=50000.75)
        self.assertIsInstance(res, IncomeTaxResult)
        self.assertGreater(res.total_tax, 0)
        self.assertGreater(res.taxable_income, 0)

    # ── Scotland (region="scotland") tests ───────────────────────────────

    def test_scotland_basic_rate(self):
        # Scotland 50k, PA 12570 -> taxable 37430
        # Starter 3967@19%=754 + Basic 12989@20%=2598 + Intermediate 14136@21%=2969
        # + Higher (37430-31092)=6338@42%=2662 => 8983
        res = calc_income_tax(50000, 12570, region="scotland")
        self.assertEqual(res.region, "scotland")
        self.assertEqual(res.total_tax, 8983)
        self.assertEqual(res.starter_band, 3967)
        self.assertEqual(res.starter_tax, 754)
        self.assertEqual(res.intermediate_band, 14136)
        self.assertEqual(res.additional_band, 0)

    def test_scotland_mid_rate(self):
        # Scotland 80k, PA 12570 -> taxable 67430
        # Starter 754 + Basic 2598 + Intermediate 2969 + Higher 31338@42%=13162
        # + Advanced 5000@45%=2250 => 21733
        res = calc_income_tax(80000, 12570, region="scotland")
        self.assertEqual(res.total_tax, 21733)
        self.assertEqual(res.higher_band, 31338)
        self.assertEqual(res.advanced_band, 5000)
        self.assertEqual(res.top_band, 0)

    def test_scotland_top_rate(self):
        # Scotland 150k, PA 0 -> taxable 150000
        # 3967@19 + 12989@20 + 14136@21 + 31338@42 + 50140@45 + 37430@48 = 60012
        res = calc_income_tax(150000, 0, region="scotland")
        self.assertEqual(res.total_tax, 60012)
        self.assertEqual(res.advanced_band, 50140)
        self.assertEqual(res.top_band, 37430)

    def test_scotland_advanced_top_boundary(self):
        # Regression: advanced must cap at 50140 (112570-62430), top starts at 112570.
        # Before the fix advanced was 62710 (125140-62430).
        res = calc_income_tax(150000, 0, region="scotland")
        self.assertEqual(res.advanced_band, 50140)
        res2 = calc_income_tax(125140, 12570, region="scotland")
        # 125140-12570=112570 taxable -> exactly fills advanced, no top
        self.assertEqual(res2.advanced_band, 50140)
        self.assertEqual(res2.top_band, 0)

    def test_scotland_aliases_normalise_to_rest_of_uk(self):
        for alias in ("england", "wales", "northern_ireland", "rest_of_uk", None):
            res = calc_income_tax(50000, 12570, region=alias)
            self.assertEqual(res.region, "rest_of_uk")
            self.assertEqual(res.total_tax, 7486)

    def test_scotland_existing_income_reduces_bands(self):
        # Existing 30k: PA 12570 consumed + 17430 of Scottish bands.
        #   existing taxable 17430 -> starter 3967 + basic 12989 + intermediate 474
        # Combined 50k: taxable 37430 -> starter 3967 + basic 12989 + intermediate 14136 + higher 6338
        # New 20k: starter 0, basic 0, intermediate 13662, higher 6338
        #   tax: 13662*0.21=2869 + 6338*0.42=2662 => 5531
        res = calc_income_tax(20000, 12570, existing_income=30000, region="scotland")
        self.assertEqual(res.region, "scotland")
        self.assertEqual(res.additional_band, 0)
        self.assertEqual(res.total_tax, 5531)
        self.assertEqual(res.starter_band, 0)
        self.assertEqual(res.basic_band, 0)
        self.assertEqual(res.intermediate_band, 13662)
        self.assertEqual(res.higher_band, 6338)
        self.assertEqual(res.advanced_band, 0)
        self.assertEqual(res.top_band, 0)

    # ── relief-at-source band extension ──────────────────────────────

    def test_ruk_band_extension_higher_rate(self):
        # 80k, PA 12570, G=2,202 extends basic band 37,700→39,902
        # No ext: basic 37,700 + higher 29,730 -> tax 19,432
        # With ext: basic 39,902 + higher 27,528 -> tax 18,991 (diff 441)
        no_ext = calc_income_tax(80000, 12570, basic_rate_band_extension=0)
        with_ext = calc_income_tax(80000, 12570, basic_rate_band_extension=2202)
        self.assertEqual(no_ext.total_tax, 19432)
        self.assertEqual(with_ext.total_tax, 18991)
        self.assertEqual(with_ext.basic_band, 39902)
        self.assertEqual(with_ext.higher_band, 27528)

    def test_ruk_band_extension_basic_rate_no_effect(self):
        # 50k within basic even after extension -> same tax
        res = calc_income_tax(50000, 12570, basic_rate_band_extension=2188)
        self.assertEqual(res.total_tax, 7486)
        self.assertEqual(res.higher_band, 0)

    def test_ruk_band_extension_with_existing_income(self):
        # New 40k on top of 50k existing: remaining basic shrinks
        # Without ext remaining basic 270; with ext 2472 -> tax lower
        no_ext = calc_income_tax(40000, 12570, existing_income=50000)
        with_ext = calc_income_tax(
            40000, 12570, existing_income=50000, basic_rate_band_extension=2202
        )
        self.assertEqual(no_ext.basic_band, 270)
        self.assertEqual(with_ext.basic_band, 2472)
        self.assertLess(with_ext.total_tax, no_ext.total_tax)

    def test_scotland_band_extension_intermediate(self):
        # 50k Scotland G=2,188 extends intermediate 31,092→33,280
        # No ext 8,983 -> with ext 8,523 (diff 460 at 21%)
        no_ext = calc_income_tax(50000, 12570, region="scotland")
        with_ext = calc_income_tax(
            50000, 12570, region="scotland", basic_rate_band_extension=2188
        )
        self.assertEqual(no_ext.total_tax, 8983)
        self.assertEqual(with_ext.total_tax, 8523)
        self.assertEqual(with_ext.intermediate_band, 16324)
        self.assertEqual(with_ext.higher_band, 4150)

    def test_scotland_band_extension_higher_and_advanced_shift(self):
        # 80k Scotland G=2,202: intermediate +2202, higher unchanged,
        # advanced shrinks (5000 -> 2798) as thresholds shift
        with_ext = calc_income_tax(
            80000, 12570, region="scotland", basic_rate_band_extension=2202
        )
        self.assertEqual(with_ext.advanced_band, 2798)
        self.assertEqual(with_ext.total_tax, 21204)

    def test_band_extension_zero_is_default(self):
        # Explicit 0 must equal default (no arg)
        default = calc_income_tax(80000, 12570)
        explicit = calc_income_tax(80000, 12570, basic_rate_band_extension=0)
        self.assertEqual(default.total_tax, explicit.total_tax)
        scot_default = calc_income_tax(80000, 12570, region="scotland")
        scot_explicit = calc_income_tax(
            80000, 12570, region="scotland", basic_rate_band_extension=0
        )
        self.assertEqual(scot_default.total_tax, scot_explicit.total_tax)


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
