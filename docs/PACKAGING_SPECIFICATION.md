# Технічне завдання: Модуль фасування (Packaging)

**Версія:** 1.0
**Дата:** 18 грудня 2025
**Статус:** Production Ready

---

## 1. Загальний опис

Модуль фасування призначений для перетворення вагової готової продукції в фасовані SKU (Stock Keeping Unit) з автоматичним розрахунком та обліком пакувальних матеріалів, браку та залишків.

### 1.1 Бізнес-процес

```
1. Створення сесії фасування
   - Обирається вагова продукція (Бастурма, Суджук, Махан...)
   - Вказується вага що береться зі складу
   - Система списує вагову продукцію зі складу
   ↓
2. Фасування в різні SKU
   - Оператор обирає цільовий SKU (наприклад: "Бастурма вакуум 100г")
   - Вводить кількість упаковок
   - Система автоматично розраховує необхідні матеріали:
     * Пакети вакуумні (1 шт на упаковку)
     * Етикетки (1 шт на упаковку)
     * Лотки (для скін-упаковки)
     * Плівка (для скін-упаковки, кг на кг продукту)
   - Оператор підтверджує або коригує матеріали
   - Можливість вказати брак по кожному матеріалу
   - Повторити для інших SKU
   ↓
3. Облік залишків
   - Осипана специя → повертається на склад
   - Обрізки → повертаються на склад або утилізуються
   - Інші залишки
   ↓
4. Завершення сесії
   - Перевірка балансу: взято = використано + брак + залишки
   - Списання матеріалів зі складу
   - Оприходування SKU на склад
   - Оприходування залишків
   - Закриття сесії
```

---

## 2. Структура даних

### 2.1 Таблиця: packaging_recipes

**Призначення:** Рецепти фасування (норми витрати матеріалів)

```sql
id                    INT PRIMARY KEY IDENTITY
source_product_id     INT NOT NULL → nomenclature(id)  -- Вагова продукція
target_product_id     INT NOT NULL → nomenclature(id)  -- SKU
packaging_type        NVARCHAR(50) NOT NULL             -- "vacuum", "skin"
target_weight_grams   INT NOT NULL                      -- Цільова вага (г)
is_active             BIT NOT NULL DEFAULT 1
notes                 NVARCHAR(MAX) NULL
created_at            DATETIME2 DEFAULT GETUTCDATE()
updated_at            DATETIME2 DEFAULT GETUTCDATE()

UNIQUE (source_product_id, target_product_id, packaging_type)
```

**Приклади:**
- Бастурма вагова (108) → Бастурма вакуум 100г (201), type: vacuum, вага: 100г
- Суджук ваговий (96) → Суджук скін 50г (210), type: skin, вага: 50г

### 2.2 Таблиця: packaging_recipe_materials

**Призначення:** Матеріали для рецепту фасування

```sql
id                    INT PRIMARY KEY IDENTITY
recipe_id             INT NOT NULL → packaging_recipes(id) ON DELETE CASCADE
material_id           INT NOT NULL → nomenclature(id)
quantity_per_unit     DECIMAL(18,6) NOT NULL            -- На 1 упаковку
rounding_precision    DECIMAL(18,6) NULL                -- Точність заокруглення
material_type         NVARCHAR(50) NOT NULL             -- "bag", "label", "tray", "film"
notes                 NVARCHAR(MAX) NULL
created_at            DATETIME2 DEFAULT GETUTCDATE()
```

**Типи матеріалів:**
- `bag` - Пакет (1 шт на упаковку)
- `label` - Етикетка (1 шт на упаковку)
- `tray` - Лоток (для скін-упаковки, 1 шт на упаковку)
- `film` - Плівка (для скін-упаковки, кг плівки на кг продукту)

**Приклад:**
```
Рецепт: "Бастурма вакуум 100г"
Матеріали:
- Пакет вакуумний 100г: 1 шт
- Етикетка "Бастурма 100г": 1 шт
```

### 2.3 Таблиця: packaging_sessions

**Призначення:** Сесії фасування

```sql
id                    INT PRIMARY KEY IDENTITY
session_number        NVARCHAR(50) NOT NULL UNIQUE      -- "PKG-20251218-001"
source_product_id     INT NOT NULL → nomenclature(id)   -- Вагова продукція
source_weight_taken   DECIMAL(18,6) NOT NULL            -- Взято зі складу (кг)
status                NVARCHAR(50) NOT NULL             -- "active", "completed"
started_at            DATETIME2 NOT NULL DEFAULT GETUTCDATE()
completed_at          DATETIME2 NULL
operator_notes        NVARCHAR(MAX) NULL
remainder_items       NVARCHAR(MAX) NULL                -- JSON з залишками
created_at            DATETIME2 DEFAULT GETUTCDATE()
updated_at            DATETIME2 DEFAULT GETUTCDATE()
```

**Статуси:**
- `active` - Сесія активна, можна додавати SKU
- `completed` - Сесія завершена, всі операції виконані

### 2.4 Таблиця: packaging_session_outputs

**Призначення:** Результати фасування (окремі SKU)

```sql
id                    INT PRIMARY KEY IDENTITY
session_id            INT NOT NULL → packaging_sessions(id)
target_product_id     INT NOT NULL → nomenclature(id)   -- SKU
quantity_packed       INT NOT NULL                       -- Кількість упаковок
calculated_materials  NVARCHAR(MAX) NULL                 -- JSON автоматичного розрахунку
confirmed_materials   NVARCHAR(MAX) NULL                 -- JSON підтверджених матеріалів
defect_quantity       DECIMAL(18,6) DEFAULT 0            -- Брак продукції (кг або шт)
notes                 NVARCHAR(MAX) NULL
created_at            DATETIME2 DEFAULT GETUTCDATE()
```

**Структура calculated_materials:**
```json
{
  "materials": [
    {
      "nomenclature_id": 150,
      "name": "Пакет вакуумний 100г",
      "material_type": "bag",
      "calculated_quantity": 100,
      "unit": "шт"
    },
    {
      "nomenclature_id": 151,
      "name": "Етикетка Бастурма 100г",
      "material_type": "label",
      "calculated_quantity": 100,
      "unit": "шт"
    }
  ],
  "product_weight_used": 10.0
}
```

**Структура confirmed_materials:**
```json
{
  "materials": [
    {
      "nomenclature_id": 150,
      "name": "Пакет вакуумний 100г",
      "material_type": "bag",
      "confirmed_quantity": 105,
      "defect_quantity": 5,
      "unit": "шт"
    },
    {
      "nomenclature_id": 151,
      "name": "Етикетка Бастурма 100г",
      "material_type": "label",
      "confirmed_quantity": 102,
      "defect_quantity": 2,
      "unit": "шт"
    }
  ],
  "product_weight_used": 10.2,
  "product_waste": 0.2
}
```

### 2.5 Таблиця: packaging_session_remainders

**Призначення:** Залишки після фасування

```sql
id                    INT PRIMARY KEY IDENTITY
session_id            INT NOT NULL → packaging_sessions(id)
nomenclature_id       INT NOT NULL → nomenclature(id)
weight_kg             DECIMAL(18,6) NOT NULL
description           NVARCHAR(255) NULL                -- "Осипана специя"
notes                 NVARCHAR(MAX) NULL
created_at            DATETIME2 DEFAULT GETUTCDATE()
```

**Приклади залишків:**
- Осипана специя → повернути на склад
- Обрізки продукту → повернути на склад
- Надлишок ваги

### 2.6 Таблиця: packaging_session_waste

**Призначення:** Брак та відходи

```sql
id                    INT PRIMARY KEY IDENTITY
session_id            INT NOT NULL → packaging_sessions(id)
waste_weight_kg       DECIMAL(18,6) NOT NULL
waste_description     NVARCHAR(255) NULL                -- "Пошкоджена продукція"
notes                 NVARCHAR(MAX) NULL
created_at            DATETIME2 DEFAULT GETUTCDATE()
```

---

## 3. API Endpoints

### 3.1 GET /api/packaging/recipes

**Призначення:** Отримати рецепти фасування

**Query параметри:**
- `source_product_id` (int, optional) - фільтр по вихідній продукції

**Response:**
```json
{
  "recipes": [
    {
      "id": 1,
      "source_product": {
        "id": 108,
        "name": "Бастурма вагова"
      },
      "target_product": {
        "id": 201,
        "name": "Бастурма вакуум 100г"
      },
      "packaging_type": "vacuum",
      "target_weight_grams": 100,
      "materials": [
        {
          "material_id": 150,
          "material_name": "Пакет вакуумний 100г",
          "material_type": "bag",
          "quantity_per_unit": 1.0,
          "unit": "шт"
        },
        {
          "material_id": 151,
          "material_name": "Етикетка Бастурма 100г",
          "material_type": "label",
          "quantity_per_unit": 1.0,
          "unit": "шт"
        }
      ]
    }
  ]
}
```

### 3.2 POST /api/packaging/sessions

**Призначення:** Створити сесію фасування

**Request:**
```json
{
  "source_product_id": 108,
  "source_weight_taken": 50.0,
  "operator_notes": "Фасування партії 20251218-001",
  "idempotency_key": "pkg-session-uuid-12345"
}
```

**Response:**
```json
{
  "session_id": 42,
  "session_number": "PKG-20251218-001",
  "source_product": {
    "id": 108,
    "name": "Бастурма вагова"
  },
  "source_weight_taken": 50.0,
  "status": "active",
  "started_at": "2025-12-18T10:00:00",
  "stock_movements": [
    {
      "id": 2001,
      "nomenclature_id": 108,
      "quantity": -50.0,
      "operation_type": "packaging_source"
    }
  ],
  "available_targets": [
    {
      "target_product_id": 201,
      "target_product_name": "Бастурма вакуум 100г",
      "packaging_type": "vacuum"
    },
    {
      "target_product_id": 202,
      "target_product_name": "Бастурма скін 50г",
      "packaging_type": "skin"
    }
  ]
}
```

**Бізнес-логіка:**
1. Перевірити наявність вагової продукції на складі
2. Створити сесію зі статусом "active"
3. Списати вагову продукцію зі складу
4. Повернути список доступних цільових SKU

### 3.3 POST /api/packaging/sessions/{session_id}/outputs

**Призначення:** Додати SKU до сесії фасування

**Request:**
```json
{
  "target_product_id": 201,
  "quantity_packed": 100,
  "confirmed_materials": {
    "materials": [
      {
        "nomenclature_id": 150,
        "confirmed_quantity": 105,
        "defect_quantity": 5
      },
      {
        "nomenclature_id": 151,
        "confirmed_quantity": 102,
        "defect_quantity": 2
      }
    ],
    "product_weight_used": 10.2,
    "product_waste": 0.2
  },
  "notes": "Упаковка вакуумна",
  "idempotency_key": "pkg-output-uuid-12345"
}
```

**Response:**
```json
{
  "output_id": 101,
  "session_id": 42,
  "target_product": {
    "id": 201,
    "name": "Бастурма вакуум 100г"
  },
  "quantity_packed": 100,
  "calculated_materials": {
    "materials": [
      {
        "nomenclature_id": 150,
        "name": "Пакет вакуумний 100г",
        "calculated_quantity": 100,
        "unit": "шт"
      },
      {
        "nomenclature_id": 151,
        "name": "Етикетка Бастурма 100г",
        "calculated_quantity": 100,
        "unit": "шт"
      }
    ],
    "product_weight_used": 10.0
  },
  "confirmed_materials": {
    "materials": [
      {
        "nomenclature_id": 150,
        "name": "Пакет вакуумний 100г",
        "confirmed_quantity": 105,
        "defect_quantity": 5,
        "unit": "шт"
      },
      {
        "nomenclature_id": 151,
        "name": "Етикетка Бастурма 100г",
        "confirmed_quantity": 102,
        "defect_quantity": 2,
        "unit": "шт"
      }
    ],
    "product_weight_used": 10.2,
    "product_waste": 0.2
  },
  "deviations": [
    {
      "material_name": "Пакет вакуумний 100г",
      "deviation": 5,
      "deviation_percent": 5.0
    },
    {
      "material_name": "Етикетка Бастурма 100г",
      "deviation": 2,
      "deviation_percent": 2.0
    }
  ]
}
```

**Бізнес-логіка:**
1. Перевірити що сесія в статусі "active"
2. Знайти рецепт фасування (source → target)
3. Розрахувати автоматично необхідні матеріали
4. Зберегти розраховані та підтверджені матеріали
5. НЕ списувати матеріали (це буде при завершенні сесії)
6. НЕ оприходувати SKU (це буде при завершенні сесії)

### 3.4 POST /api/packaging/sessions/{session_id}/remainders

**Призначення:** Додати залишки

**Request:**
```json
{
  "remainders": [
    {
      "nomenclature_id": 19,
      "weight_kg": 0.5,
      "description": "Осипана специя (пажитник)"
    },
    {
      "nomenclature_id": 108,
      "weight_kg": 1.2,
      "description": "Обрізки бастурми"
    }
  ],
  "idempotency_key": "pkg-remainder-uuid-12345"
}
```

**Response:**
```json
{
  "session_id": 42,
  "remainders": [
    {
      "id": 201,
      "nomenclature_id": 19,
      "name": "Пажитник",
      "weight_kg": 0.5,
      "description": "Осипана специя (пажитник)"
    },
    {
      "id": 202,
      "nomenclature_id": 108,
      "name": "Бастурма вагова",
      "weight_kg": 1.2,
      "description": "Обрізки бастурми"
    }
  ],
  "total_remainder_weight": 1.7
}
```

### 3.5 POST /api/packaging/sessions/{session_id}/waste

**Призначення:** Додати брак/відходи

**Request:**
```json
{
  "waste_weight_kg": 0.3,
  "waste_description": "Пошкоджена продукція",
  "notes": "Брак при упаковці",
  "idempotency_key": "pkg-waste-uuid-12345"
}
```

**Response:**
```json
{
  "session_id": 42,
  "waste_id": 301,
  "waste_weight_kg": 0.3,
  "waste_description": "Пошкоджена продукція"
}
```

### 3.6 POST /api/packaging/sessions/{session_id}/complete

**Призначення:** Завершити сесію фасування

**Request:**
```json
{
  "operator_notes": "Фасування завершено успішно",
  "idempotency_key": "pkg-complete-uuid-12345"
}
```

**Response:**
```json
{
  "session_id": 42,
  "session_number": "PKG-20251218-001",
  "status": "completed",
  "source_product": {
    "id": 108,
    "name": "Бастурма вагова"
  },
  "source_weight_taken": 50.0,
  "balance": {
    "total_taken": 50.0,
    "total_used_in_outputs": 48.5,
    "total_remainders": 1.2,
    "total_waste": 0.3,
    "total_accounted": 50.0,
    "balance_check": "OK"
  },
  "outputs_summary": [
    {
      "target_product_id": 201,
      "target_product_name": "Бастурма вакуум 100г",
      "quantity_packed": 100,
      "product_weight": 10.2
    },
    {
      "target_product_id": 202,
      "target_product_name": "Бастурма скін 50г",
      "quantity_packed": 500,
      "product_weight": 25.5
    }
  ],
  "materials_summary": [
    {
      "nomenclature_id": 150,
      "name": "Пакет вакуумний 100г",
      "total_used": 105,
      "total_defect": 5
    },
    {
      "nomenclature_id": 151,
      "name": "Етикетка Бастурма 100г",
      "total_used": 102,
      "total_defect": 2
    }
  ],
  "stock_movements": [
    {
      "id": 2010,
      "nomenclature_id": 201,
      "quantity": 100,
      "operation_type": "packaging_output"
    },
    {
      "id": 2011,
      "nomenclature_id": 202,
      "quantity": 500,
      "operation_type": "packaging_output"
    },
    {
      "id": 2012,
      "nomenclature_id": 150,
      "quantity": -105,
      "operation_type": "packaging_material"
    },
    {
      "id": 2013,
      "nomenclature_id": 151,
      "quantity": -102,
      "operation_type": "packaging_material"
    },
    {
      "id": 2014,
      "nomenclature_id": 19,
      "quantity": 0.5,
      "operation_type": "packaging_remainder"
    },
    {
      "id": 2015,
      "nomenclature_id": 108,
      "quantity": 1.2,
      "operation_type": "packaging_remainder"
    }
  ],
  "completed_at": "2025-12-18T16:30:00"
}
```

**Бізнес-логіка:**
1. Перевірити що сесія в статусі "active"
2. Розрахувати баланс:
   ```
   source_weight_taken = sum(outputs.product_weight_used) +
                         sum(remainders.weight_kg) +
                         sum(waste.weight_kg)
   ```
3. Якщо баланс НЕ сходиться → повернути помилку
4. Для кожного output:
   - Списати матеріали зі складу (confirmed_materials)
   - Оприходити SKU на склад
5. Для кожного remainder:
   - Оприходити залишок на склад
6. Брак НЕ оприходується (тільки фіксується)
7. Оновити статус сесії на "completed"

### 3.7 GET /api/packaging/sessions

**Призначення:** Отримати список сесій

**Query параметри:**
- `status` (string, optional) - "active", "completed"
- `source_product_id` (int, optional)
- `date_from`, `date_to` (datetime, optional)
- `limit`, `offset` (int)

**Response:**
```json
{
  "sessions": [
    {
      "id": 42,
      "session_number": "PKG-20251218-001",
      "source_product_name": "Бастурма вагова",
      "source_weight_taken": 50.0,
      "status": "completed",
      "started_at": "2025-12-18T10:00:00",
      "completed_at": "2025-12-18T16:30:00",
      "outputs_count": 2
    }
  ],
  "total": 78,
  "limit": 50,
  "offset": 0
}
```

### 3.8 GET /api/packaging/sessions/{session_id}

**Призначення:** Отримати деталі сесії

**Response:**
```json
{
  "id": 42,
  "session_number": "PKG-20251218-001",
  "source_product": {
    "id": 108,
    "name": "Бастурма вагова"
  },
  "source_weight_taken": 50.0,
  "status": "completed",
  "started_at": "2025-12-18T10:00:00",
  "completed_at": "2025-12-18T16:30:00",
  "outputs": [
    {
      "id": 101,
      "target_product_id": 201,
      "target_product_name": "Бастурма вакуум 100г",
      "quantity_packed": 100,
      "product_weight_used": 10.2,
      "confirmed_materials": { /* ... */ }
    }
  ],
  "remainders": [
    {
      "id": 201,
      "nomenclature_id": 19,
      "name": "Пажитник",
      "weight_kg": 0.5,
      "description": "Осипана специя"
    }
  ],
  "waste": [
    {
      "id": 301,
      "waste_weight_kg": 0.3,
      "waste_description": "Пошкоджена продукція"
    }
  ],
  "balance": {
    "total_taken": 50.0,
    "total_used": 48.5,
    "total_remainders": 1.2,
    "total_waste": 0.3,
    "balance_check": "OK"
  }
}
```

---

## 4. Frontend структура

### 4.1 Екрани (в app/packaging/)

**1. index.tsx (список сесій)**
- Список активних та завершених сесій
- Фільтри: статус, продукція, дата
- Кнопка "Нова сесія" → перехід до new-session

**2. new-session.tsx**
- Вибір вагової продукції
- Ввід ваги що береться зі складу
- Кнопка "Створити сесію"

**3. [id].tsx (деталі сесії)**
- Інформація про сесію
- Список вже запакованих SKU
- Баланс (взято / використано / залишок)
- Кнопки:
  - "Додати SKU" → modal з вибором SKU
  - "Додати залишки" → modal для введення залишків
  - "Додати брак" → modal для введення браку
  - "Завершити сесію" (якщо баланс сходиться)

**4. add-output-modal.tsx**
- Вибір цільового SKU
- Ввід кількості упаковок
- Автоматичний розрахунок матеріалів
- Таблиця з матеріалами:
  - Назва матеріалу
  - Розрахована кількість
  - Поле для підтвердження (з дефолтним значенням = розрахованій)
  - Поле для браку (+ / -)
- Кнопка "Додати"

**5. add-remainder-modal.tsx**
- Вибір номенклатури залишку
- Ввід ваги
- Опис (текстове поле)
- Кнопка "Додати"

**6. add-waste-modal.tsx**
- Ввід ваги браку
- Опис браку (текстове поле)
- Кнопка "Додати"

### 4.2 Компоненти

**PackagingSessionCard.tsx**
```tsx
interface PackagingSessionCardProps {
  session: {
    id: number;
    session_number: string;
    source_product_name: string;
    source_weight_taken: number;
    status: string;
    started_at: string;
  };
  onPress: () => void;
}
```

**PackagingOutputCard.tsx**
```tsx
interface PackagingOutputCardProps {
  output: {
    target_product_name: string;
    quantity_packed: number;
    product_weight_used: number;
    confirmed_materials: any;
  };
}
```

**MaterialsTable.tsx**
```tsx
interface MaterialsTableProps {
  materials: {
    nomenclature_id: number;
    name: string;
    calculated_quantity: number;
    confirmed_quantity?: number;
    defect_quantity?: number;
    unit: string;
  }[];
  editable: boolean;
  onMaterialChange?: (id: number, confirmed: number, defect: number) => void;
}
```

**PackagingBalanceCard.tsx**
```tsx
interface PackagingBalanceCardProps {
  balance: {
    total_taken: number;
    total_used: number;
    total_remainders: number;
    total_waste: number;
    balance_check: string;
  };
}
```

**RemaindersList.tsx**
```tsx
interface RemaindersListProps {
  remainders: {
    nomenclature_id: number;
    name: string;
    weight_kg: number;
    description: string;
  }[];
}
```

---

## 5. Бізнес-правила

### 5.1 Розрахунок матеріалів

**Для пакетів, етикеток, лотків:**
```
Кількість = quantity_packed × quantity_per_unit
```

Типово: `quantity_per_unit = 1.0` (1 шт на упаковку)

**Для плівки (скін-упаковка):**
```
Вага плівки (кг) = product_weight (кг) × film_coefficient
```

Типово: `film_coefficient = 0.05` (5% від ваги продукту)

### 5.2 Баланс сесії

**Перевірка:**
```
source_weight_taken = sum(outputs.product_weight_used) +
                      sum(remainders.weight_kg) +
                      sum(waste.waste_weight_kg)
```

**Допуск:** ±0.1 кг (100 грамів)

Якщо баланс не сходиться:
- Показати помилку
- Вказати скільки не вистачає або зайве
- НЕ дозволити завершити сесію

### 5.3 Брак матеріалів

Брак матеріалів враховується через `defect_quantity`:

```
Списати зі складу = confirmed_quantity
Оприходити SKU = quantity_packed
```

Приклад:
- Запаковано: 100 упаковок
- Використано пакетів: 105 шт (5 шт брак)
- Списати пакетів: 105 шт
- Оприходити SKU: 100 шт

### 5.4 Залишки

**Типи залишків:**
1. **Осипана специя** - повертається на склад
2. **Обрізки продукту** - повертаються на склад або утилізуються
3. **Надлишок ваги** - оприходується як вагова продукція

Всі залишки оприходуються при завершенні сесії через `stock_movements`.

### 5.5 Нумерація сесій

Формат: `PKG-YYYYMMDD-NNN`

Приклад: `PKG-20251218-001`

---

## 6. Офлайн-режим

### 6.1 Локальне зберігання

Ключі MMKV:
```
packaging_recipes           - рецепти фасування
packaging_active_session    - поточна активна сесія
packaging_offline_queue     - черга операцій
```

### 6.2 Особливості офлайн

**Складність:** Сесія фасування може тривати годинами

**Підхід:**
1. Зберігати всю сесію локально
2. Синхронізувати поетапно:
   - Створення сесії
   - Додавання кожного output
   - Додавання залишків
   - Додавання браку
   - Завершення сесії

---

## 7. Помилки та їх обробка

### 7.1 Помилки балансу

**400 Bad Request:**
```json
{
  "detail": "Баланс сесії не сходиться",
  "balance": {
    "total_taken": 50.0,
    "total_accounted": 49.5,
    "difference": 0.5,
    "status": "недостача"
  }
}
```

### 7.2 Помилки наявності

**400 Bad Request:**
```json
{
  "detail": "Недостатньо матеріалу на складі",
  "material": {
    "id": 150,
    "name": "Пакет вакуумний 100г",
    "required": 105,
    "available": 50
  }
}
```

---

## 8. Тестування

### 8.1 Тест кейси

1. **Створення сесії**
   - Перевірити списання вагової продукції

2. **Додавання output з автоматичним розрахунком**
   - Перевірити розрахунок пакетів (1:1)
   - Перевірити розрахунок етикеток (1:1)
   - Перевірити розрахунок плівки (коефіцієнт)

3. **Додавання output з браком матеріалів**
   - Підтверджена кількість > розрахованої
   - Перевірити поле defect_quantity

4. **Додавання залишків**
   - Перевірити збереження в таблицю

5. **Завершення сесії з правильним балансом**
   - Перевірити оприходування SKU
   - Перевірити списання матеріалів
   - Перевірити оприходування залишків

6. **Завершення з неправильним балансом**
   - Повинна бути помилка 400

---

## 9. Приклади використання

### 9.1 Фасування бастурми

```
ДЕНЬ 1 (10:00): Створення сесії
- Продукція: Бастурма вагова
- Взято зі складу: 50 кг
- Система списує 50 кг бастурми
- Статус: active

ДЕНЬ 1 (10:30): Упаковка в вакуум 100г
- SKU: Бастурма вакуум 100г
- Кількість: 100 упаковок
- Автоматичний розрахунок:
  * Пакети: 100 шт
  * Етикетки: 100 шт
  * Вага продукту: 10 кг
- Підтверджено:
  * Пакети: 105 шт (брак 5 шт)
  * Етикетки: 102 шт (брак 2 шт)
  * Вага продукту: 10.2 кг

ДЕНЬ 1 (13:00): Упаковка в скін 50г
- SKU: Бастурма скін 50г
- Кількість: 500 упаковок
- Автоматичний розрахунок:
  * Лотки: 500 шт
  * Плівка: 1.25 кг (25 кг × 0.05)
  * Етикетки: 500 шт
  * Вага продукту: 25 кг
- Підтверджено:
  * Лотки: 505 шт (брак 5 шт)
  * Плівка: 1.3 кг (брак 0.05 кг)
  * Етикетки: 502 шт (брак 2 шт)
  * Вага продукту: 25.3 кг

ДЕНЬ 1 (15:00): Додавання залишків
- Осипана специя (пажитник): 0.5 кг
- Обрізки бастурми: 1.2 кг
- Всього залишків: 1.7 кг

ДЕНЬ 1 (15:30): Додавання браку
- Пошкоджена продукція: 0.3 кг

ДЕНЬ 1 (16:00): Завершення сесії
- Баланс:
  * Взято: 50.0 кг
  * Використано в output: 35.5 кг (10.2 + 25.3)
  * Залишки: 1.7 кг
  * Брак: 0.3 кг
  * Залишок: 12.5 кг
  * ПОМИЛКА: баланс не сходиться!

- Оператор додає:
  * Залишок вагової бастурми: 12.5 кг

- Баланс (після корекції):
  * Взято: 50.0 кг
  * Використано: 35.5 кг
  * Залишки вагові: 12.5 кг
  * Залишки специй: 1.7 кг
  * Брак: 0.3 кг
  * Сума: 50.0 кг ✓

- Система:
  * Списує 105 пакетів вакуумних
  * Списує 102 етикетки для вакууму
  * Списує 505 лотків
  * Списує 1.3 кг плівки
  * Списує 502 етикетки для скіну
  * Оприходує 100 шт "Бастурма вакуум 100г"
  * Оприходує 500 шт "Бастурма скін 50г"
  * Оприходує 0.5 кг пажитнику
  * Оприходує 1.2 кг обрізків бастурми
  * Оприходує 12.5 кг вагової бастурми
  * Фіксує 0.3 кг браку (НЕ оприходується)

- Статус: completed
```

---

## 10. Майбутні покращення

- [ ] Автоматичне зважування через інтеграцію з вагами
- [ ] Сканування штрих-кодів матеріалів
- [ ] Прогнозування кількості матеріалів на основі планів
- [ ] Аналітика браку по операторах та матеріалах
- [ ] Інтеграція з принтером етикеток
- [ ] Фотофіксація упакованої продукції
- [ ] Автоматичне планування фасування на основі замовлень
