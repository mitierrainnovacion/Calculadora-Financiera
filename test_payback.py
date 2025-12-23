#!/usr/bin/env python3
"""
Test script for payback period calculations.
"""

import pandas as pd
import numpy as np
from calculadora_financiera import (
    payback_normal,
    payback_descontado,
    calcular_total_intereses,
    crear_tabla_amortizacion,
    generar_modelo_financiero_detallado,
    construir_cronograma_inversiones
)

def test_payback_simple():
    """Test payback with simple cash flows."""
    print("\n=== TEST 1: Simple Payback ===")
    
    # Simple case: -100 at t=0, then +30 for 4 months
    flujos = pd.Series([-100, 30, 30, 30, 30])
    
    pb_normal = payback_normal(flujos)
    pb_desc = payback_descontado(flujos, 0.12)  # 12% annual
    
    print(f"Flujos: {flujos.tolist()}")
    print(f"Payback Normal: {pb_normal:.2f} meses" if pb_normal else "No se recupera")
    print(f"Payback Descontado (12% anual): {pb_desc:.2f} meses" if pb_desc else "No se recupera")
    
    # Expected: Normal should be around 3.33 months (100/30 = 3.33)
    # Discounted should be slightly higher
    
    assert pb_normal is not None, "Payback normal should not be None"
    assert pb_desc is not None, "Payback descontado should not be None"
    assert pb_desc > pb_normal, "Discounted payback should be > normal payback"
    print("✅ Test 1 passed")

def test_payback_no_recovery():
    """Test case where investment never recovers."""
    print("\n=== TEST 2: No Recovery ===")
    
    flujos = pd.Series([-100, 10, 10, 10])
    
    pb_normal = payback_normal(flujos)
    pb_desc = payback_descontado(flujos, 0.12)
    
    print(f"Flujos: {flujos.tolist()}")
    print(f"Payback Normal: {pb_normal}" if pb_normal else "No se recupera ✓")
    print(f"Payback Descontado: {pb_desc}" if pb_desc else "No se recupera ✓")
    
    assert pb_normal is None, "Should not recover"
    assert pb_desc is None, "Should not recover"
    print("✅ Test 2 passed")

def test_total_intereses():
    """Test total interest calculation."""
    print("\n=== TEST 3: Total Interest Calculation ===")
    
    params = {
        "horizonte_meses": 12,
        "financiamiento": {
            "monto_deuda": 100000,
            "costo_deuda_anual": 0.06,  # 6% annual
            "plazo_deuda_meses": 12,
            "capitalizacion": "Mensual",
            "tasa_impuesto_renta": 0.27
        }
    }
    
    tabla = crear_tabla_amortizacion(params, 100000)
    total_int = calcular_total_intereses(tabla)
    
    print(f"Deuda: $100,000")
    print(f"Tasa: 6% anual")
    print(f"Plazo: 12 meses")
    print(f"Total Intereses: ${total_int:,.2f}")
    
    # For a 100k loan at 6% annual over 12 months, interest should be around 3k-3.5k
    assert total_int > 0, "Interest should be positive"
    assert total_int < 10000, "Interest seems too high"
    print("✅ Test 3 passed")

def test_integrated_scenario():
    """Test with real scenario from validation script."""
    print("\n=== TEST 4: Integrated Scenario ===")
    
    params = {
        "horizonte_meses": 24,
        "financiamiento": {
            "monto_deuda": 300000,
            "costo_deuda_anual": 0.05,
            "plazo_deuda_meses": 12,
            "capitalizacion": "Mensual",
            "costo_capital_propio_anual": 0.12,
            "porcentaje_deuda": 0.0,
            "tasa_impuesto_renta": 0.27
        },
        "ventas": {
            "crecimiento_precio_anual": 0.03
        },
        "planes_venta": [
            {
                "nombre": "Plan A",
                "precio_lista": 100000,
                "monto_pie": 20000,
                "monto_cuota": 5000,
                "cantidad_cuotas": 16,
                "cantidad_lotes": 10,
                "velocidad": 2,
                "mes_inicio": 1,
                "frecuencia": 1,
                "tipo": "Dinámico"
            }
        ],
        "items_periodicos": [
            {"tipo": "Gasto", "monto": 5000, "mes_inicio": 1, "mes_fin": 24, "base_calculo": "Monto Fijo"}
        ]
    }
    
    capex = pd.Series(0.0, index=range(25))
    capex[0] = 500000
    
    tabla_amort = crear_tabla_amortizacion(params, 300000)
    df = generar_modelo_financiero_detallado(params, capex, tabla_amort, 300000)
    
    fcfe = df["FCF Apalancado (FCFE)"]
    
    pb_n = payback_normal(fcfe)
    pb_d = payback_descontado(fcfe, 0.12)
    
    total_int = calcular_total_intereses(tabla_amort)
    inv_total = 500000
    inv_con_int = inv_total + total_int
    
    print(f"Inversión Total: ${inv_total:,.0f}")
    print(f"Total Intereses: ${total_int:,.0f}")
    print(f"Inversión con Intereses: ${inv_con_int:,.0f}")
    print(f"Payback Normal: {pb_n:.2f} meses" if pb_n else "No se recupera")
    print(f"Payback Descontado: {pb_d:.2f} meses" if pb_d else "No se recupera")
    
    assert total_int > 0, "Should have interest"
    assert inv_con_int > inv_total, "Investment with interest should be higher"
    
    if pb_n is not None and pb_d is not None:
        assert pb_d >= pb_n, "Discounted payback should be >= normal"
        print("✅ Test 4 passed")
    else:
        print("⚠️ Payback not achieved in horizon (may be expected)")

if __name__ == "__main__":
    print("=" * 60)
    print("TESTING PAYBACK AND INTEREST CALCULATIONS")
    print("=" * 60)
    
    test_payback_simple()
    test_payback_no_recovery()
    test_total_intereses()
    test_integrated_scenario()
    
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)
