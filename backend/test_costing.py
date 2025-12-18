"""
Тестовий скрипт для перевірки калькуляції собівартості
"""
# -*- coding: utf-8 -*-

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import pyodbc
from database import get_db_connection

def test_costing():
    print("=" * 60)
    print("ТЕСТУВАННЯ КАЛЬКУЛЯЦІЇ СОБІВАРТОСТІ")
    print("=" * 60)

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # 1. Створити тестову собівартість для яловичини
        print("\n1. Створення тестової собівартості для сировини...")
        cursor.execute("""
            -- Яловичина вищого сорту (ID=1)
            IF EXISTS (SELECT 1 FROM nomenclature_costs WHERE nomenclature_id = 1)
                UPDATE nomenclature_costs
                SET weighted_avg_cost = 150.00,
                    last_purchase_cost = 150.00,
                    total_quantity = 100.0,
                    total_value = 15000.0
                WHERE nomenclature_id = 1
            ELSE
                INSERT INTO nomenclature_costs (
                    nomenclature_id, weighted_avg_cost, last_purchase_cost,
                    total_quantity, total_value
                )
                VALUES (1, 150.00, 150.00, 100.0, 15000.0)
        """)
        conn.commit()
        print("✅ Собівартість яловичини встановлено: 150 грн/кг")

        # 2. Перевірити останню операцію розділки
        print("\n2. Пошук останньої операції розділки...")
        cursor.execute("""
            SELECT TOP 1
                id, operation_number, input_weight, status
            FROM butchery_operations
            ORDER BY created_at DESC
        """)

        op_row = cursor.fetchone()
        if not op_row:
            print("❌ Не знайдено операцій розділки")
            print("\nСпочатку створіть операцію розділки через frontend або API")
            return

        operation_id = op_row[0]
        operation_number = op_row[1]
        input_weight = float(op_row[2])
        status = op_row[3]

        print(f"✅ Знайдено операцію: {operation_number}")
        print(f"   ID: {operation_id}")
        print(f"   Вхідна вага: {input_weight} кг")
        print(f"   Статус: {status}")

        # 3. Перевірити чи є калькуляція
        print("\n3. Перевірка існуючої калькуляції...")
        cursor.execute("""
            SELECT
                input_cost_per_kg, adjusted_cost_per_kg,
                shrinkage_weight, shrinkage_percent,
                total_output_weight, semifinished_weight, waste_weight
            FROM butchery_operation_costs
            WHERE operation_id = ?
        """, (operation_id,))

        cost_row = cursor.fetchone()
        if cost_row:
            print("✅ Калькуляція знайдена:")
            print(f"   Вхідна собівартість: {cost_row[0]:.2f} грн/кг")
            print(f"   Скоригована собівартість: {cost_row[1]:.2f} грн/кг")
            print(f"   Стек: {cost_row[2]:.2f} кг ({cost_row[3]:.2f}%)")
            print(f"   Загальний вихід: {cost_row[4]:.2f} кг")
            print(f"   Полуфабрикати: {cost_row[5]:.2f} кг")
            print(f"   Відходи: {cost_row[6]:.2f} кг")

            if cost_row[2] > 0:
                print(f"\n   ⚠️  ВИЯВЛЕНО СТЕК!")
                cost_increase = ((cost_row[1] - cost_row[0]) / cost_row[0] * 100) if cost_row[0] > 0 else 0
                print(f"   Собівартість зросла на {cost_increase:.2f}%")
        else:
            print("ℹ️  Калькуляція ще не створена")
            print("   Вона створюється автоматично при завершенні операції розділки")

        # 4. Перевірити виходи операції
        print("\n4. Перевірка виходів операції...")
        cursor.execute("""
            SELECT
                n.name,
                n.nomenclature_type,
                boo.actual_weight,
                nc.weighted_avg_cost
            FROM butchery_operation_outputs boo
            JOIN nomenclature n ON n.id = boo.output_nomenclature_id
            LEFT JOIN nomenclature_costs nc ON nc.nomenclature_id = boo.output_nomenclature_id
            WHERE boo.operation_id = ?
            ORDER BY n.nomenclature_type, n.name
        """, (operation_id,))

        outputs = cursor.fetchall()
        if outputs:
            print(f"✅ Знайдено {len(outputs)} виходів:")
            for output in outputs:
                name = output[0]
                nom_type = output[1]
                weight = float(output[2])
                avg_cost = float(output[3]) if output[3] else 0.0

                type_label = {
                    'semi-finished': 'Полуфабрикат',
                    'liquid-waste': 'Стек (вода)',
                    'solid-waste': 'Відходи'
                }.get(nom_type, nom_type)

                print(f"\n   {name} ({type_label})")
                print(f"   Вага: {weight:.2f} кг")
                if avg_cost > 0:
                    print(f"   Собівартість: {avg_cost:.2f} грн/кг")
                    print(f"   Загальна вартість: {weight * avg_cost:.2f} грн")
        else:
            print("ℹ️  Виходи ще не зафіксовані")

    print("\n" + "=" * 60)
    print("ТЕСТУВАННЯ ЗАВЕРШЕНО")
    print("=" * 60)

if __name__ == "__main__":
    test_costing()
