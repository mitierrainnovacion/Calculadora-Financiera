# Calculadora Financiera de Alta Precisión para Proyectos Inmobiliarios
# Versión 2.1
# Descripción: Este script realiza un análisis financiero detallado para evaluar la
# viabilidad de proyectos de inversión inmobiliaria.

import numpy as np
import pandas as pd
import copy

# ==============================================================================
# 1. PARÁMETROS DEL PROYECTO
# ==============================================================================
parametros = {
    "horizonte_meses": 120,
    "cronograma_inversion": [
        {"item": "Compra Terreno", "monto": 5_000_000, "mes": 0, "tag_sensibilidad": "costo_terreno"},
        {"item": "Comercialización Inicial", "monto": 800_000, "mes": 0, "tag_sensibilidad": "costo_marketing"},
        {"item": "Otros Costos Iniciales", "monto": 500_000, "mes": 0, "tag_sensibilidad": "costo_otros"},
        {"item": "Urbanización - Fase 1", "monto": 4_000_000, "mes": 2, "tag_sensibilidad": "costo_urbanizacion"},
        {"item": "Proyecto Legal", "monto": 1_200_000, "mes": 3, "tag_sensibilidad": "costo_legal"},
        {"item": "Urbanización - Fase 2", "monto": 4_000_000, "mes": 6, "tag_sensibilidad": "costo_urbanizacion"},
    ],
    "ventas": {
        "crecimiento_precio_anual": 0.05,
    },
    "planes_venta": [
        {
            "nombre": "Preventa",
            "tipo": "Dinámico",
            "mes_inicio": 1,
            "cantidad_lotes": 100,
            "velocidad": 5,
            "monto_pie": 30000,
            "monto_cuota": 2000,
            "frecuencia": 1,
            "cantidad_cuotas": 60
        },
        {
            "nombre": "Venta Normal",
            "tipo": "Dinámico",
            "mes_inicio": 20,
            "cantidad_lotes": 100,
            "velocidad": 3,
            "monto_pie": 50000,
            "monto_cuota": 3000,
            "frecuencia": 1,
            "cantidad_cuotas": 48
        }
    ],
    "costos_operativos": {
        "costo_operativo_mensual": 120_000,
        "mantenimiento_mensual": 40_000,
        "impuestos_prediales_mensual": 25_000,
    },
    "financiamiento": {
        "monto_deuda": 9_300_000,
        "costo_deuda_anual": 0.12,
        "plazo_deuda_meses": 84,
        "capitalizacion": "Mensual", # Mensual, Trimestral, Semestral, Anual
        "costo_capital_propio_anual": 0.18,
        "tasa_impuesto_renta": 0.30,
    },
    "items_periodicos": [],
}

# ==============================================================================
# 2. CÁLCULOS PRELIMINARES Y CRONOGRAMAS
# ==============================================================================

def calcular_inversion_total(p):
    return sum(item["monto"] for item in p["cronograma_inversion"])

def construir_cronograma_inversiones(p):
    horizonte = p["horizonte_meses"]
    cronograma = pd.Series([0.0] * (horizonte + 1), name="Inversiones (CAPEX)")
    for item in p["cronograma_inversion"]:
        if item["mes"] <= horizonte:
            cronograma[item["mes"]] += item["monto"]
    return cronograma

def crear_tabla_amortizacion(p, monto_deuda):
    """
    Calcula la tabla de amortización usando el SISTEMA ALEMÁN.
    Soporta diferentes frecuencias de capitalización.
    """
    plazo = p["financiamiento"]["plazo_deuda_meses"]
    tasa_anual = p["financiamiento"]["costo_deuda_anual"]
    freq_map = {"Mensual": 1, "Trimestral": 3, "Semestral": 6, "Anual": 12}
    freq = freq_map.get(p["financiamiento"].get("capitalizacion", "Mensual"), 1)
    
    tasa_mensual = (1 + tasa_anual)**(1/12) - 1
    
    # En sistema Alemán, la amortización es constante
    amort_mensual = monto_deuda / plazo if plazo > 0 else 0
    
    cronograma = []
    saldo = monto_deuda
    interes_acumulado = 0.0
    
    for mes in range(1, p["horizonte_meses"] + 1):
        if mes <= plazo:
            # El interés se calcula siempre sobre el saldo pendiente del mes anterior
            interes_mes = saldo * tasa_mensual
            interes_acumulado += interes_mes
            
            # La capitalización/pago de intereses ocurre según la frecuencia
            interes_a_pagar = 0.0
            if mes % freq == 0:
                interes_a_pagar = interes_acumulado
                interes_acumulado = 0.0
            
            principal = amort_mensual
            saldo -= principal
            cronograma.append({
                "Mes": mes,
                "Saldo Inicial": saldo + principal,
                "Interés": interes_a_pagar,
                "Principal": principal,
                "Saldo Pendiente": max(0, saldo)
            })
        else:
            cronograma.append({
                "Mes": mes, "Saldo Inicial": 0, "Interés": 0, "Principal": 0, "Saldo Pendiente": 0
            })
            
    return pd.DataFrame(cronograma).set_index("Mes")

# ==============================================================================
# 3. MOTOR DE CÁLCULO FINANCIERO DETALLADO
# ==============================================================================

def generar_modelo_financiero_detallado(p, capex, tabla_amortizacion, monto_deuda_total):
    """
    Genera el modelo financiero detallado con lógica de gastos dinámicos y lotes.
    """
    horizonte = p["horizonte_meses"]
    tasa_impuesto = p["financiamiento"]["tasa_impuesto_renta"]
    
    columnas = [
        "Ingresos Ventas Pies", "Ingresos Ventas Cuotas", "Otros Ingresos", "Ingresos Totales",
        "Costos Operativos Dinámicos", "EBITDA", "Depreciacion", "EBIT",
        "Intereses", "EBT", "Perdida Arrastrable Usada", "Base Imponible", "Impuestos",
        "Utilidad Neta", "NOPAT", "FCF Operativo", "CAPEX",
        "FCF No Apalancado (FCFF)", "Entrada Deuda", "Amortización Principal", "Net Debt Issued",
        "FCF Apalancado (FCFE)", "Aportación Capital", "Flujo Caja Neto Inversionista", "Saldo Deuda",
        "Lotes Vendidos", "Lotes en Inventario"
    ]
    df = pd.DataFrame(0.0, index=range(horizonte + 1), columns=columnas)
    
    # --- Inicialización de Deuda y CAPEX ---
    df["CAPEX"] = -capex.reindex(df.index, fill_value=0.0)
    if tabla_amortizacion is not None:
        df["Intereses"] = tabla_amortizacion["Interés"].reindex(df.index, fill_value=0.0)
        df["Amortización Principal"] = -tabla_amortizacion["Principal"].reindex(df.index, fill_value=0.0)
        df["Saldo Deuda"] = tabla_amortizacion["Saldo Pendiente"].reindex(df.index, fill_value=0.0)
        # El saldo en t=0 es el monto total a desembolsar
        df.loc[0, "Saldo Deuda"] = monto_deuda_total

    df.loc[0, "Entrada Deuda"] = monto_deuda_total
    df.loc[0, "Net Debt Issued"] = monto_deuda_total
    df.loc[0, "FCF No Apalancado (FCFF)"] = df.loc[0, "CAPEX"]
    df.loc[0, "FCF Apalancado (FCFE)"] = df.loc[0, "FCF No Apalancado (FCFF)"] + df.loc[0, "Net Debt Issued"]
    df.loc[0, "Flujo Caja Neto Inversionista"] = df.loc[0, "FCF Apalancado (FCFE)"]
    
    # Lotes Totales
    total_lotes = sum(plan["cantidad_lotes"] for plan in p.get("planes_venta", []))
    df.loc[0, "Lotes en Inventario"] = total_lotes
    
    cobros_programados_pies = np.zeros(horizonte + 1)
    cobros_programados_cuotas = np.zeros(horizonte + 1)
    
    v_planes = []
    for p_v in p.get("planes_venta", []):
        v_planes.append({**p_v, "lotes_restantes": p_v["cantidad_lotes"]})
    
    crecimiento_anual = p["ventas"].get("crecimiento_precio_anual", 0.0)
    perdida_arrastrable = 0.0

    for mes in range(1, horizonte + 1):
        factor_precio = (1 + crecimiento_anual) ** ((mes - 1) // 12)
        lotes_vendidos_mes = 0
        
        for plan in v_planes:
            if plan["lotes_restantes"] > 0:
                if plan.get("tipo", "Dinámico") == "Programado":
                    if mes == plan.get("mes_inicio", 1):
                        vendidos = plan["lotes_restantes"]
                        plan["lotes_restantes"] = 0
                    else: vendidos = 0
                else:
                    vendidos = min(plan["velocidad"], plan["lotes_restantes"])
                    plan["lotes_restantes"] -= vendidos
                
                lotes_vendidos_mes += vendidos
                if vendidos > 0:
                    monto_pie = (plan["monto_pie"] * factor_precio) * vendidos
                    if mes <= horizonte: cobros_programados_pies[mes] += monto_pie
                    monto_cuota = plan["monto_cuota"] * factor_precio
                    for _ in range(vendidos):
                        for c_idx in range(plan["cantidad_cuotas"]):
                            mes_cobro = mes + (c_idx * plan["frecuencia"]) + (0 if plan.get("tipo") == "Programado" else 1)
                            if mes_cobro <= horizonte:
                                cobros_programados_cuotas[mes_cobro] += monto_cuota

        df.loc[mes, "Lotes Vendidos"] = lotes_vendidos_mes
        df.loc[mes, "Lotes en Inventario"] = df.loc[mes-1, "Lotes en Inventario"] - lotes_vendidos_mes
        df.loc[mes, "Ingresos Ventas Pies"] = cobros_programados_pies[mes]
        df.loc[mes, "Ingresos Ventas Cuotas"] = cobros_programados_cuotas[mes]
        
        # Otros Ingresos y Gastos
        ing_periodico = 0
        cost_dinamico = 0
        
        # Primero sumamos ingresos para tener la base de ventas
        for item in p.get("items_periodicos", []):
            if item["mes_inicio"] <= mes <= item["mes_fin"] and item["tipo"] == "Ingreso":
                ing_periodico += item["monto"]
        
        df.loc[mes, "Otros Ingresos"] = ing_periodico
        ing_totales = df.loc[mes, "Ingresos Ventas Pies"] + df.loc[mes, "Ingresos Ventas Cuotas"] + ing_periodico
        df.loc[mes, "Ingresos Totales"] = ing_totales
        
        # Ahora calculamos gastos (que pueden depender de Ingresos Totales o Lotes en Inventario)
        for item in p.get("items_periodicos", []):
            if item["mes_inicio"] <= mes <= item["mes_fin"] and item["tipo"] == "Gasto":
                base = item.get("base_calculo", "Monto Fijo")
                if base == "Monto Fijo":
                    cost_dinamico += item["monto"]
                elif base == "% Ventas":
                    cost_dinamico += ing_totales * (item["monto"] / 100)
                elif base == "Por Lote Inventario":
                    cost_dinamico += df.loc[mes, "Lotes en Inventario"] * item["monto"]
                elif base == "% Utilidad":
                    # EBITDA preliminar sin este gasto
                    ebitda_pre = ing_totales - cost_dinamico
                    cost_dinamico += max(0, ebitda_pre) * (item["monto"] / 100)

        df.loc[mes, "Costos Operativos Dinámicos"] = -cost_dinamico
        df.loc[mes, "EBITDA"] = df.loc[mes, "Ingresos Totales"] + df.loc[mes, "Costos Operativos Dinámicos"]
        
        # Resto del P&L
        df.loc[mes, "EBIT"] = df.loc[mes, "EBITDA"] - df.loc[mes, "Depreciacion"]
        df.loc[mes, "EBT"] = df.loc[mes, "EBIT"] - df.loc[mes, "Intereses"]
        
        base_imp = df.loc[mes, "EBT"]
        if base_imp < 0:
            perdida_arrastrable += abs(base_imp)
            df.loc[mes, "Impuestos"] = 0
        else:
            uso_perdida = min(base_imp, perdida_arrastrable)
            df.loc[mes, "Perdida Arrastrable Usada"] = uso_perdida
            perdida_arrastrable -= uso_perdida
            df.loc[mes, "Base Imponible"] = base_imp - uso_perdida
            df.loc[mes, "Impuestos"] = -df.loc[mes, "Base Imponible"] * tasa_impuesto
            
        df.loc[mes, "Utilidad Neta"] = df.loc[mes, "EBT"] + df.loc[mes, "Impuestos"]
        df.loc[mes, "NOPAT"] = df.loc[mes, "EBIT"] * (1 - tasa_impuesto)
        df.loc[mes, "FCF Operativo"] = df.loc[mes, "EBITDA"] + df.loc[mes, "Impuestos"]
        df.loc[mes, "FCF No Apalancado (FCFF)"] = df.loc[mes, "FCF Operativo"] + df.loc[mes, "CAPEX"]
        df.loc[mes, "Net Debt Issued"] = df.loc[mes, "Entrada Deuda"] + df.loc[mes, "Amortización Principal"]
        df.loc[mes, "FCF Apalancado (FCFE)"] = df.loc[mes, "FCF No Apalancado (FCFF)"] + df.loc[mes, "Net Debt Issued"]
        
        df.loc[mes, "Flujo Caja Neto Inversionista"] = df.loc[mes, "FCF Apalancado (FCFE)"]

    # Métricas de rentabilidad basadas en el flujo del inversionista
    flujo_inv = df["Flujo Caja Neto Inversionista"]
    # La inversión total de equity es la suma de todos los flujos negativos
    equity_invertido = abs(flujo_inv[flujo_inv < 0].sum())
    total_retornado = flujo_inv[flujo_inv > 0].sum()
    
    df.attrs["roi_estatico"] = (total_retornado - equity_invertido) / equity_invertido if equity_invertido > 0 else 0
    df.attrs["multiplo_capital"] = (total_retornado / equity_invertido) if equity_invertido > 0 else 0
    
    return df

# ==============================================================================
# 4. FUNCIONES DE MÉTRICAS FINANCIERAS
# ==============================================================================

def calculateIRR(cashFlows):
    """
    Implementa el cálculo de la TIR según el estándar fintech inmobiliario.
    """
    flujos = np.array(cashFlows, dtype=float)
    n = len(flujos)
    
    res_error = {
        "tir_mensual": None,
        "tir_anual_equivalente": None,
        "cash_flows": flujos.tolist(),
        "converged": False
    }

    if n == 0: return res_error
    
    pos_flows = flujos[flujos > 0]
    neg_flows = flujos[flujos < 0]
    
    if len(pos_flows) == 0 or len(neg_flows) == 0:
        return res_error
        
    if np.sum(pos_flows) <= abs(np.sum(neg_flows)):
        return res_error

    def calcular_van(tasa):
        if tasa <= -1.0: return np.inf
        try:
            with np.errstate(all='ignore'):
                t = np.arange(n)
                factores = (1.0 + tasa) ** (-t)
                van = np.sum(flujos * factores)
                return van if np.isfinite(van) else (np.inf if van > 0 else -np.inf)
        except:
            return np.nan

    # Bracketing y Bisección por rangos
    # Priorizamos encontrar la raíz más cercana a 0 que sea financieramente lógica
    r_found = False
    res_is_cash_out = False
    
    # 1. Caso Especial: Cash-Out Inicial (Rentabilidad potencialmente infinita o no definida tradicionalmente)
    # Si el primer flujo es positivo y la suma total es positiva, es un Cash-Out.
    if flujos[0] > 0 and np.sum(flujos) > 0:
        return {
            "tir_mensual": 10.0, # Representamos como 1000% mensual (límite)
            "tir_anual_equivalente": float((1 + 10.0) ** 12 - 1),
            "cash_flows": flujos.tolist(),
            "converged": True,
            "is_cash_out": True
        }

    # 2. Búsqueda de bracket en múltiples puntos para manejar multi-raíz por apalancamiento
    # Probamos una malla de puntos desde -99% hasta 500% mensual
    puntos = np.concatenate([
        np.linspace(-0.99, -0.1, 10),
        np.linspace(-0.1, 1.0, 20),
        np.linspace(1.0, 10.0, 10)
    ])
    
    for i in range(len(puntos) - 1):
        low, high = puntos[i], puntos[i+1]
        v_low = calcular_van(low)
        v_high = calcular_van(high)
        
        if np.isfinite(v_low) and np.isfinite(v_high) and np.sign(v_low) != np.sign(v_high):
            # Encontramos un bracket! Bisección
            for _ in range(100):
                mid = (low + high) / 2.0
                v_mid = calcular_van(mid)
                
                if not np.isfinite(v_mid):
                    mid = low + (high - low) * 0.1
                    v_mid = calcular_van(mid)

                if abs(v_mid) < 1e-4: # Tolerancia relajada para flujos grandes
                    low = mid
                    r_found = True
                    break
                
                if np.sign(v_low) != np.sign(v_mid):
                    high = mid
                    v_high = v_mid
                else:
                    low = mid
                    v_low = v_mid
            
            if r_found: break

    if not r_found:
        return res_error

    tir_m = low
    # Validación final: El VAN debe ser pequeño relativo a la magnitud de los flujos
    van_final = calcular_van(tir_m)
    magnitud_flujos = np.abs(flujos).max()
    if not np.isfinite(van_final) or (abs(van_final) / magnitud_flujos > 1e-3):
        return res_error
        
    # Detectar cambios de signo para advertencia de multiplicidad
    sign_changes = 0
    last_sign = 0
    for f in flujos:
        if abs(f) > 1e-4:
            current_sign = np.sign(f)
            if last_sign != 0 and current_sign != last_sign:
                sign_changes += 1
            last_sign = current_sign

    return {
        "tir_mensual": float(tir_m),
        "tir_anual_equivalente": float((1 + tir_m) ** 12 - 1),
        "cash_flows": flujos.tolist(),
        "converged": True,
        "multiple_roots_possible": bool(sign_changes > 1),
        "is_cash_out": False
    }

def TIR_anual(flujos):
    """Mantiene compatibilidad con el resto del código."""
    res = calculateIRR(flujos)
    return res["tir_anual_equivalente"] if res["converged"] else None

def VAN(flujos, tasa_descuento_anual):
    """
    Calcula el Valor Actual Neto (VAN) con compounding mensual.
    """
    tasa_mensual = tasa_descuento_anual / 12
    val_actual = 0
    flujos_valores = flujos.values if isinstance(flujos, pd.Series) else flujos
    for t, cf in enumerate(flujos_valores):
        val_actual += cf / ((1 + tasa_mensual) ** t)
    return val_actual

def WACC(p):
    cfg_fin = p["financiamiento"]
    kd, ke = cfg_fin["costo_deuda_anual"], cfg_fin["costo_capital_propio_anual"]
    
    # Si no existe porcentaje_deuda, calcularlo dinámicamente
    if "porcentaje_deuda" in cfg_fin:
        wd = cfg_fin["porcentaje_deuda"]
    else:
        inv_total = calcular_inversion_total(p)
        monto_d = cfg_fin.get("monto_deuda", 0)
        wd = monto_d / inv_total if inv_total > 0 else 0
        
    we = 1 - wd
    t = cfg_fin["tasa_impuesto_renta"]
    return (we * ke) + (wd * kd * (1 - t)) if wd > 0 else ke

# ==============================================================================
# 5. MÓDULO DE ANÁLISIS DE SENSIBILIDAD
# ==============================================================================

def analisis_de_sensibilidad(p_base):
    print("\n" + "="*70)
    print(" ANÁLISIS DE SENSIBILIDAD")
    print("="*70)

    escenarios = {
        "Crecimiento Precio": ("ventas", "crecimiento_precio_anual"),
        "Tasa Préstamo": ("financiamiento", "costo_deuda_anual"),
        "Monto Préstamo": ("financiamiento", "monto_deuda"),
    }
    variaciones = [-0.20, -0.10, 0.0, 0.10, 0.20]
    resultados_sensibilidad = []

    for nombre_variable, (seccion, clave) in escenarios.items():
        for variacion in variaciones:
            p_test = copy.deepcopy(p_base)
            
            if seccion == "cronograma_inversion":
                for item in p_test[seccion]:
                    if item.get("tag_sensibilidad") == clave:
                        item["monto"] *= (1 + variacion)
            else:
                valor_base = p_test[seccion][clave]
                p_test[seccion][clave] = valor_base * (1 + variacion)

            # Re-correr el modelo con los nuevos parámetros
            inv_total_test = calcular_inversion_total(p_test)
            monto_deuda_test = p_test["financiamiento"]["monto_deuda"]
            capex_test = construir_cronograma_inversiones(p_test)
            deuda_test = crear_tabla_amortizacion(p_test, monto_deuda_test)
            modelo_test = generar_modelo_financiero_detallado(p_test, capex_test, deuda_test, monto_deuda_test)
            
            flujo_inv_test = modelo_test["Flujo Caja Neto Inversionista"]
            
            costo_capital_test = p_test["financiamiento"]["costo_capital_propio_anual"]
            van_inv_test = VAN(flujo_inv_test, costo_capital_test)
            tir_inv_test = TIR_anual(flujo_inv_test)
            
            resultados_sensibilidad.append({
                "Variable": nombre_variable,
                "Variación": f"{variacion:.0%}",
                "VAN Inversionista": van_inv_test,
                "TIR Inversionista": tir_inv_test
            })

    df_sensibilidad = pd.DataFrame(resultados_sensibilidad)
    
    # Formatear y mostrar la tabla de sensibilidad
    df_pivot = df_sensibilidad.pivot(index="Variable", columns="Variación", values="VAN Inversionista")
    df_pivot_tir = df_sensibilidad.pivot(index="Variable", columns="Variación", values="TIR Inversionista")
    
    print("\n--- Sensibilidad del VAN del Inversionista (en miles) ---")
    print(df_pivot.to_string(float_format="{:,.0f}".format))
    
    print("\n--- Sensibilidad de la TIR del Inversionista ---")
    print(df_pivot_tir.to_string(float_format="{:.2%}".format))
    print("="*70)

# ==============================================================================
# 6. EJECUCIÓN DEL MODELO Y REPORTE DE RESULTADOS (SI SE EJECUTA COMO SCRIPT)
# ==============================================================================
if __name__ == "__main__":
    # --- Parámetros Base del Proyecto ---
    parametros = {
        "horizonte_meses": 120,
        "cronograma_inversion": [
            {"item": "Compra Terreno", "monto": 5_000_000, "mes": 0, "tag_sensibilidad": "costo_terreno"},
            {"item": "Comercialización Inicial", "monto": 800_000, "mes": 0, "tag_sensibilidad": "costo_marketing"},
            {"item": "Otros Costos Iniciales", "monto": 500_000, "mes": 0, "tag_sensibilidad": "costo_otros"},
            {"item": "Urbanización - Fase 1", "monto": 4_000_000, "mes": 2, "tag_sensibilidad": "costo_urbanizacion"},
            {"item": "Proyecto Legal", "monto": 1_200_000, "mes": 3, "tag_sensibilidad": "costo_legal"},
            {"item": "Urbanización - Fase 2", "monto": 4_000_000, "mes": 6, "tag_sensibilidad": "costo_urbanizacion"},
        ],
        "ventas": {
            "crecimiento_precio_anual": 0.05,
        },
        "costos_operativos": {
            "costo_operativo_mensual": 120_000,
            "mantenimiento_mensual": 40_000,
            "impuestos_prediales_mensual": 25_000,
        },
        "financiamiento": {
            "monto_deuda": 9_300_000,
            "costo_deuda_anual": 0.12,
            "plazo_deuda_meses": 84,
            "costo_capital_propio_anual": 0.18,
            "tasa_impuesto_renta": 0.30,
            "capitalizacion": "Mensual",
        },
        "planes_venta": [
            {
                "nombre": "Preventa",
                "cantidad_lotes": 100,
                "velocidad": 5,
                "monto_pie": 30000,
                "monto_cuota": 2000,
                "frecuencia": 1,
                "cantidad_cuotas": 60
            },
            {
                "nombre": "Venta Normal",
                "cantidad_lotes": 100,
                "velocidad": 3,
                "monto_pie": 50000,
                "monto_cuota": 3000,
                "frecuencia": 1,
                "cantidad_cuotas": 48
            }
        ],
        "items_periodicos": [],
    }

    print("="*70)
    print(" ANÁLISIS FINANCIERO v4.0 (CON ANÁLISIS DE SENSIBILIDAD)")
    print("="*70)

    # --- Cálculos Base ---
    inversion_total = calcular_inversion_total(parametros)
    monto_deuda = parametros["financiamiento"]["monto_deuda"]
    monto_capital_propio = inversion_total - monto_deuda
    
    # Inyectar porcentaje para cálculo de WACC
    parametros["financiamiento"]["porcentaje_deuda"] = monto_deuda / inversion_total if inversion_total > 0 else 0

    cronograma_capex = construir_cronograma_inversiones(parametros)
    tabla_amortizacion = crear_tabla_amortizacion(parametros, monto_deuda)
    modelo_financiero_df = generar_modelo_financiero_detallado(parametros, cronograma_capex, tabla_amortizacion, monto_deuda)

    flujo_caja_proyecto = modelo_financiero_df["FCF No Apalancado (FCFF)"]
    flujo_caja_inversionista = modelo_financiero_df["Flujo Caja Neto Inversionista"]

    wacc_calculado = WACC(parametros)
    costo_capital = parametros["financiamiento"]["costo_capital_propio_anual"]
    van_proyecto = VAN(flujo_caja_proyecto, wacc_calculado)
    tir_proyecto = TIR_anual(flujo_caja_proyecto)
    van_inversionista = VAN(flujo_caja_inversionista, costo_capital)
    tir_inversionista = TIR_anual(flujo_caja_inversionista)
    
    # Métricas de rentabilidad del modelo
    roi_total = modelo_financiero_df.attrs["roi_estatico"]
    multiplo = modelo_financiero_df.attrs["multiplo_capital"]

    # --- Reporte de Resultados Base ---
    print("\n--- RESULTADOS DEL CASO BASE ---")
    print(f"Inversión Total Proyectada: {inversion_total:,.2f}")
    print(f"  - Monto Deuda: {parametros['financiamiento']['monto_deuda']:,.2f}")
    print(f"  - Capital Propio Requerido: {monto_capital_propio:,.2f}")
    print(f"WACC: {wacc_calculado:.2%}")
    print(f"Costo del Capital Propio (Ke): {costo_capital:.2%}")
    print("\n--- Métricas del Proyecto (No Apalancado - FCFF) ---")
    print(f"VAN del Proyecto: {van_proyecto:,.2f}")
    print(f"TIR del Proyecto (IRR): {tir_proyecto:.2%}" if tir_proyecto is not None else "TIR del Proyecto (IRR): No se pudo calcular")
    print("\n--- Métricas del Inversionista (Apalancado - FCFE) ---")
    print(f"VAN para el Inversionista: {van_inversionista:,.2f}")
    print(f"TIR para el Inversionista (IRR): {tir_inversionista:.2%}" if tir_inversionista is not None else "TIR para el Inversionista (IRR): No se pudo calcular")
    print(f"Retorno sobre Inversión (ROI Total): {roi_total:.2%}")
    print(f"Múltiplo sobre Capital (MOIC): {multiplo:.2f}x")

    # --- Ejecución del Análisis de Sensibilidad ---
    analisis_de_sensibilidad(parametros)