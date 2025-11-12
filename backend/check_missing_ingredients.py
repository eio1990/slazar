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
            SELECT id, name, unit, category
            FROM nomenclature
            WHERE name IN (N'Перець чілі', N'Борошно')
        """)
        
        existing = {row.name: row for row in cursor.fetchall()}
        print(f"Найдено в базе: {list(existing.keys())}")
        
        # Добавляем недостающие ингредиенты
        to_add = []
        
        if 'Перець чілі' not in existing:
            to_add.append(('Перець чілі', 'кг', 'Спеції'))
            
        if 'Борошно' not in existing:
            to_add.append(('Борошно', 'кг', 'Спеції'))
        
        if to_add:
            print(f"\nДобавляем {len(to_add)} ингредиента(ов)...")
            for name, unit, category in to_add:
                cursor.execute("""
                    INSERT INTO nomenclature (name, unit, category)
                    VALUES (?, ?, ?)
                """, name, unit, category)
                print(f"✅ Добавлен: {name} ({unit})")
            conn.commit()
        else:
            print("\n✅ Все ингредиенты уже есть в номенклатуре")
        
        # Проверяем результат
        cursor.execute("""
            SELECT id, name, unit, category
            FROM nomenclature
            WHERE name IN (N'Перець чілі', N'Борошно')
        """)
        
        print("\n=== Итоговый список ===")
        for row in cursor.fetchall():
            print(f"ID: {row.id}, Название: {row.name}, Единица: {row.unit}, Категория: {row.category}")

if __name__ == "__main__":
    check_and_add_missing_ingredients()
