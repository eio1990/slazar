# Технічне завдання: Модуль розділки м'яса (Butchery)

**Версія:** 1.0
**Дата:** 18 грудня 2025
**Статус:** Production Ready

---

## 1. Загальний опис

Модуль розділки призначений для автоматизації процесу розділки туш на полуфабрикати з автоматичним розрахунком виходу продукції та обліком відходів.

### 1.1 Бізнес-процес

```
1. Оператор обирає тип сировини (яловичина/конина)
   ↓
2. Обирає рівень/сорт (перший/вищий/другий)
   ↓
3. Обирає конкретний рецепт розділки
   ↓
4. Вводить вагу туші
   ↓
5. Система показує очікуваний вихід полуфабрикатів
   ↓
6. Оператор вводит фактичні ваги полуфабрикатів
   ↓
7. Система:
   - Списує сировину зі складу
   - Оприходує полуфабрикати
   - Фіксує відходи (БЕЗ оприходування на склад)
```

---

## 2. Структура даних

### 2.1 Таблиця: butchery_recipes

Зберігає рецепти розділки (шаблони процесу).

**Поля:**
```sql
id                      INT PRIMARY KEY IDENTITY
name                    NVARCHAR(255) NOT NULL           -- "Розділка яловичини вищого сорту"
source_nomenclature_id  INT NOT NULL → nomenclature(id)  -- ID туші (сировина)
description             NVARCHAR(MAX) NULL               -- Опис процесу
level                   NVARCHAR(50) NULL                -- "1", "2", "вищий"
is_active               BIT NOT NULL DEFAULT 1           -- Чи активний рецепт
created_at              DATETIME2 DEFAULT GETUTCDATE()
```

**Приклади рецептів:**
- "Розділка яловичини вищого сорту" (source: яловичина вищого сорту)
- "Розділка конини першого сорту" (source: конина першого сорту)

### 2.2 Таблиця: butchery_recipe_outputs

Визначає які полуфабрикати отримуємо з рецепту та їх відсоток виходу.

**Поля:**
```sql
id                      INT PRIMARY KEY IDENTITY
recipe_id               INT NOT NULL → butchery_recipes(id)
output_nomenclature_id  INT NOT NULL → nomenclature(id)  -- ID полуфабрикату
yield_percentage        DECIMAL(5,2) NOT NULL            -- Відсоток виходу (0-100)
is_main_output          BIT DEFAULT 0                    -- Чи це основний продукт
output_type             NVARCHAR(50)                     -- "semifinished", "waste", "other"
```

**Приклад:**
Рецепт "Розділка яловичини вищого сорту" (100 кг туші):
- Філе яловичини: 35% (35 кг)
- Грудинка яловичини: 25% (25 кг)
- Лопатка яловичини: 20% (20 кг)
- Відходи: 20% (20 кг) - НЕ оприходується

### 2.3 Таблиця: butchery_operations

Фактичні операції розділки.

**Поля:**
```sql
id                      INT PRIMARY KEY IDENTITY
operation_number        NVARCHAR(50) NOT NULL UNIQUE     -- "BUT-20251218-001"
recipe_id               INT NOT NULL → butchery_recipes(id)
source_nomenclature_id  INT NOT NULL → nomenclature(id)  -- ID туші
input_weight            DECIMAL(18,6) NOT NULL           -- Вага туші (кг)
status                  NVARCHAR(50) NOT NULL            -- "in_progress", "completed"
started_at              DATETIME2 DEFAULT GETUTCDATE()
completed_at            DATETIME2 NULL
operator_notes          NVARCHAR(MAX) NULL
idempotency_key         NVARCHAR(255) NOT NULL UNIQUE
```

### 2.4 Таблиця: butchery_operation_outputs

Фактичні результати розділки.

**Поля:**
```sql
id                      INT PRIMARY KEY IDENTITY
operation_id            INT NOT NULL → butchery_operations(id)
output_nomenclature_id  INT NOT NULL → nomenclature(id)
expected_weight         DECIMAL(18,6) NULL               -- Очікувана вага (за рецептом)
actual_weight           DECIMAL(18,6) NOT NULL           -- Фактична вага
notes                   NVARCHAR(MAX) NULL
```

---

## 3. API Endpoints

### 3.1 GET /api/butchery/recipes

**Призначення:** Отримати список рецептів розділки

**Query параметри:**
- `source_id` (int, optional) - фільтр по сировині
- `level` (int, optional) - фільтр по рівню (1 або 2)

**Response:**
```json
{
  "recipes": [
    {
      "id": 1,
      "name": "Розділка яловичини вищого сорту",
      "source_nomenclature_id": 1,
      "source_name": "Яловичина вищого сорту",
      "description": "Розділка туші яловичини на полуфабрикати",
      "level": "вищий",
      "is_active": true,
      "outputs": [
        {
          "output_nomenclature_id": 201,
          "output_name": "Філе яловичини",
          "yield_percentage": 35.0,
          "is_main_output": true,
          "output_type": "semifinished"
        },
        {
          "output_nomenclature_id": 202,
          "output_name": "Грудинка яловичини",
          "yield_percentage": 25.0,
          "is_main_output": false,
          "output_type": "semifinished"
        }
      ]
    }
  ]
}
```

### 3.2 GET /api/butchery/recipes/{recipe_id}

**Призначення:** Отримати деталі рецепту

**Response:** Той же формат що і для списку, але один рецепт

### 3.3 POST /api/butchery/operations

**Призначення:** Створити операцію розділки

**Request body:**
```json
{
  "recipe_id": 1,
  "source_nomenclature_id": 1,
  "input_weight": 100.5,
  "outputs": [
    {
      "output_nomenclature_id": 201,
      "actual_weight": 36.2
    },
    {
      "output_nomenclature_id": 202,
      "actual_weight": 24.8
    },
    {
      "output_nomenclature_id": 203,
      "actual_weight": 19.5
    }
  ],
  "waste_weight": 20.0,
  "operator_notes": "Туша якісна",
  "idempotency_key": "but-uuid-12345"
}
```

**Response:**
```json
{
  "operation_id": 42,
  "operation_number": "BUT-20251218-001",
  "status": "completed",
  "summary": {
    "input_weight": 100.5,
    "total_output_weight": 80.5,
    "waste_weight": 20.0,
    "outputs": [
      {
        "nomenclature_id": 201,
        "name": "Філе яловичини",
        "expected_weight": 35.175,
        "actual_weight": 36.2,
        "deviation_percent": 2.91
      }
    ]
  },
  "stock_movements": [
    {
      "id": 1001,
      "nomenclature_id": 1,
      "quantity": -100.5,
      "operation_type": "butchery_source"
    },
    {
      "id": 1002,
      "nomenclature_id": 201,
      "quantity": 36.2,
      "operation_type": "butchery_output"
    }
  ]
}
```

**Бізнес-логіка:**
1. Перевірити наявність сировини на складі (>= input_weight)
2. Створити запис butchery_operations зі статусом "in_progress"
3. Списати сировину зі складу (-input_weight)
4. Створити записи butchery_operation_outputs
5. Оприходити кожен полуфабрикат (+actual_weight)
6. Відходи НЕ оприходуються, лише фіксуються в metadata
7. Змінити статус операції на "completed"
8. Повернути результат

**Ідемпотентність:**
- Якщо операція з таким idempotency_key вже існує - повернути її результат без виконання

### 3.4 GET /api/butchery/operations

**Призначення:** Отримати список операцій розділки

**Query параметри:**
- `limit` (int, default=50) - кількість записів
- `offset` (int, default=0) - зсув
- `status` (string, optional) - фільтр по статусу
- `date_from` (datetime, optional) - фільтр по даті
- `date_to` (datetime, optional) - фільтр по даті

**Response:**
```json
{
  "operations": [
    {
      "id": 42,
      "operation_number": "BUT-20251218-001",
      "recipe_name": "Розділка яловичини вищого сорту",
      "source_name": "Яловичина вищого сорту",
      "input_weight": 100.5,
      "status": "completed",
      "started_at": "2025-12-18T10:30:00",
      "completed_at": "2025-12-18T11:45:00",
      "outputs_count": 3
    }
  ],
  "total": 156,
  "limit": 50,
  "offset": 0
}
```

### 3.5 GET /api/butchery/operations/{operation_id}

**Призначення:** Отримати деталі операції

**Response:**
```json
{
  "id": 42,
  "operation_number": "BUT-20251218-001",
  "recipe": {
    "id": 1,
    "name": "Розділка яловичини вищого сорту"
  },
  "source": {
    "nomenclature_id": 1,
    "name": "Яловичина вищого сорту"
  },
  "input_weight": 100.5,
  "status": "completed",
  "started_at": "2025-12-18T10:30:00",
  "completed_at": "2025-12-18T11:45:00",
  "operator_notes": "Туша якісна",
  "outputs": [
    {
      "output_nomenclature_id": 201,
      "output_name": "Філе яловичини",
      "expected_weight": 35.175,
      "actual_weight": 36.2,
      "deviation_kg": 1.025,
      "deviation_percent": 2.91
    }
  ],
  "waste_weight": 20.0
}
```

---

## 4. Frontend структура

### 4.1 Екрани (в app/butchery/)

**1. select-meat-type.tsx**
- Вибір типу м'яса (яловичина/конина)
- Показує картки з назвами та іконками
- При виборі → перехід до select-grade

**2. select-grade.tsx**
- Вибір сорту/рівня (перший/вищий/другий)
- Фільтрується по обраному типу м'яса
- При виборі → перехід до select-recipe

**3. select-recipe.tsx**
- Список рецептів розділки (відфільтровано по типу та сорту)
- Показує:
  - Назву рецепту
  - Опис
  - Список очікуваних виходів (з відсотками)
- При виборі → перехід до input-weight

**4. input-weight.tsx**
- Ввід ваги туші
- Кнопки: +/- для швидкого регулювання
- Показує розрахований очікуваний вихід по кожному полуфабрикату
- Кнопка "Далі" → перехід до complete-form

**5. complete-form.tsx**
- Остаточна форма з:
  - Інформацією про рецепт та вагу туші
  - Полями для введення фактичних ваг кожного полуфабрикату
  - Полем для ваги відходів
  - Полем для приміток
- Показує відхилення (фактична вага - очікувана)
- Кнопка "Завершити розділку"
- При натисканні → викликає POST /api/butchery/operations

**6. [id].tsx**
- Деталі завершеної операції розділки
- Показує:
  - Номер операції
  - Рецепт
  - Вхідну вагу
  - Таблицю виходів (очікуване vs фактичне)
  - Відходи
  - Примітки

### 4.2 Компоненти

**ButcheryMeatCard.tsx**
```tsx
interface ButcheryMeatCardProps {
  meat_type: string;
  icon: string;
  onSelect: () => void;
}
```

**ButcheryRecipeCard.tsx**
```tsx
interface ButcheryRecipeCardProps {
  recipe: {
    id: number;
    name: string;
    description: string;
    outputs: {
      output_name: string;
      yield_percentage: number;
    }[];
  };
  onSelect: () => void;
}
```

**ButcheryOutputList.tsx**
```tsx
interface ButcheryOutputListProps {
  outputs: {
    nomenclature_id: number;
    name: string;
    expected_weight: number;
    actual_weight?: number;
    editable: boolean;
  }[];
  onWeightChange?: (id: number, weight: number) => void;
}
```

---

## 5. Бізнес-правила

### 5.1 Розрахунок виходу

При введенні ваги туші `W`:
```
Очікувана вага полуфабрикату = W × (yield_percentage / 100)
```

Приклад:
- Вага туші: 100 кг
- Філе (35%): 100 × 0.35 = 35 кг
- Грудинка (25%): 100 × 0.25 = 25 кг

### 5.2 Відходи

**ВАЖЛИВО:** Відходи НЕ попадають на склад!

Відходи фіксуються тільки для статистики:
- Зберігаються в metadata операції
- Відображаються в звітах
- НЕ створюють stock_movements

### 5.3 Валідація

**При створенні операції:**
1. Перевірити наявність сировини на складі
   ```
   stock_balances[source_id].quantity >= input_weight
   ```
2. Перевірити що сума фактичних ваг <= вага туші
   ```
   sum(actual_weights) + waste_weight <= input_weight
   ```
3. Перевірити що всі ваги > 0

**Допустиме відхилення:**
- Якщо відхилення > 10% - показати попередження (але дозволити)
- Якщо відхилення > 30% - показати помилку та запит підтвердження

### 5.4 Нумерація операцій

Формат: `BUT-YYYYMMDD-NNN`

Приклад: `BUT-20251218-001`

Генерується автоматично при створенні операції.

---

## 6. Офлайн-режим

### 6.1 Локальне зберігання (MMKV)

Ключі:
```
butchery_recipes          - список рецептів
butchery_draft_operation  - чернетка поточної операції
butchery_offline_queue    - черга операцій для синхронізації
```

### 6.2 Синхронізація

При поверненні онлайн:
1. Відправити всі операції з offline_queue
2. Використовувати idempotency_key для уникнення дублів
3. Оновити локальний кеш рецептів

---

## 7. Помилки та їх обробка

### 7.1 Помилки API

**400 Bad Request:**
```json
{
  "detail": "Недостатньо сировини на складі. Доступно: 50.5 кг, потрібно: 100.5 кг"
}
```

**404 Not Found:**
```json
{
  "detail": "Рецепт розділки не знайдено"
}
```

**409 Conflict:**
```json
{
  "detail": "Операція вже виконана (idempotency_key conflict)"
}
```

### 7.2 Обробка на frontend

```typescript
try {
  const result = await api.post('/butchery/operations', data);
  // Успіх - показати результат
  router.push(`/butchery/${result.operation_id}`);
} catch (error) {
  if (error.status === 400) {
    // Показати помилку валідації
    Alert.alert('Помилка', error.detail);
  } else if (error.status === 409) {
    // Операція вже виконана - показати існуючу
    router.push(`/butchery/${error.operation_id}`);
  } else {
    // Інша помилка - додати в офлайн чергу
    await offlineQueue.add('butchery_operation', data);
    Alert.alert('Офлайн режим', 'Операція буде виконана при з\'явленні зв\'язку');
  }
}
```

---

## 8. Тестування

### 8.1 Unit тести (backend)

```python
def test_create_butchery_operation():
    """Тест створення операції розділки"""
    # Arrange
    recipe_id = 1
    input_weight = 100.0
    outputs = [
        {"output_nomenclature_id": 201, "actual_weight": 36.0},
        {"output_nomenclature_id": 202, "actual_weight": 25.0},
    ]

    # Act
    result = client.post("/api/butchery/operations", json={
        "recipe_id": recipe_id,
        "input_weight": input_weight,
        "outputs": outputs,
        "waste_weight": 20.0,
        "idempotency_key": "test-key-123"
    })

    # Assert
    assert result.status_code == 200
    assert result.json()["status"] == "completed"

    # Перевірити зміни балансів
    source_balance = get_stock_balance(1)  # Сировина
    assert source_balance == initial_balance - input_weight

    output_balance = get_stock_balance(201)  # Філе
    assert output_balance == initial_balance + 36.0
```

### 8.2 E2E тести (frontend)

1. Тест повного флоу розділки
2. Тест валідації (недостатньо сировини)
3. Тест офлайн-режиму
4. Тест відображення деталей операції

---

## 9. Приклади використання

### 9.1 Стандартний процес

```
Оператор приймає тушу яловичини вищого сорту вагою 120 кг

1. Відкриває додаток → вкладка "Обробка"
2. Натискає "Нова розділка"
3. Обирає "Яловичина" → "Вищий сорт" → Рецепт розділки
4. Вводить 120 кг
5. Система показує очікуваний вихід:
   - Філе: 42 кг
   - Грудинка: 30 кг
   - Лопатка: 24 кг
   - Інше: 14 кг
   - Відходи: 10 кг
6. Після розділки вводить фактичні ваги:
   - Філе: 43.5 кг (+1.5 кг)
   - Грудинка: 29.2 кг (-0.8 кг)
   - Лопатка: 24.8 кг (+0.8 кг)
   - Інше: 13.5 кг (-0.5 кг)
   - Відходи: 9.0 кг
7. Натискає "Завершити"
8. Система:
   - Списує 120 кг яловичини зі складу
   - Додає 43.5 кг філе
   - Додає 29.2 кг грудинки
   - Додає 24.8 кг лопатки
   - Додає 13.5 кг іншого
   - Фіксує 9 кг відходів (без оприходування)
9. Показує підтвердження та деталі операції
```

---

## 10. Майбутні покращення

- [ ] Додати QR-код сканування для ідентифікації туш
- [ ] Автоматичний розрахунок собівартості полуфабрикатів
- [ ] Звіт по відхиленням (факт vs план)
- [ ] Аналітика виходу по операторам
- [ ] Інтеграція з вагами (автоматичне зчитування ваги)
- [ ] Фотофіксація процесу розділки
- [ ] Push-нотифікації при великих відхиленнях
