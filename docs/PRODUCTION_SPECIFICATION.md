# Технічне завдання: Модуль виробництва (Production)

**Версія:** 1.0
**Дата:** 18 грудня 2025
**Статус:** Production Ready

---

## 1. Загальний опис

Модуль виробництва призначений для управління повним циклом виробництва м'ясних виробів від сировини до готової вагової продукції через багатоетапний процес.

### 1.1 Бізнес-процес

```
ЕТАП 0: Створення партії (created)
  - Обирається рецепт
  - Вводиться вага сировини
  - Система списує сировину зі складу
  ↓
ЕТАП 1: Засолення (salt)
  - Додається сіль (розрахунок автоматично)
  - Додається вода (розрахунок автоматично)
  - Фіксується вага після засолення
  ↓
ЕТАП 2: Замішування специй (mix)
  - Система розраховує кількість кожної специї
  - Пажитник має коефіцієнт 1:4 (на 1 кг пажитнику → 4 кг води)
  - Виробляється суміш специй
  - Суміш використовується для покриття м'яса
  - Залишок суміші зберігається для наступних партій
  - Можливість використати суміш зі складу
  ↓
ЕТАП 3: Набивка в оболонку (stuff)
  - Додається оболонка (розрахунок автоматично)
  - Фіксується вага після набивки
  ↓
ЕТАП 4: Сушіння (dry)
  - Вказується тривалість сушіння (днів)
  - Фіксується дата початку
  ↓
ЕТАП 5: Завершення (completed)
  - Фіксується фінальна вага готового продукту
  - Розраховується відсоток виходу
  - Готова вагова продукція оприходується на склад
```

---

## 2. Структура даних

### 2.1 Таблиця: recipes

**Призначення:** Рецепти виробництва готової продукції

```sql
id                    INT PRIMARY KEY IDENTITY
name                  NVARCHAR(255) NOT NULL UNIQUE    -- "Бастурма класична"
target_product_id     INT NOT NULL → nomenclature(id)  -- ID готового продукту (вагового)
expected_yield_min    DECIMAL(5,2) NULL                -- Мінімальний вихід (%)
expected_yield_max    DECIMAL(5,2) NULL                -- Максимальний вихід (%)
description           NVARCHAR(MAX) NULL
created_at            DATETIME2 DEFAULT GETUTCDATE()
updated_at            DATETIME2 DEFAULT GETUTCDATE()
```

**Приклади:**
- "Бастурма класична" → target: "Бастурма вагова" (ID 108)
- "Суджук" → target: "Суджук ваговий" (ID 96)
- "Махан" → target: "Махан ваговий" (ID 111)

### 2.2 Таблиця: recipe_ingredients

**Призначення:** Сировина (м'ясо) для рецепту

```sql
id                    INT PRIMARY KEY IDENTITY
recipe_id             INT NOT NULL → recipes(id) ON DELETE CASCADE
nomenclature_id       INT NOT NULL → nomenclature(id)
quantity_per_100kg    DECIMAL(18,6) NULL                -- Кількість на 100 кг (NULL = 100%)
is_optional           BIT DEFAULT 0
notes                 NVARCHAR(MAX) NULL
created_at            DATETIME2 DEFAULT GETUTCDATE()
```

**Бізнес-правила:**
- Якщо `quantity_per_100kg = NULL` → використовується вся вага (100%)
- Сировина списується при створенні партії (етап 0)

### 2.3 Таблиця: recipe_spices

**Призначення:** Спеції для рецепту

```sql
id                    INT PRIMARY KEY IDENTITY
recipe_id             INT NOT NULL → recipes(id) ON DELETE CASCADE
nomenclature_id       INT NOT NULL → nomenclature(id)
quantity_per_100kg    DECIMAL(18,6) NULL                -- Грамів на 100 кг продукту
is_fenugreek          BIT DEFAULT 0                     -- Чи є пажитником
notes                 NVARCHAR(MAX) NULL
created_at            DATETIME2 DEFAULT GETUTCDATE()
```

**Особливості пажитнику:**
- `is_fenugreek = 1` означає особливу обробку
- Коефіцієнт: на 1 кг пажитнику додається 4 кг води
- Ця вода враховується окремо від води для засолення

### 2.4 Таблиця: recipe_steps

**Призначення:** Етапи виробництва

```sql
id                    INT PRIMARY KEY IDENTITY
recipe_id             INT NOT NULL → recipes(id) ON DELETE CASCADE
step_order            INT NOT NULL                      -- Порядковий номер (1, 2, 3...)
step_type             NVARCHAR(50) NOT NULL             -- "salt", "mix", "stuff", "dry"
step_name             NVARCHAR(255) NOT NULL            -- "Засолення", "Замішування"
duration_days         DECIMAL(5,2) NULL                 -- Тривалість (для dry)
parameters            NVARCHAR(MAX) NULL                -- JSON з параметрами
description           NVARCHAR(MAX) NULL
created_at            DATETIME2 DEFAULT GETUTCDATE()
```

**Типи етапів:**
- `salt` - Засолення (додається сіль + вода)
- `mix` - Замішування специй (виробництво суміші)
- `stuff` - Набивка в оболонку
- `dry` - Сушіння

### 2.5 Таблиця: batches

**Призначення:** Виробничі партії

```sql
id                    INT PRIMARY KEY IDENTITY
batch_number          NVARCHAR(100) NOT NULL UNIQUE     -- "20251218-001"
recipe_id             INT NOT NULL → recipes(id)
status                NVARCHAR(50) NOT NULL             -- "created", "salt", "mix", "stuff", "dry", "completed"
current_step          INT DEFAULT 0                     -- Поточний етап
started_at            DATETIME2 DEFAULT GETUTCDATE()
completed_at          DATETIME2 NULL
initial_weight        DECIMAL(18,6) NULL                -- Початкова вага сировини
final_weight          DECIMAL(18,6) NULL                -- Фінальна вага готового продукту
trim_waste            DECIMAL(18,6) NULL                -- Вага обрізків
trim_returned         BIT DEFAULT 0                     -- Чи повернуто обрізки на склад
operator_notes        NVARCHAR(MAX) NULL
created_at            DATETIME2 DEFAULT GETUTCDATE()
updated_at            DATETIME2 DEFAULT GETUTCDATE()
```

**Статуси:**
- `created` - Створена, сировина списана
- `salt` - Засолення виконано
- `mix` - Замішування виконано
- `stuff` - Набивка виконана
- `dry` - Сушіння почалося
- `completed` - Завершено, продукція на складі

### 2.6 Таблиця: batch_operations

**Призначення:** Операції в рамках партії

```sql
id                    INT PRIMARY KEY IDENTITY
batch_id              INT NOT NULL → batches(id) ON DELETE CASCADE
step_id               INT NOT NULL → recipe_steps(id)
operation_type        NVARCHAR(50) NOT NULL             -- "salt", "mix", "stuff", "dry"
status                NVARCHAR(50) NOT NULL             -- "in_progress", "completed"
started_at            DATETIME2 DEFAULT GETUTCDATE()
completed_at          DATETIME2 NULL
weight_before         DECIMAL(18,6) NULL
weight_after          DECIMAL(18,6) NULL
parameters            NVARCHAR(MAX) NULL                -- JSON параметри
notes                 NVARCHAR(MAX) NULL
idempotency_key       NVARCHAR(255) NOT NULL UNIQUE
created_at            DATETIME2 DEFAULT GETUTCDATE()
```

### 2.7 Таблиця: batch_mix_production

**Призначення:** Виробництво та використання суміші специй

```sql
id                    INT PRIMARY KEY IDENTITY
batch_id              INT NOT NULL → batches(id) ON DELETE CASCADE
mix_nomenclature_id   INT NOT NULL → nomenclature(id)  -- ID позиції "Суміш специй"
produced_quantity     DECIMAL(18,6) NOT NULL DEFAULT 0 -- Вироблено суміші (кг)
used_quantity         DECIMAL(18,6) NOT NULL DEFAULT 0 -- Використано суміші (кг)
leftover_quantity     DECIMAL(18,6) NOT NULL DEFAULT 0 -- Залишок = produced - used
warehouse_mix_used    DECIMAL(18,6) NOT NULL DEFAULT 0 -- Використано зі складу (кг)
idempotency_key       NVARCHAR(255) NOT NULL UNIQUE
created_at            DATETIME2 DEFAULT GETUTCDATE()
```

**Бізнес-логіка:**
- Спочатку використовується суміш зі складу (якщо є)
- Потім виробляється нова суміш з специй
- Залишок нової суміші оприходується на склад

### 2.8 Таблиця: batch_materials

**Призначення:** Всі матеріали використані в партії

```sql
id                    INT PRIMARY KEY IDENTITY
batch_id              INT NOT NULL → batches(id) ON DELETE CASCADE
nomenclature_id       INT NOT NULL → nomenclature(id)
material_type         NVARCHAR(50) NOT NULL             -- "salt", "water", "spice", "casing"
quantity_used         DECIMAL(18,6) NOT NULL
movement_id           INT NULL → stock_movements(id)
notes                 NVARCHAR(MAX) NULL
created_at            DATETIME2 DEFAULT GETUTCDATE()
```

---

## 3. API Endpoints

### 3.1 GET /api/production/recipes

**Призначення:** Отримати список рецептів виробництва

**Response:**
```json
{
  "recipes": [
    {
      "id": 1,
      "name": "Бастурма класична",
      "target_product": {
        "id": 108,
        "name": "Бастурма вагова"
      },
      "expected_yield_min": 65.0,
      "expected_yield_max": 75.0,
      "description": "Класичний рецепт бастурми з яловичини",
      "ingredients": [
        {
          "nomenclature_id": 1,
          "name": "Яловичина вищого сорту",
          "quantity_per_100kg": 100000
        }
      ],
      "spices": [
        {
          "nomenclature_id": 19,
          "name": "Пажитник",
          "quantity_per_100kg": 500,
          "is_fenugreek": true
        },
        {
          "nomenclature_id": 20,
          "name": "Чесник сушений",
          "quantity_per_100kg": 300
        }
      ],
      "steps": [
        {
          "step_order": 1,
          "step_type": "salt",
          "step_name": "Засолення",
          "duration_days": 3
        },
        {
          "step_order": 2,
          "step_type": "mix",
          "step_name": "Замішування специй"
        },
        {
          "step_order": 3,
          "step_type": "stuff",
          "step_name": "Набивка в оболонку"
        },
        {
          "step_order": 4,
          "step_type": "dry",
          "step_name": "Сушіння",
          "duration_days": 21
        }
      ]
    }
  ]
}
```

### 3.2 POST /api/production/batches

**Призначення:** Створити нову партію

**Request:**
```json
{
  "recipe_id": 1,
  "initial_weight": 100.0,
  "operator_notes": "Використано яловичину з поставки №123",
  "idempotency_key": "batch-uuid-12345"
}
```

**Response:**
```json
{
  "batch_id": 42,
  "batch_number": "20251218-001",
  "recipe_name": "Бастурма класична",
  "status": "created",
  "current_step": 0,
  "initial_weight": 100.0,
  "started_at": "2025-12-18T10:00:00",
  "stock_movements": [
    {
      "id": 1001,
      "nomenclature_id": 1,
      "nomenclature_name": "Яловичина вищого сорту",
      "quantity": -100.0,
      "operation_type": "production_source"
    }
  ],
  "next_step": {
    "step_order": 1,
    "step_type": "salt",
    "step_name": "Засолення"
  }
}
```

**Бізнес-логіка:**
1. Перевірити наявність сировини на складі
2. Створити партію зі статусом "created"
3. Списати сировину зі складу
4. Повернути інформацію про наступний етап

### 3.3 POST /api/production/batches/{batch_id}/salt

**Призначення:** Виконати етап засолення

**Request:**
```json
{
  "weight_after": 102.5,
  "salt_kg": 2.0,
  "water_liters": 0.5,
  "notes": "Засолення пройшло нормально",
  "idempotency_key": "salt-uuid-12345"
}
```

**Response:**
```json
{
  "batch_id": 42,
  "operation_id": 101,
  "status": "salt",
  "current_step": 1,
  "weight_before": 100.0,
  "weight_after": 102.5,
  "materials_used": [
    {
      "nomenclature_id": 15,
      "name": "Сіль",
      "quantity": 2.0,
      "unit": "кг"
    },
    {
      "nomenclature_id": 16,
      "name": "Вода",
      "quantity": 0.5,
      "unit": "л"
    }
  ],
  "next_step": {
    "step_order": 2,
    "step_type": "mix",
    "step_name": "Замішування специй"
  }
}
```

**Бізнес-логіка:**
1. Перевірити що партія в статусі "created"
2. Списати сіль та воду зі складу
3. Створити запис batch_operations
4. Створити записи batch_materials
5. Оновити статус партії на "salt"
6. Повернути інформацію про наступний етап

### 3.4 POST /api/production/batches/{batch_id}/mix

**Призначення:** Виконати етап замішування специй

**Request:**
```json
{
  "weight_after": 105.0,
  "use_warehouse_mix": true,
  "warehouse_mix_kg": 2.5,
  "notes": "Використано суміш зі складу",
  "idempotency_key": "mix-uuid-12345"
}
```

**Response:**
```json
{
  "batch_id": 42,
  "operation_id": 102,
  "status": "mix",
  "current_step": 2,
  "weight_before": 102.5,
  "weight_after": 105.0,
  "mix_production": {
    "warehouse_mix_used": 2.5,
    "new_mix_produced": 0,
    "new_mix_used": 0,
    "leftover_to_warehouse": 0
  },
  "materials_used": [
    {
      "nomenclature_id": 999,
      "name": "Суміш специй",
      "quantity": 2.5,
      "source": "warehouse"
    }
  ],
  "next_step": {
    "step_order": 3,
    "step_type": "stuff",
    "step_name": "Набивка в оболонку"
  }
}
```

**Альтернативний запит (виробництво нової суміші):**
```json
{
  "weight_after": 108.0,
  "use_warehouse_mix": false,
  "spices_used": [
    {
      "nomenclature_id": 19,
      "quantity": 0.5
    },
    {
      "nomenclature_id": 20,
      "quantity": 0.3
    }
  ],
  "mix_produced_kg": 5.0,
  "mix_used_kg": 2.5,
  "idempotency_key": "mix-uuid-12346"
}
```

**Response (з виробництвом суміші):**
```json
{
  "batch_id": 42,
  "operation_id": 102,
  "status": "mix",
  "current_step": 2,
  "weight_before": 102.5,
  "weight_after": 108.0,
  "mix_production": {
    "warehouse_mix_used": 0,
    "new_mix_produced": 5.0,
    "new_mix_used": 2.5,
    "leftover_to_warehouse": 2.5,
    "fenugreek_water_added": 2.0
  },
  "materials_used": [
    {
      "nomenclature_id": 19,
      "name": "Пажитник",
      "quantity": 0.5
    },
    {
      "nomenclature_id": 20,
      "name": "Чесник сушений",
      "quantity": 0.3
    },
    {
      "nomenclature_id": 16,
      "name": "Вода (для пажитнику)",
      "quantity": 2.0
    }
  ],
  "stock_movements": [
    {
      "id": 1005,
      "nomenclature_id": 999,
      "quantity": 2.5,
      "operation_type": "production_mix_leftover"
    }
  ]
}
```

**Бізнес-логіка пажитнику:**
```python
if spice.is_fenugreek:
    water_needed = spice_quantity * 4  # На 1 кг пажитнику → 4 л води
    # Списати воду зі складу
    # Додати вагу до виробленої суміші
```

### 3.5 POST /api/production/batches/{batch_id}/stuff

**Призначення:** Виконати етап набивки в оболонку

**Request:**
```json
{
  "weight_after": 107.5,
  "casing_used_kg": 0.5,
  "notes": "Використано натуральну оболонку",
  "idempotency_key": "stuff-uuid-12345"
}
```

**Response:**
```json
{
  "batch_id": 42,
  "operation_id": 103,
  "status": "stuff",
  "current_step": 3,
  "weight_before": 105.0,
  "weight_after": 107.5,
  "materials_used": [
    {
      "nomenclature_id": 50,
      "name": "Оболонка натуральна",
      "quantity": 0.5
    }
  ],
  "next_step": {
    "step_order": 4,
    "step_type": "dry",
    "step_name": "Сушіння"
  }
}
```

### 3.6 POST /api/production/batches/{batch_id}/dry

**Призначення:** Почати етап сушіння

**Request:**
```json
{
  "duration_days": 21,
  "notes": "Сушка в камері №2",
  "idempotency_key": "dry-uuid-12345"
}
```

**Response:**
```json
{
  "batch_id": 42,
  "operation_id": 104,
  "status": "dry",
  "current_step": 4,
  "dry_started_at": "2025-12-18T15:00:00",
  "expected_completion": "2026-01-08T15:00:00",
  "duration_days": 21
}
```

### 3.7 POST /api/production/batches/{batch_id}/complete

**Призначення:** Завершити партію

**Request:**
```json
{
  "final_weight": 75.5,
  "trim_waste": 2.0,
  "return_trim": false,
  "notes": "Продукція якісна, відповідає стандартам",
  "idempotency_key": "complete-uuid-12345"
}
```

**Response:**
```json
{
  "batch_id": 42,
  "operation_id": 105,
  "status": "completed",
  "batch_number": "20251218-001",
  "recipe_name": "Бастурма класична",
  "initial_weight": 100.0,
  "final_weight": 75.5,
  "trim_waste": 2.0,
  "total_loss": 24.5,
  "yield_percentage": 75.5,
  "expected_yield_min": 65.0,
  "expected_yield_max": 75.0,
  "yield_status": "in_range",
  "completed_at": "2026-01-08T16:30:00",
  "stock_movements": [
    {
      "id": 1010,
      "nomenclature_id": 108,
      "nomenclature_name": "Бастурма вагова",
      "quantity": 75.5,
      "operation_type": "production_output"
    }
  ],
  "summary": {
    "duration_days": 21,
    "total_materials": [
      {"name": "Яловичина вищого сорту", "quantity": 100.0},
      {"name": "Сіль", "quantity": 2.0},
      {"name": "Вода", "quantity": 2.5},
      {"name": "Пажитник", "quantity": 0.5},
      {"name": "Чесник", "quantity": 0.3},
      {"name": "Оболонка", "quantity": 0.5}
    ]
  }
}
```

**Бізнес-логіка:**
1. Перевірити що партія в статусі "dry"
2. Розрахувати вихід: `yield = (final_weight / initial_weight) * 100`
3. Перевірити чи вихід в межах очікуваного діапазону
4. Якщо `return_trim = true` → оприходити обрізки на склад
5. Оприходити готову продукцію
6. Оновити статус партії на "completed"

### 3.8 GET /api/production/batches

**Призначення:** Отримати список партій

**Query параметри:**
- `status` (string, optional) - фільтр по статусу
- `recipe_id` (int, optional) - фільтр по рецепту
- `date_from`, `date_to` (datetime, optional)
- `limit`, `offset` (int)

**Response:**
```json
{
  "batches": [
    {
      "id": 42,
      "batch_number": "20251218-001",
      "recipe_name": "Бастурма класична",
      "status": "dry",
      "current_step": 4,
      "initial_weight": 100.0,
      "started_at": "2025-12-18T10:00:00",
      "expected_completion": "2026-01-08T15:00:00"
    }
  ],
  "total": 156,
  "limit": 50,
  "offset": 0
}
```

### 3.9 GET /api/production/batches/{batch_id}

**Призначення:** Отримати деталі партії

**Response:**
```json
{
  "id": 42,
  "batch_number": "20251218-001",
  "recipe": {
    "id": 1,
    "name": "Бастурма класична",
    "target_product_id": 108,
    "target_product_name": "Бастурма вагова"
  },
  "status": "dry",
  "current_step": 4,
  "initial_weight": 100.0,
  "started_at": "2025-12-18T10:00:00",
  "expected_completion": "2026-01-08T15:00:00",
  "operations": [
    {
      "id": 101,
      "step_type": "salt",
      "step_name": "Засолення",
      "weight_before": 100.0,
      "weight_after": 102.5,
      "completed_at": "2025-12-18T11:00:00"
    },
    {
      "id": 102,
      "step_type": "mix",
      "step_name": "Замішування специй",
      "weight_before": 102.5,
      "weight_after": 105.0,
      "completed_at": "2025-12-18T12:00:00"
    }
  ],
  "materials_used": [
    {"name": "Яловичина вищого сорту", "quantity": 100.0, "unit": "кг"},
    {"name": "Сіль", "quantity": 2.0, "unit": "кг"},
    {"name": "Вода", "quantity": 2.5, "unit": "л"}
  ],
  "next_step": {
    "step_order": 5,
    "step_type": "complete",
    "step_name": "Завершення партії"
  }
}
```

---

## 4. Frontend структура

### 4.1 Екрани (в app/batches/)

**1. index.tsx (список партій)**
- Список всіх активних та завершених партій
- Фільтри: статус, рецепт, дата
- Кнопка "Нова партія" → перехід до new-batch

**2. new-batch.tsx**
- Вибір рецепту
- Ввід початкової ваги сировини
- Показує інформацію про етапи
- Кнопка "Створити" → викликає POST /api/production/batches

**3. [id].tsx (деталі партії)**
- Показує всю інформацію про партію
- Список виконаних етапів
- Використані матеріали
- Графік ваги по етапах
- Кнопка "Продовжити" (якщо не завершена)

**4. salt-form.tsx**
- Форма для етапу засолення
- Поля: вага після, кількість солі, кількість води
- Розрахунок автоматично (можна редагувати)
- Кнопка "Завершити засолення"

**5. mix-form.tsx**
- Вибір: використати суміш зі складу або виробити нову
- Якщо виробляти:
  - Показує список необхідних специй (з розрахунком)
  - Поля для введення фактичних кількостей
  - Розрахунок води для пажитнику (автоматично)
  - Поля: вироблено суміші, використано
  - Розрахунок залишку (оприходується на склад)
- Якщо зі складу:
  - Вибір позиції "Суміш специй"
  - Ввід кількості
- Кнопка "Завершити замішування"

**6. stuff-form.tsx**
- Форма для етапу набивки
- Поля: вага після, кількість оболонки
- Кнопка "Завершити набивку"

**7. dry-form.tsx**
- Форма для початку сушіння
- Поля: тривалість (днів)
- Показує розрахункову дату завершення
- Кнопка "Почати сушіння"

**8. complete-form.tsx**
- Форма для завершення партії
- Поля:
  - Фінальна вага готового продукту
  - Вага обрізків
  - Чи повернути обрізки на склад (checkbox)
  - Примітки
- Показує розрахунковий вихід (%)
- Показує чи вихід в межах очікуваного
- Кнопка "Завершити партію"

### 4.2 Компоненти

**BatchCard.tsx**
```tsx
interface BatchCardProps {
  batch: {
    id: number;
    batch_number: string;
    recipe_name: string;
    status: string;
    current_step: number;
    initial_weight: number;
    started_at: string;
  };
  onPress: () => void;
}
```

**BatchStepIndicator.tsx**
```tsx
interface BatchStepIndicatorProps {
  steps: {
    step_order: number;
    step_name: string;
    completed: boolean;
    current: boolean;
  }[];
}
```

**MaterialsList.tsx**
```tsx
interface MaterialsListProps {
  materials: {
    name: string;
    quantity: number;
    unit: string;
  }[];
}
```

**WeightProgressChart.tsx**
```tsx
interface WeightProgressChartProps {
  operations: {
    step_name: string;
    weight_before: number;
    weight_after: number;
  }[];
}
```

---

## 5. Бізнес-правила

### 5.1 Розрахунок материалів

**Сіль (для засолення):**
```
Кількість солі = initial_weight × (salt_percentage / 100)
```
Типово: 2% від ваги м'яса

**Вода (для засолення):**
```
Кількість води = initial_weight × (water_percentage / 100)
```
Типово: 0.5-1% від ваги м'яса

**Специї:**
```
Кількість специї = current_weight × (spice_per_100kg / 100000)
```

**Вода для пажитнику:**
```
Вода = fenugreek_quantity × 4
```

**Оболонка:**
```
Кількість оболонки = current_weight × (casing_coefficient)
```
Типово: 0.3-0.5% від ваги

### 5.2 Розрахунок виходу

```
Вихід (%) = (final_weight / initial_weight) × 100
```

**Типові значення:**
- Бастурма: 65-75%
- Суджук: 60-70%
- Махан: 70-80%

**Статуси виходу:**
- `below_range` - нижче очікуваного (попередження)
- `in_range` - в межах норми
- `above_range` - вище очікуваного (перевірити)

### 5.3 Обрізки (trim)

При завершенні партії:
- Якщо `return_trim = true`:
  - Обрізки оприходуються на склад як сировина
  - Створюється stock_movement з operation_type = "production_trim_return"
- Якщо `return_trim = false`:
  - Обрізки списуються як відходи (фіксуються в metadata)

### 5.4 Валідація

**При створенні партії:**
- Перевірити наявність сировини: `stock >= initial_weight`

**При кожному етапі:**
- Перевірити що партія в правильному статусі
- Перевірити що weight_after >= 0
- Перевірити наявність матеріалів на складі

**При завершенні:**
- Перевірити що final_weight > 0
- Перевірити що final_weight + trim_waste <= current_weight

### 5.5 Нумерація партій

Формат: `YYYYMMDD-NNN`

Приклад: `20251218-001`

Генерується автоматично:
```sql
SELECT ISNULL(MAX(CAST(RIGHT(batch_number, 3) AS INT)), 0) + 1
FROM batches
WHERE batch_number LIKE '20251218-%'
```

---

## 6. Офлайн-режим

### 6.1 Локальне зберігання

Ключі MMKV:
```
production_recipes         - список рецептів
production_active_batches  - активні партії
production_offline_queue   - черга операцій
```

### 6.2 Черга операцій

Кожна операція зберігається локально з:
- `operation_type`: "create_batch", "salt_step", "mix_step", etc.
- `batch_id` (локальний)
- `data`: об'єкт запиту
- `idempotency_key`: UUID
- `created_at`: timestamp

При поверненні онлайн - виконати всі з черги.

---

## 7. Тестування

### 7.1 Тест кейси

1. **Створення партії**
   - Перевірити списання сировини
   - Перевірити генерацію batch_number

2. **Етап засолення**
   - Перевірити списання солі та води
   - Перевірити оновлення статусу

3. **Етап замішування (з виробництвом суміші)**
   - Перевірити списання специй
   - Перевірити розрахунок води для пажитнику (1:4)
   - Перевірити оприходування залишку суміші

4. **Етап замішування (використання складської суміші)**
   - Перевірити списання суміші зі складу
   - Перевірити що специї НЕ списуються

5. **Завершення партії**
   - Перевірити оприходування готової продукції
   - Перевірити розрахунок виходу
   - Перевірити обробку обрізків (return/waste)

6. **Ідемпотентність**
   - Повторний запит з тим же idempotency_key → той же результат

---

## 8. Приклади використання

### 8.1 Стандартний процес виробництва бастурми

```
ДЕНЬ 1 (10:00): Створення партії
- Рецепт: Бастурма класична
- Вага яловичини: 100 кг
- Система списує 100 кг яловичини зі складу
- Статус: created

ДЕНЬ 1 (11:00): Засолення
- Додано 2 кг солі, 0.5 л води
- Вага після: 102.5 кг
- Система списує сіль та воду
- Статус: salt

ДЕНЬ 1 (14:00): Замішування специй
- Виробництво суміші:
  - Пажитник: 0.5 кг
  - Вода для пажитнику: 2 л (автоматично 0.5×4)
  - Чесник: 0.3 кг
  - Перець: 0.2 кг
  - Всього вироблено суміші: 5 кг
  - Використано для покриття: 2.5 кг
  - Залишок на склад: 2.5 кг
- Вага після: 105 кг
- Система:
  - Списує специї
  - Списує 2 л води
  - Оприходує 2.5 кг суміші на склад
- Статус: mix

ДЕНЬ 1 (16:00): Набивка в оболонку
- Використано оболонки: 0.5 кг
- Вага після: 105.5 кг
- Система списує оболонку
- Статус: stuff

ДЕНЬ 1 (17:00): Початок сушіння
- Тривалість: 21 день
- Очікуване завершення: 08.01.2026
- Статус: dry

ДЕНЬ 22 (08.01.2026, 16:00): Завершення
- Фінальна вага: 75 кг
- Обрізки: 2 кг (повернути на склад)
- Вихід: 75% (в межах 65-75%)
- Система:
  - Оприходує 75 кг бастурми вагової
  - Оприходує 2 кг яловичини (обрізки)
- Статус: completed
```

---

## 9. Майбутні покращення

- [ ] Автоматичне визначення оптимального терміну сушіння (ML)
- [ ] QR-коди на партіях для швидкого доступу
- [ ] Push-нотифікації про завершення сушіння
- [ ] Інтеграція з датчиками температури/вологості
- [ ] Аналітика якості по партіях
- [ ] Прогнозування виходу на основі історичних даних
- [ ] Автоматичне планування виробництва
- [ ] Інтеграція з вагами (автоматичне зчитування)
