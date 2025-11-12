import os
from dotenv import load_dotenv
from database import get_db_connection

load_dotenv()

def check_and_add_missing_ingredients():
    """Проверяет наличие Перець чілі и Борошно, добавляет если их нет"""
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Проверяем наличие ингредиентов
        print("Проверка наличия ингредиентов...")
        cursor.execute("""
            SELECT id_nomenclature, name, unit
            FROM nomenclature
            WHERE name IN (N'Перець чілі', N'Борошно')
        """)
        
        existing = {row.name: row for row in cursor.fetchall()}
        print(f"Найдено в базе: {list(existing.keys())}")
        
        # Получаем ID категории для специй
        cursor.execute("""
            SELECT id_category FROM categories WHERE name = N'Спеції'
        """)
        spice_category = cursor.fetchone()
        if not spice_category:
            print("ОШИБКА: Категория 'Спеції' не найдена")
            return
        
        spice_category_id = spice_category.id_category
        print(f"ID категории 'Спеції': {spice_category_id}")
        
        # Добавляем недостающие ингредиенты
        to_add = []
        
        if 'Перець чілі' not in existing:
            to_add.append(('Перець чілі', 'кг', spice_category_id))
            
        if 'Борошно' not in existing:
            to_add.append(('Борошно', 'кг', spice_category_id))
        
        if to_add:
            print(f"\nДобавляем {len(to_add)} ингредиента(ов)...")
            for name, unit, cat_id in to_add:
                cursor.execute("""
                    INSERT INTO nomenclature (name, unit, id_category)
                    VALUES (?, ?, ?)
                """, name, unit, cat_id)
                print(f"✅ Добавлен: {name} ({unit})")
            conn.commit()
        else:
            print("\n✅ Все ингредиенты уже есть в номенклатуре")
        
        # Проверяем результат
        cursor.execute("""
            SELECT id_nomenclature, name, unit
            FROM nomenclature
            WHERE name IN (N'Перець чілі', N'Борошно')
        """)
        
        print("\n=== Итоговый список ===")
        for row in cursor.fetchall():
            print(f"ID: {row.id_nomenclature}, Название: {row.name}, Единица: {row.unit}")

if __name__ == "__main__":
    check_and_add_missing_ingredients()
