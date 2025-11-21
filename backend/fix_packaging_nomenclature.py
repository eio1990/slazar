"""
Fix packaging recipes nomenclature based on user feedback
"""
from database import get_db_connection

def fix_nomenclature():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print("=== FIXING NOMENCLATURE ===\n")
        
        # 1. Переименовать "Банкетна весова фасована" → "Банкетна вагова"
        cursor.execute("UPDATE nomenclature SET name = 'Банкетна вагова' WHERE name = 'Банкетна весова фасована'")
        print("✅ Renamed: Банкетна весова фасована → Банкетна вагова")
        
        # 2. Переименовать "Конина вагова" → "Конина"
        cursor.execute("UPDATE nomenclature SET name = 'Конина' WHERE name = 'Конина вагова'")
        print("✅ Renamed: Конина вагова → Конина")
        
        # 3. Переименовать "Конина весова фасована" → "Конина вагова"
        cursor.execute("UPDATE nomenclature SET name = 'Конина вагова' WHERE name = 'Конина весова фасована'")
        print("✅ Renamed: Конина весова фасована → Конина вагова")
        
        # 4. Переименовать "Філе курицы 40г вакуум" → "Філе курки 40г вакуум"
        cursor.execute("UPDATE nomenclature SET name = 'Філе курки 40г вакуум' WHERE name = 'Філе курицы 40г вакуум'")
        print("✅ Renamed: Філе курицы 40г вакуум → Філе курки 40г вакуум")
        
        # 5. Переименовать "Суджук весовий фасований" → "Суджук ваговий"
        cursor.execute("UPDATE nomenclature SET name = 'Суджук ваговий' WHERE name = 'Суджук весовий фасований'")
        print("✅ Renamed: Суджук весовий фасований → Суджук ваговий")
        
        # 6. Переименовать "Махан весовий фасований" → "Махан ваговий"
        cursor.execute("UPDATE nomenclature SET name = 'Махан ваговий' WHERE name = 'Махан весовий фасований'")
        print("✅ Renamed: Махан весовий фасований → Махан ваговий")
        
        # 7. Удалить packaging recipes для дублей (источники которые сами являются результатами фасовки)
        # "Банкетна вагова" (ID 179), "Махан ваговий" (ID 177), "Суджук ваговий" (ID 176) не должны быть источниками
        
        cursor.execute("DELETE FROM packaging_recipes WHERE source_product_id = 179")  # Банкетна вагова
        print("✅ Deleted packaging recipes for source: Банкетна вагова (duplicate)")
        
        cursor.execute("DELETE FROM packaging_recipes WHERE source_product_id = 177")  # Махан ваговий
        print("✅ Deleted packaging recipes for source: Махан ваговий (duplicate)")
        
        cursor.execute("DELETE FROM packaging_recipes WHERE source_product_id = 176")  # Суджук ваговий
        print("✅ Deleted packaging recipes for source: Суджук ваговий (duplicate)")
        
        # 8. Удалить packaging recipes для "Конина вагова" (теперь это "Конина" - источник)
        cursor.execute("SELECT id FROM nomenclature WHERE name = 'Конина вагова'")
        konina_vagova = cursor.fetchone()
        if konina_vagova:
            cursor.execute("DELETE FROM packaging_recipes WHERE source_product_id = ?", konina_vagova[0])
            print(f"✅ Deleted packaging recipes for source: Конина вагова (now a target)")
        
        # 9. Удалить recipes для "Пластина конина" (не производим)
        cursor.execute("SELECT id FROM nomenclature WHERE name = 'Пластина конина'")
        plastina_konina = cursor.fetchone()
        if plastina_konina:
            cursor.execute("DELETE FROM packaging_recipes WHERE source_product_id = ?", plastina_konina[0])
            print(f"✅ Deleted packaging recipes for source: Пластина конина (not produced)")
        
        # 10. Удалить recipes для "Етикетка Махан 75*75" как источника
        cursor.execute("SELECT id FROM nomenclature WHERE name = 'Етикетка Махан 75*75'")
        etiketa = cursor.fetchone()
        if etiketa:
            cursor.execute("DELETE FROM packaging_recipes WHERE source_product_id = ?", etiketa[0])
            print(f"✅ Deleted packaging recipes for source: Етикетка Махан 75*75 (not a product)")
        
        # 11. Удалить recipes для "Асорті бастурма та суджук вакуум" как источника
        cursor.execute("SELECT id FROM nomenclature WHERE name = 'Асорті бастурма та суджук вакуум'")
        asorti = cursor.fetchone()
        if asorti:
            cursor.execute("DELETE FROM packaging_recipes WHERE source_product_id = ?", asorti[0])
            print(f"✅ Deleted packaging recipes for source: Асорті (this is a result of packaging)")
        
        # 12. Добавить "Асорті бастурма та суджук вакуум" как результат для "Бастурма" и "Суджук"
        cursor.execute("SELECT id FROM nomenclature WHERE name = 'Бастурма'")
        basturma = cursor.fetchone()
        
        cursor.execute("SELECT id FROM nomenclature WHERE name = 'Суджук'")
        sudjuk = cursor.fetchone()
        
        cursor.execute("SELECT id FROM nomenclature WHERE name = 'Асорті бастурма та суджук вакуум'")
        asorti = cursor.fetchone()
        
        if basturma and asorti:
            # Проверить существует ли уже
            cursor.execute("""
                SELECT id FROM packaging_recipes 
                WHERE source_product_id = ? AND target_product_id = ?
            """, basturma[0], asorti[0])
            
            if not cursor.fetchone():
                # Добавить рецепт: Бастурма → Асорті
                cursor.execute("""
                    INSERT INTO packaging_recipes (
                        source_product_id, target_product_id,
                        packaging_type, target_weight_grams, is_active
                    ) VALUES (?, ?, 'vacuum_assortment', 0, 1)
                """, basturma[0], asorti[0])
                print(f"✅ Added: Бастурма → Асорті бастурма та суджук вакуум")
        
        if sudjuk and asorti:
            cursor.execute("""
                SELECT id FROM packaging_recipes 
                WHERE source_product_id = ? AND target_product_id = ?
            """, sudjuk[0], asorti[0])
            
            if not cursor.fetchone():
                # Добавить рецепт: Суджук → Асорті
                cursor.execute("""
                    INSERT INTO packaging_recipes (
                        source_product_id, target_product_id,
                        packaging_type, target_weight_grams, is_active
                    ) VALUES (?, ?, 'vacuum_assortment', 0, 1)
                """, sudjuk[0], asorti[0])
                print(f"✅ Added: Суджук → Асорті бастурма та суджук вакуум")
        
        conn.commit()
        print("\n✅ ALL FIXES APPLIED!")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    fix_nomenclature()
