
import pandas as pd
import numpy as np
from calculadora_financiera import crear_tabla_amortizacion, parametros

def test_systems():
    p = parametros.copy()
    p["horizonte_meses"] = 24
    p["financiamiento"]["monto_deuda"] = 120000
    p["financiamiento"]["plazo_deuda_meses"] = 12
    p["financiamiento"]["costo_deuda_anual"] = 0.12 # ~1% monthly eff if annual
    # Let's use simple rates for easier mental check? No, code uses EAR conversion. 
    # If capitalizacion is Monthly, and cost_deuda_anual is 0.12 EAR:
    # Monthly rate = (1.12)^(1/12) - 1 ~= 0.00948...
    
    p["financiamiento"]["capitalizacion"] = "Mensual"
    
    monto = 120000
    
    # 1. Test German
    print("--- TESTING GERMAN SYSTEM ---")
    p["financiamiento"]["sistema_amortizacion"] = "Alemán"
    df_german = crear_tabla_amortizacion(p, monto)
    
    print(df_german[["Saldo Inicial", "Interés", "Principal", "Saldo Pendiente"]].head(13).to_string())
    
    total_principal_g = df_german["Principal"].sum()
    print(f"Total Principal (German): {total_principal_g:,.2f} vs {monto}")
    
    # Check consistency: Principal should be roughly constant
    principals_g = df_german[df_german["Principal"] > 0]["Principal"]
    print(f"Principal values (std dev): {principals_g.std():.4f}")
    
    if abs(total_principal_g - monto) < 1.0 and principals_g.std() < 1.0:
        print("✅ GERMAN SYSTEM: Valid (Constant Principal)")
    else:
        print("❌ GERMAN SYSTEM: Invalid")

    # 2. Test French
    print("\n--- TESTING FRENCH SYSTEM ---")
    p["financiamiento"]["sistema_amortizacion"] = "Francés"
    df_french = crear_tabla_amortizacion(p, monto)
    
    print(df_french[["Saldo Inicial", "Interés", "Principal", "Saldo Pendiente"]].head(13).to_string())
    
    total_principal_f = df_french["Principal"].sum()
    print(f"Total Principal (French): {total_principal_f:,.2f} vs {monto}")

    # Check consistency: Total Payment (Principal + Interest) should be constant
    payments_f = df_french[df_french["Principal"] > 0]["Principal"] + df_french[df_french["Principal"] > 0]["Interés"]
    print(f"Total Payment values (std dev): {payments_f.std():.4f}")
    if len(payments_f) > 0:
        print(f"First Payment: {payments_f.iloc[0]:.2f}")
        print(f"Last Payment: {payments_f.iloc[-1]:.2f}")
    
    if abs(total_principal_f - monto) < 1.0 and payments_f.std() < 1.0:
        print("✅ FRENCH SYSTEM: Valid (Constant Total Payment)")
    else:
        print("❌ FRENCH SYSTEM: Invalid")

if __name__ == "__main__":
    test_systems()
