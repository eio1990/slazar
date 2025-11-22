"""
Детальна перевірка всіх рецептів виробництва
"""
import sys
sys.path.append('/app/backend')

from database import get_db_connection
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

with get_db_connection() as conn:
    cursor = conn.cursor()
    
    # Перевірка кожного рецепту
    cursor.execute("""
        SELECT r.id, r.name, r.target_product_id, n.name as target_name
        FROM recipes r
        LEFT JOIN nomenclature n ON r.target_product_id = n.id
        ORDER BY r.id
    """)
    
    recipes = cursor.fetchall()
    
    print("ДЕТАЛЬНА ПЕРЕВІРКА РЕЦЕПТІВ:")
    print("="*80)
    
    issues = []
    
    for recipe in recipes:
        recipe_id, recipe_name, target_id, target_name = recipe
        
        print(f"\nРецепт ID {recipe_id}: {recipe_name}")
        print(f"  Target: ID {target_id} - {target_name}")
        
        # Перевірка інгредієнтів
        cursor.execute("""
            SELECT ri.nomenclature_id, n.name, ri.quantity_per_kg, n.category
            FROM recipe_ingredients ri
            LEFT JOIN nomenclature n ON ri.nomenclature_id = n.id
            WHERE ri.recipe_id = ?
            ORDER BY n.name
        """, recipe_id)
        
        ingredients = cursor.fetchall()
        
        if ingredients:
            print(f"  Інгредієнти ({len(ingredients)}):")
            for ing_id, ing_name, qty, category in ingredients:
                if ing_name:
                    print(f"    - ID {ing_id}: {ing_name} ({qty} г/кг) [{category}]")
                else:
                    print(f"    - ❌ ID {ing_id}: НОМЕНКЛАТУРА НЕ ЗНАЙДЕНА!")
                    issues.append(f"Recipe {recipe_id}: ingredient ID {ing_id} not found")
        else:
            print("  ⚠️ Немає інгредієнтів!")
            issues.append(f"Recipe {recipe_id} has no ingredients")
        
        # Перевірка чи назва рецепту співпадає з target product
        if target_name:
            # Для "вагових" рецептів - видалити "ваговий/вагова"
            clean_recipe_name = recipe_name.replace(" вагова", "").replace(" ваговий", "")
            clean_recipe_name = clean_recipe_name.replace(" сиров'ялена", "").replace(" класична", "")
            
            if "Бастурма з конини" in recipe_name and target_name == "Конина":
                issues.append(f"Recipe {recipe_id}: name mismatch - '{recipe_name}' → target '{target_name}'")
            elif clean_recipe_name.lower() != target_name.lower():
                if not ("Бастурма" in recipe_name and target_name == "Бастурма"):
                    issues.append(f"Recipe {recipe_id}: name mismatch - '{recipe_name}' → target '{target_name}'")
        
        print("-"*80)
    
    print("\n" + "="*80)
    print("ЗНАЙДЕНІ ПРОБЛЕМИ:")
    print("="*80)
    
    if issues:
        for issue in issues:
            print(f"  ❌ {issue}")
    else:
        print("  ✅ Проблем не знайдено!")
    
    print("\n" + "="*80)
    print("РЕКОМЕНДАЦІЇ ПО ОНОВЛЕННЮ:")
    print("="*80)
    
    updates = [
        (3, "Бастурма з конини вагова", "Конина", 108),
        (8, "Суджук ваговий", "Суджук", 96),
        (9, "Махан ваговий", "Махан", 111),
        (4, "Індичка сиров'ялена", "Індичка сиров'ялена", 106),  # Перевірити чи потрібно змінити на 233
    ]
    
    print("\nОНОВИТИ НАЗВИ РЕЦЕПТІВ:")
    for recipe_id, old_name, new_name, target_id in updates:
        print(f"  Recipe {recipe_id}: '{old_name}' → '{new_name}'")
