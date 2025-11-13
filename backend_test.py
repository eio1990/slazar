#!/usr/bin/env python3
"""
Backend Testing for Weight-based Casing Accounting for Stuffing Step
Tests the new weight-based accounting logic for sausage casings (кишки) in the stuffing step.
"""

import requests
import json
import uuid
from datetime import datetime
import time

# Configuration
BACKEND_URL = "https://butcherflow.preview.emergentagent.com/api"

# Test constants
SUDJUK_RECIPE_ID = 8  # Sudjuk recipe
MAHAN_RECIPE_ID = 9   # Mahan recipe
CASING_SUDJUK_ID = 42  # Casing for Sudjuk
CASING_MAHAN_ID = 43   # Casing for Mahan

class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
        
    def add_pass(self, test_name):
        self.passed += 1
        print(f"✅ PASS: {test_name}")
        
    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append(f"{test_name}: {error}")
        print(f"❌ FAIL: {test_name} - {error}")
        
    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"TEST SUMMARY: {self.passed}/{total} tests passed")
        if self.errors:
            print(f"\nFAILED TESTS:")
            for error in self.errors:
                print(f"  - {error}")
        print(f"{'='*60}")

def make_request(method, endpoint, data=None, expected_status=200):
    """Make HTTP request with error handling"""
    url = f"{BACKEND_URL}{endpoint}"
    try:
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        elif method == "PUT":
            response = requests.put(url, json=data)
        else:
            raise ValueError(f"Unsupported method: {method}")
            
        if response.status_code != expected_status:
            return None, f"Expected {expected_status}, got {response.status_code}: {response.text}"
            
        return response.json(), None
    except Exception as e:
        return None, str(e)

def get_stock_balance(nomenclature_id):
    """Get current stock balance for a nomenclature item"""
    data, error = make_request("GET", "/stock/balances")
    if error:
        return None, error
    
    for item in data:
        if item['nomenclature_id'] == nomenclature_id:
            return item['quantity'], None
    return 0, None

def create_test_batch(recipe_id, initial_weight=10.0):
    """Create a test batch for stuffing tests"""
    batch_data = {
        "recipe_id": recipe_id,
        "initial_weight": initial_weight,
        "trim_waste": 0,
        "trim_returned": False,
        "operator_notes": "Test batch for casing accounting"
    }
    
    return make_request("POST", "/production/batches", batch_data)

def test_happy_path_stuffing(results):
    """Test 1: Happy Path - Normal Stuffing Operation"""
    print("\n🧪 Test 1: Happy Path - Normal Stuffing Operation")
    
    # Create test batch for Sudjuk
    batch_data, error = create_test_batch(SUDJUK_RECIPE_ID, 100.0)
    if error:
        results.add_fail("Create test batch", error)
        return
    
    batch_id = batch_data['id']
    print(f"Created test batch: {batch_data['batch_number']} (ID: {batch_id})")
    
    # Get initial casing stock
    initial_stock, error = get_stock_balance(CASING_SUDJUK_ID)
    if error:
        results.add_fail("Get initial casing stock", error)
        return
    
    print(f"Initial casing stock (ID={CASING_SUDJUK_ID}): {initial_stock} kg")
    
    # Prepare stuffing data
    stuff_data = {
        "casing": {
            "casing_id": CASING_SUDJUK_ID,
            "start_weight": 1.8,
            "end_weight": 0.3
        },
        "materials": [],
        "notes": "Test stuffing",
        "idempotency_key": f"test-stuff-unique-{uuid.uuid4()}"
    }
    
    # Call stuff endpoint
    response_data, error = make_request("POST", f"/production/batches/{batch_id}/stuff", stuff_data)
    if error:
        results.add_fail("Stuffing operation", error)
        return
    
    # Verify response
    expected_usage = 1.8 - 0.3  # 1.5 kg
    if 'casing' not in response_data:
        results.add_fail("Response contains casing info", "No casing info in response")
        return
    
    casing_info = response_data['casing']
    if abs(casing_info['usage_kg'] - expected_usage) > 0.01:
        results.add_fail("Correct usage calculation", f"Expected {expected_usage}, got {casing_info['usage_kg']}")
        return
    
    # Verify stock deduction
    final_stock, error = get_stock_balance(CASING_SUDJUK_ID)
    if error:
        results.add_fail("Get final casing stock", error)
        return
    
    expected_final_stock = initial_stock - expected_usage
    if abs(final_stock - expected_final_stock) > 0.01:
        results.add_fail("Stock deduction", f"Expected {expected_final_stock}, got {final_stock}")
        return
    
    # Verify stock movements
    movements_data, error = make_request("GET", f"/stock/movements?nomenclature_id={CASING_SUDJUK_ID}&limit=1")
    if error:
        results.add_fail("Get stock movements", error)
        return
    
    if not movements_data or len(movements_data) == 0:
        results.add_fail("Stock movement created", "No stock movements found")
        return
    
    latest_movement = movements_data[0]
    if latest_movement['operation_type'] != 'withdrawal':
        results.add_fail("Stock movement type", f"Expected 'withdrawal', got {latest_movement['operation_type']}")
        return
    
    if abs(latest_movement['quantity'] - expected_usage) > 0.01:
        results.add_fail("Stock movement quantity", f"Expected {expected_usage}, got {latest_movement['quantity']}")
        return
    
    # Verify metadata
    if latest_movement['metadata']:
        try:
            metadata = json.loads(latest_movement['metadata'])
            if 'start_weight_kg' not in metadata or 'end_weight_kg' not in metadata:
                results.add_fail("Stock movement metadata", "Missing weight metadata")
                return
        except:
            results.add_fail("Stock movement metadata parsing", "Could not parse metadata JSON")
            return
    
    results.add_pass("Happy Path - Normal Stuffing Operation")

def test_validation_end_greater_than_start(results):
    """Test 2: Validation - End Weight Greater Than Start"""
    print("\n🧪 Test 2: Validation - End Weight Greater Than Start")
    
    # Create test batch
    batch_data, error = create_test_batch(SUDJUK_RECIPE_ID, 50.0)
    if error:
        results.add_fail("Create test batch for validation", error)
        return
    
    batch_id = batch_data['id']
    
    # Test with end_weight > start_weight
    stuff_data = {
        "casing": {
            "casing_id": CASING_SUDJUK_ID,
            "start_weight": 1.0,
            "end_weight": 1.5  # Greater than start
        },
        "materials": [],
        "notes": "Test invalid weights",
        "idempotency_key": f"test-invalid-weights-{uuid.uuid4()}"
    }
    
    # Should return 400 error
    response_data, error = make_request("POST", f"/production/batches/{batch_id}/stuff", stuff_data, expected_status=400)
    if error and "400" not in error:
        results.add_fail("End weight validation", f"Expected 400 error, got: {error}")
        return
    
    # Check if error message is in Ukrainian
    if response_data and 'detail' in response_data:
        error_msg = response_data['detail']
        if 'кінцева' not in error_msg.lower() and 'початкову' not in error_msg.lower():
            results.add_fail("Ukrainian error message", f"Error message not in Ukrainian: {error_msg}")
            return
    
    results.add_pass("Validation - End Weight Greater Than Start")

def test_validation_zero_usage(results):
    """Test 3: Validation - Zero Usage"""
    print("\n🧪 Test 3: Validation - Zero Usage")
    
    # Create test batch
    batch_data, error = create_test_batch(SUDJUK_RECIPE_ID, 50.0)
    if error:
        results.add_fail("Create test batch for zero usage", error)
        return
    
    batch_id = batch_data['id']
    
    # Test with start_weight = end_weight
    stuff_data = {
        "casing": {
            "casing_id": CASING_SUDJUK_ID,
            "start_weight": 2.0,
            "end_weight": 2.0  # Same as start
        },
        "materials": [],
        "notes": "Test zero usage",
        "idempotency_key": f"test-zero-usage-{uuid.uuid4()}"
    }
    
    # Should return 400 error
    response_data, error = make_request("POST", f"/production/batches/{batch_id}/stuff", stuff_data, expected_status=400)
    if error and "400" not in error:
        results.add_fail("Zero usage validation", f"Expected 400 error, got: {error}")
        return
    
    # Check error message mentions zero usage
    if response_data and 'detail' in response_data:
        error_msg = response_data['detail']
        if 'використано 0' not in error_msg.lower():
            results.add_fail("Zero usage error message", f"Error message doesn't mention zero usage: {error_msg}")
            return
    
    results.add_pass("Validation - Zero Usage")

def test_insufficient_stock(results):
    """Test 4: Stock Availability Check"""
    print("\n🧪 Test 4: Stock Availability Check")
    
    # Create test batch
    batch_data, error = create_test_batch(SUDJUK_RECIPE_ID, 50.0)
    if error:
        results.add_fail("Create test batch for stock check", error)
        return
    
    batch_id = batch_data['id']
    
    # Get current stock
    current_stock, error = get_stock_balance(CASING_SUDJUK_ID)
    if error:
        results.add_fail("Get current stock for insufficient test", error)
        return
    
    # Try to use more than available
    excessive_usage = current_stock + 10.0
    stuff_data = {
        "casing": {
            "casing_id": CASING_SUDJUK_ID,
            "start_weight": excessive_usage + 1.0,
            "end_weight": 1.0
        },
        "materials": [],
        "notes": "Test insufficient stock",
        "idempotency_key": f"test-insufficient-{uuid.uuid4()}"
    }
    
    # Should return 400 error
    response_data, error = make_request("POST", f"/production/batches/{batch_id}/stuff", stuff_data, expected_status=400)
    if error and "400" not in error:
        results.add_fail("Insufficient stock validation", f"Expected 400 error, got: {error}")
        return
    
    # Check error message is in Ukrainian
    if response_data and 'detail' in response_data:
        error_msg = response_data['detail']
        if 'недостатньо' not in error_msg.lower():
            results.add_fail("Ukrainian insufficient stock message", f"Error message not in Ukrainian: {error_msg}")
            return
    
    results.add_pass("Stock Availability Check")

def test_idempotency(results):
    """Test 5: Idempotency"""
    print("\n🧪 Test 5: Idempotency")
    
    # Create test batch
    batch_data, error = create_test_batch(SUDJUK_RECIPE_ID, 50.0)
    if error:
        results.add_fail("Create test batch for idempotency", error)
        return
    
    batch_id = batch_data['id']
    
    # Get initial stock
    initial_stock, error = get_stock_balance(CASING_SUDJUK_ID)
    if error:
        results.add_fail("Get initial stock for idempotency", error)
        return
    
    # Prepare stuffing data with same idempotency key
    idempotency_key = f"test-idempotency-{uuid.uuid4()}"
    stuff_data = {
        "casing": {
            "casing_id": CASING_SUDJUK_ID,
            "start_weight": 2.0,
            "end_weight": 0.5
        },
        "materials": [],
        "notes": "Test idempotency",
        "idempotency_key": idempotency_key
    }
    
    # First call
    response1, error = make_request("POST", f"/production/batches/{batch_id}/stuff", stuff_data)
    if error:
        results.add_fail("First idempotent call", error)
        return
    
    # Get stock after first call
    stock_after_first, error = get_stock_balance(CASING_SUDJUK_ID)
    if error:
        results.add_fail("Get stock after first call", error)
        return
    
    # Second call with same idempotency key
    response2, error = make_request("POST", f"/production/batches/{batch_id}/stuff", stuff_data)
    if error:
        results.add_fail("Second idempotent call", error)
        return
    
    # Get stock after second call
    stock_after_second, error = get_stock_balance(CASING_SUDJUK_ID)
    if error:
        results.add_fail("Get stock after second call", error)
        return
    
    # Stock should be the same after both calls (no double deduction)
    if abs(stock_after_first - stock_after_second) > 0.01:
        results.add_fail("Idempotency - no double deduction", f"Stock changed: {stock_after_first} -> {stock_after_second}")
        return
    
    # Verify only one deduction happened
    expected_usage = 2.0 - 0.5  # 1.5 kg
    expected_final_stock = initial_stock - expected_usage
    if abs(stock_after_second - expected_final_stock) > 0.01:
        results.add_fail("Idempotency - correct single deduction", f"Expected {expected_final_stock}, got {stock_after_second}")
        return
    
    results.add_pass("Idempotency")

def test_backward_compatibility(results):
    """Test 6: Backward Compatibility"""
    print("\n🧪 Test 6: Backward Compatibility")
    
    # Create test batch
    batch_data, error = create_test_batch(SUDJUK_RECIPE_ID, 50.0)
    if error:
        results.add_fail("Create test batch for backward compatibility", error)
        return
    
    batch_id = batch_data['id']
    
    # Test old format (materials only, no casing)
    stuff_data = {
        "materials": [],  # Empty materials list
        "notes": "Test backward compatibility",
        "idempotency_key": f"test-backward-compat-{uuid.uuid4()}"
    }
    
    # Should succeed without casing
    response_data, error = make_request("POST", f"/production/batches/{batch_id}/stuff", stuff_data)
    if error:
        results.add_fail("Backward compatibility - old format", error)
        return
    
    # Response should not contain casing info
    if 'casing' in response_data:
        results.add_fail("Backward compatibility - no casing in response", "Casing info present when not expected")
        return
    
    results.add_pass("Backward Compatibility")

def test_database_verification(results):
    """Test 7: Database Verification"""
    print("\n🧪 Test 7: Database Verification")
    
    # Create test batch
    batch_data, error = create_test_batch(SUDJUK_RECIPE_ID, 75.0)
    if error:
        results.add_fail("Create test batch for DB verification", error)
        return
    
    batch_id = batch_data['id']
    batch_number = batch_data['batch_number']
    
    # Get initial stock and batch info
    initial_stock, error = get_stock_balance(CASING_SUDJUK_ID)
    if error:
        results.add_fail("Get initial stock for DB verification", error)
        return
    
    # Perform stuffing
    stuff_data = {
        "casing": {
            "casing_id": CASING_SUDJUK_ID,
            "start_weight": 3.0,
            "end_weight": 0.8
        },
        "materials": [],
        "notes": "Test DB verification",
        "idempotency_key": f"test-db-verify-{uuid.uuid4()}"
    }
    
    response_data, error = make_request("POST", f"/production/batches/{batch_id}/stuff", stuff_data)
    if error:
        results.add_fail("Stuffing for DB verification", error)
        return
    
    # Verify stock_balances updated correctly
    final_stock, error = get_stock_balance(CASING_SUDJUK_ID)
    if error:
        results.add_fail("Get final stock for DB verification", error)
        return
    
    expected_usage = 3.0 - 0.8  # 2.2 kg
    expected_final_stock = initial_stock - expected_usage
    if abs(final_stock - expected_final_stock) > 0.01:
        results.add_fail("DB - stock_balances updated", f"Expected {expected_final_stock}, got {final_stock}")
        return
    
    # Verify stock_movements has proper metadata
    movements_data, error = make_request("GET", f"/stock/movements?nomenclature_id={CASING_SUDJUK_ID}&limit=1")
    if error:
        results.add_fail("Get movements for DB verification", error)
        return
    
    if not movements_data:
        results.add_fail("DB - stock_movements created", "No stock movements found")
        return
    
    movement = movements_data[0]
    if movement['metadata']:
        try:
            metadata = json.loads(movement['metadata'])
            required_fields = ['start_weight_kg', 'end_weight_kg', 'usage_kg', 'waste_kg']
            for field in required_fields:
                if field not in metadata:
                    results.add_fail(f"DB - metadata has {field}", f"Missing {field} in metadata")
                    return
        except:
            results.add_fail("DB - metadata parsing", "Could not parse metadata JSON")
            return
    
    # Verify batch status updated
    batch_info, error = make_request("GET", f"/production/batches/{batch_id}")
    if error:
        results.add_fail("Get batch info for DB verification", error)
        return
    
    if batch_info['status'] != 'in_progress':
        results.add_fail("DB - batch status updated", f"Expected 'in_progress', got {batch_info['status']}")
        return
    
    results.add_pass("Database Verification")

def test_rounding_precision(results):
    """Test 8: Proper Rounding (2 decimal places)"""
    print("\n🧪 Test 8: Proper Rounding (2 decimal places)")
    
    # Create test batch
    batch_data, error = create_test_batch(SUDJUK_RECIPE_ID, 50.0)
    if error:
        results.add_fail("Create test batch for rounding", error)
        return
    
    batch_id = batch_data['id']
    
    # Test with values that need rounding
    stuff_data = {
        "casing": {
            "casing_id": CASING_SUDJUK_ID,
            "start_weight": 1.234567,  # Should round to 1.23
            "end_weight": 0.456789     # Should round to 0.46
        },
        "materials": [],
        "notes": "Test rounding",
        "idempotency_key": f"test-rounding-{uuid.uuid4()}"
    }
    
    response_data, error = make_request("POST", f"/production/batches/{batch_id}/stuff", stuff_data)
    if error:
        results.add_fail("Stuffing with rounding values", error)
        return
    
    # Check if usage is properly rounded
    if 'casing' in response_data:
        usage = response_data['casing']['usage_kg']
        expected_usage = round(1.234567 - 0.456789, 2)  # Should be 0.78
        if abs(usage - expected_usage) > 0.001:
            results.add_fail("Proper rounding", f"Expected {expected_usage}, got {usage}")
            return
    
    results.add_pass("Proper Rounding (2 decimal places)")

def main():
    """Run all tests"""
    print("🚀 Starting Weight-based Casing Accounting Tests")
    print(f"Backend URL: {BACKEND_URL}")
    print(f"Test started at: {datetime.now()}")
    
    results = TestResults()
    
    # Check backend health
    health_data, error = make_request("GET", "/health")
    if error:
        print(f"❌ Backend health check failed: {error}")
        return
    
    print(f"✅ Backend is healthy: {health_data}")
    
    # Run all tests
    test_happy_path_stuffing(results)
    test_validation_end_greater_than_start(results)
    test_validation_zero_usage(results)
    test_insufficient_stock(results)
    test_idempotency(results)
    test_backward_compatibility(results)
    test_database_verification(results)
    test_rounding_precision(results)
    
    # Print summary
    results.summary()
    
    return results.failed == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)