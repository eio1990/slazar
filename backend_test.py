#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Packaging Module Session-Based API
Testing all packaging endpoints systematically
"""

import requests
import json
import time
from datetime import datetime

# Get backend URL from environment
BACKEND_URL = "https://packmaster-6.preview.emergentagent.com/api"

def log_test(test_name, status, details=""):
    """Log test results"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_symbol = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
    print(f"[{timestamp}] {status_symbol} {test_name}")
    if details:
        print(f"    {details}")

def make_request(method, endpoint, data=None, expected_status=200):
    """Make HTTP request with error handling"""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        print(f"    {method} {endpoint} -> {response.status_code}")
        
        if response.status_code != expected_status:
            print(f"    Response: {response.text}")
            return None, response.status_code
        
        return response.json() if response.content else {}, response.status_code
    except Exception as e:
        print(f"    ERROR: {str(e)}")
        return None, 0

def test_packaging_recipes():
    """Test GET /api/packaging/recipes"""
    print("\n=== TESTING PACKAGING RECIPES ===")
    
    # Test 1: Get all recipes
    data, status = make_request("GET", "/packaging/recipes")
    if data is None:
        log_test("GET /packaging/recipes", "FAIL", f"Request failed with status {status}")
        return []
    
    if not isinstance(data, list):
        log_test("GET /packaging/recipes", "FAIL", "Response is not a list")
        return []
    
    log_test("GET /packaging/recipes", "PASS", f"Retrieved {len(data)} recipes")
    
    # Display recipe details
    for recipe in data:
        print(f"    Recipe ID {recipe.get('id')}: {recipe.get('source_product_name')} -> {recipe.get('target_product_name')}")
        print(f"      Materials: {len(recipe.get('materials', []))}")
    
    # Test 2: Filter by source_product_id if recipes exist
    if data:
        source_id = data[0].get('source_product_id')
        filtered_data, status = make_request("GET", f"/packaging/recipes?source_product_id={source_id}")
        if filtered_data is not None:
            log_test("GET /packaging/recipes with filter", "PASS", f"Filtered to {len(filtered_data)} recipes")
        else:
            log_test("GET /packaging/recipes with filter", "FAIL", f"Filter request failed")
    
    return data

def test_recipe_details_no_trim():
    """Test 2: Verify each recipe has no trim step and correct nomenclature"""
    print("\n🧪 Test 2: Recipe details - no trim step, correct nomenclature")
    
    all_passed = True
    
    for recipe_id, expected_nomenclature_id in EXPECTED_NOMENCLATURE.items():
        print(f"\n  Testing Recipe ID {recipe_id} ({RECIPE_NAMES[recipe_id]})")
        
        try:
            # Get recipe details
            response = requests.get(f"{BACKEND_URL}/production/recipes/{recipe_id}", timeout=10)
            
            if response.status_code != 200:
                print(f"    ❌ FAILED: Expected 200, got {response.status_code}")
                all_passed = False
                continue
                
            recipe = response.json()
            
            # Check steps don't contain trim
            steps = recipe.get('steps', [])
            if not steps:
                print(f"    ❌ FAILED: No steps found")
                all_passed = False
                continue
                
            # Check first step is NOT trim
            first_step = steps[0]
            if first_step.get('step_type') == 'trim' or 'trim' in first_step.get('step_name', '').lower():
                print(f"    ❌ FAILED: First step is still trim: {first_step.get('step_name')}")
                all_passed = False
                continue
                
            # Check step_order starts from 1
            if first_step.get('step_order') != 1:
                print(f"    ❌ FAILED: First step order is {first_step.get('step_order')}, expected 1")
                all_passed = False
                continue
                
            # Check no trim steps exist
            trim_steps = [s for s in steps if s.get('step_type') == 'trim' or 'trim' in s.get('step_name', '').lower()]
            if trim_steps:
                print(f"    ❌ FAILED: Found trim steps: {[s.get('step_name') for s in trim_steps]}")
                all_passed = False
                continue
                
            print(f"    ✅ No trim steps found")
            print(f"    ✅ First step: {first_step.get('step_name')} (order: {first_step.get('step_order')})")
            
            # Get recipe ingredients to check nomenclature
            materials_response = requests.get(f"{BACKEND_URL}/production/recipes/{recipe_id}/materials", timeout=10)
            
            if materials_response.status_code != 200:
                print(f"    ❌ FAILED: Could not get materials, status {materials_response.status_code}")
                all_passed = False
                continue
                
            materials = materials_response.json()
            ingredients = materials.get('ingredients', [])
            
            if not ingredients:
                print(f"    ❌ FAILED: No ingredients found")
                all_passed = False
                continue
                
            # Find main ingredient (should be the butchery output)
            main_ingredient = ingredients[0]  # Assuming first ingredient is main
            actual_nomenclature_id = main_ingredient.get('nomenclature_id')
            
            if actual_nomenclature_id != expected_nomenclature_id:
                print(f"    ❌ FAILED: Nomenclature mismatch")
                print(f"    Expected: {expected_nomenclature_id}")
                print(f"    Actual: {actual_nomenclature_id}")
                print(f"    Ingredient: {main_ingredient.get('name')}")
                all_passed = False
                continue
                
            print(f"    ✅ Correct nomenclature: {main_ingredient.get('name')} (ID: {actual_nomenclature_id})")
            
        except Exception as e:
            print(f"    ❌ FAILED: Exception occurred: {e}")
            all_passed = False
            
    return all_passed

def test_batch_creation_with_new_nomenclature():
    """Test 3: Create batch with new nomenclature (requires stock)"""
    print("\n🧪 Test 3: Batch creation with new nomenclature")
    
    # Test with Recipe ID 2 (Бастурма класична) using nomenclature_id 199
    recipe_id = 2
    nomenclature_id = 199
    test_weight = 50.0
    
    print(f"  Testing batch creation for Recipe {recipe_id} with {test_weight} kg")
    
    try:
        # First, add stock for the required nomenclature
        print(f"  Adding stock for nomenclature ID {nomenclature_id}")
        
        stock_data = {
            "nomenclature_id": nomenclature_id,
            "quantity": 100.0,  # Add 100 kg
            "price_per_unit": 150.0,
            "idempotency_key": f"test-stock-{nomenclature_id}-{datetime.now().timestamp()}",
            "metadata": {
                "test": True,
                "purpose": "batch_creation_test"
            }
        }
        
        stock_response = requests.post(f"{BACKEND_URL}/stock/receipt", json=stock_data, timeout=10)
        
        if stock_response.status_code != 200:
            print(f"    ❌ FAILED: Could not add stock, status {stock_response.status_code}")
            print(f"    Response: {stock_response.text}")
            return False
            
        print(f"    ✅ Stock added successfully")
        
        # Now create batch
        batch_data = {
            "recipe_id": recipe_id,
            "initial_weight": test_weight,
            "trim_waste": 0.0,
            "trim_returned": False,
            "operator_notes": "Test batch for nomenclature verification"
        }
        
        batch_response = requests.post(f"{BACKEND_URL}/production/batches", json=batch_data, timeout=10)
        
        if batch_response.status_code != 200:
            print(f"    ❌ FAILED: Batch creation failed, status {batch_response.status_code}")
            print(f"    Response: {batch_response.text}")
            return False
            
        batch = batch_response.json()
        batch_id = batch.get('id')
        batch_number = batch.get('batch_number')
        
        print(f"    ✅ Batch created successfully")
        print(f"    Batch ID: {batch_id}")
        print(f"    Batch Number: {batch_number}")
        print(f"    Recipe: {batch.get('recipe_name')}")
        print(f"    Initial Weight: {batch.get('initial_weight')} kg")
        
        # Verify stock was deducted
        balance_response = requests.get(f"{BACKEND_URL}/stock/balances", timeout=10)
        
        if balance_response.status_code == 200:
            balances = balance_response.json()
            target_balance = next((b for b in balances if b['nomenclature_id'] == nomenclature_id), None)
            
            if target_balance:
                remaining_balance = target_balance['quantity']
                expected_balance = 100.0 - test_weight  # 100 - 50 = 50
                
                if abs(remaining_balance - expected_balance) < 0.01:  # Allow small floating point differences
                    print(f"    ✅ Stock deduction verified: {remaining_balance} kg remaining")
                else:
                    print(f"    ⚠️  Stock deduction mismatch: expected {expected_balance}, got {remaining_balance}")
            else:
                print(f"    ⚠️  Could not verify stock balance")
        
        return True
        
    except Exception as e:
        print(f"    ❌ FAILED: Exception occurred: {e}")
        return False

def test_step_order_verification():
    """Test 4: Verify step orders start from 1 and are sequential"""
    print("\n🧪 Test 4: Step order verification")
    
    all_passed = True
    
    for recipe_id in EXPECTED_NOMENCLATURE.keys():
        print(f"\n  Testing step orders for Recipe ID {recipe_id}")
        
        try:
            response = requests.get(f"{BACKEND_URL}/production/recipes/{recipe_id}", timeout=10)
            
            if response.status_code != 200:
                print(f"    ❌ FAILED: Could not get recipe, status {response.status_code}")
                all_passed = False
                continue
                
            recipe = response.json()
            steps = recipe.get('steps', [])
            
            if not steps:
                print(f"    ❌ FAILED: No steps found")
                all_passed = False
                continue
                
            # Check step orders are sequential starting from 1
            expected_order = 1
            for step in steps:
                actual_order = step.get('step_order')
                if actual_order != expected_order:
                    print(f"    ❌ FAILED: Step order mismatch at step '{step.get('step_name')}'")
                    print(f"    Expected: {expected_order}, Actual: {actual_order}")
                    all_passed = False
                    break
                expected_order += 1
                
            if all_passed:
                print(f"    ✅ Step orders are sequential (1 to {len(steps)})")
                
        except Exception as e:
            print(f"    ❌ FAILED: Exception occurred: {e}")
            all_passed = False
            
    return all_passed

def run_all_tests():
    """Run all tests and return overall result"""
    print("🚀 Starting Production Recipe Update Tests")
    print("=" * 60)
    
    tests = [
        ("Get All Recipes", test_get_all_recipes),
        ("Recipe Details - No Trim + Correct Nomenclature", test_recipe_details_no_trim),
        ("Batch Creation with New Nomenclature", test_batch_creation_with_new_nomenclature),
        ("Step Order Verification", test_step_order_verification),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        result = test_func()
        results.append((test_name, result))
        
        if result:
            print(f"✅ {test_name}: PASSED")
        else:
            print(f"❌ {test_name}: FAILED")
    
    print(f"\n{'='*60}")
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\n🎯 Overall Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Recipe updates are working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)