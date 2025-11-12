import os
from dotenv import load_dotenv
from database import get_db_connection

load_dotenv()

def add_missing_spices():
    """Добавляет Перець чілі и Борошно в рецепт Бастурма класична"""
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Получаем ID рецепта Бастурма
        cursor.execute("""
            SELECT id, name FROM recipes WHERE name = N'Бастурма класична'
        """)
        basturma = cursor.fetchone()
        if not basturma:
            print("ОШИБКА: Рецепт 'Бастурма класична' не найден")
            return
        
        recipe_id = basturma.id
        print(f"Рецепт найден: ID={recipe_id}, Название={basturma.name}")
        
        # Получаем ID специй
        cursor.execute("""
            SELECT id, name FROM nomenclature 
            WHERE name IN (N'Перець чілі', N'Борошно')
        """)
        
        spices = {row.name: row.id for row in cursor.fetchall()}
        print(f"\nСпеции найдены:")
        for name, spice_id in spices.items():
            print(f"  {name}: ID={spice_id}")
        
        if 'Перець чілі' not in spices or 'Борошно' not in spices:
            print("ОШИБКА: Не все специи найдены в номенклатуре")
            return
        
        # Добавляем специи в рецепт
        # Согласно спецификации пользователя:
        # - Перець чілі: 1.54 кг
        # - Борошно: 3.08 кг
        
        spices_to_add = [
            (recipe_id, spices['Перець чілі'], 1.54, 0, 'Перець чілі'),
            (recipe_id, spices['Борошно'], 3.08, 0, 'Борошно')
        ]
        
        print(f"\nДобавляем специи в рецепт...")
        for recipe_id, nomenclature_id, quantity, is_fenugreek, name in spices_to_add:
            # Проверяем, не добавлена ли уже
            cursor.execute("""
                SELECT id FROM recipe_spices 
                WHERE recipe_id = ? AND nomenclature_id = ?
            """, recipe_id, nomenclature_id)
            
            if cursor.fetchone():
                print(f"  ⚠️  {name} уже есть в рецепте, пропускаем")
                continue
            
            cursor.execute("""
                INSERT INTO recipe_spices (recipe_id, nomenclature_id, quantity_per_100kg, is_fenugreek)
                VALUES (?, ?, ?, ?)
            """, recipe_id, nomenclature_id, quantity, is_fenugreek)
            print(f"  ✅ Добавлено: {name} - {quantity} кг на 100 кг")
        
        conn.commit()
        
        # Проверяем итоговый список
        cursor.execute("""
            SELECT n.name, rs.quantity_per_100kg
            FROM recipe_spices rs
            JOIN nomenclature n ON rs.nomenclature_id = n.id
            WHERE rs.recipe_id = ?
            ORDER BY n.name
        """, basturma.id)
        
        print("\n=== Итоговый список специй в рецепте Бастурма класична ===")
        total = 0
        for row in cursor.fetchall():
            print(f"  {row.name}: {float(row.quantity_per_100kg)} кг")
            total += float(row.quantity_per_100kg)
        print(f"\n  ИТОГО: {total} кг специй на 100 кг сырья")

if __name__ == "__main__":
    add_missing_spices()
