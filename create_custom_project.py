#!/usr/bin/env python3
"""
Interactive script to create and upload a custom project to Firebase.
This script guides you through creating a project step-by-step.
"""
from firebase_manager import FirebaseManager

def get_input(prompt, default=None, input_type=str):
    """Helper to get user input with default value."""
    if default is not None:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "
    
    value = input(prompt).strip()
    
    if not value and default is not None:
        return default
    
    if input_type == int:
        return int(value)
    elif input_type == float:
        return float(value)
    else:
        return value

def create_custom_project():
    """Interactive project creation."""
    print("\n" + "=" * 60)
    print("CUSTOM PROJECT CREATOR")
    print("=" * 60)
    
    project = {}
    
    # Basic parameters
    print("\n--- BASIC PARAMETERS ---")
    project["horizonte_meses"] = get_input("Project duration (months)", 120, int)
    
    # Investment schedule
    print("\n--- INVESTMENT SCHEDULE ---")
    project["cronograma_inversion"] = []
    
    num_investments = get_input("How many investment items?", 3, int)
    for i in range(num_investments):
        print(f"\nInvestment #{i+1}:")
        item = {
            "item": get_input("  Item name", f"Investment {i+1}"),
            "monto": get_input("  Amount ($)", 1000000, float),
            "mes": get_input("  Month", 0, int),
            "tag_sensibilidad": get_input("  Sensitivity tag (optional)", "")
        }
        if not item["tag_sensibilidad"]:
            item["tag_sensibilidad"] = None
        project["cronograma_inversion"].append(item)
    
    # Sales
    print("\n--- SALES CONFIGURATION ---")
    project["ventas"] = {
        "crecimiento_precio_anual": get_input("Annual price growth (%)", 5, float) / 100
    }
    
    # Sales plans
    print("\n--- SALES PLANS ---")
    project["planes_venta"] = []
    num_plans = get_input("How many sales plans?", 2, int)
    
    for i in range(num_plans):
        print(f"\nSales Plan #{i+1}:")
        plan_type = get_input("  Type (Dinámico/Programado)", "Dinámico")
        
        plan = {
            "nombre": get_input("  Plan name", f"Plan {i+1}"),
            "cantidad_lotes": get_input("  Number of lots", 100, int),
            "monto_pie": get_input("  Down payment ($)", 30000, float),
            "monto_cuota": get_input("  Installment amount ($)", 2000, float),
            "frecuencia": get_input("  Payment frequency (months)", 1, int),
            "cantidad_cuotas": get_input("  Number of installments", 60, int),
            "tipo": plan_type,
            "mes_inicio": get_input("  Start month", 1, int)
        }
        
        if plan_type == "Dinámico":
            plan["velocidad"] = get_input("  Sales velocity (lots/month)", 5, int)
        else:
            plan["velocidad"] = 0
        
        project["planes_venta"].append(plan)
    
    # Financing
    print("\n--- FINANCING ---")
    project["financiamiento"] = {
        "monto_deuda": get_input("Loan amount ($)", 9000000, float),
        "costo_deuda_anual": get_input("Annual interest rate (%)", 12, float) / 100,
        "plazo_deuda_meses": get_input("Loan term (months)", 84, int),
        "capitalizacion": get_input("Capitalization (Mensual/Trimestral/Semestral/Anual)", "Mensual"),
        "costo_capital_propio_anual": get_input("Cost of equity (%)", 18, float) / 100,
        "tasa_impuesto_renta": get_input("Income tax rate (%)", 30, float) / 100,
    }
    
    # Periodic items
    print("\n--- PERIODIC INCOME/EXPENSES ---")
    project["items_periodicos"] = []
    add_periodic = get_input("Add periodic items? (y/n)", "n")
    
    while add_periodic.lower() == 'y':
        print("\nNew periodic item:")
        item = {
            "nombre": get_input("  Name"),
            "monto": get_input("  Amount or %", 0, float),
            "base_calculo": get_input("  Calculation base (Monto Fijo/% Ventas/Por Lote Inventario/% Utilidad)", "Monto Fijo"),
            "mes_inicio": get_input("  Start month", 1, int),
            "mes_fin": get_input("  End month", 120, int),
            "tipo": get_input("  Type (Ingreso/Gasto)", "Gasto")
        }
        project["items_periodicos"].append(item)
        add_periodic = get_input("Add another periodic item? (y/n)", "n")
    
    # Operating costs (legacy structure)
    project["costos_operativos"] = {
        "costo_operativo_mensual": 0,
        "mantenimiento_mensual": 0,
        "impuestos_prediales_mensual": 0,
    }
    
    return project

def main():
    """Main function."""
    project = create_custom_project()
    
    print("\n" + "=" * 60)
    print("PROJECT SUMMARY")
    print("=" * 60)
    print(f"Duration: {project['horizonte_meses']} months")
    print(f"Investment items: {len(project['cronograma_inversion'])}")
    print(f"Sales plans: {len(project['planes_venta'])}")
    print(f"Loan amount: ${project['financiamiento']['monto_deuda']:,.0f}")
    print(f"Periodic items: {len(project['items_periodicos'])}")
    
    # Upload
    print("\n" + "=" * 60)
    project_id = get_input("\nEnter project ID to save in Firebase", "my_custom_project")
    
    confirm = get_input(f"Upload to Firebase as '{project_id}'? (y/n)", "y")
    
    if confirm.lower() == 'y':
        fm = FirebaseManager()
        if fm.db:
            success = fm.upload_project_data(project_id, project)
            if success:
                print(f"\n✓ Project '{project_id}' uploaded successfully!")
                print(f"\nYou can now load it in the GUI using ID: {project_id}")
            else:
                print("\n✗ Upload failed")
        else:
            print("\n✗ Could not connect to Firebase")
    else:
        print("\nUpload cancelled")

if __name__ == "__main__":
    main()
