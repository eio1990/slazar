"""
Скрипт для масового тестування операцій
Створює приходи (200+) та розходи (50+) для всіх номенклатур
"""
import requests
import time
from datetime import datetime

API_URL = "https://meat-tracker-6.preview.emergentagent.com/api"

def get_nomenclature():
    """Отримати всі номенклатури"""
    response = requests.get(f"{API_URL}/nomenclature")
    response.raise_for_status()
    return response.json()

def create_receipt(nomenclature_id, nomenclature_name, quantity, price):
    """Створити прихід"""
    payload = {
        "type": "receipt",
        "nomenclature_id": nomenclature_id,
        "quantity": quantity,
        "price": price,
        "notes": f"Mass test receipt for {nomenclature_name}"
    }
    response = requests.post(f"{API_URL}/operations", json=payload)
    return response.status_code == 200

def create_expense(nomenclature_id, nomenclature_name, quantity):
    """Створити розхід"""
    payload = {
        "type": "expense",
        "nomenclature_id": nomenclature_id,
        "quantity": quantity,
        "notes": f"Mass test expense for {nomenclature_name}"
    }
    response = requests.post(f"{API_URL}/operations", json=payload)
    return response.status_code == 200

def check_balance(nomenclature_id):
    """Перевірити баланс"""
    response = requests.get(f"{API_URL}/stock/balances")
    if response.status_code == 200:
        balances = response.json()
        for balance in balances:
            if balance['nomenclature_id'] == nomenclature_id:
                return balance['quantity']
    return None

def main():
    print("="*80)
    print("МАСОВЕ ТЕСТУВАННЯ ОПЕРАЦІЙ")
    print("="*80)
    
    # Отримати всі номенклатури
    print("\n[1/4] Отримання списку номенклатур...")
    nomenclature = get_nomenclature()
    print(f"✅ Отримано {len(nomenclature)} позицій")
    
    # Групувати за категоріями
    categories = {}
    for item in nomenclature:
        cat = item.get('category', 'Інші')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    print(f"\nКатегорії:")
    for cat, items in categories.items():
        print(f"  - {cat}: {len(items)} позицій")
    
    # ЕТАП 1: МАСОВІ ПРИХОДИ
    print("\n" + "="*80)
    print("[2/4] СТВОРЕННЯ ПРИХОДІВ (200+ одиниць для кожної позиції)")
    print("="*80)
    
    receipts_success = 0
    receipts_failed = 0
    
    for idx, item in enumerate(nomenclature, 1):
        item_id = item['id']
        item_name = item['name']
        item_cat = item.get('category', 'Інші')
        
        # Різна кількість для різних товарів
        quantity = 200 + (idx * 10)
        price = 100.00
        
        try:
            success = create_receipt(item_id, item_name, quantity, price)
            if success:
                print(f"✅ [{idx}/{len(nomenclature)}] {item_cat} | {item_name}: {quantity} од.")
                receipts_success += 1
            else:
                print(f"❌ [{idx}/{len(nomenclature)}] {item_cat} | {item_name}: FAILED")
                receipts_failed += 1
        except Exception as e:
            print(f"❌ [{idx}/{len(nomenclature)}] {item_cat} | {item_name}: ERROR - {e}")
            receipts_failed += 1
        
        # Пауза між запитами
        time.sleep(0.1)
        
        # Проміжний звіт кожні 50 позицій
        if idx % 50 == 0:
            print(f"\n--- Проміжний результат: {receipts_success} успішно, {receipts_failed} помилок ---\n")
    
    print(f"\n📊 Приходи: {receipts_success} успішно / {receipts_failed} помилок / {len(nomenclature)} всього")
    
    # ЕТАП 2: ПЕРЕВІРКА ЗАЛИШКІВ
    print("\n" + "="*80)
    print("[3/4] ПЕРЕВІРКА ЗАЛИШКІВ")
    print("="*80)
    
    response = requests.get(f"{API_URL}/stock/balances")
    if response.status_code == 200:
        balances = response.json()
        print(f"✅ Знайдено {len(balances)} позицій із залишками")
        
        # Показати перші 10
        print("\nПерші 10 залишків:")
        for balance in balances[:10]:
            nom_id = balance['nomenclature_id']
            qty = balance['quantity']
            nom = next((n for n in nomenclature if n['id'] == nom_id), None)
            name = nom['name'] if nom else f"ID {nom_id}"
            print(f"  - {name}: {qty} од.")
    
    # ЕТАП 3: МАСОВІ РОЗХОДИ
    print("\n" + "="*80)
    print("[4/4] СТВОРЕННЯ РОЗХОДІВ (50 одиниць для кожної позиції)")
    print("="*80)
    
    expenses_success = 0
    expenses_failed = 0
    
    for idx, item in enumerate(nomenclature, 1):
        item_id = item['id']
        item_name = item['name']
        item_cat = item.get('category', 'Інші')
        quantity = 50
        
        try:
            success = create_expense(item_id, item_name, quantity)
            if success:
                print(f"✅ [{idx}/{len(nomenclature)}] {item_cat} | {item_name}: {quantity} од.")
                expenses_success += 1
            else:
                print(f"❌ [{idx}/{len(nomenclature)}] {item_cat} | {item_name}: FAILED")
                expenses_failed += 1
        except Exception as e:
            print(f"❌ [{idx}/{len(nomenclature)}] {item_cat} | {item_name}: ERROR - {e}")
            expenses_failed += 1
        
        time.sleep(0.1)
        
        if idx % 50 == 0:
            print(f"\n--- Проміжний результат: {expenses_success} успішно, {expenses_failed} помилок ---\n")
    
    print(f"\n📊 Розходи: {expenses_success} успішно / {expenses_failed} помилок / {len(nomenclature)} всього")
    
    # ФІНАЛЬНИЙ ЗВІТ
    print("\n" + "="*80)
    print("ФІНАЛЬНИЙ ЗВІТ")
    print("="*80)
    
    total_operations = receipts_success + expenses_success
    total_expected = len(nomenclature) * 2
    
    print(f"\nВсього номенклатур: {len(nomenclature)}")
    print(f"Очікувалось операцій: {total_expected} ({len(nomenclature)} приходів + {len(nomenclature)} розходів)")
    print(f"\nПРИХОДИ:")
    print(f"  ✅ Успішно: {receipts_success}")
    print(f"  ❌ Помилок: {receipts_failed}")
    print(f"\nРОЗХОДИ:")
    print(f"  ✅ Успішно: {expenses_success}")
    print(f"  ❌ Помилок: {expenses_failed}")
    print(f"\nВСЬОГО ОПЕРАЦІЙ: {total_operations} / {total_expected}")
    
    if total_operations == total_expected:
        print("\n🎉 ТЕСТУВАННЯ ЗАВЕРШЕНО УСПІШНО!")
    else:
        print(f"\n⚠️  ТЕСТУВАННЯ ЗАВЕРШЕНО З ПОМИЛКАМИ: {total_expected - total_operations} операцій не створено")
    
    # Фінальна перевірка залишків
    print("\nФінальні залишки (перші 10):")
    response = requests.get(f"{API_URL}/stock/balances")
    if response.status_code == 200:
        balances = response.json()
        for balance in balances[:10]:
            nom_id = balance['nomenclature_id']
            qty = balance['quantity']
            nom = next((n for n in nomenclature if n['id'] == nom_id), None)
            name = nom['name'] if nom else f"ID {nom_id}"
            print(f"  - {name}: {qty} од.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ КРИТИЧНА ПОМИЛКА: {e}")
        import traceback
        traceback.print_exc()
