#!/usr/bin/env python3
"""
Test script to verify Firebase data retrieval.
"""
from firebase_manager import FirebaseManager
import json

def test_firebase_retrieval():
    print("Testing Firebase data retrieval...")
    print("-" * 50)
    
    fm = FirebaseManager()
    
    if not fm.db:
        print("❌ ERROR: Could not connect to Firebase")
        return False
    
    print("✓ Connected to Firebase successfully")
    
    # Test retrieving the default project
    project_id = "default_project"
    data = fm.get_project_data(project_id)
    
    if data:
        print(f"✓ Successfully retrieved project '{project_id}'")
        print("\nProject Summary:")
        print(f"  - Horizonte (meses): {data.get('horizonte_meses', 'N/A')}")
        print(f"  - Inversión items: {len(data.get('cronograma_inversion', []))}")
        print(f"  - Planes de venta: {len(data.get('planes_venta', []))}")
        print(f"  - Monto deuda: ${data.get('financiamiento', {}).get('monto_deuda', 0):,.0f}")
        print(f"  - Tasa deuda anual: {data.get('financiamiento', {}).get('costo_deuda_anual', 0):.1%}")
        
        print("\n✓ All tests passed!")
        return True
    else:
        print(f"❌ ERROR: Could not retrieve project '{project_id}'")
        return False

if __name__ == "__main__":
    success = test_firebase_retrieval()
    exit(0 if success else 1)
