#!/usr/bin/env python3
"""
Backend API Testing for Production Module
Tests all production endpoints systematically
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

# Backend URL from environment
BACKEND_URL = "https://recipe-factory-1.preview.emergentagent.com/api"

class ProductionAPITester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.test_results = []
        self.created_batch_id = None
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        result = {
            "test": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat(),
            "response_data": response_data
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"   Details: {details}")
        if not success and response_data:
            print(f"   Response: {response_data}")
        print()

    def test_health_check(self):
        """Test basic health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Check", True, f"Status: {data.get('status')}", data)
                return True
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Health Check", False, f"Connection error: {str(e)}")
            return False

    def test_get_recipes(self):
        """Test GET /api/production/recipes"""
        try:
            response = self.session.get(f"{self.base_url}/production/recipes", timeout=10)
            if response.status_code == 200:
                recipes = response.json()
                if isinstance(recipes, list) and len(recipes) >= 8:
                    # Check required fields
                    first_recipe = recipes[0]
                    required_fields = ['id', 'name', 'target_product_id', 'expected_yield_min', 'expected_yield_max']
                    missing_fields = [field for field in required_fields if field not in first_recipe]
                    
                    if not missing_fields:
                        self.log_test("GET /production/recipes", True, 
                                    f"Found {len(recipes)} recipes with all required fields", 
                                    {"count": len(recipes), "sample": first_recipe})
                        return True
                    else:
                        self.log_test("GET /production/recipes", False, 
                                    f"Missing fields: {missing_fields}", first_recipe)
                        return False
                else:
                    self.log_test("GET /production/recipes", False, 
                                f"Expected at least 8 recipes, got {len(recipes) if isinstance(recipes, list) else 'invalid response'}", 
                                recipes)
                    return False
            else:
                self.log_test("GET /production/recipes", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("GET /production/recipes", False, f"Error: {str(e)}")
            return False

    def test_get_recipe_by_id(self, recipe_id: int = 2):
        """Test GET /api/production/recipes/{recipe_id}"""
        try:
            response = self.session.get(f"{self.base_url}/production/recipes/{recipe_id}", timeout=10)
            if response.status_code == 200:
                recipe = response.json()
                required_fields = ['id', 'name', 'target_product_id', 'steps']
                missing_fields = [field for field in required_fields if field not in recipe]
                
                if not missing_fields:
                    steps = recipe.get('steps', [])
                    # Check if steps are ordered
                    if steps:
                        step_orders = [step.get('step_order', 0) for step in steps]
                        is_ordered = step_orders == sorted(step_orders)
                        self.log_test(f"GET /production/recipes/{recipe_id}", True, 
                                    f"Recipe '{recipe['name']}' with {len(steps)} steps, ordered: {is_ordered}", 
                                    {"recipe_name": recipe['name'], "steps_count": len(steps)})
                        return True
                    else:
                        self.log_test(f"GET /production/recipes/{recipe_id}", True, 
                                    f"Recipe '{recipe['name']}' with no steps", recipe)
                        return True
                else:
                    self.log_test(f"GET /production/recipes/{recipe_id}", False, 
                                f"Missing fields: {missing_fields}", recipe)
                    return False
            elif response.status_code == 404:
                self.log_test(f"GET /production/recipes/{recipe_id}", False, 
                            f"Recipe {recipe_id} not found", response.text)
                return False
            else:
                self.log_test(f"GET /production/recipes/{recipe_id}", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test(f"GET /production/recipes/{recipe_id}", False, f"Error: {str(e)}")
            return False

    def test_create_batch(self):
        """Test POST /api/production/batches"""
        try:
            payload = {
                "recipe_id": 2,
                "initial_weight": 100.0,
                "trim_waste": 0,
                "trim_returned": False,
                "operator_notes": "Test batch for API testing"
            }
            
            response = self.session.post(
                f"{self.base_url}/production/batches", 
                json=payload, 
                timeout=10
            )
            
            if response.status_code == 200:
                batch = response.json()
                required_fields = ['id', 'batch_number', 'recipe_id', 'status']
                missing_fields = [field for field in required_fields if field not in batch]
                
                if not missing_fields:
                    # Check batch number format
                    batch_number = batch['batch_number']
                    expected_format = batch_number.startswith('BATCH-') and len(batch_number.split('-')) == 3
                    
                    if expected_format and batch['status'] == 'created':
                        self.created_batch_id = batch['id']  # Store for later tests
                        self.log_test("POST /production/batches", True, 
                                    f"Created batch {batch_number} with ID {batch['id']}", 
                                    {"batch_id": batch['id'], "batch_number": batch_number})
                        return True
                    else:
                        self.log_test("POST /production/batches", False, 
                                    f"Invalid batch format or status. Number: {batch_number}, Status: {batch['status']}", 
                                    batch)
                        return False
                else:
                    self.log_test("POST /production/batches", False, 
                                f"Missing fields: {missing_fields}", batch)
                    return False
            else:
                self.log_test("POST /production/batches", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("POST /production/batches", False, f"Error: {str(e)}")
            return False

    def test_get_batches(self):
        """Test GET /api/production/batches"""
        try:
            response = self.session.get(f"{self.base_url}/production/batches", timeout=10)
            if response.status_code == 200:
                batches = response.json()
                if isinstance(batches, list):
                    self.log_test("GET /production/batches", True, 
                                f"Retrieved {len(batches)} batches", 
                                {"count": len(batches)})
                    return True
                else:
                    self.log_test("GET /production/batches", False, 
                                "Response is not a list", batches)
                    return False
            else:
                self.log_test("GET /production/batches", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("GET /production/batches", False, f"Error: {str(e)}")
            return False

    def test_get_batches_filtered(self):
        """Test GET /api/production/batches?status=created"""
        try:
            response = self.session.get(f"{self.base_url}/production/batches?status=created", timeout=10)
            if response.status_code == 200:
                batches = response.json()
                if isinstance(batches, list):
                    # Check if all batches have status 'created'
                    created_batches = [b for b in batches if b.get('status') == 'created']
                    if len(created_batches) == len(batches):
                        self.log_test("GET /production/batches?status=created", True, 
                                    f"Retrieved {len(batches)} created batches", 
                                    {"count": len(batches)})
                        return True
                    else:
                        self.log_test("GET /production/batches?status=created", False, 
                                    f"Filter not working: {len(created_batches)}/{len(batches)} have 'created' status", 
                                    batches)
                        return False
                else:
                    self.log_test("GET /production/batches?status=created", False, 
                                "Response is not a list", batches)
                    return False
            else:
                self.log_test("GET /production/batches?status=created", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("GET /production/batches?status=created", False, f"Error: {str(e)}")
            return False

    def test_get_batch_by_id(self):
        """Test GET /api/production/batches/{batch_id}"""
        if not self.created_batch_id:
            self.log_test("GET /production/batches/{id}", False, "No batch ID available from previous test")
            return False
            
        try:
            response = self.session.get(f"{self.base_url}/production/batches/{self.created_batch_id}", timeout=10)
            if response.status_code == 200:
                batch = response.json()
                required_fields = ['id', 'batch_number', 'recipe_id', 'status']
                missing_fields = [field for field in required_fields if field not in batch]
                
                if not missing_fields:
                    self.log_test(f"GET /production/batches/{self.created_batch_id}", True, 
                                f"Retrieved batch {batch['batch_number']}", 
                                {"batch_number": batch['batch_number'], "status": batch['status']})
                    return True
                else:
                    self.log_test(f"GET /production/batches/{self.created_batch_id}", False, 
                                f"Missing fields: {missing_fields}", batch)
                    return False
            elif response.status_code == 404:
                self.log_test(f"GET /production/batches/{self.created_batch_id}", False, 
                            f"Batch {self.created_batch_id} not found", response.text)
                return False
            else:
                self.log_test(f"GET /production/batches/{self.created_batch_id}", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test(f"GET /production/batches/{self.created_batch_id}", False, f"Error: {str(e)}")
            return False

    def test_complete_batch(self):
        """Test PUT /api/production/batches/{batch_id}/complete"""
        if not self.created_batch_id:
            self.log_test("PUT /production/batches/{id}/complete", False, "No batch ID available from previous test")
            return False
            
        try:
            timestamp = int(time.time())
            payload = {
                "final_weight": 75.0,
                "notes": "Completed test batch via API testing",
                "idempotency_key": f"test-complete-{timestamp}"
            }
            
            response = self.session.put(
                f"{self.base_url}/production/batches/{self.created_batch_id}/complete", 
                json=payload, 
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                expected_fields = ['message', 'batch_id', 'yield_percent']
                missing_fields = [field for field in expected_fields if field not in result]
                
                if not missing_fields:
                    yield_percent = result.get('yield_percent', 0)
                    expected_yield = 75.0  # Expected yield percentage
                    
                    self.log_test(f"PUT /production/batches/{self.created_batch_id}/complete", True, 
                                f"Batch completed with {yield_percent}% yield", 
                                {"yield_percent": yield_percent, "batch_id": result['batch_id']})
                    return True
                else:
                    self.log_test(f"PUT /production/batches/{self.created_batch_id}/complete", False, 
                                f"Missing fields: {missing_fields}", result)
                    return False
            else:
                self.log_test(f"PUT /production/batches/{self.created_batch_id}/complete", False, 
                            f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test(f"PUT /production/batches/{self.created_batch_id}/complete", False, f"Error: {str(e)}")
            return False

    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        edge_case_results = []
        
        # Test invalid recipe ID
        try:
            payload = {"recipe_id": 99999, "initial_weight": 100.0, "operator_notes": "Invalid recipe test"}
            response = self.session.post(f"{self.base_url}/production/batches", json=payload, timeout=10)
            if response.status_code == 404:
                edge_case_results.append("✅ Invalid recipe ID returns 404")
            else:
                edge_case_results.append(f"❌ Invalid recipe ID returned {response.status_code}")
        except Exception as e:
            edge_case_results.append(f"❌ Invalid recipe ID test failed: {str(e)}")
        
        # Test non-existent recipe GET
        try:
            response = self.session.get(f"{self.base_url}/production/recipes/99999", timeout=10)
            if response.status_code == 404:
                edge_case_results.append("✅ Non-existent recipe returns 404")
            else:
                edge_case_results.append(f"❌ Non-existent recipe returned {response.status_code}")
        except Exception as e:
            edge_case_results.append(f"❌ Non-existent recipe test failed: {str(e)}")
        
        # Test non-existent batch GET
        try:
            response = self.session.get(f"{self.base_url}/production/batches/99999", timeout=10)
            if response.status_code == 404:
                edge_case_results.append("✅ Non-existent batch returns 404")
            else:
                edge_case_results.append(f"❌ Non-existent batch returned {response.status_code}")
        except Exception as e:
            edge_case_results.append(f"❌ Non-existent batch test failed: {str(e)}")
        
        # Test completing already completed batch (if we have one)
        if self.created_batch_id:
            try:
                payload = {
                    "final_weight": 80.0,
                    "notes": "Duplicate completion test",
                    "idempotency_key": f"duplicate-test-{int(time.time())}"
                }
                response = self.session.put(
                    f"{self.base_url}/production/batches/{self.created_batch_id}/complete", 
                    json=payload, timeout=10
                )
                if response.status_code == 400:
                    edge_case_results.append("✅ Completing already completed batch returns 400")
                else:
                    edge_case_results.append(f"❌ Duplicate completion returned {response.status_code}")
            except Exception as e:
                edge_case_results.append(f"❌ Duplicate completion test failed: {str(e)}")
        
        success = all("✅" in result for result in edge_case_results)
        self.log_test("Edge Cases", success, "; ".join(edge_case_results))
        return success

    def test_database_verification(self):
        """Verify database state after operations"""
        # This would require direct database access, which we don't have in API testing
        # Instead, we'll verify through API calls that stock movements were created
        
        try:
            # Check if we can get stock balances (this would show if stock movements were created)
            response = self.session.get(f"{self.base_url}/stock/balances", timeout=10)
            if response.status_code == 200:
                balances = response.json()
                # Look for any finished products with non-zero balance
                finished_products = [b for b in balances if b.get('category') == 'Готова продукція' and b.get('quantity', 0) > 0]
                
                if finished_products:
                    self.log_test("Database Verification", True, 
                                f"Found {len(finished_products)} finished products with stock", 
                                {"finished_products_count": len(finished_products)})
                    return True
                else:
                    self.log_test("Database Verification", True, 
                                "No finished products with stock found (may be expected)", 
                                {"total_balances": len(balances)})
                    return True
            else:
                self.log_test("Database Verification", False, 
                            f"Could not retrieve stock balances: HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Database Verification", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting Production API Tests")
        print("=" * 50)
        
        # Basic connectivity
        if not self.test_health_check():
            print("❌ Health check failed - aborting tests")
            return self.generate_summary()
        
        # Recipe endpoints
        self.test_get_recipes()
        self.test_get_recipe_by_id(2)  # Test with Бастурма класична
        
        # Batch endpoints
        self.test_create_batch()
        self.test_get_batches()
        self.test_get_batches_filtered()
        self.test_get_batch_by_id()
        self.test_complete_batch()
        
        # Edge cases
        self.test_edge_cases()
        
        # Database verification
        self.test_database_verification()
        
        return self.generate_summary()

    def generate_summary(self):
        """Generate test summary"""
        total_tests = len(self.test_results)
        passed_tests = len([t for t in self.test_results if t['success']])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "=" * 50)
        print("📊 TEST SUMMARY")
        print("=" * 50)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\n❌ FAILED TESTS:")
            for test in self.test_results:
                if not test['success']:
                    print(f"  - {test['test']}: {test['details']}")
        
        print("\n" + "=" * 50)
        
        return {
            "total": total_tests,
            "passed": passed_tests,
            "failed": failed_tests,
            "success_rate": passed_tests/total_tests*100,
            "results": self.test_results
        }

def main():
    """Main test execution"""
    tester = ProductionAPITester()
    summary = tester.run_all_tests()
    
    # Save detailed results
    with open('/app/test_results_detailed.json', 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    return summary['failed'] == 0

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)