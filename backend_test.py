#!/usr/bin/env python3
"""
Backend API Testing Script - Post Nomenclature Migration
Тестирование критических API endpoints после финальной миграции номенклатуры
"""

import requests
import json
import sys
from typing import Dict, List, Any
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/app/frontend/.env')

# Get backend URL from environment
BACKEND_URL = os.getenv('EXPO_PUBLIC_BACKEND_URL', 'http://localhost:8001')
API_BASE = f"{BACKEND_URL}/api"

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

def test_nomenclature():
    """Get nomenclature for testing"""
    print("\n=== GETTING NOMENCLATURE FOR TESTING ===")
    
    data, status = make_request("GET", "/nomenclature")
    if data is None:
        log_test("GET /nomenclature", "FAIL", "Could not retrieve nomenclature")
        return [], []
    
    # Find source products (bulk products for packaging)
    source_products = []
    target_products = []
    
    for item in data:
        name = item.get('name', '').lower()
        # Look for bulk/weight products that could be source
        if any(keyword in name for keyword in ['вагова', 'вагов', 'кг', 'bulk']):
            source_products.append(item)
        # Look for packaged products that could be targets
        elif any(keyword in name for keyword in ['100г', '200г', '50г', 'вакуум', 'пакет']):
            target_products.append(item)
    
    log_test("Nomenclature analysis", "PASS", 
             f"Found {len(source_products)} potential source products, {len(target_products)} target products")
    
    return source_products, target_products

def test_create_session(source_products):
    """Test POST /api/packaging/sessions"""
    print("\n=== TESTING SESSION CREATION ===")
    
    if not source_products:
        log_test("Session creation", "FAIL", "No source products available for testing")
        return None
    
    # Use first available source product
    source_product = source_products[0]
    source_id = source_product['id']
    
    # Test 1: Create session with valid data
    session_data = {
        "source_product_id": source_id,
        "source_weight_taken": 10.5,
        "notes": "Test packaging session"
    }
    
    data, status = make_request("POST", "/packaging/sessions", session_data)
    if data is None:
        log_test("POST /packaging/sessions", "FAIL", f"Session creation failed with status {status}")
        return None
    
    session_id = data.get('session_id')
    session_number = data.get('session_number')
    
    log_test("POST /packaging/sessions", "PASS", 
             f"Created session {session_number} (ID: {session_id})")
    
    # Test 2: Try to create session with insufficient stock
    large_session_data = {
        "source_product_id": source_id,
        "source_weight_taken": 999999.0,  # Very large amount
        "notes": "Test insufficient stock"
    }
    
    data2, status2 = make_request("POST", "/packaging/sessions", large_session_data, expected_status=400)
    if status2 == 400:
        log_test("POST /packaging/sessions (insufficient stock)", "PASS", "Correctly rejected insufficient stock")
    else:
        log_test("POST /packaging/sessions (insufficient stock)", "FAIL", f"Expected 400, got {status2}")
    
    return session_id

def test_list_sessions():
    """Test GET /api/packaging/sessions"""
    print("\n=== TESTING SESSION LISTING ===")
    
    # Test 1: Get all sessions
    data, status = make_request("GET", "/packaging/sessions")
    if data is None:
        log_test("GET /packaging/sessions", "FAIL", f"Request failed with status {status}")
        return
    
    log_test("GET /packaging/sessions", "PASS", f"Retrieved {len(data)} sessions")
    
    # Display session details
    for session in data:
        print(f"    Session {session.get('session_number')}: {session.get('source_product_name')}")
        print(f"      Status: {session.get('status')}, Outputs: {session.get('outputs_count')}, Total packed: {session.get('total_packed')}")
    
    # Test 2: Filter by status
    data2, status2 = make_request("GET", "/packaging/sessions?status=in_progress")
    if data2 is not None:
        log_test("GET /packaging/sessions (filtered)", "PASS", f"Found {len(data2)} in-progress sessions")
    else:
        log_test("GET /packaging/sessions (filtered)", "FAIL", "Filter request failed")

def test_session_details(session_id):
    """Test GET /api/packaging/sessions/{id}"""
    print("\n=== TESTING SESSION DETAILS ===")
    
    if session_id is None:
        log_test("Session details", "FAIL", "No session ID available")
        return
    
    # Test 1: Get valid session details
    data, status = make_request("GET", f"/packaging/sessions/{session_id}")
    if data is None:
        log_test("GET /packaging/sessions/{id}", "FAIL", f"Request failed with status {status}")
        return
    
    log_test("GET /packaging/sessions/{id}", "PASS", 
             f"Retrieved session details with {len(data.get('outputs', []))} outputs")
    
    # Test 2: Try non-existent session
    data2, status2 = make_request("GET", "/packaging/sessions/99999", expected_status=404)
    if status2 == 404:
        log_test("GET /packaging/sessions/{id} (not found)", "PASS", "Correctly returned 404 for non-existent session")
    else:
        log_test("GET /packaging/sessions/{id} (not found)", "FAIL", f"Expected 404, got {status2}")

def test_add_output(session_id, recipes, target_products):
    """Test POST /api/packaging/sessions/{id}/outputs"""
    print("\n=== TESTING SESSION OUTPUTS ===")
    
    if session_id is None:
        log_test("Add output", "FAIL", "No session ID available")
        return
    
    # Find a target product that has a recipe
    target_product_id = None
    if recipes:
        target_product_id = recipes[0].get('target_product_id')
    elif target_products:
        target_product_id = target_products[0]['id']
    
    if target_product_id is None:
        log_test("Add output", "FAIL", "No target product available")
        return
    
    # Test 1: Add valid output
    output_data = {
        "target_product_id": target_product_id,
        "quantity_packed": 50,
        "defect_quantity": 0,
        "notes": "Test output"
    }
    
    data, status = make_request("POST", f"/packaging/sessions/{session_id}/outputs", output_data)
    if data is None:
        log_test("POST /packaging/sessions/{id}/outputs", "FAIL", f"Request failed with status {status}")
        return
    
    log_test("POST /packaging/sessions/{id}/outputs", "PASS", 
             f"Added output: {data.get('quantity_packed')} units")
    
    # Display calculated materials
    materials = data.get('materials_used', [])
    print(f"    Calculated materials: {len(materials)}")
    for material in materials:
        print(f"      {material.get('material_name')}: {material.get('quantity')} {material.get('unit')}")
    
    # Test 2: Try invalid target product (no recipe)
    invalid_output_data = {
        "target_product_id": 99999,  # Non-existent product
        "quantity_packed": 10,
        "defect_quantity": 0,
        "notes": "Test invalid"
    }
    
    data2, status2 = make_request("POST", f"/packaging/sessions/{session_id}/outputs", 
                                 invalid_output_data, expected_status=404)
    if status2 == 404:
        log_test("POST /packaging/sessions/{id}/outputs (invalid product)", "PASS", 
                "Correctly rejected invalid target product")
    else:
        log_test("POST /packaging/sessions/{id}/outputs (invalid product)", "FAIL", 
                f"Expected 404, got {status2}")

def test_add_remainder(session_id, source_products):
    """Test POST /api/packaging/sessions/{id}/remainders"""
    print("\n=== TESTING SESSION REMAINDERS ===")
    
    if session_id is None:
        log_test("Add remainder", "FAIL", "No session ID available")
        return
    
    if not source_products:
        log_test("Add remainder", "FAIL", "No nomenclature available for remainder")
        return
    
    # Use first available nomenclature for remainder
    nomenclature_id = source_products[0]['id']
    
    remainder_data = {
        "nomenclature_id": nomenclature_id,
        "weight_kg": 1.5,
        "description": "Fallen spices during packaging",
        "notes": "Test remainder"
    }
    
    data, status = make_request("POST", f"/packaging/sessions/{session_id}/remainders", remainder_data)
    if data is None:
        log_test("POST /packaging/sessions/{id}/remainders", "FAIL", f"Request failed with status {status}")
        return
    
    log_test("POST /packaging/sessions/{id}/remainders", "PASS", 
             f"Added remainder: {data.get('weight_kg')} kg")

def test_add_waste(session_id):
    """Test POST /api/packaging/sessions/{id}/waste"""
    print("\n=== TESTING SESSION WASTE ===")
    
    if session_id is None:
        log_test("Add waste", "FAIL", "No session ID available")
        return
    
    waste_data = {
        "waste_weight_kg": 0.5,
        "waste_description": "Packaging losses",
        "notes": "Test waste"
    }
    
    data, status = make_request("POST", f"/packaging/sessions/{session_id}/waste", waste_data)
    if data is None:
        log_test("POST /packaging/sessions/{id}/waste", "FAIL", f"Request failed with status {status}")
        return
    
    log_test("POST /packaging/sessions/{id}/waste", "PASS", 
             f"Added waste: {data.get('waste_weight_kg')} kg")

def test_complete_session(session_id):
    """Test PUT /api/packaging/sessions/{id}/complete"""
    print("\n=== TESTING SESSION COMPLETION ===")
    
    if session_id is None:
        log_test("Complete session", "FAIL", "No session ID available")
        return
    
    # Test 1: Complete session
    completion_data = {
        "notes": "Session completed successfully"
    }
    
    data, status = make_request("PUT", f"/packaging/sessions/{session_id}/complete", completion_data)
    if data is None:
        log_test("PUT /packaging/sessions/{id}/complete", "FAIL", f"Request failed with status {status}")
        return
    
    log_test("PUT /packaging/sessions/{id}/complete", "PASS", "Session completed successfully")
    
    # Test 2: Try to complete again (should fail)
    data2, status2 = make_request("PUT", f"/packaging/sessions/{session_id}/complete", 
                                 completion_data, expected_status=400)
    if status2 == 400:
        log_test("PUT /packaging/sessions/{id}/complete (double completion)", "PASS", 
                "Correctly rejected double completion")
    else:
        log_test("PUT /packaging/sessions/{id}/complete (double completion)", "FAIL", 
                f"Expected 400, got {status2}")

def test_completed_session_operations(session_id):
    """Test operations on completed session (should fail)"""
    print("\n=== TESTING COMPLETED SESSION RESTRICTIONS ===")
    
    if session_id is None:
        log_test("Completed session restrictions", "FAIL", "No session ID available")
        return
    
    # Try to add remainder to completed session
    remainder_data = {
        "nomenclature_id": 1,
        "weight_kg": 1.0,
        "description": "Should fail",
        "notes": "Test"
    }
    
    data, status = make_request("POST", f"/packaging/sessions/{session_id}/remainders", 
                               remainder_data, expected_status=400)
    if status == 400:
        log_test("Add remainder to completed session", "PASS", "Correctly rejected operation on completed session")
    else:
        log_test("Add remainder to completed session", "FAIL", f"Expected 400, got {status}")

def add_test_stock():
    """Add some stock for testing purposes"""
    print("\n=== ADDING TEST STOCK ===")
    
    # Get nomenclature first
    data, status = make_request("GET", "/nomenclature")
    if data is None:
        log_test("Add test stock", "FAIL", "Could not get nomenclature")
        return
    
    # Find source products (bulk/weight products) and add stock to them
    source_products = []
    for item in data:
        name = item.get('name', '').lower()
        if any(keyword in name for keyword in ['вагова', 'вагов', 'кг', 'bulk']):
            source_products.append(item)
    
    # Add stock to source products
    for item in source_products[:10]:  # Add to first 10 source products
        stock_data = {
            "nomenclature_id": item['id'],
            "quantity": 100.0,
            "price_per_unit": 50.0,
            "idempotency_key": f"test-stock-{item['id']}-{datetime.now().timestamp()}",
            "metadata": {"test": True, "purpose": "packaging_test"}
        }
        
        stock_result, stock_status = make_request("POST", "/stock/receipt", stock_data)
        if stock_result:
            print(f"    Added 100 kg to {item['name']}")
        else:
            print(f"    Failed to add stock to {item['name']}")
    
    # Also add stock to some materials for packaging
    material_keywords = ['пакет', 'етикетка', 'коробка', 'скін', 'вакуум']
    material_count = 0
    for item in data:
        if material_count >= 10:
            break
        name = item.get('name', '').lower()
        if any(keyword in name for keyword in material_keywords):
            stock_data = {
                "nomenclature_id": item['id'],
                "quantity": 1000.0,  # More materials
                "price_per_unit": 1.0,
                "idempotency_key": f"test-material-{item['id']}-{datetime.now().timestamp()}",
                "metadata": {"test": True, "purpose": "packaging_materials"}
            }
            
            stock_result, stock_status = make_request("POST", "/stock/receipt", stock_data)
            if stock_result:
                print(f"    Added 1000 units to material {item['name']}")
                material_count += 1

def main():
    """Run all packaging API tests"""
    print("🧪 PACKAGING MODULE SESSION-BASED API TESTING")
    print("=" * 60)
    
    # Step 0: Add some test stock
    add_test_stock()
    
    # Step 1: Test recipes endpoint
    recipes = test_packaging_recipes()
    
    # Step 2: Get nomenclature for testing
    source_products, target_products = test_nomenclature()
    
    # Step 3: Create a new session
    session_id = test_create_session(source_products)
    
    # Step 4: Test session listing
    test_list_sessions()
    
    # Step 5: Test session details
    test_session_details(session_id)
    
    # Step 6: Add output to session
    test_add_output(session_id, recipes, target_products)
    
    # Step 7: Add remainder to session
    test_add_remainder(session_id, source_products)
    
    # Step 8: Add waste to session
    test_add_waste(session_id)
    
    # Step 9: Complete session
    test_complete_session(session_id)
    
    # Step 10: Test operations on completed session
    test_completed_session_operations(session_id)
    
    print("\n" + "=" * 60)
    print("🏁 PACKAGING API TESTING COMPLETED")
    print("Check the logs above for detailed results")

if __name__ == "__main__":
    main()