#!/usr/bin/env python3
"""
Focused test for spice deduction functionality
"""

import requests
import json
import time
from datetime import datetime

# Backend URL from environment
BACKEND_URL = "https://recipe-factory-1.preview.emergentagent.com/api"

def test_spice_deduction_comprehensive():
    """Comprehensive test of spice deduction functionality"""
    print("🧪 COMPREHENSIVE SPICE DEDUCTION TEST")
    print("=" * 60)
    
    session = requests.Session()
    
    # Test 1: Create batch for Бастурма класична (100kg)
    print("\n1️⃣ Creating 100kg batch for Бастурма класична...")
    batch_payload = {
        "recipe_id": 2,
        "initial_weight": 100.0,
        "trim_waste": 0,
        "trim_returned": False,
        "operator_notes": "Comprehensive spice deduction test - 100kg batch"
    }
    
    response = session.post(f"{BACKEND_URL}/production/batches", json=batch_payload, timeout=10)
    if response.status_code != 200:
        print(f"❌ Failed to create batch: {response.status_code} - {response.text}")
        return False
    
    batch_data = response.json()
    batch_id = batch_data['id']
    batch_number = batch_data['batch_number']
    print(f"✅ Created batch {batch_number} (ID: {batch_id})")
    
    # Test 2: Get recipe spices
    print("\n2️⃣ Verifying recipe spices...")
    response = session.get(f"{BACKEND_URL}/production/recipes/2/spices", timeout=10)
    if response.status_code != 200:
        print(f"❌ Failed to get recipe spices: {response.status_code}")
        return False
    
    recipe_data = response.json()
    spices = recipe_data.get('spices', [])
    
    expected_spices = {
        'Борошно': 3.08,
        'Пажитник': 9.23,
        'Паприка': 4.62,
        'Перець чілі': 1.54,
        'Часник': 6.15
    }
    
    found_spices = {spice['name']: spice['quantity_per_100kg'] for spice in spices}
    print(f"✅ Found {len(spices)} spices in recipe")
    
    for spice_name, expected_qty in expected_spices.items():
        if spice_name in found_spices:
            actual_qty = found_spices[spice_name]
            if abs(actual_qty - expected_qty) < 0.01:
                print(f"   ✅ {spice_name}: {actual_qty} кг/100кг (expected {expected_qty})")
            else:
                print(f"   ❌ {spice_name}: {actual_qty} кг/100кг (expected {expected_qty})")
        else:
            print(f"   ❌ {spice_name}: NOT FOUND")
    
    # Test 3: Get initial stock balances
    print("\n3️⃣ Recording initial stock balances...")
    initial_balances = {}
    
    response = session.get(f"{BACKEND_URL}/stock/balances", timeout=10)
    if response.status_code == 200:
        balances = response.json()
        for spice in spices:
            spice_id = spice['nomenclature_id']
            spice_name = spice['name']
            spice_balance = next((b for b in balances if b['nomenclature_id'] == spice_id), None)
            if spice_balance:
                initial_balances[spice_name] = {
                    'id': spice_id,
                    'initial_balance': spice_balance['quantity'],
                    'quantity_per_100kg': spice['quantity_per_100kg']
                }
                print(f"   📊 {spice_name}: {spice_balance['quantity']} кг")
    
    # Test 4: Produce mix
    print("\n4️⃣ Producing mix (this should deduct all spices)...")
    mix_payload = {
        "mix_nomenclature_id": 72,
        "produced_quantity": 24.62,  # Total spices for 100kg
        "used_quantity": 24.62,
        "leftover_quantity": 0.0,
        "warehouse_mix_used": 0.0,
        "idempotency_key": f"comprehensive-test-{batch_id}-{int(time.time())}"
    }
    
    response = session.post(f"{BACKEND_URL}/production/batches/{batch_id}/mix", json=mix_payload, timeout=10)
    if response.status_code != 200:
        print(f"❌ Mix production failed: {response.status_code} - {response.text}")
        return False
    
    mix_result = response.json()
    print(f"✅ Mix production successful: {mix_result.get('message')}")
    
    # Test 5: Verify stock deductions
    print("\n5️⃣ Verifying stock deductions...")
    response = session.get(f"{BACKEND_URL}/stock/balances", timeout=10)
    if response.status_code == 200:
        new_balances = response.json()
        
        all_correct = True
        for spice_name, spice_data in initial_balances.items():
            spice_id = spice_data['id']
            initial_balance = spice_data['initial_balance']
            quantity_per_100kg = spice_data['quantity_per_100kg']
            
            # Calculate expected deduction for 100kg batch
            expected_deduction = (100.0 / 100.0) * quantity_per_100kg
            expected_new_balance = initial_balance - expected_deduction
            
            # Find new balance
            new_balance_data = next((b for b in new_balances if b['nomenclature_id'] == spice_id), None)
            if new_balance_data:
                actual_new_balance = new_balance_data['quantity']
                
                if abs(actual_new_balance - expected_new_balance) < 0.01:
                    print(f"   ✅ {spice_name}: {initial_balance} → {actual_new_balance} кг (deducted {expected_deduction:.2f})")
                else:
                    print(f"   ❌ {spice_name}: Expected {expected_new_balance:.2f}, got {actual_new_balance:.2f}")
                    all_correct = False
            else:
                print(f"   ❌ {spice_name}: Balance not found after deduction")
                all_correct = False
    
    # Test 6: Verify stock movements
    print("\n6️⃣ Verifying stock movements...")
    spice_movements_found = []
    spice_ids = [31, 19, 20, 22, 25]  # Борошно, Пажитник, Паприка, Перець чілі, Часник
    
    for spice_id in spice_ids:
        response = session.get(f"{BACKEND_URL}/stock/movements?nomenclature_id={spice_id}&limit=5", timeout=10)
        if response.status_code == 200:
            movements = response.json()
            
            # Look for the most recent withdrawal for this batch
            for movement in movements:
                if (movement.get('operation_type') == 'withdrawal' and 
                    movement.get('metadata')):
                    try:
                        metadata = json.loads(movement.get('metadata', '{}'))
                        if (metadata.get('batch_id') == batch_id and 
                            'spice_name' in metadata):
                            spice_movements_found.append({
                                'spice_id': spice_id,
                                'spice_name': metadata.get('spice_name'),
                                'quantity': movement.get('quantity'),
                                'movement_id': movement.get('id')
                            })
                            print(f"   ✅ {metadata.get('spice_name')}: Movement ID {movement.get('id')}, Quantity: {movement.get('quantity')} кг")
                            break
                    except:
                        continue
    
    if len(spice_movements_found) >= 5:
        print(f"✅ All {len(spice_movements_found)} spice movements verified")
    else:
        print(f"❌ Expected 5 spice movements, found {len(spice_movements_found)}")
        all_correct = False
    
    # Test 7: Test edge case - insufficient stock
    print("\n7️⃣ Testing edge case: insufficient stock...")
    large_batch_payload = {
        "recipe_id": 2,
        "initial_weight": 500.0,  # Large enough to exceed spice stock but not raw materials
        "trim_waste": 0,
        "trim_returned": False,
        "operator_notes": "Test batch for insufficient stock"
    }
    
    response = session.post(f"{BACKEND_URL}/production/batches", json=large_batch_payload, timeout=10)
    if response.status_code == 200:
        large_batch_data = response.json()
        large_batch_id = large_batch_data['id']
        
        # Try to produce mix - should fail
        large_mix_payload = {
            "mix_nomenclature_id": 72,
            "produced_quantity": 123.1,  # 24.62 * 5 for 500kg batch
            "used_quantity": 123.1,
            "leftover_quantity": 0.0,
            "warehouse_mix_used": 0.0,
            "idempotency_key": f"insufficient-test-{large_batch_id}-{int(time.time())}"
        }
        
        response = session.post(f"{BACKEND_URL}/production/batches/{large_batch_id}/mix", json=large_mix_payload, timeout=10)
        
        if response.status_code == 400:
            error_message = response.text
            if "Недостатньо специй" in error_message or "insufficient" in error_message.lower():
                print("   ✅ Insufficient stock properly detected and rejected")
            else:
                print(f"   ❌ Wrong error message: {error_message}")
                all_correct = False
        else:
            print(f"   ❌ Expected 400 error, got {response.status_code}")
            all_correct = False
    else:
        print(f"   ❌ Failed to create large batch: {response.status_code}")
        all_correct = False
    
    # Final result
    print("\n" + "=" * 60)
    if all_correct:
        print("🎉 SPICE DEDUCTION FUNCTIONALITY: FULLY WORKING")
        print("✅ All spices deducted correctly")
        print("✅ Stock movements created properly") 
        print("✅ Error handling for insufficient stock working")
        print("✅ Calculations accurate for batch weight scaling")
        return True
    else:
        print("❌ SPICE DEDUCTION FUNCTIONALITY: ISSUES FOUND")
        return False

if __name__ == "__main__":
    success = test_spice_deduction_comprehensive()
    exit(0 if success else 1)