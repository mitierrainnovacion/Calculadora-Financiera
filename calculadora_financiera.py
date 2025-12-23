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
            "cantidad_lotes": 100,
            "velocidad": 5,
            "monto_pie": 30000,
            "monto_cuota": 2000,
            "frecuencia": 1,
            "cantidad_cuotas": 60,
            "tipo": "Dinámico",
            "mes_inicio": 1
        },
        {
            "nombre": "Venta Normal",
            "cantidad_lotes": 100,
            "velocidad": 3,
            "monto_pie": 50000,
            "monto_cuota": 3000,
            "frecuencia": 1,
            "cantidad_cuotas": 48,
            "tipo": "Dinámico",
            "mes_inicio": 1
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
    Calcula la tabla de amortización usando el SISTEMA ALEMÁN (amortización de capital constante por período de pago).
    Soporta diferentes frecuencias de capitalización/pago.

    - `plazo_deuda_meses` es el horizonte en meses del préstamo.
    - `capitalizacion` define la frecuencia de pago en meses (Mensual=1, Trimestral=3, Semestral=6, Anual=12).
    - La tasa anual `costo_deuda_anual` se interpreta como tasa efectiva anual (EAR).
    """
    import math

    plazo_meses = p["financiamiento"]["plazo_deuda_meses"]
    tasa_anual = p["financiamiento"]["costo_deuda_anual"]
    freq_map = {"Mensual": 1, "Trimestral": 3, "Semestral": 6, "Anual": 12}
    period_months = freq_map.get(p["financiamiento"].get("capitalizacion", "Mensual"), 1)

    # Número de pagos (uno cada `period_months`)
    if period_months <= 0:
        period_months = 1
    num_payments = math.ceil(plazo_meses / period_months) if plazo_meses > 0 else 0

    # Tasa por período de pago (efectiva para el periodo)
    # Si tasa_anual es EAR, la tasa periódica es:
    periodic_rate = (1 + tasa_anual) ** (period_months / 12.0) - 1 if num_payments > 0 else 0.0

    # Amortización de capital por pago (sistema alemán: capital constante por pago)
    amort_por_pago = (monto_deuda / num_payments) if num_payments > 0 else 0.0

    cronograma = []
    saldo = monto_deuda

    horizonte = p["horizonte_meses"]
    for mes in range(1, horizonte + 1):
        if mes <= plazo_meses:
            interes_pagado = 0.0
            principal_pagado = 0.0

            # Si es mes de pago (cada period_months), se paga interés + principal
            if mes % period_months == 0:
                # calcular interés sobre el saldo vigente al inicio del período
                interes_pagado = saldo * periodic_rate
                principal_pagado = amort_por_pago

                # evitar sobregiro final por redondeos
                principal_pagado = min(principal_pagado, saldo)
                saldo -= principal_pagado

            cronograma.append({
                "Mes": mes,
                "Saldo Inicial": saldo + principal_pagado,
                "Interés": interes_pagado,
                "Principal": principal_pagado,
                "Saldo Pendiente": max(0.0, saldo)
            })
        else:
            cronograma.append({
                "Mes": mes,
                "Saldo Inicial": 0.0,
                "Interés": 0.0,
                "Principal": 0.0,
                "Saldo Pendiente": 0.0
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
    
    # Deuda y CAPEX
    df["CAPEX"] = -capex.reindex(df.index, fill_value=0.0)
    if tabla_amortizacion is not None:
        df["Intereses"] = tabla_amortizacion["Interés"].reindex(df.index, fill_value=0.0)
        df["Amortización Principal"] = -tabla_amortizacion["Principal"].reindex(df.index, fill_value=0.0)
        df["Saldo Deuda"] = tabla_amortizacion["Saldo Pendiente"].reindex(df.index, fill_value=0.0)
    df.loc[0, "Entrada Deuda"] = monto_deuda_total
    
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
        factor_precio = (1 + crecimiento_anual) ** ((mes - 1) / 12.0)
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
        
        capital_aportado = 0
        if mes == 1:
            capital_inv = abs(df.loc[0, "CAPEX"]) - df.loc[0, "Entrada Deuda"]
            capital_aportado = max(0, capital_inv)
        
        df.loc[mes, "Aportación Capital"] = capital_aportado
        df.loc[mes, "Flujo Caja Neto Inversionista"] = df.loc[mes, "FCF Apalancado (FCFE)"] - capital_aportado

    df.attrs["roi_estatico"] = (df["Utilidad Neta"].sum() / abs(df.loc[0, "CAPEX"])) if abs(df.loc[0, "CAPEX"]) != 0 else 0
    aport = df.loc[1, "Aportación Capital"] if 1 in df.index else 0
    df.attrs["multiplo_capital"] = ((np.nan if aport == 0 else (df["Flujo Caja Neto Inversionista"].sum() + aport) / aport))
    
    return df

# ==============================================================================
# 4. FUNCIONES DE MÉTRICAS FINANCIERAS
# ==============================================================================

def _resolver_tir(flujos, iteraciones=100):
    """
    Resuelve la Tasa Interna de Retorno (TIR) usando las raíces del polinomio
    del Valor Presente Neto (VPN).
    
    VPN = C0 + C1/(1+r) + C2/(1+r)^2 + ... + Cn/(1+r)^n = 0
    Haciendo x = 1/(1+r), tenemos:
    C0 + C1*x + C2*x^2 + ... + Cn*x^n = 0
    
    Se usa numpy.roots para hallar x, y luego se despeja r = (1/x) - 1.
    """
    flujos = np.array(flujos, dtype=float)
    
    # Validaciones básicas
    if len(flujos) == 0:
        print("DEBUG TIR: Flujos vacíos.")
        return None
    # Debe haber al menos un positivo y un negativo
    if not (np.any(flujos > 0) and np.any(flujos < 0)):
        print(f"DEBUG TIR: Flujos sin cambio de signo. Min: {flujos.min()}, Max: {flujos.max()}")
        return None

    try:
        # np.roots espera coeficientes de mayor a menor potencia: [Cn, ..., C1, C0]
        # Nuestros flujos son [C0, C1, ..., Cn].
        # El polinomio es C0 + C1*x + ... + Cn*x^n.
        # Por lo tanto, los coeficientes en orden descendente de potencia son flujos invertidos.
        coeffs = flujos[::-1]
        
        # Calcular raíces
        roots = np.roots(coeffs)
        
        # Filtrar raíces reales
        real_roots = roots[np.isreal(roots)].real
        
        # x = 1/(1+r). Si r > -1 (tasa razonable), entonces x > 0.
        positive_roots = real_roots[real_roots > 0]
        
        if len(positive_roots) == 0:
            print("DEBUG TIR: No se encontraron raíces positivas (x > 0).")
            return None
        
        # Convertir a tasas: r = (1/x) - 1
        rates = (1.0 / positive_roots) - 1.0
        
        # Validar tasas razonables (ej. > -0.99 para evitar -100%)
        # Ampliamos filtro inferior por si es una pérdida casi total
        valid_rates = rates[rates > -0.9999]
        
        if len(valid_rates) == 0:
            print(f"DEBUG TIR: Todas las tasas filtradas por ser < -99.99%. Tasas crudas: {rates}")
            return None
        
        # Filtrar tasas excesivamente altas (ej. > 100% mensual)
        # Esto evita tasas astronómicas que resultan de raíces espurias cercanas a 0.
        final_rates = valid_rates[valid_rates < 1.0]
        
        if len(final_rates) == 0:
             print(f"DEBUG TIR: Todas las tasas filtradas por ser > 100% mensual. Tasas válidas: {valid_rates}")
             return None

        # Si hay múltiples soluciones lógicas, buscamos la que dé el VAN más cercano a cero
        # Y preferimos la tasa más cercana a 0 (más realista) si el error de VAN es similar.
        best_rate = None
        min_van_error = float('inf')
        
        # Pre-cálculo para VAN rápido
        t = np.arange(len(flujos))
        
        for r in final_rates:
            try:
                # Calcular VAN para esta tasa
                factor = 1.0 + r
                # Evitar overflow en potencias grandes
                denom = factor ** t
                van = np.sum(flujos / denom)
                
                # Check error
                err = abs(van)
                if err < min_van_error:
                    min_van_error = err
                    best_rate = r
            except:
                continue
                
        return best_rate

    except Exception as e:
        print(f"DEBUG TIR: Error en cálculo: {str(e)}")
        return None

def TIR_anual(flujos):
    try:
        # IRR is only meaningful if there is at least one positive and one negative cash flow
        flujos_validos = flujos.values if isinstance(flujos, pd.Series) else flujos
        if not (any(f > 0 for f in flujos_validos) and any(f < 0 for f in flujos_validos)):
            return None
            
        # Resolver la TIR mensual usando el método de Newton-Raphson
        tir_m = _resolver_tir(flujos_validos)

        # Si no se encuentra raíz, retornar None
        if tir_m is None or not np.isfinite(tir_m):
            return None
            
        # Anualizar la TIR mensual
        return (1 + tir_m) ** 12 - 1
    except Exception:
        # If any other unexpected error occurs, return None
        return None

def VAN(flujos, tasa_descuento_anual, periodo_meses=1):
    """
    Calcula el Valor Actual Neto (VAN).
    - `tasa_descuento_anual` se interpreta como tasa efectiva anual (EAR).
    - `periodo_meses` define la periodicidad de los flujos (por defecto 1 => mensual).
    """
    # Convertir tasa anual efectiva a tasa por período
    tasa_periodica = (1 + tasa_descuento_anual) ** (periodo_meses / 12.0) - 1
    val_actual = 0.0
    flujos_valores = flujos.values if isinstance(flujos, pd.Series) else np.asarray(flujos, dtype=float)
    for t, cf in enumerate(flujos_valores):
        val_actual += cf / ((1 + tasa_periodica) ** t)
    return val_actual

def WACC(p):
    cfg_fin = p["financiamiento"]
    kd, ke = cfg_fin["costo_deuda_anual"], cfg_fin["costo_capital_propio_anual"]
    wd = p["financiamiento"]["porcentaje_deuda"]
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
        "OPEX Mensual": ("costos_operativos", "costo_operativo_mensual"),
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
            monto_deuda_test = inv_total_test * p_test["financiamiento"]["porcentaje_deuda"]
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