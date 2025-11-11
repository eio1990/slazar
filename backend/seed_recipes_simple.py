# -*- coding: utf-8 -*-
"""
Simplified seed for recipes
"""
import json
from database import get_db_connection
from dotenv import load_dotenv

load_dotenv()

def seed_recipes_simple():
    """Seed only basic recipe structure"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Simple recipe data: (name, target_product_name, yield_min, yield_max)
        recipes_data = [
            ('Бастурма класична', 'Бастурма класична вагова', 73.0, 78.0),
            ('Бастурма з конини вагова', 'Бастурма з конини вагова', 67.0, 68.0),
            ('Індичка сиров\'ялена', 'Індичка сиров\'ялена вагова', 58.0, 61.0),
            ('Курка сиров\'ялена', 'Курка сиров\'ялена вагова', 53.0, 55.0),
            ('Свинина сиров\'ялена', 'Свинина сиров\'ялена вагова', 62.0, 64.0),
            ('Пластина яловичина', 'Пластина яловичина вагова', 53.0, 56.0),
            ('Суджук ваговий', 'Суджук ваговий', 60.0, 62.0),
            ('Махан ваговий', 'Махан ваговий', 60.0, 66.0),
        ]
        
        for recipe_name, product_name, yield_min, yield_max in recipes_data:
            # Get target product ID
            cursor.execute("SELECT id FROM nomenclature WHERE name = ?", product_name)
            result = cursor.fetchone()
            if not result:
                print(f"❌ Продукт '{product_name}' не знайдено")
                continue
            
            product_id = result[0]
            
            # Check if recipe exists
            cursor.execute("SELECT id FROM recipes WHERE name = ?", recipe_name)
            if cursor.fetchone():
                print(f"⏭️  Рецепт '{recipe_name}' вже існує")
                continue
            
            # Insert recipe
            cursor.execute("""
                INSERT INTO recipes (name, target_product_id, expected_yield_min, expected_yield_max, description)
                VALUES (?, ?, ?, ?, ?)
            """, recipe_name, product_id, yield_min, yield_max, f'Рецепт для {product_name}')
            
            recipe_id = cursor.execute("SELECT @@IDENTITY").fetchone()[0]
            print(f"✅ Створено рецепт: {recipe_name} (ID={recipe_id})")
            
            # Add basic steps for each recipe
            add_basic_steps(cursor, recipe_id, recipe_name)
        
        conn.commit()
        print("\n✅ Рецепти успішно додано")

def add_basic_steps(cursor, recipe_id, recipe_name):
    """Add basic production steps"""
    if 'Бастурма класична' in recipe_name:
        steps = [
            (1, 'trim', 'Обрізка та підготовка', 0, '{"trim_percent_min": 0, "trim_percent_max": 0}'),
            (2, 'salt', 'Засолка', 3, '{"salt_per_100kg": 20.67, "water_per_100kg": 66.67}'),
            (3, 'wash', 'Промивка', 0.125, '{"duration_hours": 3}'),
            (4, 'dry', 'Сушка 1', 1, '{"type": "initial"}'),
            (5, 'press', 'Прес 1', 1, '{"press_number": 1}'),
            (6, 'dry', 'Сушка 2', 4, '{"days_min": 3, "days_max": 4}'),
            (7, 'mix', 'Нанесення чаману', 0, '{"mix_type": "chaman", "mix_id": 134}'),
            (8, 'dry', 'Сушка фінальна', 4, '{"days_min": 3, "days_max": 4}')
        ]
    elif 'конини' in recipe_name:
        steps = [
            (1, 'trim', 'Обрізка та підготовка', 0, '{}'),
            (2, 'salt', 'Засолка', 3, '{"salt_per_100kg": 20.67, "water_per_100kg": 66.67}'),
            (3, 'wash', 'Промивка', 0.125, '{"duration_hours": 3}'),
            (4, 'dry', 'Сушка 1', 1, '{}'),
            (5, 'sugar', 'Масажер з цукром', 0.083, '{"sugar_per_kg": 20}'),
            (6, 'dry', 'В\'ялення', 1, '{}'),
            (7, 'press', 'Прес 1', 1, '{}'),
            (8, 'dry', 'Сушка 2', 4, '{"days_min": 3, "days_max": 4}'),
            (9, 'mix', 'Нанесення маринаду', 0, '{"mix_type": "marinade_horse", "mix_id": 135}'),
            (10, 'dry', 'Сушка фінальна', 4, '{"days_min": 3, "days_max": 4}')
        ]
    elif 'Індичка' in recipe_name:
        steps = [
            (1, 'trim', 'Обрізка філе', 0, '{"trim_percent_min": 7, "trim_percent_max": 10}'),
            (2, 'marinade', 'Виготовлення маринаду', 0, '{}'),
            (3, 'vacuum', 'Вакуумна фасовка та маринування', 6, '{"marinate_days_min": 5, "marinate_days_max": 6}'),
            (4, 'press', 'Пресування', 1, '{}'),
            (5, 'dry', 'Сушка', 5, '{"days_min": 3, "days_max": 5}')
        ]
    elif 'Курка' in recipe_name:
        steps = [
            (1, 'trim', 'Обрізка філе', 0, '{"trim_percent_min": 22, "trim_percent_max": 25}'),
            (2, 'marinade', 'Виготовлення маринаду', 0, '{}'),
            (3, 'vacuum', 'Вакуумна фасовка та маринування', 5, '{"marinate_days_min": 4, "marinate_days_max": 5}'),
            (4, 'press', 'Пресування', 1, '{}'),
            (5, 'dry', 'Сушка', 3, '{"days_min": 2, "days_max": 3}')
        ]
    elif 'Свинина' in recipe_name:
        steps = [
            (1, 'trim', 'Обрізка', 0, '{"trim_percent_min": 15, "trim_percent_max": 20}'),
            (2, 'marinade', 'Виготовлення маринаду', 0, '{}'),
            (3, 'vacuum', 'Вакуумна фасовка та маринування', 6, '{"marinate_days_min": 5, "marinate_days_max": 6}'),
            (4, 'press', 'Пресування', 1, '{}'),
            (5, 'dry', 'Сушка', 6, '{"days_min": 5, "days_max": 6}')
        ]
    elif 'Пластина' in recipe_name:
        steps = [
            (1, 'trim', 'Обрізка та підготовка', 0, '{}'),
            (2, 'marinade', 'Виготовлення маринаду', 0, '{}'),
            (3, 'vacuum', 'Вакуумна фасовка та маринування', 6, '{"marinate_days_min": 4, "marinate_days_max": 6}'),
            (4, 'press', 'Пресування', 1, '{}'),
            (5, 'dry', 'Сушка', 3, '{"days_min": 2, "days_max": 3}')
        ]
    elif 'Суджук' in recipe_name:
        steps = [
            (1, 'trim', 'Підготовка м\'яса', 0, '{}'),
            (2, 'marinade_spices', 'Замішування зі специями', 2, '{}'),
            (3, 'grind', 'Помол м\'яса', 0, '{}'),
            (4, 'massage', 'Масажер з водою та барвником', 0, '{"water_per_100kg": 15}'),
            (5, 'stuff', 'Заправка в кишку', 0, '{}'),
            (6, 'dry', 'Сушка 1', 3, '{}'),
            (7, 'press', 'Прес 1', 1, '{}'),
            (8, 'dry', 'Сушка 2', 2, '{"days_min": 1, "days_max": 2}'),
            (9, 'press', 'Прес 2', 1, '{}'),
            (10, 'dry', 'Сушка фінальна', 4, '{"days_min": 3, "days_max": 4}')
        ]
    elif 'Махан' in recipe_name:
        steps = [
            (1, 'trim', 'Підготовка конини', 0, '{}'),
            (2, 'marinade_first', 'Перший маринад та масажер', 5, '{}'),
            (3, 'marinade_second', 'Другий маринад з гусарською', 0, '{}'),
            (4, 'stuff', 'Заправка в кишку/оболонку', 0, '{}'),
            (5, 'cure', 'В\'ялення в холоді', 10, '{}'),
            (6, 'dry', 'Сушка', 10, '{}')
        ]
    else:
        return  # No steps for unknown recipe
    
    for step_order, step_type, step_name, duration, params in steps:
        cursor.execute("""
            INSERT INTO recipe_steps (recipe_id, step_order, step_type, step_name, duration_days, parameters)
            VALUES (?, ?, ?, ?, ?, ?)
        """, recipe_id, step_order, step_type, step_name, duration, params)

if __name__ == "__main__":
    seed_recipes_simple()
