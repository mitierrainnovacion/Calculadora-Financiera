
import unittest
import numpy as np
from calculadora_financiera import TIR_anual, _resolver_tir

class TestCalculadoraFinanciera(unittest.TestCase):

    def test_resolver_tir_simple(self):
        """
        Test the monthly IRR solver (np.roots based) with a simple case.
        """
        # Invest 100, receive 110 next month -> 10% monthly return
        cash_flow = [-100, 110]
        expected_monthly = 0.10
        
        result_monthly = _resolver_tir(cash_flow)
        self.assertIsNotNone(result_monthly)
        self.assertAlmostEqual(result_monthly, expected_monthly, places=6)

    def test_tir_anual_consistency(self):
        """
        Test that TIR_anual correctly annualizes the monthly rate.
        """
        cash_flow = [-100, 110]
        expected_monthly = 0.10
        expected_annual = (1 + expected_monthly)**12 - 1
        
        result_annual = TIR_anual(cash_flow)
        self.assertIsNotNone(result_annual)
        self.assertAlmostEqual(result_annual, expected_annual, places=6)

    def test_tir_real_estate_scenario(self):
        """
        Test a more realistic real estate cash flow.
        """
        # Investment, then rental income, then sale
        cash_flow = [-500000, 10000, 10000, 10000, 10000, 600000]
        # Monthly IRR approx 5.24%
        
        monthly_tir = _resolver_tir(cash_flow)
        self.assertIsNotNone(monthly_tir)
        self.assertAlmostEqual(monthly_tir, 0.052418, places=4)

    def test_no_solution_tir(self):
        """
        Test a cash flow that should technically have a solution in math (roots exist),
        but might be filtered if no positive real roots > -1 exist.
        Actually, [-100, 10, 10] never recovers investment. Return should be negative.
        np.roots handles negative rates fine.
        """
        cash_flow = [-100, 10, 10]
        # This will have a negative IRR.
        # NPV = -100 + 10/(1+r) + 10/(1+r)^2 = 0
        # This equation definitely has a solution for r > -1.
        
        tir = _resolver_tir(cash_flow)
        self.assertIsNotNone(tir)
        self.assertLess(tir, 0)

    def test_empty_cash_flow(self):
        cash_flow = []
        self.assertIsNone(TIR_anual(cash_flow))

    def test_all_positive(self):
        cash_flow = [100, 200, 300]
        self.assertIsNone(TIR_anual(cash_flow))

    def test_all_negative(self):
        cash_flow = [-100, -200, -300]
        self.assertIsNone(TIR_anual(cash_flow))

if __name__ == '__main__':
    unittest.main()
