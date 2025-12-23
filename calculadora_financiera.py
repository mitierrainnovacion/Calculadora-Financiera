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
    Genera el modelo financiero detallado con estricta separación de flujos
    de PROYECTO (No Apalancado) vs INVERSIONISTA (Apalancado).
    
    Reglas de Negocio:
    1. FCFF (Proyecto) = NOPAT + Depreciacion + CAPEX (+/- WK).
       - NOPAT usa Impuestos Operativos (asumiendo deuda=0).
       - Excluye intereses y amortización.
    2. FCFE (Inversionista) = FCFF - Intereses*(1-T) - Amortización + Nueva Deuda.
       - Refleja el flujo neto real para el accionista.
    3. t=0: Se maneja explícitamente. Si (CAPEX_0 + Deuda_0) < 0, es aporte de equity.
    """
    horizonte = p["horizonte_meses"]
    tasa_impuesto = p["financiamiento"]["tasa_impuesto_renta"]
    
    # Columnas extendidas para traza clara
    columnas = [
        "Ingresos Ventas Pies", "Ingresos Ventas Cuotas", "Otros Ingresos", "Ingresos Totales",
        "Costos Operativos Dinámicos", "EBITDA", "Depreciacion", "EBIT",
        "Impuestos Operativos (Teóricos)", "NOPAT", "FCF Operativo", "CAPEX", "FCF No Apalancado (FCFF)",
        "Intereses", "Ahorro Fiscal Intereses", "Amortización Principal", "Entrada Deuda",
        "Net Debt Cashflow", "FCF Apalancado (FCFE)",
        # Métricas P&L Real (Contable)
        "EBT", "Impuestos Reales", "Utilidad Neta",
        "Lotes Vendidos", "Lotes en Inventario", "Saldo Deuda"
    ]
    
    # Inicializar DataFrame con t=0 hasta t=Horizonte
    df = pd.DataFrame(0.0, index=range(horizonte + 1), columns=columnas)
    
    # --------------------------------------------------------------------------
    # 1. CARGA DE ESTRUCTURAS DE TIEMPO (CAPEX, DEUDA)
    # --------------------------------------------------------------------------
    
    # CAPEX es negativo (salida de caja)
    df["CAPEX"] = -capex.reindex(df.index, fill_value=0.0)
    
    # Deuda (Tabla Amortización del sistema alemán/francés ya calculado)
    if tabla_amortizacion is not None:
        # Interés y amortización son salidas (positivas en tabla, negativas en flujo)
        # Ajustamos signo en el bucle o aquí. Preferible explícito:
        # Interés es gasto, Amortización es flujo salida.
        interes_reindex = tabla_amortizacion["Interés"].reindex(df.index, fill_value=0.0)
        principal_reindex = tabla_amortizacion["Principal"].reindex(df.index, fill_value=0.0)
        saldo_reindex = tabla_amortizacion["Saldo Pendiente"].reindex(df.index, fill_value=0.0)
        
        df["Intereses"] = interes_reindex
        df["Amortización Principal"] = -principal_reindex # Flujo salida
        df["Saldo Deuda"] = saldo_reindex
    else:
        df["Intereses"] = 0.0
        df["Amortización Principal"] = 0.0
        df["Saldo Deuda"] = 0.0

    # Entrada de Deuda (t=0 usualmente)
    df.loc[0, "Entrada Deuda"] = monto_deuda_total

    # Lotes e Inventario
    total_lotes = sum(plan["cantidad_lotes"] for plan in p.get("planes_venta", []))
    df.loc[0, "Lotes en Inventario"] = total_lotes
    
    # --------------------------------------------------------------------------
    # 2. PROYECCIÓN OPERATIVA (INGRESOS, COSTOS, EBITDA)
    # --------------------------------------------------------------------------
    
    cobros_programados_pies = np.zeros(horizonte + 1)
    cobros_programados_cuotas = np.zeros(horizonte + 1)
    
    v_planes = []
    for p_v in p.get("planes_venta", []):
        v_planes.append({**p_v, "lotes_restantes": p_v["cantidad_lotes"]})
    
    crecimiento_anual = p["ventas"].get("crecimiento_precio_anual", 0.0)
    
    # Variables de estado para pérdidas fiscales (real y operativa)
    perdida_arrastrable_real = 0.0
    # Podríamos modelar pérdida operativa teórica para NOPAT si se desea estricto,
    # por simplicidad NOPAT = EBIT * (1-t) asumiendo escudo inmediato o simplificado.
    
    for mes in range(1, horizonte + 1):
        # A. Ventas
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
        
        # B. Otros Ingresos
        ing_periodico = 0
        for item in p.get("items_periodicos", []):
            if item["mes_inicio"] <= mes <= item["mes_fin"] and item["tipo"] == "Ingreso":
                ing_periodico += item["monto"]
        
        df.loc[mes, "Otros Ingresos"] = ing_periodico
        ing_totales = df.loc[mes, "Ingresos Ventas Pies"] + df.loc[mes, "Ingresos Ventas Cuotas"] + ing_periodico
        df.loc[mes, "Ingresos Totales"] = ing_totales
        
        # C. Costos Operativos
        cost_dinamico = 0
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
                    ebitda_pre = ing_totales - cost_dinamico
                    cost_dinamico += max(0, ebitda_pre) * (item["monto"] / 100)
        
        df.loc[mes, "Costos Operativos Dinámicos"] = -cost_dinamico
        df.loc[mes, "EBITDA"] = df.loc[mes, "Ingresos Totales"] + df.loc[mes, "Costos Operativos Dinámicos"]
        df.loc[mes, "EBIT"] = df.loc[mes, "EBITDA"] - df.loc[mes, "Depreciacion"]

    # --------------------------------------------------------------------------
    # 3. FLUJO DE CAJA DEL PROYECTO (UNLEVERAGED)
    # --------------------------------------------------------------------------
    # NOPAT = EBIT * (1 - T). Asumimos impuestos operativos teóricos sin deuda.
    # FCFF = NOPAT + Depreciacion + CAPEX
    
    # Manejo de impuestos operativos negativos:
    # Si EBIT < 0, impuesto operativo es 0 (o crédito fiscal si se asume simetría perfecta).
    # Para ser conservador y estándar: Impuesto Operativo = max(0, EBIT) * T
    df["Impuestos Operativos (Teóricos)"] = df["EBIT"].apply(lambda x: -x * tasa_impuesto if x > 0 else 0)
    df["NOPAT"] = df["EBIT"] + df["Impuestos Operativos (Teóricos)"] 
    df["FCF Operativo"] = df["NOPAT"] + df["Depreciacion"] # (+/- Variación Capital de Trabajo si existiera)
    
    # FCFF incluye todos los periodos (t=0 también, donde EBIT=0, pero CAPEX != 0)
    df["FCF No Apalancado (FCFF)"] = df["FCF Operativo"] + df["CAPEX"]

    # --------------------------------------------------------------------------
    # 4. FLUJO DE CAJA DEL INVERSIONISTA (LEVERAGED)
    # --------------------------------------------------------------------------
    # P&L Real (con Intereses) para impuestos reales
    df["EBT"] = df["EBIT"] - df["Intereses"]
    
    # Cálculo de impuestos reales con pérdida arrastrable
    impuestos_reales = []
    p_arrastrable = 0.0
    
    for val_ebt in df["EBT"]:
        if val_ebt < 0:
            p_arrastrable += abs(val_ebt)
            impuestos_reales.append(0.0)
        else:
            uso = min(val_ebt, p_arrastrable)
            p_arrastrable -= uso
            base = val_ebt - uso
            impuestos_reales.append(-base * tasa_impuesto)
            
    df["Impuestos Reales"] = impuestos_reales
    df["Utilidad Neta"] = df["EBT"] + df["Impuestos Reales"]
    
    # Derivación FCFE desde FCFF (Método Estándar Robusto)
    # FCFE = FCFF - Intereses*(1-T) - Amortización + Deuda Nueva
    
    # Ahorro Fiscal de Intereses (Tax Shield)
    # OJO: La fórmula FCFF - Int(1-t) asume que la empresa paga impuestos operativos y recupera el escudo.
    # Si usamos los impuestos reales calculados arriba, es más exacto hacer:
    # FCFE = Utilidad Neta + Depreciacion + CAPEX + Amortizacion + Deuda Nueva - VariacionCapitalTrabajo
    # Validemos contra la fórmula pedida:
    # FCFE request: FCFF - Int(1-T) - Amort + Deuda
    
    # Calculamos el Escudo Fiscal REAL que se usó (diferencia entre impuesto operativo y real no es solo intereses, es p.arrastrable)
    # Para consistencia absoluta con el P&L, usaremos el método directo desde la Utilidad Neta, 
    # que es matemáticamente equivalente pero evita errores de escudo fiscal teórico vs real.
    
    # FCFE = Utilidad Neta + Depreciacion + CAPEX + (Entrada Deuda + Amortización Principal)
    # Nota: Amortización Principal ya es negativa.
    
    df["Net Debt Cashflow"] = df["Entrada Deuda"] + df["Amortización Principal"]
    
    # Método "Directo" (Más seguro para P&L complejo):
    df["FCF Apalancado (FCFE)"] = (
        df["Utilidad Neta"] + 
        df["Depreciacion"] + 
        df["CAPEX"] + 
        df["Net Debt Cashflow"]
    )
    
    # Nota: En t=0, Utilidad=0, Dep=0. FCFE_0 = CAPEX_0 + Deuda_0. 
    # Si CAPEX=-100 y Deuda=60 -> FCFE = -40 (Equity Injection). Correcto.
    
    # "Flujo Caja Neto Inversionista" es simplemente alias de FCFE para el GUI
    # Las aportaciones de capital negativas YA ESTÁN INCLUIDAS en FCFE cuando es negativo.
    # No necesitamos columna separada "Aportación Capital" forzada, salvo para visualización.
    df["Flujo Caja Neto Inversionista"] = df["FCF Apalancado (FCFE)"]
    
    # Para visualización en GUI, podemos extraer los negativos como "Aportación"
    df["Aportación Capital"] = df["FCF Apalancado (FCFE)"].apply(lambda x: -x if x < 0 else 0)

    # --------------------------------------------------------------------------
    # 5. KPIS SIMPLES
    # --------------------------------------------------------------------------
    # ROI Estático (basado en inversión inicial total o equity sumado)
    total_capex = abs(df["CAPEX"].sum())
    df.attrs["roi_estatico"] = (df["Utilidad Neta"].sum() / total_capex) if total_capex != 0 else 0
    
    # Múltiplo sobre Equity (MOIC)
    # Suma de flujos positivos / Suma de flujos negativos (en abs)
    f_pos = df[df["FCF Apalancado (FCFE)"] > 0]["FCF Apalancado (FCFE)"].sum()
    f_neg = abs(df[df["FCF Apalancado (FCFE)"] < 0]["FCF Apalancado (FCFE)"].sum())
    
    df.attrs["multiplo_capital"] = (f_pos / f_neg) if f_neg > 0 else np.nan
    
    return df


# ==============================================================================
# 4. FUNCIONES DE MÉTRICAS FINANCIERAS
# ==============================================================================

def _npv_at_rate(flujos, r):
    """
    Evaluate NPV for monthly rate r. r must be > -1 (denominator positive for t>=0).
    Robust against overflow in power calculation.
    """
    flujos_valores = flujos.values if hasattr(flujos, "values") else list(flujos)
    
    # Use loop for safety against overflow/div0 issues if r is extreme
    denom_base = 1.0 + r
    
    if denom_base <= 0:
         # Technically undefined for real log, but if r < -1 we flip signs violently or div by zero
         # For finance, we just return infinity if we hit a zero denominator
         return float('inf') 

    val_actual = 0.0
    # Suppress warnings for division/overflow as we handle them explicitly
    with np.errstate(divide='ignore', over='ignore', invalid='ignore'):
        for t, cf in enumerate(flujos_valores):
            if cf == 0: continue
            try:
                denom = denom_base ** t
                if denom == 0:
                    return float('inf') if cf > 0 else -float('inf')
                
                term = cf / denom
                val_actual += term
            except (OverflowError, FloatingPointError, ZeroDivisionError):
                 if abs(denom_base) > 1:
                     pass 
                 else:
                     return float('inf') if cf > 0 else -float('inf')
                 
    return val_actual


def _find_roots_by_bracketing(flujos, r_min=-0.9999, r_max=5.0, steps=2000, tol=1e-8, maxiter=200):
    """
    Scan r grid to find NPV sign-change intervals and apply bisection in each.
    Returns a list of monthly roots found.
    """
    r_grid = np.linspace(r_min, r_max, steps)
    npv_grid = np.array([_npv_at_rate(flujos, r) for r in r_grid])

    roots = []
    for i in range(len(r_grid) - 1):
        y1, y2 = npv_grid[i], npv_grid[i+1]
        if np.isfinite(y1) and np.isfinite(y2) and y1 == 0:
            roots.append(r_grid[i])
        # Use sign check to prevent overflow from y1 * y2
        elif np.isfinite(y1) and np.isfinite(y2) and (np.sign(y1) != np.sign(y2)):
            a, b = r_grid[i], r_grid[i+1]
            fa, fb = y1, y2
            # bisection
            for _ in range(maxiter):
                c = 0.5 * (a + b)
                fc = _npv_at_rate(flujos, c)
                if not np.isfinite(fc):
                    # shrink interval
                    a = 0.5*(a+c)
                    b = 0.5*(b+c)
                    continue
                if abs(fc) <= tol or (b - a) / 2.0 < tol:
                    roots.append(c)
                    break
                if fa * fc < 0:
                    b, fb = c, fc
                else:
                    a, fa = c, fc
            else:
                roots.append(c)
    return roots

def _resolver_tir(flujos):
    """
    Robust IRR resolver returning a single monthly IRR or None.
    Strategy:
      - Validate cash flows (at least one positive and one negative).
      - Find all real roots via bracketing/bisection.
      - If multiple roots, prefer the root with smallest abs(NPV) and penalize unrealistic extremes.
    """
    flujos_list = flujos.values if hasattr(flujos, "values") else list(flujos)
    if len(flujos_list) == 0:
        return None
    if not (any(f > 0 for f in flujos_list) and any(f < 0 for f in flujos_list)):
        return None

    roots = _find_roots_by_bracketing(flujos_list, r_min=-0.9999, r_max=5.0, steps=2000, tol=1e-8)

    feasible = [r for r in roots if np.isfinite(r) and r > -0.9999]
    if len(feasible) == 0:
        return None

    best_r = None
    best_score = float('inf')
    for r in feasible:
        err = abs(_npv_at_rate(flujos_list, r))
        # penalize astronomically large rates (optional)
        penalty = 0.0 if -0.99 < r < 10 else 1.0
        score = err + penalty * 1e6
        if score < best_score:
            best_score = score
            best_r = r

    return best_r

def TIR_anual(flujos, return_structure=False):
    """
    Calculate monthly IRR and annual equivalent.

    If return_structure is True return a dict with metadata.
    Otherwise return tir_anual_equivalente (float) or None.
    """
    flujos_list = flujos.values if hasattr(flujos, "values") else list(flujos)
    result = {
        "tir_mensual": None,
        "tir_anual_equivalente": None,
        "cash_flows": flujos_list,
        "converged": False,
        "notes": ""
    }

    if len(flujos_list) == 0:
        result["notes"] = "Empty cash flow"
        return result if return_structure else None

    if not (any(f > 0 for f in flujos_list) and any(f < 0 for f in flujos_list)):
        result["notes"] = "Cash flow must have at least one positive and one negative value"
        return result if return_structure else None

    tir_m = _resolver_tir(flujos_list)
    if tir_m is None or not np.isfinite(tir_m) or tir_m <= -1:
        result["notes"] = "IRR solver did not converge or returned infeasible rate"
        return result if return_structure else None

    tir_anual = (1.0 + tir_m) ** 12.0 - 1.0
    result["tir_mensual"] = tir_m
    result["tir_anual_equivalente"] = tir_anual
    result["converged"] = True
    return result if return_structure else tir_anual

def VAN(flujos, tasa_descuento_anual, annual_rate_is_effective=True, periodo_meses=1):
    """
    Calcula el Valor Actual Neto (VAN).

    Parameters:
      flujos: iterable of cash flows
      tasa_descuento_anual: annual discount rate (float)
      annual_rate_is_effective: if True, treat tasa_descuento_anual as effective annual rate (EAR).
                               If False, treat as nominal APR (divide by 12).
      periodo_meses: duration of each period in the flows (default 1 = monthly).
    """
    flujos_valores = flujos.values if hasattr(flujos, "values") else list(flujos)

    # 1. Calculate Monthly Effective Rate
    if annual_rate_is_effective:
        tasa_mensual = (1.0 + tasa_descuento_anual) ** (1.0 / 12.0) - 1.0
    else:
        # standard convention: nominal / 12
        tasa_mensual = tasa_descuento_anual / 12.0

    # 2. Adjust for period length
    # If flows are every `periodo_meses`, the discount factor per step is (1 + tasa_mensual)**periodo_meses
    factor_periodo = (1.0 + tasa_mensual) ** periodo_meses
    
    val_actual = 0.0
    for t, cf in enumerate(flujos_valores):
        val_actual += cf / (factor_periodo ** t)
    return val_actual

def WACC(p):
    cfg_fin = p["financiamiento"]
    kd, ke = cfg_fin["costo_deuda_anual"], cfg_fin["costo_capital_propio_anual"]
    wd = p["financiamiento"]["porcentaje_deuda"]
    we = 1 - wd
    t = cfg_fin["tasa_impuesto_renta"]
    return (we * ke) + (wd * kd * (1 - t)) if wd > 0 else ke

def calcular_total_intereses(tabla_amortizacion):
    """
    Calcula el total de intereses pagados en un cronograma de amortización.
    
    Parameters:
      tabla_amortizacion: DataFrame con columna "Interés"
    
    Returns:
      float: suma total de intereses
    """
    if tabla_amortizacion is None or tabla_amortizacion.empty:
        return 0.0
    return tabla_amortizacion["Interés"].sum()

def payback_normal(flujos):
    """
    Calcula el período de recupero simple (Payback Normal).
    
    Parameters:
      flujos: iterable de flujos de caja mensuales
              flujos[0] es la inversión inicial (negativa)
              flujos[t] son los flujos netos del mes t
    
    Returns:
      float: tiempo de recupero en meses (con decimales)
      None: si no se recupera la inversión
    """
    flujos_valores = flujos.values if hasattr(flujos, "values") else list(flujos)
    acumulado = 0.0
    
    for mes in range(len(flujos_valores)):
        acumulado_anterior = acumulado
        acumulado += flujos_valores[mes]
        
        if acumulado >= 0:
            # Interpolación lineal para el mes exacto
            faltante = abs(acumulado_anterior)
            if flujos_valores[mes] != 0:
                fraccion = faltante / flujos_valores[mes]
                return mes - 1 + fraccion
            else:
                return float(mes)
    
    return None  # No se recupera

def payback_descontado(flujos, tasa_anual):
    """
    Calcula el período de recupero descontado (Discounted Payback).
    
    Parameters:
      flujos: iterable de flujos de caja mensuales
      tasa_anual: tasa de descuento anual (EAR)
    
    Returns:
      float: tiempo de recupero en meses (con decimales)
      None: si no se recupera la inversión
    """
    flujos_valores = flujos.values if hasattr(flujos, "values") else list(flujos)
    
    # Convertir tasa anual a mensual efectiva
    tasa_mensual = (1 + tasa_anual) ** (1 / 12) - 1
    
    acumulado = 0.0
    
    for mes in range(len(flujos_valores)):
        # Descontar el flujo del mes actual
        flujo_descontado = flujos_valores[mes] / ((1 + tasa_mensual) ** mes)
        acumulado_anterior = acumulado
        acumulado += flujo_descontado
        
        if acumulado >= 0:
            # Interpolación lineal para el mes exacto
            faltante = abs(acumulado_anterior)
            if flujo_descontado != 0:
                fraccion = faltante / flujo_descontado
                return mes - 1 + fraccion
            else:
                return float(mes)
    
    return None  # No se recupera


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