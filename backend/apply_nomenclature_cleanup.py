"""
Применить финальную очистку номенклатуры согласно утвержденному списку
"""
from database import get_db_connection

def apply_cleanup():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print("=" * 80)
        print("ЭТАП 1: ПЕРЕИМЕНОВАНИЯ")
        print("=" * 80)
        
        # Производство
        cursor.execute("UPDATE nomenclature SET name = N'Індичка' WHERE id = 233")
        print("✅ ID 233: Індичка вагова → Індичка")
        
        cursor.execute("UPDATE nomenclature SET name = N'Курхан' WHERE id = 113")
        print("✅ ID 113: Курхан ваговий → Курхан")
        
        cursor.execute("UPDATE nomenclature SET name = N'Конина' WHERE id = 108")
        print("✅ ID 108: Бастурма з конини → Конина")
        
        # Фасовка
        cursor.execute("UPDATE nomenclature SET name = N'Асорті бастурма та суджук 100г вакуум' WHERE id = 100")
        print("✅ ID 100: добавлено '100г'")
        
        cursor.execute("UPDATE nomenclature SET name = N'Курка 40г вакуум' WHERE id = 105")
        print("✅ ID 105: Курка сиров'ялена 40г вакуум → Курка 40г вакуум")
        
        cursor.execute("UPDATE nomenclature SET name = N'Конина 80г вакуум' WHERE id = 109")
        print("✅ ID 109: Бастурма з конини 80г → Конина 80г")
        
        # Изменить (шт) → (од)
        ids_to_update = [167, 168, 169, 164, 165, 172, 173, 174, 171, 166]
        for item_id in ids_to_update:
            cursor.execute("UPDATE nomenclature SET unit = N'од' WHERE id = ?", item_id)
        print(f"✅ Изменено (шт) → (од) для {len(ids_to_update)} продуктов")
        
        conn.commit()
        
        print("\n" + "=" * 80)
        print("ЭТАП 2: СОЗДАНИЕ НОВЫХ ПРОДУКТОВ")
        print("=" * 80)
        
        # Создать Курка вагова
        cursor.execute("SELECT id FROM nomenclature WHERE name = N'Курка вагова'")
        if not cursor.fetchone():
            cursor.execute("""
                INSERT INTO nomenclature (name, category, unit)
                VALUES (N'Курка вагова', N'Готова продукція', N'кг')
            """)
            kurka_vagova_id = int(cursor.execute("SELECT @@IDENTITY").fetchone()[0])
            print(f"✅ Создано: Курка вагова (ID {kurka_vagova_id})")
            
            # Создать packaging recipe: Курка сиров'ялена → Курка вагова
            cursor.execute("""
                INSERT INTO packaging_recipes (source_product_id, target_product_id, packaging_type, target_weight_grams, is_active)
                VALUES (104, ?, 'vacuum_bulk', 0, 1)
            """, kurka_vagova_id)
            print(f"✅ Создан packaging recipe: Курка сиров'ялена → Курка вагова")
        else:
            print("⚠️  Курка вагова уже существует")
        
        conn.commit()
        
        print("\n" + "=" * 80)
        print("ЭТАП 3: УДАЛЕНИЕ НЕИСПОЛЬЗУЕМЫХ ПОЛУФАБРИКАТОВ")
        print("=" * 80)
        
        # Проверить что ID 205, 221 не используются
        for sf_id in [205, 221]:
            cursor.execute("SELECT COUNT(*) FROM recipe_ingredients WHERE nomenclature_id = ?", sf_id)
            count = cursor.fetchone()[0]
            if count == 0:
                cursor.execute("DELETE FROM nomenclature WHERE id = ?", sf_id)
                print(f"✅ Удален полуфабрикат ID {sf_id}")
            else:
                print(f"⚠️  ID {sf_id} используется в {count} рецептах, не удаляем")
        
        conn.commit()
        
        print("\n" + "=" * 80)
        print("ЭТАП 4: УДАЛЕНИЕ ДУБЛЕЙ ФАСОВКИ")
        print("=" * 80)
        
        # Удалить дубли фасовки
        duplicates = [120, 119, 107, 114, 112, 99, 110, 103, 102, 97, 170]
        
        for dup_id in duplicates:
            # Удалить packaging recipes где этот продукт является target
            cursor.execute("DELETE FROM packaging_recipe_materials WHERE recipe_id IN (SELECT id FROM packaging_recipes WHERE target_product_id = ?)", dup_id)
            cursor.execute("DELETE FROM packaging_recipes WHERE target_product_id = ?", dup_id)
            
            # Удалить сам продукт
            cursor.execute("DELETE FROM nomenclature WHERE id = ?", dup_id)
            print(f"✅ Удален дубль фасовки ID {dup_id}")
        
        conn.commit()
        
        print("\n" + "=" * 80)
        print("ЭТАП 5: УДАЛЕНИЕ ДУБЛЕЙ ПРОИЗВОДСТВА")
        print("=" * 80)
        
        # Удалить дубли производства (кроме тех что теперь в фасовке)
        prod_duplicates = [181, 106, 178, 101]
        
        for dup_id in prod_duplicates:
            # Удалить packaging recipes где этот продукт является source
            cursor.execute("SELECT id FROM packaging_recipes WHERE source_product_id = ?", dup_id)
            recipe_ids = [row[0] for row in cursor.fetchall()]
            
            for recipe_id in recipe_ids:
                cursor.execute("DELETE FROM packaging_recipe_materials WHERE recipe_id = ?", recipe_id)
            cursor.execute("DELETE FROM packaging_recipes WHERE source_product_id = ?", dup_id)
            
            # Проверить что не является target в production recipes
            cursor.execute("SELECT COUNT(*) FROM recipes WHERE target_product_id = ?", dup_id)
            if cursor.fetchone()[0] == 0:
                cursor.execute("DELETE FROM nomenclature WHERE id = ?", dup_id)
                print(f"✅ Удален дубль производства ID {dup_id}")
            else:
                print(f"⚠️  ID {dup_id} используется в production recipe, обновляем target")
        
        # Обновить production recipe для Свинина сиров'ялена → Банкетна
        cursor.execute("UPDATE recipes SET target_product_id = 180 WHERE target_product_id = 101")
        print("✅ Production recipe: Свинина сиров'ялена теперь производит Банкетна (ID 180)")
        
        conn.commit()
        
        print("\n" + "=" * 80)
        print("ЭТАП 6: СОЗДАНИЕ PACKAGING RECIPES ДЛЯ КОНИНЫ")
        print("=" * 80)
        
        # Создать packaging recipes для Конина (ID 108)
        konina_targets = [
            (109, 80, 'vacuum'),
            (172, 50, 'vacuum'),
            (173, 50, 'skin'),
            (184, 0, 'vacuum_bulk'),  # Конина вагова
        ]
        
        for target_id, weight, pkg_type in konina_targets:
            cursor.execute("""
                SELECT id FROM packaging_recipes 
                WHERE source_product_id = 108 AND target_product_id = ?
            """, target_id)
            
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO packaging_recipes (source_product_id, target_product_id, packaging_type, target_weight_grams, is_active)
                    VALUES (108, ?, ?, ?, 1)
                """, target_id, pkg_type, weight)
                cursor.execute("SELECT name FROM nomenclature WHERE id = ?", target_id)
                target_name = cursor.fetchone()[0]
                print(f"✅ Создан recipe: Конина → {target_name}")
        
        conn.commit()
        
        print("\n" + "=" * 80)
        print("ЗАВЕРШЕНО!")
        print("=" * 80)

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    apply_cleanup()
