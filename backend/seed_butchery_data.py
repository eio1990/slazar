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

# Нова номенклатура (для всіх типів м'яса)
NEW_NOMENCLATURE = [
    # === СПЕЦІАЛЬНА НАРІЗКА (cut-specific) ===
    # Яловичина
    {'name': 'Яловичина для бастурми', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    {'name': 'Яловичина для пластин', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    {'name': 'Яловичина для суджука', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    
    # Конина
    {'name': 'Конина другий ґатунок', 'category': 'Сировина - М\'ясо', 'unit': 'кг', 'type': 'semi'},
    {'name': 'Конина для бастурми з конини', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    {'name': 'Конина для пластин з конини', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    {'name': 'Конина для махан', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    {'name': 'Конина для махан пластина', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    {'name': 'Конина для суджук', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    
    # Свинина
    {'name': 'Свинина для бастурма банкетна', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    {'name': 'Свинина для суджука', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    
    # Курка
    {'name': 'Курка для весової курки', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    {'name': 'Курка для суджука', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    
    # Індичка
    {'name': 'Індичка для бастурми з індички', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    {'name': 'Індичка для суджука', 'category': 'Напівфабрикати', 'unit': 'кг', 'type': 'cut-specific'},
    
    # === ПОБІЧНІ ПРОДУКТИ ===
    # Кістки та жир
    {'name': 'Кістки яловичі', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'by-product'},
    {'name': 'Жир яловичий', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'by-product'},
    {'name': 'Кістки кінські', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'by-product'},
    {'name': 'Жир кінський', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'by-product'},
    
    # Стек (liquid-waste - не зберігається на складі)
    {'name': 'Стек яловичий', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'liquid-waste'},
    {'name': 'Стек кінський', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'liquid-waste'},
    {'name': 'Стек свинячий', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'liquid-waste'},
    {'name': 'Стек курячий', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'liquid-waste'},
    {'name': 'Стек індичий', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'liquid-waste'},
    
    # Відходи (загальні для всіх)
    {'name': 'Відходи м\'ясні', 'category': 'Побічні продукти', 'unit': 'кг', 'type': 'waste'},
]

# Рецепти розділки (12 рецептів для всіх типів м'яса)
BUTCHERY_RECIPES = [
    # === ЯЛОВИЧИНА (4 рецепти) ===
    {
        'name': 'Розділка туші яловичини',
        'source': 'Яловичина туша',
        'level': 1,
        'description': 'Первинна розділка туші яловичини на сорти, нарізку та побічні продукти',
        'outputs': [
            {'name': 'Яловичина вищій ґатунок', 'yield': 15.0, 'type': 'main', 'is_main': True},
            {'name': 'Яловичина перший ґатунок', 'yield': 20.0, 'type': 'main', 'is_main': True},
            {'name': 'Яловичина другий ґатунок', 'yield': 15.0, 'type': 'main', 'is_main': False},
            {'name': 'Яловичина для бастурми', 'yield': 10.0, 'type': 'main', 'is_main': True},
            {'name': 'Яловичина для пластин', 'yield': 10.0, 'type': 'main', 'is_main': True},
            {'name': 'Кістки яловичі', 'yield': 15.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Жир яловичий', 'yield': 8.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Стек яловичий', 'yield': 5.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи м\'ясні', 'yield': 2.0, 'type': 'waste', 'is_main': False},
        ]
    },
    {
        'name': 'Обробка яловичини вищого сорту',
        'source': 'Яловичина вищій ґатунок',
        'level': 2,
        'description': 'Нарізка вищого сорту яловичини для різних продуктів',
        'outputs': [
            {'name': 'Яловичина для бастурми', 'yield': 40.0, 'type': 'main', 'is_main': True},
            {'name': 'Яловичина для суджука', 'yield': 25.0, 'type': 'main', 'is_main': True},
            {'name': 'Яловичина для пластин', 'yield': 20.0, 'type': 'main', 'is_main': True},
            {'name': 'Яловичина другий ґатунок', 'yield': 10.0, 'type': 'main', 'is_main': False},
            {'name': 'Стек яловичий', 'yield': 3.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи м\'ясні', 'yield': 2.0, 'type': 'waste', 'is_main': False},
        ]
    },
    {
        'name': 'Обробка яловичини першого сорту',
        'source': 'Яловичина перший ґатунок',
        'level': 2,
        'description': 'Нарізка першого сорту яловичини',
        'outputs': [
            {'name': 'Яловичина для суджука', 'yield': 35.0, 'type': 'main', 'is_main': True},
            {'name': 'Яловичина для пластин', 'yield': 40.0, 'type': 'main', 'is_main': True},
            {'name': 'Яловичина другий ґатунок', 'yield': 18.0, 'type': 'main', 'is_main': False},
            {'name': 'Стек яловичий', 'yield': 5.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи м\'ясні', 'yield': 2.0, 'type': 'waste', 'is_main': False},
        ]
    },
    {
        'name': 'Обробка яловичини другого сорту',
        'source': 'Яловичина другий ґатунок',
        'level': 2,
        'description': 'Підготовка другого сорту яловичини для суджука',
        'outputs': [
            {'name': 'Яловичина для суджука', 'yield': 88.0, 'type': 'main', 'is_main': True},
            {'name': 'Стек яловичий', 'yield': 8.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи м\'ясні', 'yield': 4.0, 'type': 'waste', 'is_main': False},
        ]
    },
    
    # === КОНИНА (4 рецепти) ===
    {
        'name': 'Розділка туші конини',
        'source': 'Конина туша',
        'level': 1,
        'description': 'Первинна розділка туші конини на сорти, нарізку та побічні продукти',
        'outputs': [
            {'name': 'Конина вищій ґатунок', 'yield': 18.0, 'type': 'main', 'is_main': True},
            {'name': 'Конина перший ґатунок', 'yield': 20.0, 'type': 'main', 'is_main': True},
            {'name': 'Конина другий ґатунок', 'yield': 12.0, 'type': 'main', 'is_main': False},
            {'name': 'Конина для бастурми з конини', 'yield': 8.0, 'type': 'main', 'is_main': True},
            {'name': 'Конина для пластин з конини', 'yield': 8.0, 'type': 'main', 'is_main': True},
            {'name': 'Кістки кінські', 'yield': 18.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Жир кінський', 'yield': 8.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Стек кінський', 'yield': 6.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи м\'ясні', 'yield': 2.0, 'type': 'waste', 'is_main': False},
        ]
    },
    {
        'name': 'Обробка конини вищого сорту',
        'source': 'Конина вищій ґатунок',
        'level': 2,
        'description': 'Нарізка вищого сорту конини для різних продуктів',
        'outputs': [
            {'name': 'Конина для бастурми з конини', 'yield': 25.0, 'type': 'main', 'is_main': True},
            {'name': 'Конина для махан', 'yield': 25.0, 'type': 'main', 'is_main': True},
            {'name': 'Конина для махан пластина', 'yield': 20.0, 'type': 'main', 'is_main': True},
            {'name': 'Конина для суджук', 'yield': 15.0, 'type': 'main', 'is_main': True},
            {'name': 'Конина другий ґатунок', 'yield': 10.0, 'type': 'main', 'is_main': False},
            {'name': 'Стек кінський', 'yield': 3.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи м\'ясні', 'yield': 2.0, 'type': 'waste', 'is_main': False},
        ]
    },
    {
        'name': 'Обробка конини першого сорту',
        'source': 'Конина перший ґатунок',
        'level': 2,
        'description': 'Нарізка першого сорту конини',
        'outputs': [
            {'name': 'Конина для бастурми з конини', 'yield': 20.0, 'type': 'main', 'is_main': True},
            {'name': 'Конина для махан', 'yield': 20.0, 'type': 'main', 'is_main': True},
            {'name': 'Конина для махан пластина', 'yield': 25.0, 'type': 'main', 'is_main': True},
            {'name': 'Конина для суджук', 'yield': 20.0, 'type': 'main', 'is_main': True},
            {'name': 'Конина другий ґатунок', 'yield': 8.0, 'type': 'main', 'is_main': False},
            {'name': 'Стек кінський', 'yield': 5.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи м\'ясні', 'yield': 2.0, 'type': 'waste', 'is_main': False},
        ]
    },
    {
        'name': 'Обробка конини другого сорту',
        'source': 'Конина другий ґатунок',
        'level': 2,
        'description': 'Підготовка другого сорту конини',
        'outputs': [
            {'name': 'Конина для махан', 'yield': 45.0, 'type': 'main', 'is_main': True},
            {'name': 'Конина для суджук', 'yield': 45.0, 'type': 'main', 'is_main': True},
            {'name': 'Стек кінський', 'yield': 7.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи м\'ясні', 'yield': 3.0, 'type': 'waste', 'is_main': False},
        ]
    },
    
    # === СВИНИНА (1 рецепт) ===
    {
        'name': 'Обробка свинини биток',
        'source': 'Свинина биток',
        'level': 1,
        'description': 'Обробка та нарізка свинини биток',
        'outputs': [
            {'name': 'Свинина для бастурма банкетна', 'yield': 50.0, 'type': 'main', 'is_main': True},
            {'name': 'Свинина для суджука', 'yield': 40.0, 'type': 'main', 'is_main': True},
            {'name': 'Стек свинячий', 'yield': 7.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи м\'ясні', 'yield': 3.0, 'type': 'waste', 'is_main': False},
        ]
    },
    
    # === КУРКА (1 рецепт) ===
    {
        'name': 'Обробка філе курки',
        'source': 'Курка філе',
        'level': 1,
        'description': 'Обробка та нарізка філе курки',
        'outputs': [
            {'name': 'Курка для весової курки', 'yield': 55.0, 'type': 'main', 'is_main': True},
            {'name': 'Курка для суджука', 'yield': 35.0, 'type': 'main', 'is_main': True},
            {'name': 'Стек курячий', 'yield': 8.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи м\'ясні', 'yield': 2.0, 'type': 'waste', 'is_main': False},
        ]
    },
    
    # === ІНДИЧКА (1 рецепт) ===
    {
        'name': 'Обробка філе індички',
        'source': 'Індик філе',
        'level': 1,
        'description': 'Обробка та нарізка філе індички',
        'outputs': [
            {'name': 'Індичка для бастурми з індички', 'yield': 55.0, 'type': 'main', 'is_main': True},
            {'name': 'Індичка для суджука', 'yield': 35.0, 'type': 'main', 'is_main': True},
            {'name': 'Стек індичий', 'yield': 8.0, 'type': 'by-product', 'is_main': False},
            {'name': 'Відходи м\'ясні', 'yield': 2.0, 'type': 'waste', 'is_main': False},
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

def clean_old_recipes(conn):
    """Видалити старі рецепти перед створенням нових"""
    cursor = conn.cursor()
    
    print("\n" + "=" * 60)
    print("ОЧИЩЕННЯ СТАРИХ ДАНИХ")
    print("=" * 60)
    
    # Видалити операції розділки
    cursor.execute("DELETE FROM butchery_operations")
    print("   ✅ Видалено всі операції розділки")
    
    # Видалити виходи рецептів
    cursor.execute("DELETE FROM butchery_recipe_outputs")
    print("   ✅ Видалено всі виходи рецептів")
    
    # Видалити рецепти
    cursor.execute("DELETE FROM butchery_recipes")
    print("   ✅ Видалено всі рецепти")
    
    conn.commit()

def main():
    conn = get_connection()
    
    try:
        # 1. Додати нову номенклатуру
        seed_nomenclature(conn)
        
        # 2. Оновити типи існуючої номенклатури
        update_existing_types(conn)
        
        # 3. Очистити старі рецепти
        clean_old_recipes(conn)
        
        # 4. Створити нові рецепти розділки
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
