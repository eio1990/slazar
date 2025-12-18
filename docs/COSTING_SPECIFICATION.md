# Технічне завдання: Калькуляція собівартості продукції

**Версія:** 1.0
**Дата:** 18 грудня 2025
**Статус:** Проектування

---

## 1. Загальний опис

Система калькуляції собівартості призначена для розрахунку реальної вартості виробництва кожної одиниці продукції з урахуванням всіх витрат на сировину, матеріали та втрат у процесі виробництва.

### 1.1 Бізнес-завдання

**Мета:** Автоматичний розрахунок собівартості для:
- Вагової готової продукції після завершення виробництва
- SKU (фасованої продукції) після завершення фасування
- Контроль рентабельності виробництва
- Аналіз витрат на кожному етапі

**Принципи калькуляції:**
1. **Фактична собівартість** - базується на реальних витратах та виході
2. **Метод середньозваженої вартості** - для розрахунку вартості залишків
3. **Облік втрат** - усушка, відходи, брак включаються у вартість готової продукції
4. **Пооб'єктний облік** - кожна партія має свою собівартість

---

## 2. Структура даних

### 2.1 Таблиця: butchery_operation_costs (нова)

**Призначення:** Калькуляція собівартості операції розділки з урахуванням стека

```sql
CREATE TABLE butchery_operation_costs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    operation_id INT NOT NULL UNIQUE,

    -- Вхідна сировина
    input_nomenclature_id INT NOT NULL,
    input_weight DECIMAL(18, 6) NOT NULL,
    input_cost_per_kg DECIMAL(18, 4) NOT NULL,
    input_total_cost DECIMAL(18, 4) NOT NULL,

    -- Вихід
    total_output_weight DECIMAL(18, 6) NOT NULL,      -- Сума полуфабрикатів + відходів
    semifinished_weight DECIMAL(18, 6) NOT NULL,      -- Тільки полуфабрикати (без відходів)
    waste_weight DECIMAL(18, 6) NOT NULL,             -- Відходи

    -- Стек (усушка/вихід води)
    shrinkage_weight DECIMAL(18, 6) NOT NULL,         -- input_weight - total_output_weight
    shrinkage_percent DECIMAL(5, 2) NOT NULL,

    -- Скоригована собівартість
    adjusted_cost_per_kg DECIMAL(18, 4) NOT NULL,     -- З урахуванням стека

    calculated_at DATETIME2 DEFAULT GETUTCDATE(),

    FOREIGN KEY (operation_id) REFERENCES butchery_operations(id) ON DELETE CASCADE,
    FOREIGN KEY (input_nomenclature_id) REFERENCES nomenclature(id)
);
```

**Приклад запису:**
```sql
operation_id: 15
input_nomenclature_id: 1 (Яловичина вищого сорту)
input_weight: 100.000
input_cost_per_kg: 150.00
input_total_cost: 15000.00
total_output_weight: 95.000 (70 кг полуфабрикатів + 25 кг відходів)
semifinished_weight: 70.000
waste_weight: 25.000
shrinkage_weight: 5.000 (100 - 95)
shrinkage_percent: 5.00
adjusted_cost_per_kg: 157.89 (15000 / 95)
```

### 2.2 Таблиця: nomenclature_costs (нова)

**Призначення:** Поточна середньозважена собівартість кожної номенклатури

```sql
CREATE TABLE nomenclature_costs (
    nomenclature_id INT PRIMARY KEY,
    weighted_avg_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,  -- Середньозважена вартість за кг/шт
    last_purchase_cost DECIMAL(18, 4),                    -- Остання ціна закупівлі
    last_updated DATETIME2 DEFAULT GETUTCDATE(),

    FOREIGN KEY (nomenclature_id) REFERENCES nomenclature(id)
);
```

**Бізнес-правила:**
- Оновлюється при кожному приході товару
- Формула: `new_avg = (old_balance × old_avg + receipt_qty × receipt_price) / (old_balance + receipt_qty)`
- Використовується для списання матеріалів

### 2.2 Таблиця: batch_costs (нова)

**Призначення:** Детальна калькуляція собівартості виробничої партії

```sql
CREATE TABLE batch_costs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    batch_id INT NOT NULL UNIQUE,

    -- Сировина (етап 0)
    raw_materials_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
    raw_materials_qty DECIMAL(18, 6) NOT NULL DEFAULT 0,

    -- Сіль та вода (етап 1)
    salt_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
    water_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,

    -- Спеції (етап 2)
    spices_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
    mix_produced_qty DECIMAL(18, 6) NOT NULL DEFAULT 0,
    mix_used_qty DECIMAL(18, 6) NOT NULL DEFAULT 0,
    warehouse_mix_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,

    -- Матеріали (етап 3)
    casings_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
    other_materials_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,

    -- Підсумки
    total_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
    final_weight DECIMAL(18, 6) NOT NULL DEFAULT 0,
    cost_per_kg DECIMAL(18, 4) NOT NULL DEFAULT 0,

    -- Втрати
    waste_weight DECIMAL(18, 6) NOT NULL DEFAULT 0,
    waste_percent DECIMAL(5, 2) NOT NULL DEFAULT 0,
    yield_percent DECIMAL(5, 2) NOT NULL DEFAULT 0,

    calculated_at DATETIME2 DEFAULT GETUTCDATE(),

    FOREIGN KEY (batch_id) REFERENCES batches(id) ON DELETE CASCADE
);
```

### 2.3 Таблиця: packaging_batch_costs (нова)

**Призначення:** Калькуляція собівартості партії фасування

```sql
CREATE TABLE packaging_batch_costs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    packaging_batch_id INT NOT NULL UNIQUE,

    -- Вихідна продукція
    source_product_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,     -- Вартість вагової продукції
    source_product_qty DECIMAL(18, 6) NOT NULL DEFAULT 0,      -- Кількість взята
    source_cost_per_kg DECIMAL(18, 4) NOT NULL DEFAULT 0,      -- Вартість за кг

    -- Матеріали для фасування
    packaging_materials_cost DECIMAL(18, 4) NOT NULL DEFAULT 0, -- Пакети, лотки, плівка
    labels_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,             -- Етикетки

    -- Результат
    total_packed_qty INT NOT NULL DEFAULT 0,                   -- Кількість упаковок
    waste_qty DECIMAL(18, 6) NOT NULL DEFAULT 0,               -- Відходи (осипання)

    -- Собівартість
    total_cost DECIMAL(18, 4) NOT NULL DEFAULT 0,
    cost_per_unit DECIMAL(18, 4) NOT NULL DEFAULT 0,           -- Собівартість 1 упаковки

    calculated_at DATETIME2 DEFAULT GETUTCDATE(),

    FOREIGN KEY (packaging_batch_id) REFERENCES packaging_batches(id) ON DELETE CASCADE
);
```

### 2.4 Оновлення stock_movements

**Додати поля для зберігання собівартості:**

```sql
ALTER TABLE stock_movements ADD cost_per_unit DECIMAL(18, 4);
ALTER TABLE stock_movements ADD total_cost DECIMAL(18, 4);
```

**Бізнес-правила:**
- `price_per_unit` - закупівельна ціна (для приходів)
- `cost_per_unit` - собівартість (для виробництва/фасування)
- `total_cost = quantity × cost_per_unit`

---

## 3. Алгоритми калькуляції

### 3.1 Калькуляція розділки (СТЕК)

**Момент розрахунку:** При завершенні операції розділки

**Проблема "СТЕК":**
Закуплене м'ясо може містити вколоту воду або бути замороженим. При розморожуванні або розділці з м'яса виходить вода, і реальна вага стає меншою за закуплену. Це призводить до збільшення собівартості сировини.

**Приклад:**
```
Закуплено: 100 кг яловичини × 150 грн/кг = 15,000 грн
При розділці отримано: 95 кг (5% стек - вийшла вода)
Реальна собівартість сировини: 15,000 / 95 = 157.89 грн/кг (+5.26%)
```

**Формула розрахунку:**

```
INPUT_COST = input_weight × source_avg_cost

ACTUAL_OUTPUT = Σ(output_weights)  // Сума всіх полуфабрикатів + відходів

SHRINKAGE = input_weight - ACTUAL_OUTPUT
SHRINKAGE_PERCENT = (SHRINKAGE / input_weight) × 100

// Якщо є стек (усушка сировини)
if SHRINKAGE > 0:
    ADJUSTED_COST_PER_KG = INPUT_COST / ACTUAL_OUTPUT
else:
    ADJUSTED_COST_PER_KG = source_avg_cost

// Для кожного полуфабрикату
SEMIFINISHED_COST_PER_KG = ADJUSTED_COST_PER_KG

// Оновити nomenclature_costs для кожного полуфабрикату
update_avg_cost(semifinished_id, output_weight, SEMIFINISHED_COST_PER_KG)
```

**Бізнес-правила:**

1. **Стек на вході:**
   - Якщо `input_weight > Σ(outputs)` → є стек
   - Різниця розподіляється на вихідні полуфабрикати
   - Собівартість кожного кг полуфабрикату зростає

2. **Відходи:**
   - НЕ оприходуються на склад
   - Але враховуються в розрахунку стека
   - Якщо 100 кг → 70 кг полуф + 25 кг відходи = 95 кг (5% стек)

3. **Нульовий стек:**
   - Якщо `input_weight = Σ(outputs)` → стека немає
   - Собівартість = закупівельна ціна

**Приклад розрахунку зі стеком:**

```
Розділка яловичини:
Закуплено: 100 кг × 150 грн/кг = 15,000 грн

Фактичний вихід:
- Філе: 30 кг
- Грудинка: 25 кг
- Лопатка: 20 кг
- Відходи: 20 кг
TOTAL OUTPUT = 95 кг

SHRINKAGE = 100 - 95 = 5 кг (5% стек - вода вийшла)

Скоригована собівартість:
ADJUSTED_COST = 15,000 / 95 = 157.89 грн/кг (+5.26%)

Полуфабрикати на склад:
- Філе: 30 кг × 157.89 = 4,736.84 грн (собівартість 157.89 грн/кг)
- Грудинка: 25 кг × 157.89 = 3,947.37 грн (собівартість 157.89 грн/кг)
- Лопатка: 20 кг × 157.89 = 3,157.89 грн (собівартість 157.89 грн/кг)

Втрати від стека (5 кг води) розподілено на полуфабрикати
```

**Без стека (нормальна ситуація):**

```
Розділка конини:
Закуплено: 100 кг × 180 грн/кг = 18,000 грн

Фактичний вихід:
- Конина 1с: 35 кг
- Конина 2с: 40 кг
- Відходи: 25 кг
TOTAL OUTPUT = 100 кг

SHRINKAGE = 0 кг (стека немає)

Собівартість полуфабрикатів = 180 грн/кг (без змін)
```

### 3.2 Калькуляція виробничої партії

**Момент розрахунку:** При завершенні партії (етап 5 - completed)

**Формула загальної собівартості:**
```
TOTAL_COST = RAW_MATERIALS + SALT + WATER + SPICES + WAREHOUSE_MIX + CASINGS + OTHER_MATERIALS

де:
RAW_MATERIALS = Σ(ingredient_qty × ingredient_avg_cost)
SALT = salt_qty × salt_avg_cost
WATER = water_qty × water_avg_cost
SPICES = Σ(spice_qty × spice_avg_cost) - INCLUDING fenugreek water
WAREHOUSE_MIX = warehouse_mix_qty × warehouse_mix_avg_cost
CASINGS = casing_qty × casing_avg_cost
OTHER_MATERIALS = Σ(material_qty × material_avg_cost)
```

**Розрахунок собівартості за кг:**
```
COST_PER_KG = TOTAL_COST / FINAL_WEIGHT
```

**Облік втрат:**
```
WASTE_WEIGHT = INITIAL_WEIGHT - FINAL_WEIGHT
WASTE_PERCENT = (WASTE_WEIGHT / INITIAL_WEIGHT) × 100
YIELD_PERCENT = (FINAL_WEIGHT / INITIAL_WEIGHT) × 100
```

> ⚠️ Втрати НЕ є окремою статтею - вони включені в собівартість готової продукції через зменшення фінального виходу

**Приклад розрахунку:**

```
Партія бастурми:
- Сировина: 100 кг × 150 грн/кг = 15,000 грн
- Сіль: 2 кг × 10 грн/кг = 20 грн
- Вода: 5 кг × 0 грн/кг = 0 грн
- Спеції: 3 кг (суміш) × 80 грн/кг = 240 грн
- Оболонки: 1 кг × 50 грн/кг = 50 грн

TOTAL_COST = 15,310 грн
FINAL_WEIGHT = 75 кг (25% втрат)
COST_PER_KG = 15,310 / 75 = 204.13 грн/кг

Собівартість зросла через усушку (25% втрат розподілено на 75 кг)
```

### 3.2 Калькуляція фасування

**Момент розрахунку:** При завершенні партії фасування

**Формула собівартості упаковки:**
```
SOURCE_COST = source_qty × source_product_cost_per_kg
MATERIALS_COST = Σ(material_qty × material_avg_cost)
TOTAL_COST = SOURCE_COST + MATERIALS_COST
COST_PER_UNIT = TOTAL_COST / packed_quantity
```

**Приклад розрахунку:**

```
Фасування бастурми в вакуум 100г:
- Вагова бастурма: 10 кг × 204.13 грн/кг = 2,041.30 грн
- Пакети вакуумні: 100 шт × 0.50 грн/шт = 50 грн
- Етикетки: 100 шт × 0.10 грн/шт = 10 грн
- Лотки: 100 шт × 0.30 грн/шт = 30 грн

TOTAL_COST = 2,131.30 грн
PACKED_QUANTITY = 98 шт (2 брак)
COST_PER_UNIT = 2,131.30 / 98 = 21.75 грн/шт

Собівартість 1 упаковки = 21.75 грн
```

### 3.3 Облік суміші специй на складі

**Проблема:** Залишки суміші зі складу мають собівартість з попередніх партій

**Рішення:**

1. **При виробництві нової суміші:**
   - Розраховується вартість виробленої суміші
   - Залишок зберігається на складі з вартістю `cost_per_kg`

2. **При використанні суміші зі складу:**
   - Береться поточна середньозважена вартість зі `nomenclature_costs`
   - Додається до витрат партії

3. **Метод FIFO не використовується** - тільки середньозважена вартість

---

## 4. API Endpoints

### 4.1 POST /api/costing/calculate-butchery/{operation_id}

**Призначення:** Розрахунок собівартості операції розділки з урахуванням стека

**Request:** (без параметрів)

**Response:**
```json
{
  "operation_id": 15,
  "operation_number": "BUT-20251218-001",
  "input": {
    "nomenclature_id": 1,
    "name": "Яловичина вищого сорту",
    "weight": 100.0,
    "cost_per_kg": 150.00,
    "total_cost": 15000.00
  },
  "output": {
    "semifinished": [
      {"nomenclature_id": 10, "name": "Філе яловичини", "weight": 30.0},
      {"nomenclature_id": 11, "name": "Грудинка яловичини", "weight": 25.0},
      {"nomenclature_id": 12, "name": "Лопатка яловичини", "weight": 20.0}
    ],
    "waste": {"weight": 20.0},
    "total_weight": 95.0
  },
  "shrinkage": {
    "weight": 5.0,
    "percent": 5.0,
    "reason": "Вихід води з наколотого м'яса"
  },
  "adjusted_cost_per_kg": 157.89,
  "cost_increase_percent": 5.26,
  "semifinished_total_cost": 11842.11
}
```

**Бізнес-логіка:**
1. Якщо `shrinkage > 0` → показати попередження про стек
2. Скоригована собівартість розподіляється на всі полуфабрикати рівномірно
3. Оновлюються `nomenclature_costs` для кожного полуфабрикату

### 4.2 POST /api/costing/calculate-batch/{batch_id}

**Призначення:** Розрахунок собівартості виробничої партії

**Request:** (без параметрів)

**Response:**
```json
{
  "batch_id": 123,
  "batch_number": "BAST-20251218-001",
  "costs": {
    "raw_materials": {
      "cost": 15000.00,
      "items": [
        {"nomenclature_id": 1, "name": "Яловичина 1с", "qty": 100.0, "cost_per_kg": 150.00, "total": 15000.00}
      ]
    },
    "salt": {"qty": 2.0, "cost_per_kg": 10.00, "total": 20.00},
    "water": {"qty": 5.0, "cost_per_kg": 0.00, "total": 0.00},
    "spices": {
      "cost": 240.00,
      "items": [
        {"nomenclature_id": 19, "name": "Пажитник", "qty": 1.0, "cost_per_kg": 100.00, "total": 100.00},
        {"nomenclature_id": 28, "name": "Часник", "qty": 2.0, "cost_per_kg": 70.00, "total": 140.00}
      ]
    },
    "warehouse_mix": {"qty": 0.5, "cost_per_kg": 80.00, "total": 40.00},
    "casings": {"qty": 1.0, "cost_per_kg": 50.00, "total": 50.00},
    "other_materials": {"cost": 0.00, "items": []},
    "total_cost": 15310.00
  },
  "output": {
    "initial_weight": 100.0,
    "final_weight": 75.0,
    "waste_weight": 25.0,
    "waste_percent": 25.0,
    "yield_percent": 75.0
  },
  "cost_per_kg": 204.13
}
```

### 4.2 POST /api/costing/calculate-packaging/{packaging_batch_id}

**Призначення:** Розрахунок собівартості партії фасування

**Response:**
```json
{
  "packaging_batch_id": 45,
  "batch_number": "PKG-20251218-001",
  "source_product": {
    "nomenclature_id": 108,
    "name": "Бастурма вагова",
    "qty": 10.0,
    "cost_per_kg": 204.13,
    "total": 2041.30
  },
  "materials": {
    "cost": 90.00,
    "items": [
      {"nomenclature_id": 45, "name": "Пакет вакуум 100г", "qty": 100, "cost_per_unit": 0.50, "total": 50.00},
      {"nomenclature_id": 46, "name": "Етикетка", "qty": 100, "cost_per_unit": 0.10, "total": 10.00},
      {"nomenclature_id": 47, "name": "Лоток", "qty": 100, "cost_per_unit": 0.30, "total": 30.00}
    ]
  },
  "output": {
    "total_packed": 98,
    "waste_qty": 0.2,
    "waste_percent": 2.0
  },
  "total_cost": 2131.30,
  "cost_per_unit": 21.75
}
```

### 4.3 GET /api/costing/nomenclature/{nomenclature_id}

**Призначення:** Отримати поточну собівартість номенклатури

**Response:**
```json
{
  "nomenclature_id": 108,
  "name": "Бастурма вагова",
  "weighted_avg_cost": 204.13,
  "last_purchase_cost": null,
  "last_updated": "2025-12-18T14:30:00"
}
```

### 4.4 POST /api/costing/update-receipt-cost

**Призначення:** Оновлення середньозваженої вартості при приході товару

**Request:**
```json
{
  "nomenclature_id": 1,
  "receipt_qty": 50.0,
  "receipt_price": 155.00,
  "idempotency_key": "receipt-20251218-001"
}
```

**Response:**
```json
{
  "nomenclature_id": 1,
  "old_balance": 100.0,
  "old_avg_cost": 150.00,
  "new_balance": 150.0,
  "new_avg_cost": 151.67,
  "updated": true
}
```

---

## 5. Бізнес-правила

### 5.1 Ціноутворення

**Початкові ціни (seed data):**
- При першому розгортанні системи потрібно ввести закупівельні ціни для всіх позицій
- Може бути окремий endpoint `/api/costing/seed-prices` або CSV імпорт

**Оновлення цін:**
- Ціни оновлюються тільки при приході товару з ціною
- Якщо прихід без ціни - використовується поточна середньозважена

**Нульова ціна:**
- Вода, відходи можуть мати вартість 0
- При розрахунках враховуються як 0

### 5.2 Точність розрахунків

**Заокруглення:**
- Всі грошові суми: 2 знаки після коми (копійки)
- Вага: 3 знаки після коми (грами)
- Вартість за кг: 4 знаки після коми

**Дрібні розбіжності:**
- При розподілі вартості можливі відхилення в межах 0.01 грн
- Використовується округлення banker's rounding

### 5.3 Історія змін

**Незмінність калькуляції:**
- Після розрахунку собівартості партії дані НЕ перераховуються
- Це історична калькуляція на момент виробництва
- Зміни цін сировини НЕ впливають на минулі партії

**Аудит:**
- Всі зміни цін логуються
- Можливість перегляду калькуляції будь-якої партії

---

## 6. Інтеграція з існуючими модулями

### 6.1 Модуль розділки (butchery_api.py)

**Зміни:**

1. **При завершенні розділки** (`POST /api/butchery/operations/{id}/complete`):
   ```python
   # Після оприходування полуфабрикатів
   costing_result = await calculate_butchery_cost(operation_id)

   # Зберегти калькуляцію
   save_butchery_costs(operation_id, costing_result)

   # Перевірити наявність стека
   if costing_result['shrinkage_weight'] > 0:
       # Показати попередження оператору
       warning = f"Виявлено стек {costing_result['shrinkage_percent']:.2f}%. "
       warning += f"Собівартість збільшено на {costing_result['cost_increase_percent']:.2f}%"
       log_warning(operation_id, warning)

   # Оновити nomenclature_costs для кожного полуфабрикату
   for output in outputs:
       if output['output_type'] == 'semifinished':
           update_nomenclature_avg_cost(
               output['nomenclature_id'],
               output['weight'],
               costing_result['adjusted_cost_per_kg']
           )

   # Записати в stock_movements з cost_per_unit
   for output in outputs:
       if output['output_type'] == 'semifinished':
           create_stock_movement(
               nomenclature_id=output['nomenclature_id'],
               quantity=output['weight'],
               operation_type='butchery_output',
               cost_per_unit=costing_result['adjusted_cost_per_kg']
           )
   ```

2. **Відображення у frontend:**
   ```typescript
   // Показати попередження про стек
   if (costingResult.shrinkage_weight > 0) {
       Alert.alert(
           'Виявлено стек',
           `Втрата ваги: ${costingResult.shrinkage_weight} кг (${costingResult.shrinkage_percent}%)\n` +
           `Собівартість збільшено на ${costingResult.cost_increase_percent}%\n` +
           `Нова собівартість: ${costingResult.adjusted_cost_per_kg} грн/кг`,
           [{text: 'Зрозуміло'}]
       );
   }
   ```

**Важливо:**
- Стек може бути від 0% до 10-15% (типово 3-7%)
- Якщо стек > 15% → потрібна верифікація (можлива помилка зважування)
- Стек враховується тільки якщо `input_weight > total_output_weight`

### 6.2 Модуль виробництва (production_api.py)

**Зміни:**

1. **При завершенні партії** (`POST /api/production/batches/{id}/complete`):
   ```python
   # Після оприходування готової продукції
   costing_result = await calculate_batch_cost(batch_id)

   # Зберегти собівартість в batch_costs
   save_batch_costs(batch_id, costing_result)

   # Оновити nomenclature_costs для готової продукції
   update_nomenclature_avg_cost(
       target_product_id,
       final_weight,
       costing_result['cost_per_kg']
   )

   # Записати в stock_movements з cost_per_unit
   create_stock_movement(
       nomenclature_id=target_product_id,
       quantity=final_weight,
       operation_type='production_output',
       cost_per_unit=costing_result['cost_per_kg']
   )
   ```

2. **При створенні партії** (етап 0):
   - Списувати матеріали з вартістю з `nomenclature_costs`
   - Зберігати `cost_per_unit` в `stock_movements`

### 6.2 Модуль фасування (packaging_api.py)

**Зміни:**

1. **При завершенні фасування** (`POST /api/packaging/batches/{id}/complete`):
   ```python
   # Після оприходування SKU
   costing_result = await calculate_packaging_cost(packaging_batch_id)

   # Зберегти собівартість
   save_packaging_costs(packaging_batch_id, costing_result)

   # Оновити nomenclature_costs для SKU
   update_nomenclature_avg_cost(
       target_product_id,
       packed_quantity,
       costing_result['cost_per_unit']
   )

   # Записати в stock_movements
   create_stock_movement(
       nomenclature_id=target_product_id,
       quantity=packed_quantity,
       operation_type='packaging_output',
       cost_per_unit=costing_result['cost_per_unit']
   )
   ```

### 6.3 Модуль операцій (main.py)

**Зміни:**

1. **Прихід товару** (`POST /api/stock/receipt`):
   ```python
   # Якщо прихід з ціною - оновити середньозважену
   if operation.price_per_unit:
       update_weighted_avg_cost(
           nomenclature_id,
           quantity,
           operation.price_per_unit
       )
   ```

2. **Розхід товару** (`POST /api/stock/withdrawal`):
   - Списувати за поточною середньозваженою вартістю
   - Записувати `cost_per_unit` в `stock_movements`

---

## 7. Frontend відображення

### 7.1 Екран виробництва - деталі партії

**Додати вкладку "Собівартість":**

```typescript
interface BatchCostDetails {
  raw_materials: CostItem[];
  salt: CostItem;
  water: CostItem;
  spices: CostItem[];
  warehouse_mix: CostItem;
  casings: CostItem;
  other_materials: CostItem[];
  total_cost: number;
  final_weight: number;
  cost_per_kg: number;
  yield_percent: number;
}

// Відображення у вигляді таблиці
<View>
  <Text>Сировина: {formatMoney(costs.raw_materials_cost)}</Text>
  <Text>Спеції: {formatMoney(costs.spices_cost)}</Text>
  <Text>Матеріали: {formatMoney(costs.casings_cost)}</Text>
  <Text>──────────────────</Text>
  <Text>Разом: {formatMoney(costs.total_cost)}</Text>
  <Text>Вага: {costs.final_weight} кг</Text>
  <Text>Собівартість: {formatMoney(costs.cost_per_kg)} грн/кг</Text>
</View>
```

### 7.2 Екран фасування - деталі партії

**Показати собівартість SKU:**

```typescript
<View>
  <Text>Вагова продукція: {formatMoney(source_cost)}</Text>
  <Text>Матеріали: {formatMoney(materials_cost)}</Text>
  <Text>──────────────────</Text>
  <Text>Разом: {formatMoney(total_cost)}</Text>
  <Text>Упаковок: {packed_qty} шт</Text>
  <Text>Собівартість упаковки: {formatMoney(cost_per_unit)} грн/шт</Text>
</View>
```

### 7.3 Екран "Склад" - список залишків

**Додати колонку "Собівартість":**

```typescript
<FlatList
  data={balances}
  renderItem={({item}) => (
    <View>
      <Text>{item.name}</Text>
      <Text>{item.quantity} {item.unit}</Text>
      <Text>{formatMoney(item.avg_cost)} грн/{item.unit}</Text>
    </View>
  )}
/>
```

---

## 8. Звіти та аналітика

### 8.1 Звіт з собівартості виробництва

**GET /api/reports/production-costs**

Параметри:
- date_from, date_to
- recipe_id (опціонально)

**Показати:**
- Список всіх партій за період
- Собівартість кожної партії
- Середня собівартість за кг
- Загальні витрати

### 8.2 Звіт з рентабельності

**GET /api/reports/profitability**

**Показати:**
- Собівартість vs ціна продажу (якщо є дані про продажі)
- Маржа (%)
- ТОП-5 найдорожчих у виробництві
- ТОП-5 найдешевших

### 8.3 Аналіз втрат

**GET /api/reports/waste-analysis**

**Показати:**
- Середній відсоток усушки по рецептах виробництва
- Відхилення від норми
- Вплив втрат на собівартість

### 8.4 Аналіз стека на розділці

**GET /api/reports/butchery-shrinkage**

Параметри:
- date_from, date_to
- source_nomenclature_id (опціонально)

**Показати:**
```json
{
  "period": {"from": "2025-12-01", "to": "2025-12-18"},
  "operations_count": 25,
  "summary": {
    "total_input_weight": 2500.0,
    "total_output_weight": 2375.0,
    "total_shrinkage_weight": 125.0,
    "avg_shrinkage_percent": 5.0,
    "total_cost_increase": 6578.95
  },
  "by_source": [
    {
      "nomenclature_id": 1,
      "name": "Яловичина вищого сорту",
      "operations": 15,
      "avg_shrinkage": 6.2,
      "max_shrinkage": 12.5,
      "min_shrinkage": 2.1,
      "total_cost_increase": 4250.00
    },
    {
      "nomenclature_id": 5,
      "name": "Конина першого сорту",
      "operations": 10,
      "avg_shrinkage": 3.1,
      "max_shrinkage": 5.0,
      "min_shrinkage": 1.5,
      "total_cost_increase": 2328.95
    }
  ],
  "anomalies": [
    {
      "operation_id": 142,
      "date": "2025-12-15",
      "source": "Яловичина вищого сорту",
      "shrinkage_percent": 12.5,
      "reason": "Перевищує норму (> 10%)"
    }
  ]
}
```

**Бізнес-цінність:**
- Виявлення постачальників з низькоякісним м'ясом (високий стек)
- Контроль якості закупівель
- Прогнозування реальної собівартості

---

## 9. Міграція та seed data

### 9.1 Створення таблиць

```sql
-- 1. butchery_operation_costs (СТЕК)
CREATE TABLE butchery_operation_costs (...);

-- 2. nomenclature_costs
CREATE TABLE nomenclature_costs (...);

-- 3. batch_costs
CREATE TABLE batch_costs (...);

-- 4. packaging_batch_costs
CREATE TABLE packaging_batch_costs (...);

-- 5. Оновлення stock_movements
ALTER TABLE stock_movements ADD cost_per_unit DECIMAL(18, 4);
ALTER TABLE stock_movements ADD total_cost DECIMAL(18, 4);
```

### 9.2 Початкові ціни

**Файл: seed_prices.sql**

```sql
-- Сировина
INSERT INTO nomenclature_costs (nomenclature_id, weighted_avg_cost) VALUES
(1, 150.00),  -- Яловичина 1с
(2, 145.00),  -- Яловичина 2с
(5, 180.00),  -- Конина 1с
...

-- Спеції
(19, 100.00), -- Пажитник
(28, 70.00),  -- Часник
...

-- Матеріали
(45, 0.50),   -- Пакет вакуум
(46, 0.10),   -- Етикетка
...
```

---

## 10. Етапи впровадження

### Етап 1: Базова структура (1-2 дні)
- [ ] Створити таблиці в database.py
  - butchery_operation_costs
  - nomenclature_costs
  - batch_costs
  - packaging_batch_costs
- [ ] Додати моделі Pydantic
- [ ] Створити costing_api.py з базовими endpoints

### Етап 2: Калькуляція розділки зі СТЕКОМ (2 дні)
- [ ] Реалізувати calculate_butchery_cost()
- [ ] Додати логіку виявлення та обліку стека
- [ ] Реалізувати update_weighted_avg_cost()
- [ ] Написати тести для стека (0%, 5%, 15%)
- [ ] Додати попередження при стеку > 10%

### Етап 3: Інтеграція з розділкою (1 день)
- [ ] Оновити butchery_api.py
- [ ] Додати розрахунок при завершенні розділки
- [ ] Додати Alert про стек у frontend
- [ ] Тестування на реальних даних

### Етап 4: Калькуляція виробництва (2-3 дні)
- [ ] Реалізувати calculate_batch_cost()
- [ ] Врахувати усушку (25-35%)
- [ ] Облік суміші специй зі складу
- [ ] Написати тести для розрахунків

### Етап 5: Інтеграція з виробництвом (1-2 дні)
- [ ] Оновити production_api.py
- [ ] Додати розрахунок при завершенні партії
- [ ] Тестування на реальних даних

### Етап 6: Калькуляція фасування (1-2 дні)
- [ ] Реалізувати calculate_packaging_cost()
- [ ] Облік брака та осипання
- [ ] Написати тести

### Етап 7: Інтеграція з фасуванням (1 день)
- [ ] Оновити packaging_api.py
- [ ] Додати розрахунок при завершенні фасування
- [ ] Тестування

### Етап 8: Frontend (2-3 дні)
- [ ] Додати вкладку "Собівартість" в деталі партій
- [ ] Показати попередження про стек на розділці
- [ ] Оновити екрани виробництва та фасування
- [ ] Додати відображення собівартості в списках
- [ ] Створити екран звітів зі стеком

### Етап 9: Звіти та аналітика (2 дні)
- [ ] Звіт з собівартості виробництва
- [ ] Звіт рентабельності
- [ ] Аналіз втрат (усушка)
- [ ] Аналіз стека на розділці (ТОП постачальники)

### Етап 10: Seed data та міграція (1 день)
- [ ] Підготувати початкові ціни для всієї номенклатури
- [ ] Запустити міграцію на production
- [ ] Перерахувати собівартість існуючих партій (опціонально)

**Загальний час:** 13-18 днів

**Пріоритет 1 (критично):**
- Етапи 1-3: Розділка зі стеком (4-5 днів)

**Пріоритет 2 (важливо):**
- Етапи 4-7: Виробництво та фасування (5-9 днів)

**Пріоритет 3 (бажано):**
- Етапи 8-10: Frontend та звіти (5 днів)

---

## 11. Ризики та обмеження

### 11.1 Ризики

1. **Відсутність історичних цін**
   - Рішення: Використати експертну оцінку для seed prices

2. **Складність перерахунку минулих партій**
   - Рішення: Не перераховувати історію, починати з нових партій

3. **Точність розрахунків**
   - Рішення: Детальне тестування з реальними даними

### 11.2 Обмеження

- Не враховуються непрямі витрати (електроенергія, зарплата, оренда)
- Тільки прямі матеріальні витрати
- Можливе розширення у майбутньому

---

## 12. Приклади використання

### Сценарій 1: Повний цикл - від закупівлі до SKU (зі СТЕКОМ)

**Крок 0: Закупівля сировини**
```
Закуплено: 100 кг яловичини вищого сорту × 150 грн/кг = 15,000 грн
```

**Крок 1: Розділка (з наявністю стека)**
```
Вхід: 100 кг яловичини × 150 грн/кг = 15,000 грн

Фактичний вихід:
- Філе: 30 кг
- Грудинка: 25 кг
- Лопатка: 15 кг
- Відходи: 25 кг
TOTAL: 95 кг

⚠️ СТЕК: 5 кг (5% - вийшла вколота вода)

Скоригована собівартість:
15,000 / 95 = 157.89 грн/кг (+5.26% через стек)

Полуфабрикати на склад:
- Філе: 30 кг × 157.89 = 4,736.84 грн
- Грудинка: 25 кг × 157.89 = 3,947.37 грн
- Лопатка: 15 кг × 157.89 = 2,368.42 грн
```

**Крок 2: Виробництво бастурми з філе**
```
Вхід: 30 кг філе × 157.89 грн/кг = 4,736.84 грн
Спеції: 310 грн
Оболонки: 50 грн
TOTAL COST: 5,096.84 грн

Вихід: 22 кг готової бастурми (усушка 26.7%)

Собівартість бастурми: 5,096.84 / 22 = 231.67 грн/кг
```

**Крок 3: Фасування бастурми**
```
Вхід: 10 кг бастурми × 231.67 = 2,316.70 грн
Матеріали (пакети, лотки, етикетки): 90 грн
TOTAL COST: 2,406.70 грн

Вихід: 98 упаковок по 100г (брак 2 шт, осипання 0.2 кг)

Собівартість упаковки: 2,406.70 / 98 = 24.56 грн/шт
```

**Підсумок:**
```
Початкова закупівельна ціна: 150 грн/кг
Фінальна собівартість SKU: 245.60 грн/кг (+63.7%)

Причини зростання:
1. Стек на розділці: +5.26% (157.89 грн/кг)
2. Усушка при виробництві: +46.7% (231.67 грн/кг)
3. Матеріали фасування: +6% (245.60 грн/кг)
```

### Сценарій 2: Виробництво без стека

**Крок 1: Розділка конини (якісне м'ясо, без стека)**
```
Вхід: 100 кг конини × 180 грн/кг = 18,000 грн

Фактичний вихід:
- Конина 1с: 35 кг
- Конина 2с: 40 кг
- Відходи: 25 кг
TOTAL: 100 кг

✅ СТЕК: 0 кг (немає втрат)

Собівартість полуфабрикатів: 180 грн/кг (без змін)
```

### Сценарій 3: Виробництво бастурми

```
1. Оператор створює партію → система списує сировину за avg_cost
2. Проходження етапів → система фіксує всі витрати
3. Завершення партії → автоматичний розрахунок:
   - Входи: 100 кг × 150 грн = 15,000 грн + спеції 310 грн
   - Вихід: 75 кг
   - Собівартість: 15,310 / 75 = 204.13 грн/кг
4. Готова продукція на склад з avg_cost = 204.13 грн/кг
```

### Сценарій 2: Фасування бастурми

```
1. Оператор бере 10 кг бастурми зі складу
2. Система списує 10 кг × 204.13 грн = 2,041.30 грн
3. Додаються матеріали: 100 пакетів × 0.50 = 50 грн + ...
4. Завершення фасування:
   - Вихід: 98 упаковок
   - Собівартість: (2,041.30 + 90) / 98 = 21.75 грн/шт
5. SKU на склад з avg_cost = 21.75 грн/шт
```

---

**Автор:** Claude Sonnet 4.5
**Контакти:** github.com/anthropics/claude-code
