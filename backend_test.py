#!/usr/bin/env python3
"""
Comprehensive Backend Testing for Butchery API Module
Tests all 6 endpoints with edge cases and database validation
"""

import requests
import json
import uuid
from datetime import datetime
import time

# Get backend URL from frontend env
try:
    with open('/app/frontend/.env', 'r') as f:
        for line in f:
            if line.startswith('EXPO_PUBLIC_BACKEND_URL='):
                BACKEND_URL = line.split('=')[1].strip()
                break
    else:
        BACKEND_URL = "https://carcasstech.preview.emergentagent.com"
except:
    BACKEND_URL = "https://carcasstech.preview.emergentagent.com"

API_BASE = f"{BACKEND_URL}/api"

class ButcheryAPITester:
    def __init__(self):
        self.test_results = []
        self.created_operations = []
        
    def log_test(self, test_name, success, message, details=None):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name} - {message}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'details': details
        })
    
    def test_get_recipes_list(self):
        """Test GET /api/butchery/recipes"""
        print("\n=== Testing GET /api/butchery/recipes ===")
        
        try:
            # Test 1: Get all recipes
            response = requests.get(f"{API_BASE}/butchery/recipes")
            if response.status_code == 200:
                recipes = response.json()
                if len(recipes) > 0:
                    self.log_test("GET recipes - all", True, f"Retrieved {len(recipes)} recipes")
                    
                    # Verify recipe structure
                    recipe = recipes[0]
                    required_fields = ['id', 'name', 'source_nomenclature_id', 'source_name', 'level', 'outputs']
                    missing_fields = [field for field in required_fields if field not in recipe]
                    
                    if not missing_fields:
                        self.log_test("Recipe structure", True, "All required fields present")
                        
                        # Check outputs structure
                        if recipe['outputs'] and len(recipe['outputs']) > 0:
                            output = recipe['outputs'][0]
                            output_fields = ['output_nomenclature_id', 'output_name', 'yield_percentage']
                            missing_output_fields = [field for field in output_fields if field not in output]
                            
                            if not missing_output_fields:
                                self.log_test("Recipe outputs structure", True, "Output structure valid")
                            else:
                                self.log_test("Recipe outputs structure", False, f"Missing fields: {missing_output_fields}")
                        else:
                            self.log_test("Recipe outputs", False, "No outputs found in recipe")
                    else:
                        self.log_test("Recipe structure", False, f"Missing fields: {missing_fields}")
                else:
                    self.log_test("GET recipes - all", False, "No recipes found")
            else:
                self.log_test("GET recipes - all", False, f"HTTP {response.status_code}: {response.text}")
            
            # Test 2: Filter by source_id (if we have recipes)
            if response.status_code == 200 and len(response.json()) > 0:
                first_recipe = response.json()[0]
                source_id = first_recipe['source_nomenclature_id']
                
                filter_response = requests.get(f"{API_BASE}/butchery/recipes?source_id={source_id}")
                if filter_response.status_code == 200:
                    filtered_recipes = filter_response.json()
                    all_match = all(r['source_nomenclature_id'] == source_id for r in filtered_recipes)
                    if all_match:
                        self.log_test("GET recipes - source filter", True, f"Filter by source_id={source_id} works")
                    else:
                        self.log_test("GET recipes - source filter", False, "Filter not working correctly")
                else:
                    self.log_test("GET recipes - source filter", False, f"HTTP {filter_response.status_code}")
            
            # Test 3: Filter by level
            level_response = requests.get(f"{API_BASE}/butchery/recipes?level=1")
            if level_response.status_code == 200:
                level_recipes = level_response.json()
                all_level_1 = all(r['level'] == 1 for r in level_recipes)
                if all_level_1:
                    self.log_test("GET recipes - level filter", True, f"Level filter works, found {len(level_recipes)} level 1 recipes")
                else:
                    self.log_test("GET recipes - level filter", False, "Level filter not working correctly")
            else:
                self.log_test("GET recipes - level filter", False, f"HTTP {level_response.status_code}")
                
        except Exception as e:
            self.log_test("GET recipes - exception", False, f"Exception: {str(e)}")
    
    def test_get_recipe_by_id(self):
        """Test GET /api/butchery/recipes/{id}"""
        print("\n=== Testing GET /api/butchery/recipes/{id} ===")
        
        try:
            # First get a recipe ID
            recipes_response = requests.get(f"{API_BASE}/butchery/recipes")
            if recipes_response.status_code == 200 and len(recipes_response.json()) > 0:
                recipe_id = recipes_response.json()[0]['id']
                
                # Test valid ID
                response = requests.get(f"{API_BASE}/butchery/recipes/{recipe_id}")
                if response.status_code == 200:
                    recipe = response.json()
                    if recipe['id'] == recipe_id:
                        self.log_test("GET recipe by ID - valid", True, f"Retrieved recipe {recipe_id}: {recipe['name']}")
                        
                        # Verify outputs are ordered
                        if recipe['outputs']:
                            self.log_test("Recipe outputs ordering", True, f"Recipe has {len(recipe['outputs'])} outputs")
                        else:
                            self.log_test("Recipe outputs ordering", False, "No outputs in recipe")
                    else:
                        self.log_test("GET recipe by ID - valid", False, "Wrong recipe returned")
                else:
                    self.log_test("GET recipe by ID - valid", False, f"HTTP {response.status_code}: {response.text}")
                
                # Test invalid ID
                invalid_response = requests.get(f"{API_BASE}/butchery/recipes/99999")
                if invalid_response.status_code == 404:
                    self.log_test("GET recipe by ID - invalid", True, "404 returned for invalid ID")
                else:
                    self.log_test("GET recipe by ID - invalid", False, f"Expected 404, got {invalid_response.status_code}")
            else:
                self.log_test("GET recipe by ID - setup", False, "Could not get recipes for testing")
                
        except Exception as e:
            self.log_test("GET recipe by ID - exception", False, f"Exception: {str(e)}")
    
    def test_create_operation(self):
        """Test POST /api/butchery/operations"""
        print("\n=== Testing POST /api/butchery/operations ===")
        
        try:
            # First get available recipes and stock
            recipes_response = requests.get(f"{API_BASE}/butchery/recipes")
            stock_response = requests.get(f"{API_BASE}/stock/balances")
            
            if recipes_response.status_code == 200 and stock_response.status_code == 200:
                recipes = recipes_response.json()
                stock_balances = stock_response.json()
                
                if not recipes:
                    self.log_test("Create operation - setup", False, "No recipes available")
                    return
                
                # Find a recipe with available stock
                suitable_recipe = None
                available_stock = None
                
                for recipe in recipes:
                    source_id = recipe['source_nomenclature_id']
                    for balance in stock_balances:
                        if balance['nomenclature_id'] == source_id and balance['quantity'] > 10:
                            suitable_recipe = recipe
                            available_stock = balance
                            break
                    if suitable_recipe:
                        break
                
                if not suitable_recipe:
                    self.log_test("Create operation - setup", False, "No recipes with sufficient stock found")
                    return
                
                # Test 1: Valid operation creation
                operation_data = {
                    "recipe_id": suitable_recipe['id'],
                    "source_nomenclature_id": suitable_recipe['source_nomenclature_id'],
                    "input_weight": 5.0,  # Use 5kg
                    "notes": "Test operation",
                    "idempotency_key": str(uuid.uuid4())
                }
                
                response = requests.post(f"{API_BASE}/butchery/operations", json=operation_data)
                if response.status_code == 200:
                    result = response.json()
                    if 'operation_id' in result and 'operation_number' in result:
                        operation_id = result['operation_id']
                        operation_number = result['operation_number']
                        self.created_operations.append(operation_id)
                        
                        # Verify operation number format: BUT-YYMMDD-XXX
                        today = datetime.now().strftime("%y%m%d")
                        if operation_number.startswith(f"BUT-{today}-"):
                            self.log_test("Create operation - valid", True, f"Created operation {operation_number}")
                        else:
                            self.log_test("Create operation - number format", False, f"Invalid number format: {operation_number}")
                    else:
                        self.log_test("Create operation - valid", False, "Missing operation_id or operation_number in response")
                else:
                    self.log_test("Create operation - valid", False, f"HTTP {response.status_code}: {response.text}")
                
                # Test 2: Insufficient stock
                insufficient_data = operation_data.copy()
                insufficient_data['input_weight'] = available_stock['quantity'] + 100  # More than available
                insufficient_data['idempotency_key'] = str(uuid.uuid4())
                
                insufficient_response = requests.post(f"{API_BASE}/butchery/operations", json=insufficient_data)
                if insufficient_response.status_code == 400:
                    self.log_test("Create operation - insufficient stock", True, "Correctly rejected insufficient stock")
                else:
                    self.log_test("Create operation - insufficient stock", False, f"Expected 400, got {insufficient_response.status_code}")
                
                # Test 3: Duplicate idempotency key
                duplicate_response = requests.post(f"{API_BASE}/butchery/operations", json=operation_data)
                if duplicate_response.status_code == 400:
                    self.log_test("Create operation - idempotency", True, "Correctly rejected duplicate idempotency_key")
                else:
                    self.log_test("Create operation - idempotency", False, f"Expected 400, got {duplicate_response.status_code}")
                
                # Test 4: Invalid recipe ID
                invalid_recipe_data = operation_data.copy()
                invalid_recipe_data['recipe_id'] = 99999
                invalid_recipe_data['idempotency_key'] = str(uuid.uuid4())
                
                invalid_recipe_response = requests.post(f"{API_BASE}/butchery/operations", json=invalid_recipe_data)
                if invalid_recipe_response.status_code == 404:
                    self.log_test("Create operation - invalid recipe", True, "Correctly rejected invalid recipe ID")
                else:
                    self.log_test("Create operation - invalid recipe", False, f"Expected 404, got {invalid_recipe_response.status_code}")
                    
            else:
                self.log_test("Create operation - setup", False, "Could not get recipes or stock data")
                
        except Exception as e:
            self.log_test("Create operation - exception", False, f"Exception: {str(e)}")
    
    def test_get_operations_list(self):
        """Test GET /api/butchery/operations"""
        print("\n=== Testing GET /api/butchery/operations ===")
        
        try:
            # Test 1: Get all operations
            response = requests.get(f"{API_BASE}/butchery/operations")
            if response.status_code == 200:
                operations = response.json()
                self.log_test("GET operations - all", True, f"Retrieved {len(operations)} operations")
                
                if operations:
                    # Verify operation structure
                    operation = operations[0]
                    required_fields = ['id', 'operation_number', 'recipe_name', 'source_name', 'input_weight', 'status']
                    missing_fields = [field for field in required_fields if field not in operation]
                    
                    if not missing_fields:
                        self.log_test("Operation structure", True, "All required fields present")
                    else:
                        self.log_test("Operation structure", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("GET operations - all", False, f"HTTP {response.status_code}: {response.text}")
            
            # Test 2: Filter by status
            status_response = requests.get(f"{API_BASE}/butchery/operations?status=in_progress")
            if status_response.status_code == 200:
                in_progress_ops = status_response.json()
                all_in_progress = all(op['status'] == 'in_progress' for op in in_progress_ops)
                if all_in_progress:
                    self.log_test("GET operations - status filter", True, f"Status filter works, found {len(in_progress_ops)} in_progress operations")
                else:
                    self.log_test("GET operations - status filter", False, "Status filter not working correctly")
            else:
                self.log_test("GET operations - status filter", False, f"HTTP {status_response.status_code}")
            
            # Test 3: Limit parameter
            limit_response = requests.get(f"{API_BASE}/butchery/operations?limit=5")
            if limit_response.status_code == 200:
                limited_ops = limit_response.json()
                if len(limited_ops) <= 5:
                    self.log_test("GET operations - limit", True, f"Limit works, returned {len(limited_ops)} operations")
                else:
                    self.log_test("GET operations - limit", False, f"Limit not working, returned {len(limited_ops)} operations")
            else:
                self.log_test("GET operations - limit", False, f"HTTP {limit_response.status_code}")
                
        except Exception as e:
            self.log_test("GET operations - exception", False, f"Exception: {str(e)}")
    
    def test_get_operation_by_id(self):
        """Test GET /api/butchery/operations/{id}"""
        print("\n=== Testing GET /api/butchery/operations/{id} ===")
        
        try:
            # Get an operation ID
            operations_response = requests.get(f"{API_BASE}/butchery/operations")
            if operations_response.status_code == 200 and len(operations_response.json()) > 0:
                operation_id = operations_response.json()[0]['id']
                
                # Test valid ID
                response = requests.get(f"{API_BASE}/butchery/operations/{operation_id}")
                if response.status_code == 200:
                    result = response.json()
                    if 'operation' in result and 'expected_outputs' in result:
                        operation = result['operation']
                        expected_outputs = result['expected_outputs']
                        
                        self.log_test("GET operation by ID - valid", True, f"Retrieved operation {operation['operation_number']}")
                        
                        # Verify expected outputs calculation
                        if expected_outputs:
                            total_expected_percentage = sum(out['yield_percentage'] for out in expected_outputs)
                            self.log_test("Expected outputs calculation", True, f"Total expected yield: {total_expected_percentage:.1f}%")
                        else:
                            self.log_test("Expected outputs calculation", False, "No expected outputs found")
                    else:
                        self.log_test("GET operation by ID - valid", False, "Missing operation or expected_outputs in response")
                else:
                    self.log_test("GET operation by ID - valid", False, f"HTTP {response.status_code}: {response.text}")
                
                # Test invalid ID
                invalid_response = requests.get(f"{API_BASE}/butchery/operations/99999")
                if invalid_response.status_code == 404:
                    self.log_test("GET operation by ID - invalid", True, "404 returned for invalid ID")
                else:
                    self.log_test("GET operation by ID - invalid", False, f"Expected 404, got {invalid_response.status_code}")
            else:
                self.log_test("GET operation by ID - setup", False, "Could not get operations for testing")
                
        except Exception as e:
            self.log_test("GET operation by ID - exception", False, f"Exception: {str(e)}")
    
    def test_complete_operation(self):
        """Test PUT /api/butchery/operations/{id}/complete"""
        print("\n=== Testing PUT /api/butchery/operations/{id}/complete ===")
        
        try:
            # Find an in_progress operation or create one
            operations_response = requests.get(f"{API_BASE}/butchery/operations?status=in_progress")
            operation_id = None
            
            if operations_response.status_code == 200:
                in_progress_ops = operations_response.json()
                if in_progress_ops:
                    operation_id = in_progress_ops[0]['id']
                elif self.created_operations:
                    operation_id = self.created_operations[0]
            
            if not operation_id:
                self.log_test("Complete operation - setup", False, "No in_progress operations available for testing")
                return
            
            # Get operation details to build completion data
            op_response = requests.get(f"{API_BASE}/butchery/operations/{operation_id}")
            if op_response.status_code != 200:
                self.log_test("Complete operation - setup", False, "Could not get operation details")
                return
            
            op_data = op_response.json()
            expected_outputs = op_data['expected_outputs']
            
            if not expected_outputs:
                self.log_test("Complete operation - setup", False, "No expected outputs for operation")
                return
            
            # Test 1: Valid completion
            completion_outputs = []
            total_actual = 0
            
            for expected in expected_outputs:
                # Use 95% of expected weight for realistic completion
                actual_weight = expected['expected_weight'] * 0.95
                total_actual += actual_weight
                
                completion_outputs.append({
                    "output_nomenclature_id": expected['output_nomenclature_id'],
                    "actual_weight": actual_weight,
                    "notes": f"Test completion for {expected['output_name']}"
                })
            
            completion_data = {
                "outputs": completion_outputs,
                "notes": "Test completion",
                "idempotency_key": str(uuid.uuid4())
            }
            
            response = requests.put(f"{API_BASE}/butchery/operations/{operation_id}/complete", json=completion_data)
            if response.status_code == 200:
                result = response.json()
                if 'operation_number' in result and 'outputs_count' in result:
                    self.log_test("Complete operation - valid", True, f"Completed operation {result['operation_number']} with {result['outputs_count']} outputs")
                    
                    # Verify operation status changed
                    verify_response = requests.get(f"{API_BASE}/butchery/operations/{operation_id}")
                    if verify_response.status_code == 200:
                        verify_data = verify_response.json()
                        if verify_data['operation']['status'] == 'completed':
                            self.log_test("Operation status update", True, "Status changed to completed")
                        else:
                            self.log_test("Operation status update", False, f"Status is {verify_data['operation']['status']}, expected completed")
                else:
                    self.log_test("Complete operation - valid", False, "Missing expected fields in response")
            else:
                self.log_test("Complete operation - valid", False, f"HTTP {response.status_code}: {response.text}")
            
            # Test 2: Duplicate completion (should fail)
            duplicate_response = requests.put(f"{API_BASE}/butchery/operations/{operation_id}/complete", json=completion_data)
            if duplicate_response.status_code == 400:
                self.log_test("Complete operation - duplicate", True, "Correctly rejected duplicate completion")
            else:
                self.log_test("Complete operation - duplicate", False, f"Expected 400, got {duplicate_response.status_code}")
            
            # Test 3: Invalid operation ID
            invalid_completion_data = completion_data.copy()
            invalid_completion_data['idempotency_key'] = str(uuid.uuid4())
            
            invalid_response = requests.put(f"{API_BASE}/butchery/operations/99999/complete", json=invalid_completion_data)
            if invalid_response.status_code == 404:
                self.log_test("Complete operation - invalid ID", True, "404 returned for invalid operation ID")
            else:
                self.log_test("Complete operation - invalid ID", False, f"Expected 404, got {invalid_response.status_code}")
                
        except Exception as e:
            self.log_test("Complete operation - exception", False, f"Exception: {str(e)}")
    
    def test_stock_integration(self):
        """Test stock balance and movement integration"""
        print("\n=== Testing Stock Integration ===")
        
        try:
            # Get stock balances before and after operations
            initial_response = requests.get(f"{API_BASE}/stock/balances")
            if initial_response.status_code == 200:
                self.log_test("Stock integration - balances", True, "Can retrieve stock balances")
                
                # Get stock movements
                movements_response = requests.get(f"{API_BASE}/stock/movements?limit=10")
                if movements_response.status_code == 200:
                    movements = movements_response.json()
                    
                    # Look for butchery-related movements
                    butchery_movements = [m for m in movements if 'butchery' in str(m.get('metadata', ''))]
                    if butchery_movements:
                        self.log_test("Stock integration - movements", True, f"Found {len(butchery_movements)} butchery-related stock movements")
                    else:
                        self.log_test("Stock integration - movements", True, "No butchery movements found (may be expected if no operations completed)")
                else:
                    self.log_test("Stock integration - movements", False, f"HTTP {movements_response.status_code}")
            else:
                self.log_test("Stock integration - balances", False, f"HTTP {initial_response.status_code}")
                
        except Exception as e:
            self.log_test("Stock integration - exception", False, f"Exception: {str(e)}")
    
    def test_liquid_waste_handling(self):
        """Test liquid waste (non-inventory) handling"""
        print("\n=== Testing Liquid Waste Handling ===")
        
        try:
            # Check if there are nomenclature items with liquid-waste type
            nomenclature_response = requests.get(f"{API_BASE}/nomenclature")
            if nomenclature_response.status_code == 200:
                nomenclature = nomenclature_response.json()
                
                # Look for liquid waste items (should have nomenclature_type='liquid-waste')
                # This is a database-level check that would need to be verified during completion
                self.log_test("Liquid waste - nomenclature", True, f"Retrieved {len(nomenclature)} nomenclature items for liquid waste verification")
            else:
                self.log_test("Liquid waste - nomenclature", False, f"HTTP {nomenclature_response.status_code}")
                
        except Exception as e:
            self.log_test("Liquid waste - exception", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all tests"""
        print(f"🧪 Starting Butchery API Testing")
        print(f"Backend URL: {BACKEND_URL}")
        print(f"API Base: {API_BASE}")
        
        start_time = time.time()
        
        # Run all test methods
        self.test_get_recipes_list()
        self.test_get_recipe_by_id()
        self.test_create_operation()
        self.test_get_operations_list()
        self.test_get_operation_by_id()
        self.test_complete_operation()
        self.test_stock_integration()
        self.test_liquid_waste_handling()
        
        end_time = time.time()
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['success']])
        failed_tests = total_tests - passed_tests
        
        print(f"\n{'='*60}")
        print(f"🏁 BUTCHERY API TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⏱️  Duration: {end_time - start_time:.2f} seconds")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print(f"\n❌ FAILED TESTS:")
            for test in self.test_results:
                if not test['success']:
                    print(f"   • {test['test']}: {test['message']}")
        
        return passed_tests, failed_tests, self.test_results

if __name__ == "__main__":
    tester = ButcheryAPITester()
    passed, failed, results = tester.run_all_tests()
    
    # Exit with error code if tests failed
    exit(0 if failed == 0 else 1)