"""
Скрипт для заповнення рецептів фасовки з нормами витрат матеріалів
"""
import os
from dotenv import load_dotenv
from database import get_db_connection

load_dotenv()

# Маппінг весових продуктів до їх ID (будемо отримувати з БД)
WEIGHT_PRODUCTS = {
    "Бастурма": None,
    "Суджук": None,
    "Банкетна": None,
    "Курка філе": None,
    "Пластина яловичина": None,
    "Конина вагова": None,  # Поки залишаємо, бо немає просто "Конина"
    "Махан": None
}

# Структура всіх рецептів фасовки
PACKAGING_RECIPES = [
    # 1. Бастурма 50г вакуум
    {
        "source": "Бастурма",
        "target": "Бастурма 50г вакуум",
        "type": "vacuum",
        "weight_grams": 50,
        "materials": [
            {"name": "Пакет вакуум 100*200", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Бастурма 75*75", "quantity": 1, "unit": "шт", "type": "label"}
        ]
    },
    # 2. Бастурма 50г скін
    {
        "source": "Бастурма класична",
        "target": "Бастурма 50г скін",
        "type": "skin",
        "weight_grams": 50,
        "materials": [
            {"name": "Скін лоток нижній", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Скін плівка верхня", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Бастурма скін передня", "quantity": 1, "unit": "шт", "type": "label"},
            {"name": "Термо етикетка", "quantity": 1, "unit": "шт", "type": "label"}
        ]
    },
    # 3. Бастурма 60г скін
    {
        "source": "Бастурма класична",
        "target": "Бастурма 60г скін",
        "type": "skin",
        "weight_grams": 60,
        "materials": [
            {"name": "Скін лоток нижній", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Скін плівка верхня", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Бастурма скін передня", "quantity": 1, "unit": "шт", "type": "label"},
            {"name": "Етикетка Бастурма скін задня", "quantity": 1, "unit": "шт", "type": "label"}
        ]
    },
    # 4. Суджук 50г вакуум
    {
        "source": "Суджук ваговий",
        "target": "Суджук 50г вакуум",
        "type": "vacuum",
        "weight_grams": 50,
        "materials": [
            {"name": "Пакет вакуум 100*200", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Суджук 75*75", "quantity": 1, "unit": "шт", "type": "label"}
        ]
    },
    # 5. Суджук 50г скін
    {
        "source": "Суджук ваговий",
        "target": "Суджук 50г скін",
        "type": "skin",
        "weight_grams": 50,
        "materials": [
            {"name": "Скін лоток нижній", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Скін плівка верхня", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Суджук скін передня", "quantity": 1, "unit": "шт", "type": "label"},
            {"name": "Етикетка Суджук скін задня", "quantity": 1, "unit": "шт", "type": "label"}
        ]
    },
    # 6. Банкетна 50г вакуум
    {
        "source": "Банкетна вагова",
        "target": "Банкетна 50г вакуум",
        "type": "vacuum",
        "weight_grams": 50,
        "materials": [
            {"name": "Пакет вакуум 100*200", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Банкетна 75*75", "quantity": 1, "unit": "шт", "type": "label"}
        ]
    },
    # 7. Банкетна 50г скін
    {
        "source": "Банкетна вагова",
        "target": "Банкетна 50г скін",
        "type": "skin",
        "weight_grams": 50,
        "materials": [
            {"name": "Скін лоток нижній", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Скін плівка верхня", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Банкетна скін передня", "quantity": 1, "unit": "шт", "type": "label"},
            {"name": "Термо етикетка", "quantity": 1, "unit": "шт", "type": "label"}
        ]
    },
    # 8. Банкетна 60г скін
    {
        "source": "Банкетна вагова",
        "target": "Банкетна 60г скін",
        "type": "skin",
        "weight_grams": 60,
        "materials": [
            {"name": "Скін лоток нижній", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Скін плівка верхня", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Банкетна скін передня", "quantity": 1, "unit": "шт", "type": "label"},
            {"name": "Етикетка Банкетна скін задня", "quantity": 1, "unit": "шт", "type": "label"}
        ]
    },
    # 9. Філе курицы 40г вакуум
    {
        "source": "Курка філе",
        "target": "Філе курицы 40г вакуум",
        "type": "vacuum",
        "weight_grams": 40,
        "materials": [
            {"name": "Пакет вакуум 100*200", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Філе курицы 75*75", "quantity": 1, "unit": "шт", "type": "label"}
        ]
    },
    # 10. Пластина 50г вакуум
    {
        "source": "Пластина яловичина",
        "target": "Пластина 50г вакуум",
        "type": "vacuum",
        "weight_grams": 50,
        "materials": [
            {"name": "Пакет вакуум 100*200", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Пластина бастурма 75*75", "quantity": 1, "unit": "шт", "type": "label"}
        ]
    },
    # 11. Конина 50г вакуум
    {
        "source": "Конина вагова",
        "target": "Конина 50г вакуум",
        "type": "vacuum",
        "weight_grams": 50,
        "materials": [
            {"name": "Пакет вакуум 100*200", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Конина 75*75", "quantity": 1, "unit": "шт", "type": "label"}
        ]
    },
    # 12. Конина 50г скін
    {
        "source": "Конина вагова",
        "target": "Конина 50г скін",
        "type": "skin",
        "weight_grams": 50,
        "materials": [
            {"name": "Скін лоток нижній", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Скін плівка верхня", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Конина скін передня", "quantity": 1, "unit": "шт", "type": "label"},
            {"name": "Етикетка Конина скін задня", "quantity": 1, "unit": "шт", "type": "label"}
        ]
    },
    # 13. Махан 50г вакуум
    {
        "source": "Махан ваговий",
        "target": "Махан 50г вакуум",
        "type": "vacuum",
        "weight_grams": 50,
        "materials": [
            {"name": "Пакет вакуум 100*200", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Махан 75*75", "quantity": 1, "unit": "шт", "type": "label"}
        ]
    },
    # 14. Махан 50г скін
    {
        "source": "Махан ваговий",
        "target": "Махан 50г скін",
        "type": "skin",
        "weight_grams": 50,
        "materials": [
            {"name": "Скін лоток нижній", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Скін плівка верхня", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Махан скін передня", "quantity": 1, "unit": "шт", "type": "label"},
            {"name": "Етикетка Махан скін задня", "quantity": 1, "unit": "шт", "type": "label"}
        ]
    },
    # 15-19: Весові варіанти з ланч-боксом
    {
        "source": "Бастурма класична",
        "target": "Бастурма весова фасована",
        "type": "vacuum_bulk",
        "weight_grams": 0,  # Змінна вага
        "materials": [
            {"name": "Пакет вакуум 150*200", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Бастурма 100*50", "quantity": 1, "unit": "шт", "type": "label"},
            {"name": "Ланч-бокс", "quantity": 1, "unit": "шт", "type": "packaging"}
        ]
    },
    {
        "source": "Суджук ваговий",
        "target": "Суджук весовий фасований",
        "type": "vacuum_bulk",
        "weight_grams": 0,
        "materials": [
            {"name": "Пакет вакуум 400*120", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Суджук 75*75", "quantity": 1, "unit": "шт", "type": "label"},
            {"name": "Ланч-бокс", "quantity": 1, "unit": "шт", "type": "packaging"}
        ]
    },
    {
        "source": "Махан ваговий",
        "target": "Махан весовий фасований",
        "type": "vacuum_bulk",
        "weight_grams": 0,
        "materials": [
            {"name": "Пакет вакуум 500*180", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Махан 75*75", "quantity": 1, "unit": "шт", "type": "label"},
            {"name": "Ланч-бокс", "quantity": 1, "unit": "шт", "type": "packaging"}
        ]
    },
    {
        "source": "Конина вагова",
        "target": "Конина весова фасована",
        "type": "vacuum_bulk",
        "weight_grams": 0,
        "materials": [
            {"name": "Пакет вакуум 250*180", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Конина 75*75", "quantity": 1, "unit": "шт", "type": "label"},
            {"name": "Ланч-бокс", "quantity": 1, "unit": "шт", "type": "packaging"}
        ]
    },
    {
        "source": "Банкетна вагова",
        "target": "Банкетна весова фасована",
        "type": "vacuum_bulk",
        "weight_grams": 0,
        "materials": [
            {"name": "Пакет вакуум 250*180", "quantity": 1, "unit": "шт", "type": "packaging"},
            {"name": "Етикетка Банкетна 75*75", "quantity": 1, "unit": "шт", "type": "label"},
            {"name": "Ланч-бокс", "quantity": 1, "unit": "шт", "type": "packaging"}
        ]
    }
]


def check_and_add_materials(conn, cursor):
    """Перевірка та додавання відсутніх матеріалів"""
    print("\n" + "="*80)
    print("ПЕРЕВІРКА МАТЕРІАЛІВ")
    print("="*80)
    
    # Збираємо всі унікальні матеріали
    all_materials = set()
    for recipe in PACKAGING_RECIPES:
        for material in recipe["materials"]:
            all_materials.add(material["name"])
    
    print(f"\nВсього унікальних матеріалів: {len(all_materials)}")
    
    # Перевіряємо наявність кожного
    missing_materials = []
    existing_materials = {}
    
    for material_name in all_materials:
        cursor.execute("SELECT id FROM nomenclature WHERE name = ?", material_name)
        result = cursor.fetchone()
        
        if result:
            existing_materials[material_name] = result[0]
            print(f"  ✅ {material_name}: ID={result[0]}")
        else:
            missing_materials.append(material_name)
            print(f"  ❌ {material_name}: ВІДСУТНІЙ")
    
    # Додаємо відсутні
    if missing_materials:
        print(f"\n➕ Додаю {len(missing_materials)} відсутніх матеріалів...")
        for material_name in missing_materials:
            cursor.execute("""
                INSERT INTO nomenclature (name, unit, category)
                VALUES (?, N'шт', N'Матеріали')
            """, material_name)
            
            cursor.execute("SELECT @@IDENTITY")
            material_id = int(cursor.fetchone()[0])
            existing_materials[material_name] = material_id
            print(f"  ✅ {material_name}: ID={material_id}")
        
        conn.commit()
    
    return existing_materials


def get_product_ids(conn, cursor):
    """Отримання ID весових та фасованих продуктів"""
    print("\n" + "="*80)
    print("ОТРИМАННЯ ID ПРОДУКТІВ")
    print("="*80)
    
    # Весові продукти
    source_ids = {}
    for product_name in WEIGHT_PRODUCTS.keys():
        cursor.execute("SELECT id FROM nomenclature WHERE name LIKE ?", f"%{product_name}%")
        result = cursor.fetchone()
        if result:
            source_ids[product_name] = result[0]
            print(f"  ✅ {product_name}: ID={result[0]}")
        else:
            print(f"  ❌ {product_name}: НЕ ЗНАЙДЕНО!")
    
    # Фасовані продукти
    target_ids = {}
    for recipe in PACKAGING_RECIPES:
        target_name = recipe["target"]
        cursor.execute("SELECT id FROM nomenclature WHERE name = ?", target_name)
        result = cursor.fetchone()
        if result:
            target_ids[target_name] = result[0]
            print(f"  ✅ {target_name}: ID={result[0]}")
        else:
            print(f"  ⚠️  {target_name}: НЕ ЗНАЙДЕНО, потрібно додати")
    
    return source_ids, target_ids


def add_missing_targets(conn, cursor, target_ids):
    """Додавання відсутніх фасованих продуктів"""
    missing_targets = []
    
    for recipe in PACKAGING_RECIPES:
        target_name = recipe["target"]
        if target_name not in target_ids:
            missing_targets.append(recipe)
    
    if missing_targets:
        print(f"\n➕ Додаю {len(missing_targets)} фасованих продуктів...")
        for recipe in missing_targets:
            target_name = recipe["target"]
            unit = "шт" if recipe["weight_grams"] > 0 else "кг"
            
            cursor.execute("""
                INSERT INTO nomenclature (name, unit, category)
                VALUES (?, ?, N'Готова продукція')
            """, target_name, unit)
            
            cursor.execute("SELECT @@IDENTITY")
            target_id = int(cursor.fetchone()[0])
            target_ids[target_name] = target_id
            print(f"  ✅ {target_name}: ID={target_id}")
        
        conn.commit()
    
    return target_ids


def create_packaging_recipes(conn, cursor, source_ids, target_ids, material_ids):
    """Створення рецептів фасовки"""
    print("\n" + "="*80)
    print("СТВОРЕННЯ РЕЦЕПТІВ ФАСОВКИ")
    print("="*80)
    
    created_count = 0
    skipped_count = 0
    
    for recipe_data in PACKAGING_RECIPES:
        source_name = recipe_data["source"]
        target_name = recipe_data["target"]
        
        if source_name not in source_ids or target_name not in target_ids:
            print(f"  ⚠️  Пропускаю {target_name} - відсутні ID")
            skipped_count += 1
            continue
        
        source_id = source_ids[source_name]
        target_id = target_ids[target_name]
        
        # Перевіряємо чи вже існує
        cursor.execute("""
            SELECT id FROM packaging_recipes 
            WHERE source_product_id = ? AND target_product_id = ? AND packaging_type = ?
        """, source_id, target_id, recipe_data["type"])
        
        if cursor.fetchone():
            print(f"  ⚠️  {target_name} вже існує")
            skipped_count += 1
            continue
        
        # Створюємо рецепт
        cursor.execute("""
            INSERT INTO packaging_recipes (
                source_product_id, target_product_id, packaging_type,
                target_weight_grams, is_active
            )
            VALUES (?, ?, ?, ?, 1)
        """, source_id, target_id, recipe_data["type"], recipe_data["weight_grams"])
        
        cursor.execute("SELECT @@IDENTITY")
        recipe_id = int(cursor.fetchone()[0])
        
        # Додаємо матеріали
        for material_data in recipe_data["materials"]:
            material_name = material_data["name"]
            material_id = material_ids.get(material_name)
            
            if not material_id:
                print(f"    ⚠️  Матеріал {material_name} не знайдено")
                continue
            
            cursor.execute("""
                INSERT INTO packaging_recipe_materials (
                    recipe_id, material_id, quantity_per_unit,
                    material_type
                )
                VALUES (?, ?, ?, ?)
            """, recipe_id, material_id, material_data["quantity"], material_data["type"])
        
        print(f"  ✅ {target_name} ({recipe_data['type']}, {recipe_data['weight_grams']}г)")
        created_count += 1
    
    conn.commit()
    
    print(f"\n📊 Створено: {created_count}, Пропущено: {skipped_count}")


def main():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        print("="*80)
        print("SEED PACKAGING RECIPES")
        print("="*80)
        
        # Крок 1: Перевірка та додавання матеріалів
        material_ids = check_and_add_materials(conn, cursor)
        
        # Крок 2: Отримання ID продуктів
        source_ids, target_ids = get_product_ids(conn, cursor)
        
        # Крок 3: Додавання відсутніх фасованих продуктів
        target_ids = add_missing_targets(conn, cursor, target_ids)
        
        # Крок 4: Створення рецептів фасовки
        create_packaging_recipes(conn, cursor, source_ids, target_ids, material_ids)
        
        print("\n" + "="*80)
        print("✅ ЗАВЕРШЕНО!")
        print("="*80)


if __name__ == "__main__":
    main()
