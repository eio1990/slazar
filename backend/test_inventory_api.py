"""
Testovyi script dlia perevirky inventory API
"""
# -*- coding: utf-8 -*-

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8001/api"

def test_inventory_api():
    print("=" * 60)
    print("ТЕСТУВАННЯ INVENTORY API")
    print("=" * 60)

    # 1. Створення сесії інвентаризації (full)
    print("\n1. Створення повної інвентаризації...")
    try:
        response = requests.post(f"{BASE_URL}/inventory/sessions", json={
            "session_type": "full",
            "idempotency_key": f"test-inv-{datetime.now().timestamp()}",
            "metadata": {"test": True, "created_by": "test_script"}
        })
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            session_data = response.json()
            session_id = session_data['id']
            print(f"✅ Сесія створена: ID={session_id}")
            print(f"   Session number: {session_data.get('session_number', 'N/A')}")
            print(f"   Type: {session_data['session_type']}")
            print(f"   Status: {session_data['status']}")
        else:
            print(f"❌ Помилка: {response.text}")
            return
    except Exception as e:
        print(f"❌ Помилка підключення: {e}")
        print("\nПереконайтесь що backend запущений:")
        print("  cd C:\\slazar\\backend")
        print("  python main.py")
        return

    # 2. Отримання інформації про сесію
    print(f"\n2. Отримання інформації про сесію {session_id}...")
    response = requests.get(f"{BASE_URL}/inventory/sessions/{session_id}")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"✅ Інформація отримана")
        print(f"   {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    else:
        print(f"❌ Помилка: {response.text}")

    # 3. Отримання списку позицій для інвентаризації
    print(f"\n3. Отримання позицій інвентаризації...")
    response = requests.get(f"{BASE_URL}/inventory/sessions/{session_id}/items")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        items = response.json()
        print(f"✅ Знайдено {len(items)} позицій")
        if len(items) > 0:
            print(f"   Перші 3 позиції:")
            for item in items[:3]:
                print(f"   - {item['nomenclature_name']}: {item['system_quantity']} {item['unit']}")
    else:
        print(f"❌ Помилка: {response.text}")

    # 4. Завершення інвентаризації з тестовими даними
    print(f"\n4. Завершення інвентаризації...")

    # Візьмемо перші 5 позицій і змінимо їм кількість
    test_items = []
    if len(items) >= 5:
        for idx, item in enumerate(items[:5]):
            # Додаємо різницю: +1, -1, 0, +2, -2
            differences = [1, -1, 0, 2, -2]
            actual_qty = float(item['system_quantity']) + differences[idx]
            if actual_qty < 0:
                actual_qty = 0

            test_items.append({
                "nomenclature_id": item['nomenclature_id'],
                "actual_quantity": actual_qty
            })
            print(f"   {item['nomenclature_name']}: {item['system_quantity']} → {actual_qty} ({differences[idx]:+d})")

    response = requests.post(f"{BASE_URL}/inventory/sessions/{session_id}/complete", json={
        "items": test_items,
        "idempotency_key": f"test-complete-{datetime.now().timestamp()}"
    })

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Інвентаризацію завершено")
        print(f"   Коригувань створено: {result.get('adjustments_count', 0)}")
        print(f"   {result.get('message', '')}")
    else:
        print(f"❌ Помилка: {response.text}")

    # 5. Отримання списку всіх сесій
    print(f"\n5. Отримання списку всіх сесій...")
    response = requests.get(f"{BASE_URL}/inventory/sessions", params={"limit": 10})
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        sessions = response.json()
        print(f"✅ Знайдено {len(sessions)} сесій")
        for s in sessions[:3]:
            print(f"   - {s.get('session_number', 'N/A')}: {s['session_type']} ({s['status']})")
    else:
        print(f"❌ Помилка: {response.text}")

    print("\n" + "=" * 60)
    print("ТЕСТУВАННЯ ЗАВЕРШЕНО")
    print("=" * 60)

if __name__ == "__main__":
    test_inventory_api()
