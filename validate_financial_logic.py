
import pandas as pd
import numpy as np
from calculadora_financiera import (
    generar_modelo_financiero_detallado, 
    crear_tabla_amortizacion,
    TIR_anual
)

def run_scenario(debt_amount, scenario_name):
    # 1. Definir parámetros base (mismos para ambos escenarios)
    params = {
        "horizonte_meses": 24,
        "financiamiento": {
            "monto_deuda": debt_amount,
            "costo_deuda_anual": 0.05, # 5% anual
            "plazo_deuda_meses": 12,
            "capitalizacion": "Mensual",
            "costo_capital_propio_anual": 0.12,
            "porcentaje_deuda": 0.0, # Se recalculará si hay deuda
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
    
    # Simular Inversión (CAPEX) en t=0
    capex = pd.Series(0.0, index=range(25))
    capex[0] = 500000 # Inversión inicial
    
    # Generar Deuda si aplica
    tabla_amort = None
    if debt_amount > 0:
        tabla_amort = crear_tabla_amortizacion(params, debt_amount)
        
    df = generar_modelo_financiero_detallado(params, capex, tabla_amort, debt_amount)
    
    # Calcular Métricas
    fcff = df["FCF No Apalancado (FCFF)"]
    fcfe = df["FCF Apalancado (FCFE)"]
    
    tir_p = TIR_anual(fcff)
    tir_i = TIR_anual(fcfe)
    
    print(f"\n--- Escenario: {scenario_name} (Deuda: {debt_amount}) ---")
    print(f"FCFF (Sum): {fcff.sum():,.2f}")
    print(f"FCFE (Sum): {fcfe.sum():,.2f}")
    print(f"TIR Proyecto: {tir_p*100:.2f}%" if tir_p else "TIR Proyecto: N/A")
    print(f"TIR Inversionista: {tir_i*100:.2f}%" if tir_i else "TIR Inversionista: N/A")
    
    # Validaciones
    if debt_amount == 0:
        diff = abs(fcff.sum() - fcfe.sum())
        # En deuda cero, FCFF == FCFE exactamente (impuestos operativos == reales)
        if diff < 1.0:
            print("✅ VALIDACIÓN SIN DEUDA: FCFF y FCFE coinciden.")
        else:
            print(f"❌ ERROR SIN DEUDA: Diferencia FCFF vs FCFE = {diff:,.2f}")
            
    else:
        # En deuda moderada con costo bajo (5%) vs retorno alto, TIR inv > TIR proy
        if tir_p and tir_i and tir_i > tir_p:
             print(f"✅ VALIDACIÓN APALANCAMIENTO: TIR Inversionista ({tir_i*100:.1f}%) > TIR Proyecto ({tir_p*100:.1f}%) (Efecto palanca positivo).")
        elif tir_p and tir_i:
             print(f"⚠️ NOTA: TIR Inversionista <= TIR Proyecto. (Puede ser correcto si deuda muy cara o amortización agresiva).")

    # Mostrar primeros flujos para inspección visual
    print("\nPrimeros 5 meses:")
    cols_view = ["CAPEX", "Entrada Deuda", "FCF No Apalancado (FCFF)", "FCF Apalancado (FCFE)", "Utilidad Neta"]
    print(df[cols_view].head(5).to_string())

print("=== INICIANDO VALIDACIÓN FINANCIERA ===")
run_scenario(0, "SIN DEUDA")
run_scenario(300000, "CON DEUDA (60% CAPEX)")
