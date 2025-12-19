"""
Тест повного циклу калькуляції собівартості:
Розділка → Виробництво → Фасування

Перевіряє:
1. Встановлення початкової ціни сировини
2. Калькуляція розділки з урахуванням СТЕКУ
3. Калькуляція виробництва з усушкою
4. Калькуляція фасування з матеріалами
5. Передачу вартості між етапами
"""
# -*- coding: utf-8 -*-

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8001/api"

def print_section(title):
    """Вивести розділ"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_cost_info(data, title=""):
    """Вивести інформацію про собівартість"""
    if title:
        print(f"\n📊 {title}:")

    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, (int, float)):
                print(f"   {key}: {value:.2f}")
            else:
                print(f"   {key}: {value}")
    else:
        print(f"   {data}")

def test_full_cycle():
    """Тестування повного циклу калькуляції"""

    print_section("ТЕСТ ПОВНОГО ЦИКЛУ КАЛЬКУЛЯЦІЇ СОБІВАРТОСТІ")

    # ========================================================================
    # КРОК 1: Встановлення початкової ціни сировини
    # ========================================================================
    print_section("КРОК 1: Встановлення початкової ціни сировини")

    # Знайдемо говядину 1 сорт (ID 1)
    beef_id = 1
    beef_cost = 150.00  # грн/кг

    print(f"\n📦 Встановлюємо ціну для говядини 1 сорт (ID {beef_id}): {beef_cost} грн/кг")

    response = requests.post(f"{BASE_URL}/costing/set-cost/{beef_id}", json={
        "cost_per_kg": beef_cost,
        "quantity": 100.0  # початковий залишок 100 кг
    })

    if response.status_code == 200:
        cost_data = response.json()
        print(f"✅ Ціну встановлено:")
        print_cost_info(cost_data)
    else:
        print(f"❌ Помилка: {response.text}")
        return

    # ========================================================================
    # КРОК 2: Знаходимо останню операцію розділки
    # ========================================================================
    print_section("КРОК 2: Калькуляція розділки з урахуванням СТЕКУ")

    response = requests.get(f"{BASE_URL}/butchery/operations", params={"limit": 1})

    if response.status_code != 200 or not response.json():
        print("❌ Немає операцій розділки в базі")
        print("\nСтворіть операцію розділки в додатку та повторіть тест")
        return

    butchery_op = response.json()[0]
    operation_id = butchery_op['id']

    print(f"\n🔪 Знайдено операцію розділки ID {operation_id}")
    print(f"   Рецепт: {butchery_op.get('recipe_name', 'N/A')}")
    print(f"   Вага входу: {butchery_op.get('input_weight', 'N/A')} кг")
    print(f"   Статус: {butchery_op.get('status', 'N/A')}")

    # Якщо операція завершена, перерахуємо собівартість
    if butchery_op.get('status') == 'completed':
        print(f"\n🔢 Розрахунок собівартості розділки...")

        response = requests.post(f"{BASE_URL}/costing/calculate-butchery/{operation_id}")

        if response.status_code == 200:
            butchery_cost = response.json()
            print(f"✅ Калькуляцію виконано:")
            print_cost_info({
                "Вхід (кг)": butchery_cost['input_weight'],
                "Вартість входу (грн/кг)": butchery_cost['input_cost_per_kg'],
                "Загальна вартість входу (грн)": butchery_cost['input_total_cost'],
                "Вихід напівфабрикатів (кг)": butchery_cost['semifinished_weight'],
                "Відходи (кг)": butchery_cost['waste_weight'],
                "СТЕК - усушка (кг)": butchery_cost['shrinkage_weight'],
                "СТЕК - усушка (%)": butchery_cost['shrinkage_percent'],
                "Скоригована вартість (грн/кг)": butchery_cost['adjusted_cost_per_kg'],
                "Збільшення вартості (%)": round(
                    (butchery_cost['adjusted_cost_per_kg'] / butchery_cost['input_cost_per_kg'] - 1) * 100, 2
                )
            })
        else:
            print(f"❌ Помилка розрахунку: {response.text}")
            return
    else:
        print("⚠️ Операція розділки не завершена. Завершіть її в додатку.")
        return

    # ========================================================================
    # КРОК 3: Знаходимо останню виробничу партію
    # ========================================================================
    print_section("КРОК 3: Калькуляція виробництва з усушкою")

    response = requests.get(f"{BASE_URL}/production/batches", params={"limit": 1})

    if response.status_code != 200 or not response.json():
        print("❌ Немає виробничих партій в базі")
        print("\nСтворіть партію виробництва в додатку та повторіть тест")
        return

    batch = response.json()[0]
    batch_id = batch['id']

    print(f"\n🏭 Знайдено виробничу партію ID {batch_id}")
    print(f"   Рецепт: {batch.get('recipe_name', 'N/A')}")
    print(f"   Початкова вага: {batch.get('initial_weight', 'N/A')} кг")
    print(f"   Поточна вага: {batch.get('current_weight', 'N/A')} кг")
    print(f"   Статус: {batch.get('status', 'N/A')}")

    # Якщо партія завершена, перерахуємо собівартість
    if batch.get('status') == 'completed':
        print(f"\n🔢 Розрахунок собівартості виробництва...")

        response = requests.post(f"{BASE_URL}/costing/calculate-batch/{batch_id}")

        if response.status_code == 200:
            batch_cost = response.json()
            print(f"✅ Калькуляцію виконано:")
            print_cost_info({
                "Початкова вага (кг)": batch_cost['initial_weight'],
                "Фінальна вага (кг)": batch_cost['final_weight'],
                "Усушка (кг)": batch_cost['shrinkage_weight'],
                "Усушка (%)": batch_cost['shrinkage_percent'],
                "Вартість сировини (грн)": batch_cost['raw_materials_cost'],
                "Вартість солі (грн)": batch_cost['salt_cost'],
                "Вартість спецій (грн)": batch_cost['spices_cost'],
                "Вартість оболонок (грн)": batch_cost['casings_cost'],
                "Інші матеріали (грн)": batch_cost['other_materials_cost'],
                "Загальна вартість (грн)": batch_cost['total_cost'],
                "Собівартість (грн/кг)": batch_cost['cost_per_kg']
            })
        else:
            print(f"❌ Помилка розрахунку: {response.text}")
            return
    else:
        print("⚠️ Виробнича партія не завершена. Завершіть її в додатку.")
        return

    # ========================================================================
    # КРОК 4: Знаходимо останню сесію фасування
    # ========================================================================
    print_section("КРОК 4: Калькуляція фасування з матеріалами")

    response = requests.get(f"{BASE_URL}/packaging/sessions", params={"limit": 1})

    if response.status_code != 200 or not response.json():
        print("❌ Немає сесій фасування в базі")
        print("\nСтворіть сесію фасування в додатку та повторіть тест")
        return

    session = response.json()[0]
    session_id = session['id']

    print(f"\n📦 Знайдено сесію фасування ID {session_id}")
    print(f"   Вихідний продукт: {session.get('source_nomenclature_name', 'N/A')}")
    print(f"   Початкова вага: {session.get('initial_weight', 'N/A')} кг")
    print(f"   Статус: {session.get('status', 'N/A')}")

    # Якщо сесія завершена, перерахуємо собівартість
    if session.get('status') == 'completed':
        print(f"\n🔢 Розрахунок собівартості фасування...")

        response = requests.post(f"{BASE_URL}/costing/calculate-packaging/{session_id}")

        if response.status_code == 200:
            packaging_cost = response.json()
            print(f"✅ Калькуляцію виконано:")
            print_cost_info({
                "Вага продукту (кг)": packaging_cost['source_weight'],
                "Вартість продукту (грн)": packaging_cost['source_product_cost'],
                "Вартість матеріалів (грн)": packaging_cost['packaging_materials_cost'],
                "Відходи (кг)": packaging_cost['waste_weight'],
                "Вартість відходів (грн)": packaging_cost['waste_cost'],
                "Кількість упаковок (шт)": packaging_cost['packed_quantity'],
                "Загальна вартість (грн)": packaging_cost['total_cost'],
                "Собівартість за упаковку (грн/шт)": packaging_cost['cost_per_unit']
            })
        else:
            print(f"❌ Помилка розрахунку: {response.text}")
            return
    else:
        print("⚠️ Сесія фасування не завершена. Завершіть її в додатку.")
        return

    # ========================================================================
    # ПІДСУМОК
    # ========================================================================
    print_section("ПІДСУМОК ЦИКЛУ КАЛЬКУЛЯЦІЇ")

    print(f"""
📊 Передача вартості через весь цикл виробництва:

1️⃣ СИРОВИНА (говядина):
   💰 Початкова ціна: {beef_cost:.2f} грн/кг

2️⃣ РОЗДІЛКА:
   ➕ СТЕК (усушка): +{butchery_cost['shrinkage_percent']:.2f}%
   💰 Вартість напівфабрикату: {butchery_cost['adjusted_cost_per_kg']:.2f} грн/кг
   📈 Збільшення: +{((butchery_cost['adjusted_cost_per_kg'] / beef_cost - 1) * 100):.2f}%

3️⃣ ВИРОБНИЦТВО:
   ➕ Сіль, спеції, оболонки
   ➕ Усушка при виробництві: {batch_cost['shrinkage_percent']:.2f}%
   💰 Вартість готової продукції: {batch_cost['cost_per_kg']:.2f} грн/кг
   📈 Збільшення від сировини: +{((batch_cost['cost_per_kg'] / beef_cost - 1) * 100):.2f}%

4️⃣ ФАСУВАННЯ:
   ➕ Пакети, етикетки, лотки
   💰 Вартість SKU: {packaging_cost['cost_per_unit']:.2f} грн/шт

🎯 РЕЗУЛЬТАТ: Повний ланцюжок калькуляції від сировини до готового SKU!
    """)

    print_section("ТЕСТ ЗАВЕРШЕНО УСПІШНО ✅")

if __name__ == "__main__":
    try:
        test_full_cycle()
    except Exception as e:
        print(f"\n❌ Критична помилка: {str(e)}")
        import traceback
        traceback.print_exc()
