"""
Финальная миграция номенклатуры на основе утвержденного списка пользователя
"""
from database import get_db_connection
from dotenv import load_dotenv
import sys

load_dotenv()

# ============================================================================
# ФИНАЛЬНЫЙ СПИСОК ОТ ПОЛЬЗОВАТЕЛЯ
# ============================================================================

# 1. СЫРЬЕ - М'ЯСО (13 позиций)
RAW_MEAT_FINAL = {
    8: "Індик філе (кг)",
    11: "Кінський жир (кг)",
    9: "Конина вищій ґатунок (кг)",
    218: "Конина другий ґатунок (кг)",
    10: "Конина перший ґатунок (кг)",
    12: "Конина туша (кг)",
    7: "Курка стегно (кг)",
    6: "Курка філе (кг)",
    5: "Свинина биток (кг)",
    2: "Яловичина вищій ґатунок (кг)",
    4: "Яловичина другий ґатунок (кг)",
    3: "Яловичина перший ґатунок (кг)",
    1: "Яловичина туша (кг)"
}

# 2. НАПІВФАБРИКАТИ (13 позиций)
SEMIFABRICATES_FINAL = {
    211: "Індичка для бастурми (кг)",
    212: "Індичка для суджука (кг)",
    202: "Конина для бастурми (кг)",
    204: "Конина для махан (кг)",
    203: "Конина для пластин (кг)",
    206: "Конина для суджук (кг)",
    210: "Курка для суджука (кг)",
    209: "Курка оброблена (кг)",
    207: "Свинина для банкетної (кг)",
    208: "Свинина для суджука (кг)",
    199: "Яловичина для бастурми (кг)",
    200: "Яловичина для пластин (кг)",
    201: "Яловичина для суджука (кг)"
}

# 3. PRODUCTION OUTPUTS (весовые) - 10 позиций
PRODUCTION_OUTPUTS_FINAL = {
    180: "Банкетна (кг)",
    93: "Бастурма (кг)",
    108: "Конина (кг)",  # RENAME from "Бастурма з конини"
    233: "Індичка (кг)",  # RENAME from "Індичка вагова"
    104: "Курка сиров'ялена (кг)",
    113: "Курхан (кг)",  # RENAME from "Курхан ваговий"
    111: "Махан (кг)",
    132: "Пластина конина (кг)",
    129: "Пластина яловичина (кг)",
    96: "Суджук (кг)"
}

# 4. PACKAGING OUTPUTS (расфасованные SKU) - 31 позиция
PACKAGING_OUTPUTS_FINAL = {
    100: "Асорті бастурма та суджук 100г вакуум (од)",
    179: "Банкетна вагова (кг)",
    167: "Банкетна 50г вакуум (од)",
    168: "Банкетна 50г скін (од)",
    169: "Банкетна 60г скін (од)",
    175: "Бастурма вагова (кг)",
    95: "Бастурма 50г вакуум (од)",
    164: "Бастурма 50г скін (од)",
    165: "Бастурма 60г скін (од)",
    94: "Бастурма 80г вакуум (од)",
    184: "Конина вагова (кг)",
    109: "Конина 80г вакуум (од)",  # UPDATE from "Бастурма з конини 80г вакуум"
    172: "Конина 50г вакуум (од)",
    173: "Конина 50г скін (од)",
    # 233: "Індичка вагова (кг)",  # This is production output, not packaging
    115: "Індичка 50г вакуум (од)",
    127: "Індичка 50г скін (од)",
    128: "Індичка 60г скін (од)",
    # NEW: "Курка вагова (кг)" - нужно создать
    105: "Курка 40г вакуум (од)",  # UPDATE from "Курка сиров'ялена 40г вакуум"
    177: "Махан ваговий (кг)",
    116: "Махан 50г вакуум (од)",
    174: "Махан 50г скін (од)",
    132: "Пластина конина (кг)",  # Duplicate with production
    129: "Пластина яловичина (кг)",  # Duplicate with production
    171: "Пластина 50г вакуум (од)",
    176: "Суджук ваговий (кг)",
    98: "Суджук 50г вакуум (од)",
    166: "Суджук 50г скін (од)"
}

def execute_migration():
    print("="*80)
    print("ФИНАЛЬНАЯ МИГРАЦИЯ НОМЕНКЛАТУРЫ")
    print("="*80)
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # ========================================================================
        # STEP 0: ОБЪЕДИНЕНИЕ ДУБЛИКАТОВ
        # ========================================================================
        print("\n[STEP 0] ОБЪЕДИНЕНИЕ ДУБЛИКАТОВ")
        print("-" * 80)
        
        # ID 108 "Бастурма з конини" и ID 178 "Конина" - это дубликаты
        # По финальному списку пользователя должен остаться ID 108
        # ID 178 используется в packaging_recipes, нужно обновить ссылки
        
        print("\n  Обработка: ID 108 'Бастурма з конини' и ID 178 'Конина'")
        
        # Проверим существование
        cursor.execute("SELECT id, name FROM nomenclature WHERE id IN (108, 178)")
        existing = cursor.fetchall()
        print(f"  Найдено: {len(existing)} записей")
        for row in existing:
            print(f"    ID {row[0]}: {row[1]}")
        
        if len(existing) == 2:
            # Обновим все ссылки: 178 → 108
            print("\n  Обновление packaging_recipes: source_product_id 178 → 108")
            cursor.execute("""
                UPDATE packaging_recipes
                SET source_product_id = 108
                WHERE source_product_id = 178
            """)
            affected = cursor.rowcount
            print(f"    Обновлено записей: {affected}")
            
            print("\n  Обновление stock_movements: nomenclature_id 178 → 108")
            cursor.execute("""
                UPDATE stock_movements
                SET nomenclature_id = 108
                WHERE nomenclature_id = 178
            """)
            affected = cursor.rowcount
            print(f"    Обновлено записей: {affected}")
            
            print("\n  Обновление stock_balances: nomenclature_id 178 → 108")
            cursor.execute("""
                SELECT nomenclature_id, quantity 
                FROM stock_balances 
                WHERE nomenclature_id IN (108, 178)
            """)
            balances = cursor.fetchall()
            print(f"    Найдено балансов: {len(balances)}")
            
            if len(balances) == 2:
                # Есть балансы для обоих ID, нужно объединить
                bal_108 = next((b for b in balances if b[0] == 108), None)
                bal_178 = next((b for b in balances if b[0] == 178), None)
                if bal_108 and bal_178:
                    new_balance = bal_108[1] + bal_178[1]
                    print(f"    Объединение балансов: {bal_108[1]} + {bal_178[1]} = {new_balance}")
                    cursor.execute("""
                        UPDATE stock_balances
                        SET quantity = ?
                        WHERE nomenclature_id = ?
                    """, new_balance, 108)
                    cursor.execute("""
                        DELETE FROM stock_balances WHERE nomenclature_id = ?
                    """, 178)
            elif len(balances) == 1 and balances[0][0] == 178:
                # Есть только баланс для 178, обновим на 108
                cursor.execute("""
                    UPDATE stock_balances
                    SET nomenclature_id = 108
                    WHERE nomenclature_id = 178
                """)
            
            # Теперь можно удалить ID 178
            print(f"\n  Удаление ID 178 'Конина'")
            cursor.execute("DELETE FROM nomenclature WHERE id = 178")
            print(f"    ✅ Удалено")
            
            conn.commit()
        elif len(existing) == 1 and existing[0][0] == 108:
            print("  ✅ ID 178 уже удален, ID 108 существует")
        else:
            print("  ⚠️  Неожиданная ситуация, пропускаем")
        
        # Аналогично для других возможных дубликатов
        # Проверим ID 184 "Конина вагова" - может быть дубликатом
        cursor.execute("SELECT id, name FROM nomenclature WHERE name LIKE 'Конина вагов%'")
        konina_vagova = cursor.fetchone()
        if konina_vagova:
            kid = konina_vagova[0]
            print(f"\n  Найден: ID {kid} 'Конина вагова'")
            # Это packaging SKU, не production output, оставляем как есть
        
        # ========================================================================
        # STEP 1: ПЕРЕИМЕНОВАНИЯ
        # ========================================================================
        print("\n[STEP 1] ПЕРЕИМЕНОВАНИЯ")
        print("-" * 80)
        
        renames = {
            108: ("Бастурма з конини", "Конина"),
            233: ("Індичка вагова", "Індичка"),
            113: ("Курхан ваговий", "Курхан"),
            109: ("Бастурма з конини 80г вакуум", "Конина 80г вакуум"),
            105: ("Курка сиров'ялена 40г вакуум", "Курка 40г вакуум")
        }
        
        for id, (old_name, new_name) in renames.items():
            cursor.execute("SELECT name FROM nomenclature WHERE id = ?", id)
            current = cursor.fetchone()
            if current:
                print(f"  ID {id}: '{current[0]}' → '{new_name}'")
                cursor.execute("UPDATE nomenclature SET name = ? WHERE id = ?", new_name, id)
            else:
                print(f"  ⚠️  ID {id} не найден")
        
        conn.commit()
        print(f"\n✅ Переименования завершены")
        
        # ========================================================================
        # STEP 2: СОЗДАНИЕ НОВЫХ ПРОДУКТОВ
        # ========================================================================
        print("\n[STEP 2] СОЗДАНИЕ НОВЫХ ПРОДУКТОВ")
        print("-" * 80)
        
        # Проверим, существует ли уже "Курка вагова"
        cursor.execute("SELECT id, name FROM nomenclature WHERE name LIKE '%урка вагов%'")
        existing = cursor.fetchall()
        if existing:
            print(f"  ⚠️  'Курка вагова' уже существует:")
            for row in existing:
                print(f"      ID {row[0]}: {row[1]}")
        else:
            # Создать новый продукт
            cursor.execute("""
                INSERT INTO nomenclature (name, category, unit, precision_digits)
                VALUES (?, ?, ?, ?)
            """, "Курка вагова", "Готова продукція", "кг", 2)
            cursor.execute("SELECT @@IDENTITY")
            new_id = cursor.fetchone()[0]
            print(f"  ✅ Создан продукт 'Курка вагова' с ID {new_id}")
            conn.commit()
        
        # ========================================================================
        # STEP 3: УДАЛЕНИЕ ДУБЛИКАТОВ И УСТАРЕВШИХ ПОЗИЦИЙ
        # ========================================================================
        print("\n[STEP 3] АНАЛИЗ И УДАЛЕНИЕ ДУБЛИКАТОВ/УСТАРЕВШИХ")
        print("-" * 80)
        
        # Собираем все ID из финального списка
        all_final_ids = set()
        all_final_ids.update(RAW_MEAT_FINAL.keys())
        all_final_ids.update(SEMIFABRICATES_FINAL.keys())
        all_final_ids.update(PRODUCTION_OUTPUTS_FINAL.keys())
        all_final_ids.update(PACKAGING_OUTPUTS_FINAL.keys())
        
        print(f"  Всего позиций в финальном списке: {len(all_final_ids)}")
        
        # Получим все текущие продукты категории "Готова продукція"
        cursor.execute("""
            SELECT id, name, category 
            FROM nomenclature 
            WHERE category = 'Готова продукція'
            ORDER BY name
        """)
        
        finished_products = cursor.fetchall()
        print(f"  Текущих продуктов 'Готова продукція': {len(finished_products)}")
        
        # Найдем продукты для удаления
        to_delete = []
        for product in finished_products:
            pid, pname, pcat = product
            if pid not in all_final_ids:
                # Проверим, используется ли в рецептах
                cursor.execute("""
                    SELECT COUNT(*) FROM recipe_ingredients WHERE nomenclature_id = ?
                """, pid)
                in_recipe_ing = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM recipes WHERE target_product_id = ?
                """, pid)
                in_recipe_target = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM packaging_recipes WHERE source_product_id = ? OR target_product_id = ?
                """, pid, pid)
                in_packaging = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM butchery_recipe_outputs WHERE output_nomenclature_id = ?
                """, pid)
                in_butchery = cursor.fetchone()[0]
                
                if in_recipe_ing + in_recipe_target + in_packaging + in_butchery > 0:
                    print(f"  ⚠️  ID {pid} '{pname}' не в финальном списке, но используется в рецептах")
                    print(f"       (recipe_ing: {in_recipe_ing}, recipe_target: {in_recipe_target}, packaging: {in_packaging}, butchery: {in_butchery})")
                else:
                    to_delete.append((pid, pname))
        
        if to_delete:
            print(f"\n  Будет удалено {len(to_delete)} неиспользуемых продуктов:")
            for pid, pname in to_delete:
                print(f"    - ID {pid}: {pname}")
            
            for pid, pname in to_delete:
                cursor.execute("DELETE FROM nomenclature WHERE id = ?", pid)
            
            conn.commit()
            print(f"\n  ✅ Удалено {len(to_delete)} позиций")
        else:
            print("  ✅ Неиспользуемых дубликатов не найдено")
        
        # ========================================================================
        # STEP 4: ПРОВЕРКА И ИСПРАВЛЕНИЕ СВЯЗЕЙ В РЕЦЕПТАХ
        # ========================================================================
        print("\n[STEP 4] ПРОВЕРКА СВЯЗЕЙ В РЕЦЕПТАХ")
        print("-" * 80)
        
        # Проверим recipes
        cursor.execute("""
            SELECT r.id, r.name, r.target_product_id, n.name
            FROM recipes r
            LEFT JOIN nomenclature n ON r.target_product_id = n.id
            ORDER BY r.name
        """)
        
        recipes = cursor.fetchall()
        print(f"\n  Всего рецептов производства: {len(recipes)}")
        for recipe in recipes:
            rid, rname, tpid, tpname = recipe
            if tpname:
                print(f"    - {rname} → ID {tpid}: {tpname}")
            else:
                print(f"    ⚠️  {rname} → ID {tpid}: ПРОДУКТ НЕ НАЙДЕН!")
        
        # Проверим packaging_recipes
        cursor.execute("""
            SELECT DISTINCT pr.source_product_id, n.name
            FROM packaging_recipes pr
            LEFT JOIN nomenclature n ON pr.source_product_id = n.id
            WHERE pr.is_active = 1
            ORDER BY n.name
        """)
        
        pkg_sources = cursor.fetchall()
        print(f"\n  Источники для фасовки ({len(pkg_sources)}):")
        for spid, spname in pkg_sources:
            if spname:
                print(f"    - ID {spid}: {spname}")
            else:
                print(f"    ⚠️  ID {spid}: ПРОДУКТ НЕ НАЙДЕН!")
        
        # ========================================================================
        # STEP 5: ИСПРАВЛЕНИЕ ОСОБЫХ СЛУЧАЕВ
        # ========================================================================
        print("\n[STEP 5] ИСПРАВЛЕНИЕ ОСОБЫХ СЛУЧАЕВ")
        print("-" * 80)
        
        # Исправим рецепт "Бастурма з конини" → "Конина"
        cursor.execute("SELECT id, name, target_product_id FROM recipes WHERE name LIKE '%онин%'")
        horse_recipes = cursor.fetchall()
        for rid, rname, tpid in horse_recipes:
            print(f"  Рецепт '{rname}' (ID {rid}) → target_product_id: {tpid}")
            if "з конини" in rname.lower():
                # Переименуем рецепт
                new_recipe_name = rname.replace("з конини", "").replace("Бастурма ", "Конина ")
                print(f"    → Переименование рецепта: '{rname}' → '{new_recipe_name}'")
                cursor.execute("UPDATE recipes SET name = ? WHERE id = ?", new_recipe_name, rid)
        
        # Проверим packaging_recipes для "Курка філе"
        cursor.execute("""
            SELECT id, source_product_id, target_product_id
            FROM packaging_recipes
            WHERE source_product_id = 6 AND is_active = 1
        """)
        chicken_packaging = cursor.fetchall()
        if chicken_packaging:
            print(f"\n  ⚠️  Найдены packaging_recipes с source_product_id=6 (Курка філе):")
            for prid, spid, tpid in chicken_packaging:
                print(f"      packaging_recipe ID {prid}: {spid} → {tpid}")
            print(f"  Это сырье, а не результат производства. Нужно обновить source_product_id.")
            print(f"  Варианты:")
            print(f"    - Если это 'Курка сиров'ялена', то source_product_id = 104")
            print(f"    - Если это новая 'Курка вагова', нужен новый ID")
            
            # Найдем ID для "Курка вагова"
            cursor.execute("SELECT id FROM nomenclature WHERE name LIKE '%урка вагов%'")
            kurka_vagova = cursor.fetchone()
            if kurka_vagova:
                kurka_vagova_id = kurka_vagova[0]
                print(f"\n  Обновляем packaging_recipes: source 6 → {kurka_vagova_id} (Курка вагова)")
                cursor.execute("""
                    UPDATE packaging_recipes 
                    SET source_product_id = ? 
                    WHERE source_product_id = 6 AND is_active = 1
                """, kurka_vagova_id)
            else:
                print(f"  ⚠️  'Курка вагова' не найдена, пропускаем обновление")
        
        conn.commit()
        print("\n✅ Исправление особых случаев завершено")
        
        # ========================================================================
        # STEP 6: ФИНАЛЬНАЯ ПРОВЕРКА
        # ========================================================================
        print("\n[STEP 6] ФИНАЛЬНАЯ ПРОВЕРКА")
        print("-" * 80)
        
        # Проверка категорий
        cursor.execute("""
            SELECT category, COUNT(*) as cnt
            FROM nomenclature
            GROUP BY category
            ORDER BY category
        """)
        
        categories = cursor.fetchall()
        print("\nРаспределение по категориям:")
        for cat, cnt in categories:
            print(f"  {cat}: {cnt} позиций")
        
        # Финальный счет
        cursor.execute("SELECT COUNT(*) FROM nomenclature WHERE category = 'Сировина - М''ясо'")
        raw_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM nomenclature WHERE category = 'Напівфабрикати'")
        semi_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM nomenclature WHERE category = 'Готова продукція'")
        finished_count = cursor.fetchone()[0]
        
        print(f"\n📊 ФИНАЛЬНАЯ СТАТИСТИКА:")
        print(f"  Сырое мясо (М'ясо): {raw_count} (ожидалось: 13)")
        print(f"  Полуфабрикаты (Напівфабрикати): {semi_count} (ожидалось: 13)")
        print(f"  Готовая продукция: {finished_count}")
        
        if raw_count == 13 and semi_count == 13:
            print("\n🎉 МИГРАЦИЯ УСПЕШНО ЗАВЕРШЕНА!")
        else:
            print("\n⚠️  Проверьте результаты - количество не соответствует ожиданиям")

if __name__ == "__main__":
    try:
        execute_migration()
    except Exception as e:
        print(f"\n❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
