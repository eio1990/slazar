# 🔪 ДОРОЖНЯ КАРТА: РЕОРГАНІЗАЦІЯ ЛОГІКИ РОЗДІЛКИ

## 📋 АНАЛІЗ ЗМІН

### Поточна система (ДО):
```
Яловичина вищий сорт (сировина) 
    ↓ [виробництво]
Бастурма класична (готова продукція)
```

### Нова система (ПІСЛЯ):
```
Яловичина туша (закупка)
    ↓ [РОЗДІЛКА 1 рівень]
├─ Яловичина вищий сорт
├─ Яловичина перший сорт
├─ Яловичина другий сорт
├─ Кістки
├─ Жир
├─ Стек
└─ Відходи

Яловичина вищий сорт
    ↓ [РОЗДІЛКА 2 рівень]
├─ Яловичина на бастурму (спеціальна нарізка)
├─ Яловичина перший сорт (залишки)
├─ Яловичина другий сорт
├─ Стек
└─ Відходи

Яловичина на бастурму
    ↓ [ВИРОБНИЦТВО]
Бастурма класична
```

---

## 🎯 КЛЮЧОВІ ЗМІНИ

### 1. Нова концепція номенклатури:
- **Закупка** (raw): Туша яловичини, туша конини, свинина, індичка
- **Напівфабрикати** (semi-finished): Вищий/перший/другий сорти
- **Спеціальна нарізка** (cut-specific): "На бастурму", "На пластини", "На суджук"
- **Побічні продукти** (by-products): Кістки, жир, стек, відходи
- **Готова продукція** (finished): Бастурма, Суджук, тощо

### 2. Нові процеси:
- **Розділка** (butchery) - окремий процес
- **Виробництво** (production) - використовує результати розділки

### 3. Нова структура даних:
- Рецепти розділки (butchery_recipes)
- Операції розділки (butchery_operations)
- Виходи розділки (butchery_outputs)

---

## 📅 ДОРОЖНЯ КАРТА РЕАЛІЗАЦІЇ

---

## ФАЗА 1: АНАЛІЗ ТА ПЛАНУВАННЯ (День 1, 4-6 годин)

### Завдання 1.1: Аудит поточних даних
**Час: 1-2 години**

Перевірити:
- Які номенклатури є зараз
- Які рецепти використовують яку сировину
- Які партії в процесі (не зламати існуючі)

**SQL для аудиту:**
```sql
-- Поточні сорти м'яса
SELECT id, name, category FROM nomenclature 
WHERE name LIKE '%яловичина%' OR name LIKE '%конина%'

-- Які рецепти використовують яловичину
SELECT r.name, ri.nomenclature_id, n.name as ingredient
FROM recipes r
JOIN recipe_ingredients ri ON r.id = ri.recipe_id
JOIN nomenclature n ON ri.nomenclature_id = n.id
WHERE n.name LIKE '%яловичина%'
```

---

### Завдання 1.2: Дизайн нової структури БД
**Час: 2-3 години**

**Нові таблиці:**

```sql
-- 1. Категорії номенклатури
ALTER TABLE nomenclature ADD nomenclature_type NVARCHAR(50) DEFAULT 'raw';
-- Типи: 'raw' (туша), 'semi' (сорт), 'cut-specific' (нарізка), 
--       'by-product' (кістки, жир), 'finished' (готова продукція)

-- 2. Рецепти розділки
CREATE TABLE butchery_recipes (
    id INT IDENTITY PRIMARY KEY,
    name NVARCHAR(200) NOT NULL,
    source_nomenclature_id INT NOT NULL,  -- Що розділяємо
    description NVARCHAR(500),
    is_active BIT DEFAULT 1,
    created_at DATETIME2 DEFAULT GETUTCDATE(),
    FOREIGN KEY (source_nomenclature_id) REFERENCES nomenclature(id)
);

-- 3. Виходи розділки (що отримуємо)
CREATE TABLE butchery_recipe_outputs (
    id INT IDENTITY PRIMARY KEY,
    recipe_id INT NOT NULL,
    output_nomenclature_id INT NOT NULL,  -- Що отримуємо
    yield_percentage DECIMAL(5,2) NOT NULL,  -- % виходу від вхідної ваги
    is_main_output BIT DEFAULT 0,  -- Основний продукт
    output_type NVARCHAR(50),  -- 'main', 'by-product', 'waste'
    FOREIGN KEY (recipe_id) REFERENCES butchery_recipes(id),
    FOREIGN KEY (output_nomenclature_id) REFERENCES nomenclature(id)
);

-- 4. Операції розділки
CREATE TABLE butchery_operations (
    id INT IDENTITY PRIMARY KEY,
    operation_number NVARCHAR(50) UNIQUE NOT NULL,
    recipe_id INT NOT NULL,
    source_nomenclature_id INT NOT NULL,
    input_weight DECIMAL(10,2) NOT NULL,
    status NVARCHAR(50) DEFAULT 'in_progress',  -- 'in_progress', 'completed'
    started_at DATETIME2 DEFAULT GETUTCDATE(),
    completed_at DATETIME2,
    operator_notes NVARCHAR(500),
    idempotency_key NVARCHAR(200) UNIQUE,
    FOREIGN KEY (recipe_id) REFERENCES butchery_recipes(id),
    FOREIGN KEY (source_nomenclature_id) REFERENCES nomenclature(id)
);

-- 5. Фактичні виходи розділки
CREATE TABLE butchery_operation_outputs (
    id INT IDENTITY PRIMARY KEY,
    operation_id INT NOT NULL,
    output_nomenclature_id INT NOT NULL,
    actual_weight DECIMAL(10,2) NOT NULL,
    notes NVARCHAR(200),
    FOREIGN KEY (operation_id) REFERENCES butchery_operations(id),
    FOREIGN KEY (output_nomenclature_id) REFERENCES nomenclature(id)
);
```

**Індекси:**
```sql
CREATE INDEX idx_butchery_ops_status ON butchery_operations(status);
CREATE INDEX idx_butchery_outputs_operation ON butchery_operation_outputs(operation_id);
```

---

### Завдання 1.3: Маппінг даних
**Час: 1 година**

Створити маппінг:
```
ПОТОЧНА НОМЕНКЛАТУРА → НОВА СТРУКТУРА

Яловичина вищий сорт (ID=1) → type='semi' (залишається)
Яловичина перший сорт (ID=2) → type='semi'
Яловичина другий сорт (ID=3) → type='semi'

ДОДАТИ НОВІ:
Яловичина туша → type='raw' (закупка)
Яловичина на бастурму → type='cut-specific' (результат розділки вищого сорту)
Яловичина на пластини → type='cut-specific'
Яловичина на суджук → type='cut-specific'
Кістки яловичі → type='by-product'
Жир яловичий → type='by-product'
Стек яловичий → type='by-product'
```

---

## ФАЗА 2: BACKEND - НОВА СТРУКТУРА (День 2-3, 12-16 годин)

### Завдання 2.1: Оновлення database.py
**Час: 2 години**

1. Додати nomenclature_type до nomenclature
2. Створити 4 нові таблиці
3. Запустити міграцію

**Файл:** `/app/backend/database.py`

---

### Завдання 2.2: Створити models.py для розділки
**Час: 2 години**

```python
# models.py
class ButcheryRecipeOutput(BaseModel):
    output_nomenclature_id: int
    output_name: str
    yield_percentage: float
    is_main_output: bool
    output_type: str

class ButcheryRecipe(BaseModel):
    id: int
    name: str
    source_nomenclature_id: int
    source_name: str
    outputs: List[ButcheryRecipeOutput]

class ButcheryOperationCreate(BaseModel):
    recipe_id: int
    source_nomenclature_id: int
    input_weight: float
    notes: Optional[str] = None
    idempotency_key: str

class ButcheryOutputInput(BaseModel):
    output_nomenclature_id: int
    actual_weight: float
    notes: Optional[str] = None

class ButcheryOperationComplete(BaseModel):
    outputs: List[ButcheryOutputInput]
    notes: Optional[str] = None
    idempotency_key: str
```

---

### Завдання 2.3: Створити butchery_api.py
**Час: 6-8 годин**

**Endpoints:**

```python
# 1. Отримати рецепти розділки
@router.get("/butchery/recipes")
async def get_butchery_recipes(source_id: Optional[int] = None):
    """Список рецептів розділки"""
    # Фільтр по source (що розділяємо)
    # Повертає рецепт з усіма виходами

# 2. Отримати деталі рецепту
@router.get("/butchery/recipes/{recipe_id}")
async def get_butchery_recipe(recipe_id: int):
    """Деталі рецепту з усіма виходами"""

# 3. Створити операцію розділки
@router.post("/butchery/operations")
async def create_butchery_operation(operation: ButcheryOperationCreate):
    """
    Початок розділки:
    1. Перевірити наявність сировини на складі
    2. Списати сировину (input_weight)
    3. Створити запис операції
    4. Повернути operation_id
    """

# 4. Список операцій
@router.get("/butchery/operations")
async def get_butchery_operations(
    status: Optional[str] = None,
    limit: int = 50
):
    """Список операцій розділки з фільтрацією"""

# 5. Деталі операції
@router.get("/butchery/operations/{operation_id}")
async def get_butchery_operation(operation_id: int):
    """Деталі операції з фактичними виходами"""

# 6. Завершити розділку
@router.put("/butchery/operations/{operation_id}/complete")
async def complete_butchery_operation(
    operation_id: int,
    completion: ButcheryOperationComplete
):
    """
    Завершення розділки:
    1. Записати фактичні виходи
    2. Оприбуткувати кожен вихід на склад (receipt)
    3. Створити stock_movements для кожного
    4. Перевірити ідемпотентність
    5. Змінити status на 'completed'
    """

# 7. Аналітика розділки
@router.get("/butchery/analytics")
async def get_butchery_analytics(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """
    Аналітика:
    - % виходу по рецептах (факт vs норма)
    - Відходи
    - Топ продукти
    """
```

**Бізнес-логіка:**

```python
# Приклад: Завершення розділки
def complete_butchery_operation(operation_id, outputs):
    # 1. Отримати операцію
    operation = get_operation(operation_id)
    
    # 2. Перевірка ідемпотентності
    if operation.status == 'completed':
        return "Already completed"
    
    # 3. Записати фактичні виходи
    for output in outputs:
        insert_butchery_output(
            operation_id=operation_id,
            nomenclature_id=output.output_nomenclature_id,
            actual_weight=output.actual_weight
        )
        
        # 4. Оприбуткувати на склад
        create_stock_receipt(
            nomenclature_id=output.output_nomenclature_id,
            quantity=output.actual_weight,
            source_operation_type='butchery',
            source_operation_id=operation.operation_number
        )
    
    # 5. Змінити статус
    update_operation_status(operation_id, 'completed')
```

---

### Завдання 2.4: Seed дані для розділки
**Час: 2-3 години**

Створити `/app/backend/seed_butchery_recipes.py`:

```python
# Приклад структури

BUTCHERY_RECIPES = [
    {
        'name': 'Розділка туші яловичини (1 рівень)',
        'source': 'Яловичина туша',
        'outputs': [
            {'name': 'Яловичина вищий сорт', 'yield': 25.0, 'type': 'main'},
            {'name': 'Яловичина перший сорт', 'yield': 30.0, 'type': 'main'},
            {'name': 'Яловичина другий сорт', 'yield': 20.0, 'type': 'main'},
            {'name': 'Кістки яловичі', 'yield': 15.0, 'type': 'by-product'},
            {'name': 'Жир яловичий', 'yield': 5.0, 'type': 'by-product'},
            {'name': 'Стек яловичий', 'yield': 3.0, 'type': 'by-product'},
            {'name': 'Відходи яловичі', 'yield': 2.0, 'type': 'waste'},
        ]
    },
    {
        'name': 'Розділка вищого сорту (2 рівень)',
        'source': 'Яловичина вищий сорт',
        'outputs': [
            {'name': 'Яловичина на бастурму', 'yield': 70.0, 'type': 'main'},
            {'name': 'Яловичина перший сорт', 'yield': 20.0, 'type': 'main'},
            {'name': 'Стек яловичий', 'yield': 8.0, 'type': 'by-product'},
            {'name': 'Відходи яловичі', 'yield': 2.0, 'type': 'waste'},
        ]
    },
    {
        'name': 'Розділка першого сорту (2 рівень)',
        'source': 'Яловичина перший сорт',
        'outputs': [
            {'name': 'Яловичина на пластини', 'yield': 75.0, 'type': 'main'},
            {'name': 'Яловичина другий сорт', 'yield': 20.0, 'type': 'main'},
            {'name': 'Стек яловичий', 'yield': 3.0, 'type': 'by-product'},
            {'name': 'Відходи яловичі', 'yield': 2.0, 'type': 'waste'},
        ]
    },
    {
        'name': 'Розділка другого сорту (2 рівень)',
        'source': 'Яловичина другий сорт',
        'outputs': [
            {'name': 'Яловичина на суджук', 'yield': 90.0, 'type': 'main'},
            {'name': 'Стек яловичий', 'yield': 8.0, 'type': 'by-product'},
            {'name': 'Відходи яловичі', 'yield': 2.0, 'type': 'waste'},
        ]
    },
]

# Аналогічно для конини, свинини, індички
```

---

### Завдання 2.5: Оновити recipe_ingredients
**Час: 1-2 години**

Змінити рецепти виробництва:

```sql
-- Старий рецепт Бастурми
UPDATE recipe_ingredients 
SET nomenclature_id = (SELECT id FROM nomenclature WHERE name = 'Яловичина на бастурму')
WHERE recipe_id = (SELECT id FROM recipes WHERE name = 'Бастурма класична')
AND nomenclature_id = (SELECT id FROM nomenclature WHERE name = 'Яловичина вищий сорт')
```

---

## ФАЗА 3: FRONTEND - НОВИЙ МОДУЛЬ РОЗДІЛКИ (День 4-5, 12-16 годин)

### Завдання 3.1: Новий таб "Розділка"
**Час: 2 години**

Створити `/app/frontend/app/(tabs)/butchery.tsx`:

```typescript
// Головний екран розділки
// - Список операцій розділки
// - Фільтри: В процесі / Завершені
// - Кнопка "Нова розділка"
// - Статистика: Виходи vs норми
```

---

### Завдання 3.2: Екран вибору рецепту розділки
**Час: 2 години**

`/app/frontend/app/butchery/select-recipe.tsx`:

```typescript
// 1. Показати доступну сировину на складі
// 2. Для кожної сировини показати можливі рецепти розділки
// 3. Відображати очікувані виходи
// 4. Кнопка "Почати розділку"
```

---

### Завдання 3.3: Екран створення операції
**Час: 2 години**

`/app/frontend/app/butchery/new-operation.tsx`:

```typescript
// 1. Вибраний рецепт (source → outputs)
// 2. Введення ваги сировини
// 3. Автоматичний розрахунок очікуваних виходів
// 4. Підтвердження початку розділки
// 5. Списання сировини
```

---

### Завдання 3.4: Екран виконання розділки
**Час: 4 години**

`/app/frontend/app/butchery/[id].tsx`:

```typescript
// 1. Інформація про операцію
// 2. Очікувані виходи з recipe
// 3. Форма введення фактичних виходів:
//    - Для кожного виходу: input поле ваги
//    - Автоматичний розрахунок % від норми
//    - Підсвітка: зелений (норма), жовтий (відхилення < 10%), червоний (> 10%)
// 4. Валідація: сума виходів не може перевищувати вхід + 5%
// 5. Кнопка "Завершити розділку"
// 6. Оприбуткування всіх виходів
```

---

### Завдання 3.5: Екран аналітики розділки
**Час: 2 години**

`/app/frontend/app/butchery/analytics.tsx`:

```typescript
// 1. Графік виходів по датах
// 2. Порівняння факт vs норма по рецептах
// 3. Топ-5 продуктів розділки
// 4. % відходів
```

---

### Завдання 3.6: Оновити навігацію
**Час: 1 година**

Додати таб "Розділка" в `app/(tabs)/_layout.tsx`:

```typescript
<Tabs.Screen
  name="butchery"
  options={{
    title: 'Розділка',
    tabBarIcon: ({ color }) => <MaterialCommunityIcons name="knife" size={28} color={color} />,
  }}
/>
```

---

## ФАЗА 4: ОНОВЛЕННЯ МОДУЛЯ ВИРОБНИЦТВА (День 6, 4-6 годин)

### Завдання 4.1: Видалити trim з виробництва
**Час: 1 година**

1. Видалити `trim-form.tsx`
2. Видалити роутинг для trim з `[id].tsx`
3. Видалити trim з recipe_steps (або позначити неактивним)

---

### Завдання 4.2: Оновити списки сировини
**Час: 2 години**

При створенні партії виробництва:
- Показувати тільки `nomenclature_type = 'cut-specific'`
- "Яловичина на бастурму" замість "Яловичина вищий сорт"

---

### Завдання 4.3: Оновити валідації
**Час: 1 година**

Backend: перевіряти що використовується правильна номенклатура:
```python
# recipe_ingredients повинні мати type='cut-specific' для м'яса
```

---

### Завдання 4.4: Оновити seed_recipes.py
**Час: 1-2 години**

Змінити всі рецепти:
```python
# Бастурма класична
'ingredients': [
    {'name': 'Яловичина на бастурму', 'quantity': 100},  # Було: Яловичина вищий сорт
]
```

---

## ФАЗА 5: МІГРАЦІЯ ДАНИХ (День 7, 2-4 години)

### Завдання 5.1: Скрипт міграції номенклатури
**Час: 2 години**

`/app/backend/migrate_nomenclature.py`:

```python
# 1. Додати nomenclature_type до існуючих номенклатур
# 2. Створити нові номенклатури (туша, нарізка, побічні)
# 3. Оновити recipe_ingredients з нових номенклатур
```

---

### Завдання 5.2: Seed рецептів розділки
**Час: 1 час**

Запустити seed_butchery_recipes.py:
- 4 рецепти для яловичини
- 4 рецепти для конини
- 2-3 для свинини, індички

---

### Завдання 5.3: Тестові дані
**Час: 1 година**

Створити тестові операції розділки для перевірки

---

## ФАЗА 6: ТЕСТУВАННЯ ТА ВИПРАВЛЕННЯ (День 8-9, 8-12 годин)

### Завдання 6.1: Backend тестування
**Час: 4 години**

Тести через deep_testing_backend_v2:
1. Створення операції розділки
2. Списання сировини
3. Завершення з виходами
4. Оприбуткування
5. Ідемпотентність
6. Валідації

---

### Завдання 6.2: Frontend тестування
**Час: 4 години**

Повний цикл:
1. Закупка туші (оприбуткування)
2. Розділка туші → отримання сортів
3. Розділка сорту → отримання нарізки
4. Виробництво з нарізки → готова продукція
5. Фасування

---

### Завдання 6.3: Виправлення багів
**Час: 2-4 години**

За результатами тестування

---

## ФАЗА 7: ДОКУМЕНТАЦІЯ (День 10, 2-3 години)

### Завдання 7.1: Оновити документацію
**Час: 1-2 години**

- Оновити PRODUCTION_LOGIC.md
- Створити BUTCHERY_LOGIC.md
- Оновити COMPREHENSIVE_ANALYSIS.md

---

### Завдання 7.2: Інструкції для користувача
**Час: 1 година**

Створити покроковий гайд:
1. Як оприбуткувати тушу
2. Як виконати розділку
3. Як використати результати в виробництві

---

## 📊 ЗВЕДЕНА ТАБЛИЦЯ

| Фаза | Час | Критичність | Складність |
|------|-----|-------------|-----------|
| 1. Аналіз та планування | 4-6 год | 🔴 Критично | Низька |
| 2. Backend | 12-16 год | 🔴 Критично | Висока |
| 3. Frontend | 12-16 год | 🔴 Критично | Висока |
| 4. Оновлення виробництва | 4-6 год | 🟡 Важливо | Середня |
| 5. Міграція даних | 2-4 год | 🔴 Критично | Середня |
| 6. Тестування | 8-12 год | 🔴 Критично | Середня |
| 7. Документація | 2-3 год | 🟢 Бажано | Низька |

**ЗАГАЛОМ: 44-63 години (~6-8 робочих днів)**

---

## 🎯 КРИТИЧНІ РИЗИКИ

### Ризик 1: Існуючі партії в процесі
**Проблема:** Партії створені ДО змін використовують стару номенклатуру  
**Рішення:** 
- Зберегти сумісність зі старими партіями
- Нові партії тільки з нової номенклатури

### Ризик 2: Складність міграції даних
**Проблема:** Багато залежностей між таблицями  
**Рішення:**
- Детальний скрипт міграції з rollback
- Бекап БД перед міграцією

### Ризик 3: Зміна бізнес-процесів
**Проблема:** Оператори звикли до старої логіки  
**Рішення:**
- Детальні інструкції
- Тренування на тестових даних

---

## ✅ КРИТЕРІЇ ГОТОВНОСТІ

1. ✅ Можна створити операцію розділки туші
2. ✅ Виходи розділки оприбутковуються на склад
3. ✅ Виробництво використовує результати розділки
4. ✅ Видалено обрізки з виробництва
5. ✅ Аналітика показує виходи розділки
6. ✅ Всі тести проходять
7. ✅ Документація оновлена

---

## 🚀 НАСТУПНІ КРОКИ

**ПІДТВЕРДЖУЄТЕ ПЛАН?**

Якщо так, я почну з:
1. Фаза 1, Завдання 1.1: Аудит поточних даних
2. Створення нових таблиць БД
3. Backend API для розділки

**Чи є зауваження до плану?**
