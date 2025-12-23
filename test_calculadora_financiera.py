
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


    def test_amortizacion_alemana_simple(self):
        """
        Test German amortization: Constant principal repayment.
        Loan 1200, 12 months, 0% interest -> 100 principal/month.
        """
        from calculadora_financiera import crear_tabla_amortizacion
        p = {
            "financiamiento": {
                "plazo_deuda_meses": 12,
                "costo_deuda_anual": 0.0,
                "capitalizacion": "Mensual",
                "monto_deuda": 1200
            },
            "horizonte_meses": 12
        }
        df = crear_tabla_amortizacion(p, 1200)
        
        # Check sum of principal equals 1200
        self.assertAlmostEqual(df["Principal"].sum(), 1200.0)
        # Check constant amortization
        self.assertTrue(np.allclose(df.loc[1:12, "Principal"], 100.0))
        # Check final balance is zero
        self.assertAlmostEqual(df.iloc[-1]["Saldo Pendiente"], 0.0)

    def test_amortizacion_trimestral(self):
        """
        Test quarterly payments.
        Loan 1200, 12 months, quarterly -> 4 payments of 300 principal.
        """
        from calculadora_financiera import crear_tabla_amortizacion
        p = {
            "financiamiento": {
                "plazo_deuda_meses": 12,
                "costo_deuda_anual": 0.10, # Rate doesn't matter for principal schedule in German system
                "capitalizacion": "Trimestral",
                "monto_deuda": 1200
            },
            "horizonte_meses": 12
        }
        df = crear_tabla_amortizacion(p, 1200)
        
        # Principal should only be paid in months 3, 6, 9, 12
        payment_months = [3, 6, 9, 12]
        non_payment_months = [m for m in range(1, 13) if m not in payment_months]
        
        # Check sum
        self.assertAlmostEqual(df["Principal"].sum(), 1200.0)
        
        # Check payments
        self.assertTrue(np.allclose(df.loc[payment_months, "Principal"], 300.0))
        self.assertTrue(np.allclose(df.loc[non_payment_months, "Principal"], 0.0))
        
        # Check Interest is also only paid in payment months
        self.assertTrue(np.allclose(df.loc[non_payment_months, "Interés"], 0.0))
        self.assertTrue(np.all(df.loc[payment_months, "Interés"] > 0))

    def test_van_accuracy(self):
        """
        Test VAN calculation against a known manual calculation.
        """
        from calculadora_financiera import VAN
        # Cash flows: [-1000, 1100] one year later.
        # Discount rate 10% annual.
        # VAN = -1000 + 1100 / (1.10) = -1000 + 1000 = 0
        
        # Case 1: Annual period
        flujos = [-1000, 1100]
        van = VAN(flujos, 0.10, periodo_meses=12)
        self.assertAlmostEqual(van, 0.0)
        
        # Case 2: Monthly period
        # Invest -1000, get 1010 next month. Annual rate that gives 1% monthly is (1.01)^12 - 1
        tasa_mensual = 0.01
        tasa_anual = (1 + tasa_mensual)**12 - 1
        van_monthly = VAN([-1000, 1010], tasa_anual, periodo_meses=1)
        # -1000 + 1010 / 1.01 = -1000 + 1000 = 0
        self.assertAlmostEqual(van_monthly, 0.0)


    def test_van_ear_consistency(self):
        """
        Test that VAN uses Effective Annual Rate conversion correctly.
        """
        from calculadora_financiera import VAN
        # If rate is 10% annual EAR, monthly rate is (1.10)^(1/12) - 1.
        # Flow: -100 at t=0, +110 at t=12.
        # PV = -100 + 110 / (1+r)^12 = -100 + 110 / 1.10 = 0
        cash_flow = [-100] + [0]*11 + [110]
        
        # Default behavior: annual_rate_is_effective=True
        van = VAN(cash_flow, 0.10)
        self.assertAlmostEqual(van, 0.0)
        
        # Test explicit flag False (Nominal APR)
        # Nominal 12% APR -> 1% monthly.
        # Flow: -100, +101 next month.
        cash_flow_monthly = [-100, 101]
        van_nominal = VAN(cash_flow_monthly, 0.12, annual_rate_is_effective=False)
        self.assertAlmostEqual(van_nominal, 0.0)

    def test_irr_bracketing_robustness(self):
        """
        Test the robustness of the new bracketing solver.
        """
        # Case with multiple sign changes usually problematic for simple solvers
        # But here we just want to ensure it finds A valid root.
        # -100, 230, -132 => Roots at 10% and 20%
        # NPV(10%) = -100 + 230/1.1 - 132/1.21 = -100 + 209.09 - 109.09 = 0
        cash_flow = [-100, 230, -132]
        
        tir_m = _resolver_tir(cash_flow)
        
        # It should return one of the valid roots (approx 0.10 or 0.20)
        self.assertTrue(abs(tir_m - 0.10) < 1e-4 or abs(tir_m - 0.20) < 1e-4)

if __name__ == '__main__':
    unittest.main()
