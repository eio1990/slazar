"""
Seed даних для модуля розділки:
1. Нова номенклатура (спеціальна нарізка, побічні продукти)
2. Рецепти розділки з виходами
"""
import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    conn_str = (
        f"DRIVER={{ODBC Driver 18 for SQL Server}};"
        f"SERVER={os.getenv('MSSQL_SERVER')};"
        f"DATABASE={os.getenv('MSSQL_DATABASE')};"
        f"UID={os.getenv('MSSQL_USER')};"
        f"PWD={os.getenv('MSSQL_PASSWORD')};"
        f"TrustServerCertificate=yes;"
    )
    return pyodbc.connect(conn_str)

# Нова номенклатура
NEW_NOMENCLATURE = [
    # Спеціальна нарізка для яловичини
    {'name': 'Яловичина на бастурму', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    {'name': 'Яловичина на пластини', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    {'name': 'Яловичина на суджук', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    
    # Спеціальна нарізка для конини
    {'name': 'Конина на махан', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    {'name': 'Конина на суджук', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    
    # Побічні продукти - яловичина
    {'name': 'Кістки яловичі', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'by-product'},
    {'name': 'Жир яловичий', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'by-product'},
    {'name': 'Стек яловичий', 'category': 'Аналітика', 'unit': 'кг', 'type': 'liquid-waste'},  # Кров і вода - не зберігаються
    {'name': 'Відходи яловичі', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'waste'},
    
    # Побічні продукти - конина
    {'name': 'Кістки кінські', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'by-product'},
    {'name': 'Стек кінський', 'category': 'Аналітика', 'unit': 'кг', 'type': 'liquid-waste'},  # Кров і вода - не зберігаються
    {'name': 'Відходи кінські', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'waste'},
]

# Рецепти розділки
BUTCHERY_RECIPES = [
    {
        'name': 'Розділка туші яловичини (1 рівень)',
        'source': 'Яловичина туша',
        'level': 1,
        'description': 'Первинна розділка туші на сорти та побічні продукти',
        'outputs': [
            {'name': 'Яловичина вищій ґатунок', 'yield': 25.0, 'type': 'main', 'is_main': True},
            {'name': 'Яловичина перший ґатунок', 'yield': 30.0, 'type': 'main', 'is_main': True},
            {'name': 'Яловичина другий ґатунок', 'yield': 20.0, 'type': 'main', 'is_main': False},
            {'name': 'Кістки яловичі', 'yield': 15.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Жир яловичий', 'yield': 5.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Стек яловичий', 'yield': 3.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи яловичі', 'yield': 2.0, 'type': 'waste', 'is_main': False},
        ]
    },
    {
        'name': 'Розділка вищого сорту (2 рівень) → Бастурма',
        'source': 'Яловичина вищій ґатунок',
        'level': 2,
        'description': 'Нарізка вищого сорту для бастурми',
        'outputs': [
            {'name': 'Яловичина на бастурму', 'yield': 70.0, 'type': 'main', 'is_main': True},
            {'name': 'Яловичина перший ґатунок', 'yield': 20.0, 'type': 'main', 'is_main': False},
            {'name': 'Яловичина другий ґатунок', 'yield': 5.0, 'type': 'main', 'is_main': False},
            {'name': 'Стек яловичий', 'yield': 3.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи яловичі', 'yield': 2.0, 'type': 'waste', 'is_main': False},
        ]
    },
    {
        'name': 'Розділка першого сорту (2 рівень) → Пластини',
        'source': 'Яловичина перший ґатунок',
        'level': 2,
        'description': 'Нарізка першого сорту для пластин',
        'outputs': [
            {'name': 'Яловичина на пластини', 'yield': 75.0, 'type': 'main', 'is_main': True},
            {'name': 'Яловичина другий ґатунок', 'yield': 20.0, 'type': 'main', 'is_main': False},
            {'name': 'Стек яловичий', 'yield': 3.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи яловичі', 'yield': 2.0, 'type': 'waste', 'is_main': False},
        ]
    },
    {
        'name': 'Розділка другого сорту (2 рівень) → Суджук',
        'source': 'Яловичина другий ґатунок',
        'level': 2,
        'description': 'Підготовка другого сорту для суджука',
        'outputs': [
            {'name': 'Яловичина на суджук', 'yield': 90.0, 'type': 'main', 'is_main': True},
            {'name': 'Стек яловичий', 'yield': 8.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи яловичі', 'yield': 2.0, 'type': 'waste', 'is_main': False},
        ]
    },
    {
        'name': 'Розділка туші конини (1 рівень)',
        'source': 'Конина туша',
        'level': 1,
        'description': 'Первинна розділка туші конини',
        'outputs': [
            {'name': 'Конина вищій ґатунок', 'yield': 28.0, 'type': 'main', 'is_main': True},
            {'name': 'Конина перший ґатунок', 'yield': 32.0, 'type': 'main', 'is_main': True},
            {'name': 'Кінський жир', 'yield': 8.0, 'type': 'main', 'is_main': False},
            {'name': 'Кістки кінські', 'yield': 22.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Стек кінський', 'yield': 7.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи кінські', 'yield': 3.0, 'type': 'waste', 'is_main': False},
        ]
    },
    {
        'name': 'Розділка конини вищого сорту (2 рівень) → Махан',
        'source': 'Конина вищій ґатунок',
        'level': 2,
        'description': 'Нарізка для махана',
        'outputs': [
            {'name': 'Конина на махан', 'yield': 85.0, 'type': 'main', 'is_main': True},
            {'name': 'Конина перший ґатунок', 'yield': 10.0, 'type': 'main', 'is_main': False},
            {'name': 'Стек кінський', 'yield': 3.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи кінські', 'yield': 2.0, 'type': 'waste', 'is_main': False},
        ]
    },
    {
        'name': 'Розділка конини першого сорту (2 рівень) → Суджук',
        'source': 'Конина перший ґатунок',
        'level': 2,
        'description': 'Підготовка для суджука',
        'outputs': [
            {'name': 'Конина на суджук', 'yield': 88.0, 'type': 'main', 'is_main': True},
            {'name': 'Стек кінський', 'yield': 10.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи кінські', 'yield': 2.0, 'type': 'waste', 'is_main': False},
        ]
    },
]

def seed_nomenclature(conn):
    """Додати нову номенклатуру"""
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("ДОДАВАННЯ НОВОЇ НОМЕНКЛАТУРИ")
    print("=" * 60)
    
    for item in NEW_NOMENCLATURE:
        # Перевірити чи існує
        cursor.execute("SELECT id FROM nomenclature WHERE name = ?", item['name'])
        existing = cursor.fetchone()
        
        if existing:
            # Оновити тип
            cursor.execute("""
                UPDATE nomenclature 
                SET nomenclature_type = ?
                WHERE name = ?
            """, item['type'], item['name'])
            print(f"   🔄 Оновлено: {item['name']}")
        else:
            # Додати нову
            cursor.execute("""
                INSERT INTO nomenclature (name, category, unit, nomenclature_type)
                VALUES (?, ?, ?, ?)
            """, item['name'], item['category'], item['unit'], item['type'])
            print(f"   ✅ Додано: {item['name']}")
    
    conn.commit()

def update_existing_types(conn):
    """Оновити типи існуючої номенклатури"""
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("ОНОВЛЕННЯ ТИПІВ ІСНУЮЧОЇ НОМЕНКЛАТУРИ")
    print("=" * 60)
    
    # Туші -> raw
    cursor.execute("""
        UPDATE nomenclature 
        SET nomenclature_type = 'raw'
        WHERE name LIKE '%туша%'
    """)
    print(f"   ✅ Туші позначено як 'raw'")
    
    # Сорти -> semi
    cursor.execute("""
        UPDATE nomenclature 
        SET nomenclature_type = 'semi'
        WHERE name LIKE '%ґатунок%' OR name LIKE '%сорт%'
    """)
    print(f"   ✅ Сорти позначено як 'semi'")
    
    # Кінський жир -> semi (використовується в виробництві)
    cursor.execute("""
        UPDATE nomenclature 
        SET nomenclature_type = 'semi'
        WHERE name = 'Кінський жир'
    """)
    print(f"   ✅ Кінський жир позначено як 'semi'")
    
    # Інша сировина -> raw
    cursor.execute("""
        UPDATE nomenclature 
        SET nomenclature_type = 'raw'
        WHERE category = 'Сировина - М''ясо' 
        AND nomenclature_type IS NULL
    """)
    print(f"   ✅ Інша сировина позначена як 'raw'")
    
    conn.commit()

def seed_butchery_recipes(conn):
    """Створити рецепти розділки"""
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("СТВОРЕННЯ РЕЦЕПТІВ РОЗДІЛКИ")
    print("=" * 60)
    
    for recipe_data in BUTCHERY_RECIPES:
        # Отримати ID сировини
        cursor.execute("SELECT id FROM nomenclature WHERE name = ?", recipe_data['source'])
        source_row = cursor.fetchone()
        
        if not source_row:
            print(f"   ⚠️ ПРОПУЩЕНО: {recipe_data['name']} (сировина '{recipe_data['source']}' не знайдена)")
            continue
        
        source_id = source_row[0]
        
        # Перевірити чи існує рецепт
        cursor.execute("""
            SELECT id FROM butchery_recipes 
            WHERE name = ? AND source_nomenclature_id = ?
        """, recipe_data['name'], source_id)
        
        existing = cursor.fetchone()
        
        if existing:
            recipe_id = existing[0]
            print(f"   🔄 Рецепт вже існує: {recipe_data['name']}")
        else:
            # Створити рецепт
            cursor.execute("""
                INSERT INTO butchery_recipes 
                (name, source_nomenclature_id, description, level, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, recipe_data['name'], source_id, recipe_data['description'], recipe_data['level'])
            
            recipe_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
            print(f"   ✅ Створено рецепт: {recipe_data['name']}")
        
        # Видалити старі виходи (якщо є)
        cursor.execute("DELETE FROM butchery_recipe_outputs WHERE recipe_id = ?", recipe_id)
        
        # Додати виходи
        for output in recipe_data['outputs']:
            cursor.execute("SELECT id FROM nomenclature WHERE name = ?", output['name'])
            output_row = cursor.fetchone()
            
            if not output_row:
                print(f"      ⚠️ Вихід '{output['name']}' не знайдено")
                continue
            
            output_id = output_row[0]
            
            cursor.execute("""
                INSERT INTO butchery_recipe_outputs
                (recipe_id, output_nomenclature_id, yield_percentage, 
                 is_main_output, output_type)
                VALUES (?, ?, ?, ?, ?)
            """, recipe_id, output_id, output['yield'], 
                output['is_main'], output['type'])
            
            print(f"      + {output['name']}: {output['yield']}%")
    
    conn.commit()

def main():
    conn = get_connection()
    
    try:
        # 1. Додати нову номенклатуру
        seed_nomenclature(conn)
        
        # 2. Оновити типи існуючої номенклатури
        update_existing_types(conn)
        
        # 3. Створити рецепти розділки
        seed_butchery_recipes(conn)
        
        print("\n" + "=" * 60)
        print("✅ SEED ЗАВЕРШЕНО УСПІШНО")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ПОМИЛКА: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
