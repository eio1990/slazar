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

class BackendTester:
    def __init__(self):
        self.results = {
            'nomenclature': {'passed': 0, 'failed': 0, 'tests': []},
            'production': {'passed': 0, 'failed': 0, 'tests': []},
            'packaging': {'passed': 0, 'failed': 0, 'tests': []},
            'butchery': {'passed': 0, 'failed': 0, 'tests': []},
            'stock': {'passed': 0, 'failed': 0, 'tests': []}
        }
        self.critical_issues = []
        
    def log_test(self, category: str, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.results[category]['tests'].append({
            'name': test_name,
            'passed': passed,
            'details': details
        })
        
        if passed:
            self.results[category]['passed'] += 1
            print(f"✅ {test_name}")
        else:
            self.results[category]['failed'] += 1
            print(f"❌ {test_name}: {details}")
            self.critical_issues.append(f"{category.upper()}: {test_name} - {details}")
    
    def make_request(self, method: str, endpoint: str, data: dict = None) -> tuple:
        """Make HTTP request and return (success, response_data, status_code)"""
        try:
            url = f"{API_BASE}{endpoint}"
            
            if method.upper() == 'GET':
                response = requests.get(url, timeout=30)
            elif method.upper() == 'POST':
                response = requests.post(url, json=data, timeout=30)
            elif method.upper() == 'PUT':
                response = requests.put(url, json=data, timeout=30)
            else:
                return False, f"Unsupported method: {method}", 0
            
            if response.status_code == 200:
                try:
                    return True, response.json(), response.status_code
                except:
                    return True, response.text, response.status_code
            else:
                return False, f"HTTP {response.status_code}: {response.text}", response.status_code
                
        except requests.exceptions.RequestException as e:
            return False, f"Request failed: {str(e)}", 0
    
    def test_nomenclature_api(self):
        """Test nomenclature API after migration"""
        print("\n🔍 TESTING NOMENCLATURE API")
        
        # Test 1: Get all nomenclature
        success, data, status = self.make_request('GET', '/nomenclature')
        if success and isinstance(data, list):
            total_count = len(data)
            
            # Count by categories
            categories = {}
            for item in data:
                cat = item.get('category', 'Unknown')
                categories[cat] = categories.get(cat, 0) + 1
            
            # Check expected categories and counts
            expected_meat = 13  # Сировина - М'ясо
            expected_semi = 14  # Напівфабрикати  
            expected_finished = 37  # Готова продукція
            
            meat_count = categories.get('Сировина - М\'ясо', 0)
            semi_count = categories.get('Напівфабрикати', 0)
            finished_count = categories.get('Готова продукція', 0)
            
            self.log_test('nomenclature', 'GET /nomenclature - returns data', True, 
                         f"Total: {total_count}, М'ясо: {meat_count}, Напівфабрикати: {semi_count}, Готова продукція: {finished_count}")
            
            # Verify category counts are approximately correct
            if abs(meat_count - expected_meat) <= 2:
                self.log_test('nomenclature', 'Meat category count (~13)', True, f"Found {meat_count}")
            else:
                self.log_test('nomenclature', 'Meat category count (~13)', False, f"Expected ~{expected_meat}, got {meat_count}")
            
            if abs(semi_count - expected_semi) <= 2:
                self.log_test('nomenclature', 'Semi-finished category count (~14)', True, f"Found {semi_count}")
            else:
                self.log_test('nomenclature', 'Semi-finished category count (~14)', False, f"Expected ~{expected_semi}, got {semi_count}")
            
            if abs(finished_count - expected_finished) <= 5:
                self.log_test('nomenclature', 'Finished products category count (~37)', True, f"Found {finished_count}")
            else:
                self.log_test('nomenclature', 'Finished products category count (~37)', False, f"Expected ~{expected_finished}, got {finished_count}")
            
            # Test 2: Check specific migrated items
            nomenclature_dict = {item['id']: item for item in data}
            
            # Check ID 108 should be "Конина" (merged from 108 and 178)
            if 108 in nomenclature_dict:
                name_108 = nomenclature_dict[108]['name']
                if name_108 == 'Конина':
                    self.log_test('nomenclature', 'ID 108 renamed to "Конина"', True, f"Name: {name_108}")
                else:
                    self.log_test('nomenclature', 'ID 108 renamed to "Конина"', False, f"Expected 'Конина', got '{name_108}'")
            else:
                self.log_test('nomenclature', 'ID 108 exists', False, "ID 108 not found")
            
            # Check ID 233 should be "Індичка"
            if 233 in nomenclature_dict:
                name_233 = nomenclature_dict[233]['name']
                if name_233 == 'Індичка':
                    self.log_test('nomenclature', 'ID 233 renamed to "Індичка"', True, f"Name: {name_233}")
                else:
                    self.log_test('nomenclature', 'ID 233 renamed to "Індичка"', False, f"Expected 'Індичка', got '{name_233}'")
            else:
                self.log_test('nomenclature', 'ID 233 exists', False, "ID 233 not found")
            
            # Check ID 113 should be "Курхан"
            if 113 in nomenclature_dict:
                name_113 = nomenclature_dict[113]['name']
                if name_113 == 'Курхан':
                    self.log_test('nomenclature', 'ID 113 renamed to "Курхан"', True, f"Name: {name_113}")
                else:
                    self.log_test('nomenclature', 'ID 113 renamed to "Курхан"', False, f"Expected 'Курхан', got '{name_113}'")
            else:
                self.log_test('nomenclature', 'ID 113 exists', False, "ID 113 not found")
            
            # Check deleted IDs should not exist
            deleted_ids = [181, 119, 120, 121, 107, 110, 112, 114, 125, 131, 102, 103, 99, 117, 118, 124, 126, 130, 97, 94, 123, 122, 221]
            found_deleted = [id for id in deleted_ids if id in nomenclature_dict]
            
            if not found_deleted:
                self.log_test('nomenclature', 'Deleted IDs removed', True, "All deleted IDs properly removed")
            else:
                self.log_test('nomenclature', 'Deleted IDs removed', False, f"Found deleted IDs: {found_deleted}")
            
        else:
            self.log_test('nomenclature', 'GET /nomenclature - returns data', False, f"Failed: {data}")
    
    def test_production_api(self):
        """Test production API after migration"""
        print("\n🔍 TESTING PRODUCTION API")
        
        # Test 1: Get all recipes
        success, data, status = self.make_request('GET', '/production/recipes')
        if success and isinstance(data, list):
            recipe_count = len(data)
            
            if recipe_count == 8:
                self.log_test('production', 'GET /production/recipes - 8 recipes', True, f"Found {recipe_count} recipes")
            else:
                self.log_test('production', 'GET /production/recipes - 8 recipes', False, f"Expected 8, got {recipe_count}")
            
            # Check target_product_ids
            expected_targets = [93, 96, 101, 104, 106, 108, 111, 129]
            found_targets = [recipe.get('target_product_id') for recipe in data if recipe.get('target_product_id')]
            
            missing_targets = set(expected_targets) - set(found_targets)
            if not missing_targets:
                self.log_test('production', 'Recipe target_product_ids correct', True, f"All expected targets found: {sorted(found_targets)}")
            else:
                self.log_test('production', 'Recipe target_product_ids correct', False, f"Missing targets: {missing_targets}")
            
            # Test 2: Check specific recipe - "Бастурма з конини" should have target_product_id=108
            basturma_horse_recipe = None
            for recipe in data:
                if 'конин' in recipe.get('name', '').lower():
                    basturma_horse_recipe = recipe
                    break
            
            if basturma_horse_recipe:
                if basturma_horse_recipe.get('target_product_id') == 108:
                    self.log_test('production', '"Бастурма з конини" target_product_id=108', True, 
                                 f"Recipe ID {basturma_horse_recipe.get('id')} correctly targets ID 108")
                else:
                    self.log_test('production', '"Бастурма з конини" target_product_id=108', False, 
                                 f"Expected 108, got {basturma_horse_recipe.get('target_product_id')}")
            else:
                self.log_test('production', '"Бастурма з конини" recipe exists', False, "Recipe not found")
            
            # Test 3: Get specific recipe details
            if data:
                recipe_id = data[0]['id']
                success, recipe_data, status = self.make_request('GET', f'/production/recipes/{recipe_id}')
                if success:
                    self.log_test('production', f'GET /production/recipes/{recipe_id} - details', True, 
                                 f"Recipe has {len(recipe_data.get('steps', []))} steps")
                else:
                    self.log_test('production', f'GET /production/recipes/{recipe_id} - details', False, recipe_data)
        else:
            self.log_test('production', 'GET /production/recipes - returns data', False, f"Failed: {data}")
    
    def test_packaging_api(self):
        """Test packaging API after migration"""
        print("\n🔍 TESTING PACKAGING API")
        
        # Test 1: Get packaging recipes
        success, data, status = self.make_request('GET', '/packaging/recipes')
        if success and isinstance(data, list):
            recipe_count = len(data)
            self.log_test('packaging', 'GET /packaging/recipes - returns data', True, f"Found {recipe_count} packaging recipes")
            
            # Test 2: Check source_product_id=227 for "Курка вагова"
            kurka_vagova_found = False
            for recipe in data:
                if recipe.get('source_product_id') == 227:
                    kurka_vagova_found = True
                    self.log_test('packaging', 'Source product ID 227 used for "Курка вагова"', True, 
                                 f"Recipe: {recipe.get('source_product_name', 'Unknown')}")
                    break
            
            if not kurka_vagova_found:
                # Check if any recipe uses old ID 6
                old_id_6_found = any(recipe.get('source_product_id') == 6 for recipe in data)
                if old_id_6_found:
                    self.log_test('packaging', 'Source product ID 227 used for "Курка вагова"', False, 
                                 "Still using old ID 6 instead of 227")
                else:
                    self.log_test('packaging', 'Source product ID 227 used for "Курка вагова"', False, 
                                 "No packaging recipe found with source_product_id=227")
            
            # Test 3: Verify no deleted nomenclature IDs are used
            all_source_ids = [recipe.get('source_product_id') for recipe in data]
            all_target_ids = [recipe.get('target_product_id') for recipe in data]
            all_used_ids = set(all_source_ids + all_target_ids)
            
            deleted_ids = [181, 119, 120, 121, 107, 110, 112, 114, 125, 131, 102, 103, 99, 117, 118, 124, 126, 130, 97, 94, 123, 122, 221]
            found_deleted_in_packaging = [id for id in deleted_ids if id in all_used_ids]
            
            if not found_deleted_in_packaging:
                self.log_test('packaging', 'No deleted nomenclature IDs in packaging recipes', True, "All references updated")
            else:
                self.log_test('packaging', 'No deleted nomenclature IDs in packaging recipes', False, 
                             f"Found deleted IDs: {found_deleted_in_packaging}")
        else:
            self.log_test('packaging', 'GET /packaging/recipes - returns data', False, f"Failed: {data}")
    
    def test_butchery_api(self):
        """Test butchery API after migration"""
        print("\n🔍 TESTING BUTCHERY API")
        
        # Test 1: Get butchery recipes
        success, data, status = self.make_request('GET', '/butchery/recipes')
        if success and isinstance(data, list):
            recipe_count = len(data)
            self.log_test('butchery', 'GET /butchery/recipes - returns data', True, f"Found {recipe_count} butchery recipes")
            
            # Test 2: Check that outputs are still correct after migration
            total_outputs = 0
            for recipe in data:
                outputs = recipe.get('outputs', [])
                total_outputs += len(outputs)
                
                # Verify no deleted IDs in outputs
                output_ids = [output.get('output_nomenclature_id') for output in outputs]
                deleted_ids = [181, 119, 120, 121, 107, 110, 112, 114, 125, 131, 102, 103, 99, 117, 118, 124, 126, 130, 97, 94, 123, 122, 221]
                found_deleted = [id for id in deleted_ids if id in output_ids]
                
                if found_deleted:
                    self.log_test('butchery', f'Recipe {recipe.get("name")} - no deleted IDs', False, 
                                 f"Found deleted IDs in outputs: {found_deleted}")
                    break
            else:
                self.log_test('butchery', 'No deleted nomenclature IDs in butchery outputs', True, 
                             f"Checked {total_outputs} outputs across {recipe_count} recipes")
            
            # Test 3: Get specific recipe details
            if data:
                recipe_id = data[0]['id']
                success, recipe_data, status = self.make_request('GET', f'/butchery/recipes/{recipe_id}')
                if success:
                    outputs_count = len(recipe_data.get('outputs', []))
                    self.log_test('butchery', f'GET /butchery/recipes/{recipe_id} - details', True, 
                                 f"Recipe has {outputs_count} outputs")
                else:
                    self.log_test('butchery', f'GET /butchery/recipes/{recipe_id} - details', False, recipe_data)
        else:
            self.log_test('butchery', 'GET /butchery/recipes - returns data', False, f"Failed: {data}")
    
    def test_stock_api(self):
        """Test stock API after migration"""
        print("\n🔍 TESTING STOCK API")
        
        # Test 1: Get stock balances
        success, data, status = self.make_request('GET', '/stock/balances')
        if success and isinstance(data, list):
            balance_count = len(data)
            self.log_test('stock', 'GET /stock/balances - returns data', True, f"Found {balance_count} stock balances")
            
            # Test 2: Check that no deleted nomenclature IDs have balances
            nomenclature_ids = [item.get('nomenclature_id') for item in data]
            deleted_ids = [181, 119, 120, 121, 107, 110, 112, 114, 125, 131, 102, 103, 99, 117, 118, 124, 126, 130, 97, 94, 123, 122, 221]
            found_deleted = [id for id in deleted_ids if id in nomenclature_ids]
            
            if not found_deleted:
                self.log_test('stock', 'No balances for deleted nomenclature IDs', True, "All deleted IDs properly cleaned")
            else:
                self.log_test('stock', 'No balances for deleted nomenclature IDs', False, 
                             f"Found balances for deleted IDs: {found_deleted}")
            
            # Test 3: Check specific migrated IDs exist
            key_ids = [108, 233, 113, 109, 105, 227]  # Key migrated/renamed IDs
            found_key_ids = [id for id in key_ids if id in nomenclature_ids]
            
            self.log_test('stock', 'Key migrated IDs present in stock', True, 
                         f"Found {len(found_key_ids)}/{len(key_ids)} key IDs: {found_key_ids}")
        else:
            self.log_test('stock', 'GET /stock/balances - returns data', False, f"Failed: {data}")
        
        # Test 4: Get stock movements
        success, data, status = self.make_request('GET', '/stock/movements?limit=100')
        if success and isinstance(data, list):
            movements_count = len(data)
            self.log_test('stock', 'GET /stock/movements - returns data', True, f"Found {movements_count} recent movements")
            
            # Check that movements don't reference deleted IDs
            if data:
                movement_nomenclature_ids = [item.get('nomenclature_id') for item in data]
                deleted_ids = [181, 119, 120, 121, 107, 110, 112, 114, 125, 131, 102, 103, 99, 117, 118, 124, 126, 130, 97, 94, 123, 122, 221]
                found_deleted = [id for id in deleted_ids if id in movement_nomenclature_ids]
                
                if not found_deleted:
                    self.log_test('stock', 'No movements for deleted nomenclature IDs', True, "All movement references clean")
                else:
                    self.log_test('stock', 'No movements for deleted nomenclature IDs', False, 
                                 f"Found movements for deleted IDs: {found_deleted}")
        else:
            self.log_test('stock', 'GET /stock/movements - returns data', False, f"Failed: {data}")
    
    def run_all_tests(self):
        """Run all backend tests"""
        print(f"🚀 STARTING BACKEND API TESTING")
        print(f"Backend URL: {BACKEND_URL}")
        print("=" * 60)
        
        # Test health endpoint first
        success, data, status = self.make_request('GET', '/health')
        if success:
            print(f"✅ Backend health check passed")
        else:
            print(f"❌ Backend health check failed: {data}")
            return
        
        # Run all test suites
        self.test_nomenclature_api()
        self.test_production_api()
        self.test_packaging_api()
        self.test_butchery_api()
        self.test_stock_api()
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_passed = 0
        total_failed = 0
        
        for category, results in self.results.items():
            passed = results['passed']
            failed = results['failed']
            total = passed + failed
            
            total_passed += passed
            total_failed += failed
            
            status = "✅" if failed == 0 else "❌"
            print(f"{status} {category.upper()}: {passed}/{total} passed")
        
        print("-" * 60)
        print(f"OVERALL: {total_passed}/{total_passed + total_failed} tests passed")
        
        if self.critical_issues:
            print("\n🚨 CRITICAL ISSUES FOUND:")
            for issue in self.critical_issues:
                print(f"  • {issue}")
        else:
            print("\n🎉 ALL TESTS PASSED - MIGRATION SUCCESSFUL!")

if __name__ == "__main__":
    tester = BackendTester()
    tester.run_all_tests()