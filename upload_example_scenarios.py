#!/usr/bin/env python3
"""
Example script showing how to create and upload custom project configurations to Firebase.
You can modify this script to create different project scenarios.
"""
from firebase_manager import FirebaseManager
import copy

# Base template - you can copy and modify this
project_template = {
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
        "capitalizacion": "Mensual",
        "costo_capital_propio_anual": 0.18,
        "tasa_impuesto_renta": 0.30,
    },
    "items_periodicos": [],
}

# ============================================================================
# EXAMPLE 1: Conservative Scenario (Lower risk, lower returns)
# ============================================================================
def create_conservative_scenario():
    """Create a conservative project with lower debt and slower sales."""
    project = copy.deepcopy(project_template)
    
    # Reduce debt ratio
    project["financiamiento"]["monto_deuda"] = 6_000_000  # Lower debt
    project["financiamiento"]["costo_deuda_anual"] = 0.10  # Better rate
    
    # More conservative sales
    project["planes_venta"][0]["velocidad"] = 3  # Slower sales
    project["planes_venta"][1]["velocidad"] = 2
    
    # Lower price growth
    project["ventas"]["crecimiento_precio_anual"] = 0.03
    
    return project

# ============================================================================
# EXAMPLE 2: Aggressive Scenario (Higher risk, higher returns)
# ============================================================================
def create_aggressive_scenario():
    """Create an aggressive project with more debt and faster sales."""
    project = copy.deepcopy(project_template)
    
    # Higher debt
    project["financiamiento"]["monto_deuda"] = 12_000_000
    project["financiamiento"]["costo_deuda_anual"] = 0.15
    
    # Faster sales
    project["planes_venta"][0]["velocidad"] = 8
    project["planes_venta"][1]["velocidad"] = 5
    
    # Higher price growth
    project["ventas"]["crecimiento_precio_anual"] = 0.08
    
    # Add marketing expenses
    project["items_periodicos"].append({
        "nombre": "Marketing Agresivo",
        "monto": 50000,
        "base_calculo": "Monto Fijo",
        "mes_inicio": 1,
        "mes_fin": 24,
        "tipo": "Gasto"
    })
    
    return project

# ============================================================================
# EXAMPLE 3: Premium Project (Higher prices, luxury segment)
# ============================================================================
def create_premium_scenario():
    """Create a premium luxury project."""
    project = copy.deepcopy(project_template)
    
    # Higher land cost
    project["cronograma_inversion"][0]["monto"] = 8_000_000
    
    # Premium pricing
    project["planes_venta"][0]["monto_pie"] = 80000
    project["planes_venta"][0]["monto_cuota"] = 5000
    project["planes_venta"][1]["monto_pie"] = 120000
    project["planes_venta"][1]["monto_cuota"] = 7000
    
    # Slower but higher value sales
    project["planes_venta"][0]["velocidad"] = 2
    project["planes_venta"][1]["velocidad"] = 1
    
    # Add amenities investment
    project["cronograma_inversion"].append({
        "item": "Club House & Amenities",
        "monto": 2_500_000,
        "mes": 8,
        "tag_sensibilidad": "costo_amenities"
    })
    
    return project

# ============================================================================
# EXAMPLE 4: Quick Flip (Short-term project)
# ============================================================================
def create_quick_flip_scenario():
    """Create a quick flip project with programmed sales."""
    project = copy.deepcopy(project_template)
    
    # Shorter horizon
    project["horizonte_meses"] = 36
    
    # Programmed bulk sale
    project["planes_venta"] = [
        {
            "nombre": "Venta en Bloque",
            "cantidad_lotes": 200,
            "velocidad": 0,  # Not used for programmed
            "monto_pie": 100000,
            "monto_cuota": 0,
            "frecuencia": 1,
            "cantidad_cuotas": 0,
            "tipo": "Programado",
            "mes_inicio": 18  # Sell all at month 18
        }
    ]
    
    # Shorter debt term
    project["financiamiento"]["plazo_deuda_meses"] = 36
    
    return project

# ============================================================================
# EXAMPLE 5: With Periodic Income (e.g., rental during development)
# ============================================================================
def create_rental_income_scenario():
    """Create a project with rental income during development."""
    project = copy.deepcopy(project_template)
    
    # Add rental income from existing structures
    project["items_periodicos"].extend([
        {
            "nombre": "Alquiler Terreno Temporal",
            "monto": 30000,
            "base_calculo": "Monto Fijo",
            "mes_inicio": 1,
            "mes_fin": 12,
            "tipo": "Ingreso"
        },
        {
            "nombre": "Comisiones Ventas",
            "monto": 3,  # 3% of sales
            "base_calculo": "% Ventas",
            "mes_inicio": 1,
            "mes_fin": 120,
            "tipo": "Gasto"
        }
    ])
    
    return project

# ============================================================================
# Main Upload Function
# ============================================================================
def upload_scenarios():
    """Upload all example scenarios to Firebase."""
    fm = FirebaseManager()
    
    if not fm.db:
        print("❌ Error: Could not connect to Firebase")
        return
    
    scenarios = {
        "conservative_project": create_conservative_scenario(),
        "aggressive_project": create_aggressive_scenario(),
        "premium_project": create_premium_scenario(),
        "quick_flip_project": create_quick_flip_scenario(),
        "rental_income_project": create_rental_income_scenario(),
    }
    
    print("Uploading project scenarios to Firebase...")
    print("=" * 60)
    
    for project_id, project_data in scenarios.items():
        success = fm.upload_project_data(project_id, project_data)
        if success:
            print(f"✓ Uploaded: {project_id}")
        else:
            print(f"✗ Failed: {project_id}")
    
    print("=" * 60)
    print(f"\n✓ Successfully uploaded {len(scenarios)} project scenarios!")
    print("\nYou can now load these in the GUI using these IDs:")
    for project_id in scenarios.keys():
        print(f"  - {project_id}")

if __name__ == "__main__":
    upload_scenarios()
