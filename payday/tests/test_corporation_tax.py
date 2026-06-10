import unittest
from payday.corporation_tax import calc_corporation_tax


class TestCorporationTax(unittest.TestCase):
    def test_zero_profit(self):
        res = calc_corporation_tax(0)
        self.assertEqual(res.total_ct, 0)
        self.assertEqual(res.profit, 0)

    def test_small_profits_rate(self):
        # 40000 * 0.19 = 7600
        res = calc_corporation_tax(40000)
        self.assertEqual(res.total_ct, 7600)
        self.assertEqual(res.marginal_relief, 0)

    def test_small_profits_at_threshold(self):
        # 50000 * 0.19 = 9500
        res = calc_corporation_tax(50000)
        self.assertEqual(res.total_ct, 9500)
        self.assertEqual(res.marginal_relief, 0)

    def test_marginal_relief(self):
        # 100000 * 0.25 = 25000; relief = (250000 - 100000) * 3/200 = 2250; total = 22750
        res = calc_corporation_tax(100000)
        self.assertEqual(res.total_ct, 22750)
        self.assertEqual(res.marginal_relief, 2250)

    def test_marginal_relief_near_upper(self):
        # 249000 * 0.25 = 62250
        # relief = round((250000 - 249000) * 3/200) = round(1000 * 0.015) = 15
        # total = 62250 - 15 = 62235
        res = calc_corporation_tax(249000)
        self.assertEqual(res.total_ct, 62235)

    def test_main_rate(self):
        # 300000 * 0.25 = 75000
        res = calc_corporation_tax(300000)
        self.assertEqual(res.total_ct, 75000)
        self.assertEqual(res.marginal_relief, 0)

    def test_main_rate_at_threshold(self):
        # 250000 * 0.25 = 62500
        res = calc_corporation_tax(250000)
        self.assertEqual(res.total_ct, 62500)
        self.assertEqual(res.marginal_relief, 0)

    def test_profit_exactly_50k(self):
        # SPEC: ≤ 50k = flat 19%
        # 50000 * 0.19 = 9500
        # But using the formula: 50000 * 0.25 = 12500, relief = (250000-50000)*3/200 = 200000*0.015 = 3000
        # 12500 - 3000 = 9500
        # Both methods agree, but code uses small profits rate branch
        res = calc_corporation_tax(50000)
        self.assertEqual(res.total_ct, 9500)


if __name__ == "__main__":
    unittest.main()
