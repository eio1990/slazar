# Архітектура бази даних SLAZAR

**База даних:** MS SQL Server 2022
**Всього таблиць:** 27 (актуальна структура з production БД)
**Дата створення документа:** 15 грудня 2025
**Оновлено:** 15 грудня 2025

---

## Загальна структура

Система складається з 7 основних модулів:

1. **Номенклатура та склад** (3 таблиці)
2. **Рецепти** (4 таблиці)
3. **Виробництво** (4 таблиці)
4. **Фасування** (9 таблиць: 5 актуальних ⭐ + 4 legacy)
5. **Розділка (Butchery)** (3 таблиці)
6. **Інвентаризація** (2 таблиці)
7. **Аудит** (1 таблиця)

---

## 1. МОДУЛЬ: Номенклатура та склад

### 1.1 Таблиця: `nomenclature`
**Призначення:** Центральний довідник усіх позицій (сировина, продукція, матеріали, специї)

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | Унікальний ідентифікатор |
| `name` | NVARCHAR(255) | NOT NULL, UNIQUE | Назва позиції |
| `category` | NVARCHAR(100) | NOT NULL | Категорія (сировина, готова продукція, специи, материалы, упаковка) |
| `unit` | NVARCHAR(50) | NOT NULL | Одиниця виміру (кг, шт, л, м) |
| `precision_digits` | INT | NOT NULL, DEFAULT 2 | Точність вимірювання (знаків після коми) |
| `nomenclature_type` | NVARCHAR(100) | NULL | Додатковий тип номенклатури |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |
| `updated_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата оновлення |

**Індекси:**
- `PK_nomenclature` на `id`
- `UQ_nomenclature_name` (UNIQUE) на `name`

**Приклади даних:**
- ID 1: "Яловичина вищого сорту" (категорія: сировина, одиниця: кг)
- ID 108: "Конина" (категорія: готова продукція вагова, одиниця: кг)
- ID 19: "Пажитник" (категорія: специи, одиниця: кг)

---

### 1.2 Таблиця: `stock_balances`
**Призначення:** Поточні залишки на складі

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `nomenclature_id` | INT | PK, FK → nomenclature(id) | ID номенклатури |
| `quantity` | DECIMAL(18,6) | NOT NULL, DEFAULT 0 | Поточна кількість |
| `last_updated` | DATETIME2 | DEFAULT GETUTCDATE() | Дата останнього оновлення |

**Індекси:**
- `PK_stock_balances` на `nomenclature_id`

**Бізнес-правила:**
- Оновлюється при кожній операції (приход, расход, виробництво, фасування)
- Використовує row-level locking (`WITH (UPDLOCK, ROWLOCK)`) для запобігання race conditions

---

### 1.3 Таблиця: `stock_movements`
**Призначення:** Повна історія всіх рухів по складу (аудит)

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | Унікальний ID руху |
| `nomenclature_id` | INT | NOT NULL, FK → nomenclature(id) | ID номенклатури |
| `operation_type` | NVARCHAR(50) | NOT NULL | Тип операції (receipt, withdrawal, production, packaging, inventory_adjustment) |
| `quantity` | DECIMAL(18,6) | NOT NULL | Кількість (+ для приходу, - для витрати) |
| `balance_after` | DECIMAL(18,6) | NOT NULL | Залишок після операції |
| `price_per_unit` | DECIMAL(18,2) | NULL | Ціна за одиницю (опціонально) |
| `source_operation_type` | NVARCHAR(50) | NULL | Тип операції-джерела (batch, packaging_batch) |
| `source_operation_id` | NVARCHAR(100) | NULL | ID операції-джерела |
| `parent_movement_id` | INT | NULL, FK → stock_movements(id) | ID батьківського руху (для зв'язаних операцій) |
| `idempotency_key` | NVARCHAR(255) | NOT NULL, UNIQUE | Ключ ідемпотентності (запобігає дублюванню) |
| `metadata` | NVARCHAR(MAX) | NULL | Додаткові дані (JSON) |
| `operation_date` | DATETIME2 | NOT NULL, DEFAULT GETUTCDATE() | Дата операції |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення запису |

**Індекси:**
- `PK_stock_movements` на `id`
- `UQ_idempotency_key` (UNIQUE) на `idempotency_key`
- `IX_stock_movements_date` на `operation_date DESC` ⚡ Для швидких запитів

**Бізнес-правила:**
- **Ідемпотентність:** Кожна операція має унікальний `idempotency_key` - при повторному запиті повертається той же результат
- **Immutable:** Записи ніколи не видаляються і не змінюються (append-only log)
- **Аудит:** Містить повну історію всіх змін залишків

---

## 2. МОДУЛЬ: Рецепти

### 2.1 Таблиця: `recipes`
**Призначення:** Рецепти виробництва

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID рецепту |
| `name` | NVARCHAR(255) | NOT NULL, UNIQUE | Назва рецепту |
| `target_product_id` | INT | NOT NULL, FK → nomenclature(id) | ID готового продукту |
| `expected_yield_min` | DECIMAL(5,2) | NULL | Мінімальний вихід (%) |
| `expected_yield_max` | DECIMAL(5,2) | NULL | Максимальний вихід (%) |
| `description` | NVARCHAR(MAX) | NULL | Опис рецепту |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |
| `updated_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата оновлення |

**Індекси:**
- `PK_recipes` на `id`
- `UQ_recipe_name` (UNIQUE) на `name`

**Приклади:**
- ID 1: "Бастурма класична" → target_product_id = 108 (Конина вагова)
- ID 2: "Суджук" → target_product_id = 110

---

### 2.2 Таблиця: `recipe_ingredients`
**Призначення:** Сировина для рецепту (м'ясо)

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID інгредієнта |
| `recipe_id` | INT | NOT NULL, FK → recipes(id) ON DELETE CASCADE | ID рецепту |
| `nomenclature_id` | INT | NOT NULL, FK → nomenclature(id) | ID сировини |
| `quantity_per_100kg` | DECIMAL(18,6) | NULL | Кількість на 100 кг (опціонально) |
| `is_optional` | BIT | DEFAULT 0 | Чи є інгредієнт опціональним |
| `notes` | NVARCHAR(MAX) | NULL | Примітки |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |

**Бізнес-правила:**
- При створенні партії списується `initial_weight` кг сировини
- Приклад: Рецепт "Бастурма" вимагає яловичину вищого сорту

---

### 2.3 Таблиця: `recipe_spices`
**Призначення:** Спеції для рецепту

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID специї |
| `recipe_id` | INT | NOT NULL, FK → recipes(id) ON DELETE CASCADE | ID рецепту |
| `nomenclature_id` | INT | NOT NULL, FK → nomenclature(id) | ID специї |
| `quantity_per_100kg` | DECIMAL(18,6) | NULL | Кількість на 100 кг продукту |
| `is_fenugreek` | BIT | DEFAULT 0 | Чи є пажитником (має особливу обробку) |
| `notes` | NVARCHAR(MAX) | NULL | Примітки |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |

**Бізнес-правила:**
- **Пажитник (fenugreek)** має особливий коефіцієнт: на 1 кг пажитнику додається 4 кг води
- Спеції додаються на етапі `mix` (замішування)

---

### 2.4 Таблиця: `recipe_steps`
**Призначення:** Етапи виробництва в рецепті

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID етапу |
| `recipe_id` | INT | NOT NULL, FK → recipes(id) ON DELETE CASCADE | ID рецепту |
| `step_order` | INT | NOT NULL | Порядковий номер етапу |
| `step_type` | NVARCHAR(50) | NOT NULL | Тип етапу (salt, mix, stuff, dry) |
| `step_name` | NVARCHAR(255) | NOT NULL | Назва етапу |
| `duration_days` | DECIMAL(5,2) | NULL | Тривалість (днів) |
| `parameters` | NVARCHAR(MAX) | NULL | Параметри етапу (JSON) |
| `description` | NVARCHAR(MAX) | NULL | Опис |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |

**Типи етапів:**
- `salt` - Засолення (додавання солі та води)
- `mix` - Замішування (додавання специй)
- `stuff` - Набивання (в оболонку)
- `dry` - Сушіння

---

## 3. МОДУЛЬ: Виробництво

### 3.1 Таблиця: `batches`
**Призначення:** Виробничі партії

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID партії |
| `batch_number` | NVARCHAR(100) | NOT NULL, UNIQUE | Номер партії (формат: 20251215-001) |
| `recipe_id` | INT | NOT NULL, FK → recipes(id) | ID рецепту |
| `status` | NVARCHAR(50) | NOT NULL, DEFAULT 'created' | Статус партії |
| `current_step` | INT | DEFAULT 0 | Поточний етап (0 = created, 1 = salt, 2 = mix, ...) |
| `started_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата початку |
| `completed_at` | DATETIME2 | NULL | Дата завершення |
| `initial_weight` | DECIMAL(18,6) | NULL | Початкова вага сировини (кг) |
| `final_weight` | DECIMAL(18,6) | NULL | Кінцева вага продукту (кг) |
| `trim_waste` | DECIMAL(18,6) | NULL | Вага обрізків (кг) |
| `trim_returned` | BIT | DEFAULT 0 | Чи повернуто обрізки на склад |
| `operator_notes` | NVARCHAR(MAX) | NULL | Примітки оператора |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |
| `updated_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата оновлення |

**Індекси:**
- `PK_batches` на `id`
- `UQ_batch_number` (UNIQUE) на `batch_number`

**Статуси:**
- `created` - Створена, сировина списана
- `salt` - Засолення виконано
- `mix` - Замішування виконано
- `stuff` - Набивання виконано
- `dry` - Сушіння почалося
- `completed` - Завершено, продукція на складі

**Бізнес-правила:**
- При створенні (`created`) списується `initial_weight` кг сировини
- При завершенні (`completed`) оприходується `final_weight` кг готової продукції
- Номер партії генерується автоматично: `YYMMDD-NNN` (наприклад, `251215-001`)

---

### 3.2 Таблиця: `batch_operations`
**Призначення:** Операції в рамках партії (виконання етапів)

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID операції |
| `batch_id` | INT | NOT NULL, FK → batches(id) ON DELETE CASCADE | ID партії |
| `step_id` | INT | NOT NULL, FK → recipe_steps(id) | ID етапу рецепту |
| `operation_type` | NVARCHAR(50) | NOT NULL | Тип операції (salt, mix, stuff, dry) |
| `status` | NVARCHAR(50) | NOT NULL, DEFAULT 'in_progress' | Статус операції |
| `started_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата початку |
| `completed_at` | DATETIME2 | NULL | Дата завершення |
| `weight_before` | DECIMAL(18,6) | NULL | Вага до операції |
| `weight_after` | DECIMAL(18,6) | NULL | Вага після операції |
| `parameters` | NVARCHAR(MAX) | NULL | Параметри операції (JSON) |
| `notes` | NVARCHAR(MAX) | NULL | Примітки |
| `idempotency_key` | NVARCHAR(255) | NOT NULL, UNIQUE | Ключ ідемпотентності |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |

**Індекси:**
- `PK_batch_operations` на `id`
- `UQ_batch_operation_idempotency` (UNIQUE) на `idempotency_key`

---

### 3.3 Таблиця: `batch_mix_production`
**Призначення:** Відстеження виробництва суміші специй

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID запису |
| `batch_id` | INT | NOT NULL, FK → batches(id) ON DELETE CASCADE | ID партії |
| `mix_nomenclature_id` | INT | NOT NULL, FK → nomenclature(id) | ID позиції "Суміш специй" |
| `produced_quantity` | DECIMAL(18,6) | NOT NULL, DEFAULT 0 | Скільки суміші вироблено (кг) |
| `used_quantity` | DECIMAL(18,6) | NOT NULL, DEFAULT 0 | Скільки суміші використано (кг) |
| `leftover_quantity` | DECIMAL(18,6) | NOT NULL, DEFAULT 0 | Залишок суміші (кг) |
| `warehouse_mix_used` | DECIMAL(18,6) | NOT NULL, DEFAULT 0 | Використано суміші зі складу (кг) |
| `idempotency_key` | NVARCHAR(255) | NOT NULL, UNIQUE | Ключ ідемпотентності |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |

**Індекси:**
- `PK_batch_mix_production` на `id`
- `UQ_batch_mix_idempotency` (UNIQUE) на `idempotency_key`

**Бізнес-правила:**
- Суміш специй виробляється на етапі `mix`
- Залишок суміші може бути використаний в наступних партіях
- `leftover_quantity = produced_quantity - used_quantity`

---

### 3.4 Таблиця: `batch_materials`
**Призначення:** Відстеження всіх матеріалів, використаних у партії

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID запису |
| `batch_id` | INT | NOT NULL, FK → batches(id) ON DELETE CASCADE | ID партії |
| `nomenclature_id` | INT | NOT NULL, FK → nomenclature(id) | ID матеріалу |
| `material_type` | NVARCHAR(50) | NOT NULL | Тип матеріалу (salt, water, spice, casing, packaging) |
| `quantity_used` | DECIMAL(18,6) | NOT NULL | Використана кількість |
| `movement_id` | INT | NULL, FK → stock_movements(id) | ID руху на складі |
| `notes` | NVARCHAR(MAX) | NULL | Примітки |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |

**Типи матеріалів:**
- `salt` - Сіль
- `water` - Вода
- `spice` - Спеції
- `casing` - Оболонка
- `packaging` - Упаковка

---

## 4. МОДУЛЬ: Фасування

### 4.1 Таблиця: `packaging_recipes`
**Призначення:** Рецепти фасування (норми витрати матеріалів)

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID рецепту |
| `source_product_id` | INT | NOT NULL, FK → nomenclature(id) | ID вихідного продукту (вагова продукція) |
| `target_product_id` | INT | NOT NULL, FK → nomenclature(id) | ID цільового продукту (SKU) |
| `packaging_type` | NVARCHAR(50) | NOT NULL | Тип упаковки (vacuum, skin) |
| `target_weight_grams` | INT | NOT NULL | Цільова вага упаковки (г) |
| `is_active` | BIT | NOT NULL, DEFAULT 1 | Чи активний рецепт |
| `notes` | NVARCHAR(MAX) | NULL | Примітки |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |
| `updated_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата оновлення |

**Індекси:**
- `PK_packaging_recipes` на `id`
- `UQ_packaging_recipe` (UNIQUE) на `(source_product_id, target_product_id, packaging_type)`

**Приклади:**
- Бастурма вагова (108) → Бастурма вакуум 100г (201), тип: vacuum, вага: 100г

---

### 4.2 Таблиця: `packaging_recipe_materials`
**Призначення:** Матеріали для рецепту фасування

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID запису |
| `recipe_id` | INT | NOT NULL, FK → packaging_recipes(id) ON DELETE CASCADE | ID рецепту |
| `material_id` | INT | NOT NULL, FK → nomenclature(id) | ID матеріалу |
| `quantity_per_unit` | DECIMAL(18,6) | NOT NULL | Кількість на одну упаковку |
| `rounding_precision` | DECIMAL(18,6) | NULL | Точність заокруглення |
| `material_type` | NVARCHAR(50) | NOT NULL | Тип матеріалу (bag, label, tray, film) |
| `notes` | NVARCHAR(MAX) | NULL | Примітки |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |

**Типи матеріалів:**
- `bag` - Пакет (1 шт на упаковку)
- `label` - Етикетка (1 шт на упаковку)
- `tray` - Лоток (для скін-упаковки)
- `film` - Плівка (для скін-упаковки, кг на кг продукту)

---

### 4.3 Таблиця: `packaging_batches`
**Призначення:** Партії фасування (сесії)

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID партії |
| `batch_number` | NVARCHAR(50) | NOT NULL, UNIQUE | Номер партії |
| `recipe_id` | INT | NOT NULL, FK → packaging_recipes(id) | ID рецепту |
| `source_product_id` | INT | NOT NULL, FK → nomenclature(id) | ID вихідного продукту |
| `target_product_id` | INT | NOT NULL, FK → nomenclature(id) | ID цільового продукту |
| `status` | NVARCHAR(50) | NOT NULL, DEFAULT 'in_progress' | Статус (in_progress, completed) |
| `planned_quantity` | INT | NULL | Планова кількість упаковок |
| `source_weight_taken` | DECIMAL(18,6) | NOT NULL | Взято вихідної продукції (кг) |
| `actual_packed_quantity` | INT | DEFAULT 0 | Фактично упаковано (шт) |
| `actual_source_used` | DECIMAL(18,6) | DEFAULT 0 | Фактично використано (кг) |
| `waste_quantity` | DECIMAL(18,6) | DEFAULT 0 | Кількість браку/втрат (кг) |
| `started_at` | DATETIME2 | NOT NULL, DEFAULT GETUTCDATE() | Дата початку |
| `completed_at` | DATETIME2 | NULL | Дата завершення |
| `operator_notes` | NVARCHAR(MAX) | NULL | Примітки оператора |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |
| `updated_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата оновлення |

**Індекси:**
- `PK_packaging_batches` на `id`
- `UQ_packaging_batch_number` (UNIQUE) на `batch_number`

**Бізнес-правила:**
- При створенні списується `source_weight_taken` кг вагової продукції
- При завершенні оприходується `actual_packed_quantity` шт SKU
- Залишок = `source_weight_taken - actual_source_used - waste_quantity`

---

### 4.4 Таблиця: `packaging_operations`
**Призначення:** Операції фасування в рамках партії

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID операції |
| `batch_id` | INT | NOT NULL, FK → packaging_batches(id) ON DELETE CASCADE | ID партії |
| `operation_type` | NVARCHAR(50) | NOT NULL | Тип операції (pack, waste, return) |
| `packed_quantity` | INT | NOT NULL | Кількість упакованих одиниць |
| `source_used` | DECIMAL(18,6) | NOT NULL | Використано вихідного продукту (кг) |
| `waste_quantity` | DECIMAL(18,6) | DEFAULT 0 | Кількість браку (кг) |
| `notes` | NVARCHAR(MAX) | NULL | Примітки |
| `idempotency_key` | NVARCHAR(255) | NOT NULL, UNIQUE | Ключ ідемпотентності |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |

**Індекси:**
- `PK_packaging_operations` на `id`
- `UQ_packaging_operation_key` (UNIQUE) на `idempotency_key`

---

### 4.5 Таблиця: `packaging_material_consumption`
**Призначення:** Витрата матеріалів у операціях фасування

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID запису |
| `operation_id` | INT | NOT NULL, FK → packaging_operations(id) ON DELETE CASCADE | ID операції |
| `material_id` | INT | NOT NULL, FK → nomenclature(id) | ID матеріалу |
| `quantity_used` | DECIMAL(18,6) | NOT NULL | Використана кількість |
| `movement_id` | INT | NULL, FK → stock_movements(id) | ID руху на складі |
| `notes` | NVARCHAR(MAX) | NULL | Примітки |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |

---

### 4.6 Таблиця: `packaging_sessions` ⭐ АКТУАЛЬНА
**Призначення:** Сесії фасування (поточна реалізація)

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID сесії |
| `session_number` | NVARCHAR(50) | NOT NULL, UNIQUE | Номер сесії |
| `source_product_id` | INT | NOT NULL, FK → nomenclature(id) | ID вихідної вагової продукції |
| `source_weight_taken` | DECIMAL(18,6) | NOT NULL | Взято продукції зі складу (кг) |
| `status` | NVARCHAR(50) | NOT NULL | Статус (active, completed) |
| `started_at` | DATETIME2 | NOT NULL, DEFAULT GETUTCDATE() | Дата початку |
| `completed_at` | DATETIME2 | NULL | Дата завершення |
| `operator_notes` | NVARCHAR(MAX) | NULL | Примітки оператора |
| `remainder_items` | NVARCHAR(MAX) | NULL | JSON з залишками |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |
| `updated_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата оновлення |

**Бізнес-правила:**
- Одна сесія = одна вагова партія
- В межах сесії можна фасувати в різні SKU
- При створенні списується `source_weight_taken` кг

---

### 4.7 Таблиця: `packaging_session_outputs` ⭐ АКТУАЛЬНА
**Призначення:** Результати фасування в сесії

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID результату |
| `session_id` | INT | NOT NULL, FK → packaging_sessions(id) | ID сесії |
| `target_product_id` | INT | NOT NULL, FK → nomenclature(id) | ID цільового SKU |
| `quantity_packed` | INT | NOT NULL | Кількість упаковок (шт) |
| `calculated_materials` | NVARCHAR(MAX) | NULL | JSON з розрахованими матеріалами |
| `confirmed_materials` | NVARCHAR(MAX) | NULL | JSON з підтвердженими матеріалами |
| `defect_quantity` | DECIMAL(18,6) | DEFAULT 0 | Кількість браку (кг або шт) |
| `notes` | NVARCHAR(MAX) | NULL | Примітки |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |

---

### 4.8 Таблиця: `packaging_session_remainders` ⭐ АКТУАЛЬНА
**Призначення:** Залишки після фасування

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID залишку |
| `session_id` | INT | NOT NULL, FK → packaging_sessions(id) | ID сесії |
| `nomenclature_id` | INT | NOT NULL, FK → nomenclature(id) | ID номенклатури залишку |
| `weight_kg` | DECIMAL(18,6) | NOT NULL | Вага залишку (кг) |
| `description` | NVARCHAR(255) | NULL | Опис залишку |
| `notes` | NVARCHAR(MAX) | NULL | Примітки |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |

**Приклади залишків:**
- Осипана спеція
- Обрізки продукту
- Надлишок ваги

---

### 4.9 Таблиця: `packaging_session_waste` ⭐ АКТУАЛЬНА
**Призначення:** Відходи при фасуванні

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID відходу |
| `session_id` | INT | NOT NULL, FK → packaging_sessions(id) | ID сесії |
| `waste_weight_kg` | DECIMAL(18,6) | NOT NULL | Вага відходів (кг) |
| `waste_description` | NVARCHAR(255) | NULL | Опис відходів |
| `notes` | NVARCHAR(MAX) | NULL | Примітки |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |

**Примітка:** ⚠️ Таблиці 4.3-4.5 (`packaging_batches`, `packaging_operations`, `packaging_material_consumption`) є legacy і поступово замінюються системою packaging_sessions (4.6-4.9)

---

## 5. МОДУЛЬ: Розділка (Butchery)

### 5.1 Таблиця: `butchery_recipes`
**Призначення:** Рецепти розділки туш

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID рецепту |
| `name` | NVARCHAR(255) | NOT NULL | Назва рецепту розділки |
| `source_nomenclature_id` | INT | NOT NULL, FK → nomenclature(id) | ID сировини (туша) |
| `description` | NVARCHAR(MAX) | NULL | Опис процесу розділки |
| `level` | NVARCHAR(50) | NULL | Рівень (перший сорт, другий сорт) |
| `is_active` | BIT | NOT NULL, DEFAULT 1 | Чи активний рецепт |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |

**Приклади:**
- "Розділка яловичини (перший сорт)"
- "Розділка конини (вищий сорт)"

---

### 5.2 Таблиця: `butchery_recipe_outputs`
**Призначення:** Вихід полуфабрикатів з рецепту розділки

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID виходу |
| `recipe_id` | INT | NOT NULL, FK → butchery_recipes(id) | ID рецепту розділки |
| `output_nomenclature_id` | INT | NOT NULL, FK → nomenclature(id) | ID полуфабрикату |
| `expected_weight` | DECIMAL(18,6) | NULL | Очікувана вага (кг або %) |
| `actual_weight` | DECIMAL(18,6) | NULL | Фактична вага (кг) |
| `notes` | NVARCHAR(MAX) | NULL | Примітки |

**Бізнес-правила:**
- Визначає відсоток виходу кожного полуфабрикату
- Приклад: з 100 кг туші → 35 кг філе, 25 кг грудинки, 40 кг інших частин

---

### 5.3 Таблиця: `butchery_operations`
**Призначення:** Операції розділки

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID операції |
| `operation_number` | NVARCHAR(50) | NOT NULL, UNIQUE | Номер операції |
| `recipe_id` | INT | NOT NULL, FK → butchery_recipes(id) | ID рецепту розділки |
| `source_nomenclature_id` | INT | NOT NULL, FK → nomenclature(id) | ID сировини (туша) |
| `input_weight` | DECIMAL(18,6) | NOT NULL | Вага туші (кг) |
| `status` | NVARCHAR(50) | NOT NULL | Статус (in_progress, completed) |
| `started_at` | DATETIME2 | NOT NULL, DEFAULT GETUTCDATE() | Дата початку |
| `completed_at` | DATETIME2 | NULL | Дата завершення |
| `operator_notes` | NVARCHAR(MAX) | NULL | Примітки оператора |
| `idempotency_key` | NVARCHAR(255) | NOT NULL, UNIQUE | Ключ ідемпотентності |

---

### 5.4 Таблиця: `butchery_operation_outputs`
**Призначення:** Результати операції розділки

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID результату |
| `operation_id` | INT | NOT NULL, FK → butchery_operations(id) | ID операції |
| `output_nomenclature_id` | INT | NOT NULL, FK → nomenclature(id) | ID полуфабрикату |
| `expected_weight` | DECIMAL(18,6) | NULL | Очікувана вага (за рецептом) |
| `actual_weight` | DECIMAL(18,6) | NOT NULL | Фактична вага (кг) |
| `notes` | NVARCHAR(MAX) | NULL | Примітки |

**Бізнес-правила:**
- Відходи НЕ попадають на склад
- Лише полуфабрикати оприходуються через `stock_movements`

---

## 6. МОДУЛЬ: Інвентаризація

### 6.1 Таблиця: `inventory_sessions`
**Призначення:** Сесії інвентаризації

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID сесії |
| `session_type` | NVARCHAR(50) | NOT NULL | Тип інвентаризації (full, partial) |
| `status` | NVARCHAR(50) | NOT NULL, DEFAULT 'in_progress' | Статус (in_progress, completed) |
| `started_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата початку |
| `completed_at` | DATETIME2 | NULL | Дата завершення |
| `idempotency_key` | NVARCHAR(255) | NOT NULL, UNIQUE | Ключ ідемпотентності |
| `metadata` | NVARCHAR(MAX) | NULL | Додаткові дані (JSON) |

**Індекси:**
- `PK_inventory_sessions` на `id`
- `UQ_inventory_idempotency` (UNIQUE) на `idempotency_key`

---

### 6.2 Таблиця: `inventory_items`
**Призначення:** Позиції інвентаризації

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID позиції |
| `session_id` | INT | NOT NULL, FK → inventory_sessions(id) | ID сесії |
| `nomenclature_id` | INT | NOT NULL, FK → nomenclature(id) | ID номенклатури |
| `system_quantity` | DECIMAL(18,6) | NOT NULL | Системна кількість (з БД) |
| `actual_quantity` | DECIMAL(18,6) | NOT NULL | Фактична кількість (підрахована) |
| `difference` | DECIMAL(18,6) | NOT NULL | Різниця (actual - system) |
| `created_at` | DATETIME2 | DEFAULT GETUTCDATE() | Дата створення |

**Бізнес-правила:**
- `difference = actual_quantity - system_quantity`
- При завершенні інвентаризації різниця списується/оприходується через `stock_movements`

---

## 7. МОДУЛЬ: Аудит

### 7.1 Таблиця: `AdminAudit`
**Призначення:** Аудит адміністративних дій та змін у БД

| Колонка | Тип | Обмеження | Опис |
|---------|-----|-----------|------|
| `id` | INT | PK, IDENTITY | ID запису аудиту |
| `ts` | DATETIME2 | NOT NULL | Timestamp (дата/час події) |
| `login_name` | NVARCHAR(255) | NULL | Ім'я користувача SQL Server |
| `host_name` | NVARCHAR(255) | NULL | Ім'я хоста (комп'ютера) |
| `app_name` | NVARCHAR(255) | NULL | Назва додатку |
| `actor` | NVARCHAR(255) | NULL | Хто виконав дію |
| `event_type` | NVARCHAR(100) | NULL | Тип події (CREATE, UPDATE, DELETE, ALTER, DROP) |
| `schema_name` | NVARCHAR(100) | NULL | Назва схеми БД |
| `object_name` | NVARCHAR(255) | NULL | Назва об'єкта (таблиця, процедура, тригер) |
| `tsql` | NVARCHAR(MAX) | NULL | Текст SQL запиту, що був виконаний |

**Призначення:**
- Відстеження змін в структурі БД (DDL operations)
- Аудит адміністративних операцій
- Безпека та відповідність нормам (compliance)
- Відновлення після інцидентів

**Приклади подій:**
- `CREATE TABLE` - створення нової таблиці
- `ALTER TABLE` - зміна структури таблиці
- `DROP TABLE` - видалення таблиці
- `CREATE PROCEDURE` - створення збереженої процедури

**Бізнес-правила:**
- Таблиця наповнюється автоматично через DDL тригери
- Записи immutable (лише додавання, без редагування)
- Рекомендується періодичне архівування старих записів

---

## ДІАГРАМА ЗВ'ЯЗКІВ (ER Diagram)

```
┌─────────────────────────┐
│    nomenclature         │◄────────────┐
│  PK: id                 │             │
│  - name (UNIQUE)        │             │
│  - category             │             │
│  - unit                 │             │
└─────────────────────────┘             │
         ▲                               │
         │                               │
         │ FK                            │
         │                               │
┌────────┴──────────────┐    ┌──────────┴───────────┐
│  stock_balances       │    │  stock_movements     │
│  PK: nomenclature_id  │    │  PK: id              │
│  - quantity           │    │  FK: nomenclature_id │
│  - last_updated       │    │  - quantity          │
└───────────────────────┘    │  - operation_type    │
                             │  - idempotency_key   │
                             │    (UNIQUE)          │
                             └──────────────────────┘

┌────────────────────────┐
│      recipes           │
│  PK: id                │
│  FK: target_product_id ├──► nomenclature
│  - name (UNIQUE)       │
└────────┬───────────────┘
         │
    ┌────┴────┬──────────────────┬──────────────────┐
    │         │                  │                  │
    │         │                  │                  │
┌───▼──────────────┐  ┌─────▼───────────┐  ┌─────▼──────────┐
│recipe_ingredients│  │ recipe_spices   │  │ recipe_steps   │
│PK: id            │  │ PK: id          │  │ PK: id         │
│FK: recipe_id     │  │ FK: recipe_id   │  │ FK: recipe_id  │
│FK: nomenclature  │  │ FK: nomenclature│  │ - step_order   │
└──────────────────┘  └─────────────────┘  │ - step_type    │
                                           └────────────────┘

┌────────────────────────┐
│       batches          │
│  PK: id                │
│  FK: recipe_id         │
│  - batch_number (UQ)   │
│  - status              │
│  - initial_weight      │
│  - final_weight        │
└────────┬───────────────┘
         │
    ┌────┴────┬──────────────────┬─────────────────┐
    │         │                  │                 │
┌───▼──────────────┐  ┌──────▼─────────────┐  ┌──▼──────────────┐
│batch_operations  │  │batch_mix_production│  │batch_materials  │
│PK: id            │  │PK: id              │  │PK: id           │
│FK: batch_id      │  │FK: batch_id        │  │FK: batch_id     │
│FK: step_id       │  │FK: mix_nomenclature│  │FK: nomenclature │
│- idempotency_key │  │- produced_quantity │  │- material_type  │
└──────────────────┘  │- used_quantity     │  │- quantity_used  │
                      └────────────────────┘  └─────────────────┘

┌──────────────────────────┐
│   packaging_recipes      │
│  PK: id                  │
│  FK: source_product_id   ├──► nomenclature
│  FK: target_product_id   ├──► nomenclature
│  - packaging_type        │
│  - target_weight_grams   │
└────────┬─────────────────┘
         │
    ┌────┴────────────────────────────┐
    │                                 │
┌───▼──────────────────────┐  ┌──────▼──────────────┐
│packaging_recipe_materials│  │packaging_batches    │
│PK: id                    │  │PK: id               │
│FK: recipe_id             │  │FK: recipe_id        │
│FK: material_id           │  │- batch_number (UQ)  │
│- quantity_per_unit       │  │- status             │
│- material_type           │  │- source_weight_taken│
└──────────────────────────┘  └──────┬──────────────┘
                                     │
                         ┌───────────┴────────────────┐
                         │                            │
                 ┌───────▼──────────┐   ┌────────────▼──────────────┐
                 │packaging_ops     │   │packaging_material_consump │
                 │PK: id            │   │PK: id                     │
                 │FK: batch_id      │   │FK: operation_id           │
                 │- packed_quantity │   │FK: material_id            │
                 │- source_used     │   │- quantity_used            │
                 │- idempotency_key │   └───────────────────────────┘
                 └──────────────────┘

┌────────────────────────┐
│  inventory_sessions    │
│  PK: id                │
│  - session_type        │
│  - status              │
│  - idempotency_key (UQ)│
└────────┬───────────────┘
         │
         │
    ┌────▼──────────────┐
    │ inventory_items   │
    │ PK: id            │
    │ FK: session_id    │
    │ FK: nomenclature  │
    │ - system_quantity │
    │ - actual_quantity │
    │ - difference      │
    └───────────────────┘
```

---

## ІНДЕКСИ ТА ОПТИМІЗАЦІЯ

### Існуючі індекси:

1. **stock_movements**
   - `IX_stock_movements_date` на `operation_date DESC` ⚡
   - Призначення: Швидкі запити історії операцій

### Рекомендовані додаткові індекси:

```sql
-- Для частих фільтрів
CREATE INDEX IX_batches_status ON batches(status);
CREATE INDEX IX_batches_recipe_id ON batches(recipe_id);
CREATE INDEX IX_nomenclature_category ON nomenclature(category);

-- Для сортування
CREATE INDEX IX_batches_created_at_desc ON batches(started_at DESC);

-- Composite індекси
CREATE INDEX IX_batches_status_created ON batches(status, started_at DESC);
CREATE INDEX IX_packaging_batches_status ON packaging_batches(status);
```

---

## МЕХАНІЗМИ ЗАХИСТУ ДАНИХ

### 1. Ідемпотентність

Всі операції зміни даних мають `idempotency_key` (UNIQUE):
- `stock_movements.idempotency_key`
- `batch_operations.idempotency_key`
- `packaging_operations.idempotency_key`
- `inventory_sessions.idempotency_key`

**Приклад використання:**
```sql
-- Перевірка перед вставкою
SELECT id FROM stock_movements WHERE idempotency_key = 'unique-key-123';
IF @@ROWCOUNT > 0
    -- Операція вже виконана, повертаємо існуючий результат
ELSE
    -- Виконуємо операцію
```

### 2. Row-Level Locking

Для операцій зміни залишків використовується:
```sql
SELECT quantity
FROM stock_balances WITH (UPDLOCK, ROWLOCK)
WHERE nomenclature_id = ?
```

Це запобігає race conditions при одночасних операціях.

### 3. Foreign Key Constraints

- Всі зв'язки між таблицями захищені FK
- Використовується `ON DELETE CASCADE` для залежних записів
- Приклад: видалення `recipe` автоматично видаляє `recipe_ingredients`

### 4. Unique Constraints

- `nomenclature.name` - UNIQUE (запобігає дублям)
- `batches.batch_number` - UNIQUE
- `recipes.name` - UNIQUE
- `stock_movements.idempotency_key` - UNIQUE

---

## ТИПОВІ ЗАПИТИ

### 1. Отримати поточні залишки всіх позицій:
```sql
SELECT n.id, n.name, n.category, n.unit,
       ISNULL(sb.quantity, 0) as quantity
FROM nomenclature n
LEFT JOIN stock_balances sb ON sb.nomenclature_id = n.id
ORDER BY n.category, n.name;
```

### 2. Історія рухів по позиції за період:
```sql
SELECT sm.operation_date, sm.operation_type,
       sm.quantity, sm.balance_after, sm.source_operation_type
FROM stock_movements sm
WHERE sm.nomenclature_id = @nomenclature_id
  AND sm.operation_date >= @start_date
  AND sm.operation_date <= @end_date
ORDER BY sm.operation_date DESC;
```

### 3. Всі активні партії виробництва:
```sql
SELECT b.id, b.batch_number, r.name as recipe_name,
       b.status, b.started_at, b.initial_weight
FROM batches b
JOIN recipes r ON r.id = b.recipe_id
WHERE b.status IN ('created', 'salt', 'mix', 'stuff', 'dry')
ORDER BY b.started_at DESC;
```

### 4. Матеріали для партії фасування:
```sql
SELECT m.id, m.name, prm.quantity_per_unit, prm.material_type
FROM packaging_recipe_materials prm
JOIN nomenclature m ON m.id = prm.material_id
WHERE prm.recipe_id = @recipe_id;
```

---

## МІГРАЦІЇ ТА ВЕРСІОНУВАННЯ

### Поточна версія схеми: 1.0

### Історія змін:

**v1.0 (22.11.2025):**
- Фінальна міграція номенклатури
- Видалено 23 застарілі записи
- Об'єднано дублікати (ID 108+178 → 108)
- Додано "Курка вагова" (ID 227)

### Механізм міграцій:

Використовується `init_database()` з перевірками:
```sql
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='table_name' AND xtype='U')
CREATE TABLE ...

IF NOT EXISTS (SELECT * FROM sys.columns WHERE ...)
ALTER TABLE ... ADD ...
```

---

## СТАТИСТИКА БД

**Загальна інформація (станом на 15.12.2025):**

| Метрика | Значення |
|---------|----------|
| Всього таблиць | **27** (актуальна структура з production) |
| Всього індексів | 1 (+ рекомендовано 8) |
| Записів nomenclature | 182 |
| Рецептів виробництва | 8 |
| Рецептів розділки | ~5 |
| Категорій номенклатури | 6 |

**Розподіл таблиць по модулях:**
- Номенклатура та склад: 3 таблиці ✅
- Рецепти: 4 таблиці ✅
- Виробництво: 4 таблиці ✅
- Фасування: 9 таблиць (5 актуальних ⭐ + 4 legacy)
- Розділка: 3 таблиці ✅
- Інвентаризація: 2 таблиці ✅
- Аудит: 1 таблиця ✅
- Допоміжні: 1 таблиця (butchery_recipe_outputs)

**Категорії номенклатури:**
- Сировина (сырьё): 13 позицій
- Полуфабрикати: 14 позицій
- Готова вагова продукція: 10 позицій
- SKU (~27 позицій)
- Спеції: 29 позицій
- Матеріали та упаковка: 46 позицій

---

## BACKUP ТА RECOVERY

**Рекомендації:**

1. **Щоденні backup:**
```sql
BACKUP DATABASE SLAZAR_DB
TO DISK = 'C:\Backups\SLAZAR_DB_Daily.bak'
WITH INIT;
```

2. **Transaction log backup кожні 15 хвилин:**
```sql
BACKUP LOG SLAZAR_DB
TO DISK = 'C:\Backups\SLAZAR_DB_Log.trn'
WITH INIT;
```

3. **Point-in-time recovery:**
```sql
RESTORE DATABASE SLAZAR_DB
FROM DISK = 'C:\Backups\SLAZAR_DB_Daily.bak'
WITH NORECOVERY;

RESTORE LOG SLAZAR_DB
FROM DISK = 'C:\Backups\SLAZAR_DB_Log.trn'
WITH STOPAT = '2025-12-15 14:30:00';
```

---

## ВИСНОВОК

Схема бази даних SLAZAR демонструє:

✅ **Сильні сторони:**
- Добре продумана нормалізація
- Механізми ідемпотентності
- Повний аудит через stock_movements
- Foreign key constraints для цілісності даних
- Unique constraints для бізнес-правил

⚠️ **Потребує покращення:**
- Додаткові індекси для оптимізації запитів
- Soft deletes (is_deleted) замість фізичного видалення
- Більше composite індексів для часто використовуваних фільтрів

**Загальна оцінка схеми БД: 8/10** ✅
