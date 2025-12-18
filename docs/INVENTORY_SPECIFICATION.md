# Технічне завдання: Модуль інвентаризації (Inventory)

**Версія:** 1.0
**Дата:** 18 грудня 2025
**Статус:** In Development

---

## 1. Загальний опис

Модуль інвентаризації призначений для проведення перевірки фактичних залишків на складі з подальшим коригуванням системних даних та формуванням звітності для керівництва.

### 1.1 Бізнес-процес

```
1. Початок інвентаризації
   - Керівник/старший менеджер ініціює інвентаризацію
   - Обирається тип (повна/часткова)
   - Система робить "знімок" поточних залишків на момент старту
   - Всі залишки фіксуються в inventory_snapshot
   - Статус: in_progress
   ↓
2. Проведення інвентаризації
   - Оператори фізично перевіряють залишки на складі
   - Вводять фактичну кількість по кожній позиції
   - Можливість додавати коментарі та фото
   - Система показує різницю (факт - система)
   - Можливість зупинити та продовжити пізніше
   ↓
3. Перевірка відхилень
   - Система автоматично розраховує відхилення
   - Великі відхилення (>10%) підсвічуються
   - Вимагається коментар для значних відхилень
   - Можливість повторного підрахунку позицій з відхиленнями
   ↓
4. Узгодження (опціонально)
   - Для відхилень >20% - вимагається підтвердження керівника
   - Керівник переглядає список відхилень
   - Може запросити повторний підрахунок
   - Підтверджує або відхиляє результати
   ↓
5. Завершення інвентаризації
   - Остаточний розрахунок всіх відхилень
   - Створення коригувальних проводок (stock_movements)
   - Оновлення stock_balances на фактичні значення
   - Генерація PDF звіту
   - Статус: completed
   ↓
6. Звітність
   - Звіт по інвентаризації (PDF)
   - Список відхилень з причинами
   - Вартісна оцінка відхилень (якщо є ціни)
   - Відповідальні особи
   - Дата та час проведення
```

---

## 2. Структура даних

### 2.1 Таблиця: inventory_sessions

**Призначення:** Сесії інвентаризації

```sql
id                      INT PRIMARY KEY IDENTITY
session_number          NVARCHAR(50) NOT NULL UNIQUE      -- "INV-20251218-001"
session_type            NVARCHAR(50) NOT NULL             -- "full", "partial", "spot_check"
status                  NVARCHAR(50) NOT NULL             -- "in_progress", "pending_approval", "completed", "cancelled"
started_at              DATETIME2 NOT NULL DEFAULT GETUTCDATE()
completed_at            DATETIME2 NULL
started_by_user         NVARCHAR(255) NULL                -- Ім'я користувача який почав
approved_by_user        NVARCHAR(255) NULL                -- Хто затвердив (якщо потрібно)
approval_required       BIT DEFAULT 0                     -- Чи потрібне затвердження
notes                   NVARCHAR(MAX) NULL                -- Загальні примітки
idempotency_key         NVARCHAR(255) NOT NULL UNIQUE
created_at              DATETIME2 DEFAULT GETUTCDATE()
updated_at              DATETIME2 DEFAULT GETUTCDATE()
```

**Типи інвентаризації:**
- `full` - Повна інвентаризація (всі позиції)
- `partial` - Часткова (вибрані категорії)
- `spot_check` - Вибіркова перевірка (випадкові позиції)

**Статуси:**
- `in_progress` - Проводиться
- `pending_approval` - Очікує затвердження
- `completed` - Завершена, залишки оновлені
- `cancelled` - Скасована

### 2.2 Таблиця: inventory_snapshot

**Призначення:** Знімок залишків на момент початку інвентаризації

```sql
id                      INT PRIMARY KEY IDENTITY
session_id              INT NOT NULL → inventory_sessions(id) ON DELETE CASCADE
nomenclature_id         INT NOT NULL → nomenclature(id)
snapshot_quantity       DECIMAL(18,6) NOT NULL            -- Системна кількість на момент старту
snapshot_timestamp      DATETIME2 NOT NULL                -- Точний час знімку
unit                    NVARCHAR(50) NOT NULL             -- Одиниця виміру (кг, шт, л)
category                NVARCHAR(100) NULL                -- Категорія для зручності
created_at              DATETIME2 DEFAULT GETUTCDATE()

INDEX IX_inventory_snapshot_session (session_id)
```

**Бізнес-правила:**
- Створюється автоматично при старті інвентаризації
- Immutable - ніколи не змінюється
- Використовується для розрахунку відхилень

### 2.3 Таблиця: inventory_items

**Призначення:** Фактичні підрахунки під час інвентаризації

```sql
id                      INT PRIMARY KEY IDENTITY
session_id              INT NOT NULL → inventory_sessions(id) ON DELETE CASCADE
nomenclature_id         INT NOT NULL → nomenclature(id)
system_quantity         DECIMAL(18,6) NOT NULL            -- З snapshot (для зручності)
actual_quantity         DECIMAL(18,6) NULL                -- Фактична кількість (NULL = не підраховано)
difference              DECIMAL(18,6) NULL                -- Відхилення (actual - system)
difference_percent      DECIMAL(10,2) NULL                -- Відхилення (%)
status                  NVARCHAR(50) NOT NULL             -- "pending", "counted", "verified", "discrepancy"
counted_by_user         NVARCHAR(255) NULL                -- Хто рахував
counted_at              DATETIME2 NULL                    -- Коли порахували
verified_by_user        NVARCHAR(255) NULL                -- Хто перевірив (при великих відхиленнях)
verified_at             DATETIME2 NULL
recount_required        BIT DEFAULT 0                     -- Чи потрібен повторний підрахунок
recount_reason          NVARCHAR(MAX) NULL                -- Причина повторного підрахунку
notes                   NVARCHAR(MAX) NULL                -- Примітки
photo_urls              NVARCHAR(MAX) NULL                -- JSON з URLs фото (опціонально)
created_at              DATETIME2 DEFAULT GETUTCDATE()
updated_at              DATETIME2 DEFAULT GETUTCDATE()

INDEX IX_inventory_items_session (session_id)
INDEX IX_inventory_items_status (session_id, status)
UNIQUE (session_id, nomenclature_id)
```

**Статуси позиції:**
- `pending` - Очікує підрахунку
- `counted` - Підраховано
- `verified` - Перевірено (для великих відхилень)
- `discrepancy` - Виявлено значне відхилення

### 2.4 Таблиця: inventory_categories

**Призначення:** Категорії для часткової інвентаризації

```sql
id                      INT PRIMARY KEY IDENTITY
session_id              INT NOT NULL → inventory_sessions(id) ON DELETE CASCADE
category                NVARCHAR(100) NOT NULL            -- Категорія номенклатури
is_included             BIT DEFAULT 1                     -- Чи включена в інвентаризацію
created_at              DATETIME2 DEFAULT GETUTCDATE()

UNIQUE (session_id, category)
```

**Використання:**
- Для часткової інвентаризації - визначає які категорії перевіряються
- Приклад: перевірити тільки "сировина" та "готова продукція вагова"

### 2.5 Таблиця: inventory_adjustments

**Призначення:** Коригування залишків після інвентаризації

```sql
id                      INT PRIMARY KEY IDENTITY
session_id              INT NOT NULL → inventory_sessions(id)
inventory_item_id       INT NOT NULL → inventory_items(id)
nomenclature_id         INT NOT NULL → nomenclature(id)
old_quantity            DECIMAL(18,6) NOT NULL            -- Системна кількість
new_quantity            DECIMAL(18,6) NOT NULL            -- Нова кількість (фактична)
adjustment_quantity     DECIMAL(18,6) NOT NULL            -- Різниця (new - old)
movement_id             INT NULL → stock_movements(id)    -- Посилання на проводку
reason                  NVARCHAR(MAX) NULL                -- Причина відхилення
created_at              DATETIME2 DEFAULT GETUTCDATE()

INDEX IX_inventory_adjustments_session (session_id)
```

**Бізнес-правила:**
- Створюється тільки для позицій з відхиленнями (difference ≠ 0)
- При завершенні інвентаризації створюються stock_movements

### 2.6 Таблиця: inventory_approvals

**Призначення:** Затвердження інвентаризації керівництвом

```sql
id                      INT PRIMARY KEY IDENTITY
session_id              INT NOT NULL → inventory_sessions(id)
approval_status         NVARCHAR(50) NOT NULL             -- "pending", "approved", "rejected"
requested_at            DATETIME2 NOT NULL DEFAULT GETUTCDATE()
requested_by_user       NVARCHAR(255) NOT NULL
approved_at             DATETIME2 NULL
approved_by_user        NVARCHAR(255) NULL
rejection_reason        NVARCHAR(MAX) NULL
notes                   NVARCHAR(MAX) NULL
created_at              DATETIME2 DEFAULT GETUTCDATE()

INDEX IX_inventory_approvals_session (session_id)
```

**Використання:**
- Якщо є значні відхилення (>20%) або загальна сума відхилень велика
- Керівник переглядає та затверджує/відхиляє

---

## 3. API Endpoints

### 3.1 POST /api/inventory/sessions

**Призначення:** Почати нову інвентаризацію

**Request:**
```json
{
  "session_type": "full",
  "started_by_user": "Петро Іванович",
  "categories": ["сировина", "готова продукція вагова"],
  "approval_required": true,
  "notes": "Планова інвентаризація за грудень 2025",
  "idempotency_key": "inv-uuid-12345"
}
```

**Response:**
```json
{
  "session_id": 42,
  "session_number": "INV-20251218-001",
  "session_type": "full",
  "status": "in_progress",
  "started_at": "2025-12-18T09:00:00",
  "started_by_user": "Петро Іванович",
  "snapshot_summary": {
    "total_items": 182,
    "categories": {
      "сировина": 13,
      "готова продукція вагова": 10,
      "полуфабрикати": 14,
      "специи": 29,
      "материалы": 29,
      "упаковка": 17,
      "SKU": 70
    }
  },
  "items_to_count": 182
}
```

**Бізнес-логіка:**
1. Перевірити права користувача (тільки менеджери можуть почати)
2. Створити сесію зі статусом "in_progress"
3. Зробити знімок ВСІХ поточних залишків у inventory_snapshot
4. Створити записи в inventory_items для кожної позиції зі статусом "pending"
5. Якщо partial - врахувати тільки вибрані категорії
6. Повернути підсумок

### 3.2 GET /api/inventory/sessions/{session_id}

**Призначення:** Отримати деталі сесії інвентаризації

**Response:**
```json
{
  "id": 42,
  "session_number": "INV-20251218-001",
  "session_type": "full",
  "status": "in_progress",
  "started_at": "2025-12-18T09:00:00",
  "started_by_user": "Петро Іванович",
  "approval_required": true,
  "progress": {
    "total_items": 182,
    "counted": 95,
    "pending": 87,
    "verified": 5,
    "with_discrepancy": 8,
    "progress_percent": 52.2
  },
  "summary": {
    "items_with_difference": 12,
    "total_surplus": 5.8,
    "total_shortage": 3.2,
    "net_difference": 2.6,
    "significant_discrepancies": 3
  },
  "categories_included": ["сировина", "готова продукція вагова", "..."]
}
```

### 3.3 GET /api/inventory/sessions/{session_id}/items

**Призначення:** Отримати список позицій для підрахунку

**Query параметри:**
- `status` (string, optional) - фільтр по статусу
- `category` (string, optional) - фільтр по категорії
- `has_discrepancy` (bool, optional) - тільки з відхиленнями
- `limit`, `offset` (int)

**Response:**
```json
{
  "items": [
    {
      "id": 1001,
      "nomenclature_id": 1,
      "nomenclature_name": "Яловичина вищого сорту",
      "category": "сировина",
      "unit": "кг",
      "system_quantity": 125.5,
      "actual_quantity": 123.2,
      "difference": -2.3,
      "difference_percent": -1.83,
      "status": "counted",
      "counted_by_user": "Олексій",
      "counted_at": "2025-12-18T10:15:00",
      "notes": "Одна упаковка пошкоджена"
    },
    {
      "id": 1002,
      "nomenclature_id": 19,
      "nomenclature_name": "Пажитник",
      "category": "специи",
      "unit": "кг",
      "system_quantity": 10.0,
      "actual_quantity": null,
      "difference": null,
      "status": "pending",
      "counted_by_user": null
    }
  ],
  "total": 182,
  "limit": 50,
  "offset": 0
}
```

### 3.4 POST /api/inventory/sessions/{session_id}/items/{item_id}/count

**Призначення:** Записати фактичну кількість для позиції

**Request:**
```json
{
  "actual_quantity": 123.2,
  "counted_by_user": "Олексій",
  "notes": "Одна упаковка пошкоджена",
  "photo_urls": ["https://storage/inv/photo1.jpg"],
  "idempotency_key": "count-uuid-12345"
}
```

**Response:**
```json
{
  "item_id": 1001,
  "nomenclature_id": 1,
  "nomenclature_name": "Яловичина вищого сорту",
  "system_quantity": 125.5,
  "actual_quantity": 123.2,
  "difference": -2.3,
  "difference_percent": -1.83,
  "status": "counted",
  "requires_verification": false,
  "counted_at": "2025-12-18T10:15:00"
}
```

**Бізнес-логіка:**
1. Перевірити що сесія в статусі "in_progress"
2. Розрахувати difference = actual - system
3. Розрахувати difference_percent = (difference / system) × 100
4. Якщо |difference_percent| > 10% → status = "discrepancy", requires_verification = true
5. Інакше → status = "counted"
6. Зберегти counted_by_user та counted_at

### 3.5 POST /api/inventory/sessions/{session_id}/items/{item_id}/verify

**Призначення:** Перевірити позицію з великим відхиленням

**Request:**
```json
{
  "verified_quantity": 123.2,
  "verified_by_user": "Менеджер Іван",
  "verification_notes": "Підтверджую, одна упаковка дійсно пошкоджена",
  "idempotency_key": "verify-uuid-12345"
}
```

**Response:**
```json
{
  "item_id": 1001,
  "status": "verified",
  "verified_at": "2025-12-18T11:00:00",
  "final_quantity": 123.2
}
```

### 3.6 POST /api/inventory/sessions/{session_id}/request-approval

**Призначення:** Запросити затвердження у керівництва

**Request:**
```json
{
  "requested_by_user": "Менеджер Петро",
  "notes": "Всі позиції підраховані, є 8 відхилень",
  "idempotency_key": "approval-req-uuid-12345"
}
```

**Response:**
```json
{
  "session_id": 42,
  "approval_id": 101,
  "approval_status": "pending",
  "requested_at": "2025-12-18T16:00:00",
  "summary": {
    "total_items_counted": 182,
    "items_with_discrepancy": 8,
    "significant_discrepancies": 3,
    "total_shortage_value": 1250.50,
    "total_surplus_value": 890.20,
    "net_difference_value": -360.30
  },
  "discrepancies": [
    {
      "nomenclature_name": "Яловичина вищого сорту",
      "system_quantity": 125.5,
      "actual_quantity": 123.2,
      "difference": -2.3,
      "difference_percent": -1.83,
      "reason": "Одна упаковка пошкоджена"
    }
  ]
}
```

**Бізнес-логіка:**
1. Перевірити що всі позиції підраховані
2. Створити запис в inventory_approvals
3. Змінити статус сесії на "pending_approval"
4. Відправити нотифікацію керівництву (опціонально)

### 3.7 POST /api/inventory/sessions/{session_id}/approve

**Призначення:** Затвердити інвентаризацію (керівництво)

**Request:**
```json
{
  "approved_by_user": "Директор Василь",
  "notes": "Затверджено",
  "idempotency_key": "approve-uuid-12345"
}
```

**Response:**
```json
{
  "session_id": 42,
  "approval_status": "approved",
  "approved_at": "2025-12-18T17:00:00",
  "next_action": "complete"
}
```

### 3.8 POST /api/inventory/sessions/{session_id}/complete

**Призначення:** Завершити інвентаризацію та оновити залишки

**Request:**
```json
{
  "completed_by_user": "Менеджер Петро",
  "final_notes": "Інвентаризація завершена успішно",
  "idempotency_key": "complete-uuid-12345"
}
```

**Response:**
```json
{
  "session_id": 42,
  "session_number": "INV-20251218-001",
  "status": "completed",
  "completed_at": "2025-12-18T17:30:00",
  "adjustments_summary": {
    "total_adjustments": 12,
    "positive_adjustments": 5,
    "negative_adjustments": 7,
    "items_increased": 5,
    "items_decreased": 7
  },
  "stock_movements": [
    {
      "id": 5001,
      "nomenclature_id": 1,
      "nomenclature_name": "Яловичина вищого сорту",
      "quantity": -2.3,
      "operation_type": "inventory_adjustment",
      "balance_before": 125.5,
      "balance_after": 123.2
    }
  ],
  "report_url": "/api/inventory/sessions/42/report.pdf"
}
```

**Бізнес-логіка:**
1. Перевірити що сесія в статусі "in_progress" або "pending_approval"
2. Якщо approval_required = true → перевірити що є затвердження
3. Для кожної позиції з відхиленням:
   - Створити inventory_adjustment
   - Створити stock_movement з operation_type = "inventory_adjustment"
   - Оновити stock_balances.quantity = actual_quantity
4. Змінити статус сесії на "completed"
5. Згенерувати PDF звіт
6. Повернути підсумок

### 3.9 GET /api/inventory/sessions/{session_id}/report

**Призначення:** Отримати PDF звіт по інвентаризації

**Query параметри:**
- `format` (string) - "pdf" або "excel"

**Response:**
- Content-Type: application/pdf або application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
- Файл для завантаження

**Структура звіту:**

```
═══════════════════════════════════════════════════════════
              АКТ ІНВЕНТАРИЗАЦІЇ №INV-20251218-001
═══════════════════════════════════════════════════════════

Тип інвентаризації: Повна
Дата початку: 18.12.2025 09:00
Дата завершення: 18.12.2025 17:30
Відповідальна особа: Менеджер Петро Іванович
Затверджено: Директор Василь Петрович (18.12.2025 17:00)

───────────────────────────────────────────────────────────
ПІДСУМОК
───────────────────────────────────────────────────────────
Всього позицій:              182
Позицій з відхиленнями:      12
Надлишок (позицій):          5
Нестача (позицій):           7

Загальна сума надлишку:      890.20 грн
Загальна сума нестачі:       1,250.50 грн
Чистий результат:            -360.30 грн (нестача)

───────────────────────────────────────────────────────────
СПИСОК ВІДХИЛЕНЬ
───────────────────────────────────────────────────────────

1. Яловичина вищого сорту (кг)
   Системна кількість:       125.50 кг
   Фактична кількість:       123.20 кг
   Відхилення:               -2.30 кг (-1.83%)
   Причина: Одна упаковка пошкоджена
   Підраховано: Олексій (18.12.2025 10:15)
   Перевірено: Менеджер Іван (18.12.2025 11:00)

2. Пажитник (кг)
   Системна кількість:       10.00 кг
   Фактична кількість:       11.50 кг
   Відхилення:               +1.50 кг (+15.00%)
   Причина: Знайдено додаткову упаковку на іншому стелажі
   Підраховано: Марія (18.12.2025 11:30)
   Перевірено: Менеджер Іван (18.12.2025 12:00)

[... інші відхилення ...]

───────────────────────────────────────────────────────────
ПОЗИЦІЇ БЕЗ ВІДХИЛЕНЬ
───────────────────────────────────────────────────────────
[Список позицій де факт = система, коротко]

───────────────────────────────────────────────────────────
ПІДПИСИ
───────────────────────────────────────────────────────────

Інвентаризацію провели:
___________________ (Менеджер Петро Іванович)
___________________ (Олексій)
___________________ (Марія)

Затверджую:
___________________ (Директор Василь Петрович)

Дата: 18.12.2025
```

### 3.10 GET /api/inventory/sessions

**Призначення:** Отримати список інвентаризацій

**Query параметри:**
- `status` (string, optional)
- `date_from`, `date_to` (datetime, optional)
- `limit`, `offset` (int)

**Response:**
```json
{
  "sessions": [
    {
      "id": 42,
      "session_number": "INV-20251218-001",
      "session_type": "full",
      "status": "completed",
      "started_at": "2025-12-18T09:00:00",
      "completed_at": "2025-12-18T17:30:00",
      "started_by_user": "Петро Іванович",
      "total_items": 182,
      "items_with_discrepancy": 12
    }
  ],
  "total": 15,
  "limit": 50,
  "offset": 0
}
```

---

## 4. Frontend структура

### 4.1 Екрани (в app/inventory/)

**1. index.tsx (головний екран)**
- Поточні залишки (read-only)
- Фільтри по категоріях
- Пошук по назві
- Кнопка "Почати інвентаризацію" (тільки для менеджерів)
- Список попередніх інвентаризацій (внизу)

**2. new-session.tsx**
- Вибір типу інвентаризації (повна/часткова)
- Якщо часткова → вибір категорій (checkboxes)
- Чи потрібне затвердження (checkbox)
- Примітки
- Попередження: "Буде створено знімок поточних залишків"
- Кнопка "Почати інвентаризацію"

**3. [id].tsx (сесія інвентаризації)**

**Верхня частина:**
- Номер сесії
- Тип
- Статус (бейдж)
- Прогрес (% підрахованих позицій)
- Підсумок відхилень

**Tabs:**

**Tab 1: "Підрахунок"**
- Список позицій для підрахунку
- Фільтри: всі / очікують / підраховані / з відхиленнями
- Для кожної позиції:
  - Назва
  - Категорія
  - Системна кількість
  - Поле для введення фактичної
  - Статус (іконка)
  - Кнопка "Зберегти"

**Tab 2: "Відхилення"**
- Список позицій з відхиленнями
- Для кожної:
  - Назва
  - Система / Факт / Різниця / %
  - Статус (підраховано/перевірено)
  - Причина (якщо вказана)
  - Кнопка "Перевірити" (для >10%)

**Tab 3: "Підсумок"**
- Загальна статистика
- Надлишок / Нестача
- Кнопка "Запросити затвердження" (якщо approval_required)
- Кнопка "Завершити інвентаризацію"

**4. count-modal.tsx**
- Modal для швидкого підрахунку позиції
- Назва позиції
- Системна кількість (read-only, велика цифра)
- Поле для введення фактичної (велика цифра)
- Кнопки +/- для коригування
- Поле для приміток
- Кнопка камери (опціонально - зробити фото)
- Розрахунок відхилення (автоматично)
- Кнопка "Зберегти"

**5. verify-modal.tsx**
- Для позицій з великим відхиленням
- Показує системну та фактичну кількість
- Відхилення (підсвічене червоним якщо >10%)
- Поле для підтвердження кількості
- Поле для пояснення причини
- Кнопка "Повторити підрахунок"
- Кнопка "Підтвердити"

**6. approval-screen.tsx**
- Перегляд для керівництва
- Список всіх відхилень
- Підсумок по категоріях
- Вартісна оцінка (якщо є ціни)
- Кнопка "Затвердити"
- Кнопка "Відхилити" (з причиною)

**7. report-screen.tsx**
- Перегляд завершеної інвентаризації
- Підсумок
- Список відхилень
- Кнопка "Завантажити PDF"
- Кнопка "Завантажити Excel"

### 4.2 Компоненти

**InventorySessionCard.tsx**
```tsx
interface InventorySessionCardProps {
  session: {
    id: number;
    session_number: string;
    session_type: string;
    status: string;
    started_at: string;
    items_with_discrepancy: number;
  };
  onPress: () => void;
}
```

**InventoryItemRow.tsx**
```tsx
interface InventoryItemRowProps {
  item: {
    nomenclature_name: string;
    category: string;
    unit: string;
    system_quantity: number;
    actual_quantity: number | null;
    difference: number | null;
    status: string;
  };
  editable: boolean;
  onCount?: (actual: number) => void;
}
```

**InventoryProgressBar.tsx**
```tsx
interface InventoryProgressBarProps {
  total: number;
  counted: number;
  verified: number;
  withDiscrepancy: number;
}
```

**DiscrepancyCard.tsx**
```tsx
interface DiscrepancyCardProps {
  item: {
    nomenclature_name: string;
    system_quantity: number;
    actual_quantity: number;
    difference: number;
    difference_percent: number;
    requires_verification: boolean;
  };
  onVerify?: () => void;
}
```

---

## 5. Бізнес-правила

### 5.1 Права доступу

**Почати інвентаризацію:**
- Тільки менеджери та вище

**Проводити підрахунок:**
- Всі співробітники

**Затверджувати:**
- Тільки керівництво (директор, заступник)

### 5.2 Автоматичні перевірки

**При підрахунку:**
```javascript
const difference_percent = ((actual - system) / system) * 100;

if (Math.abs(difference_percent) > 10) {
  status = "discrepancy";
  requires_verification = true;
}

if (Math.abs(difference_percent) > 20) {
  approval_required = true; // Вимагає затвердження керівництва
}
```

**При завершенні:**
```javascript
const all_counted = items.every(item => item.status !== "pending");

if (!all_counted) {
  throw new Error("Не всі позиції підраховані");
}

if (approval_required && !approved) {
  throw new Error("Потрібне затвердження керівництва");
}
```

### 5.3 Нумерація

Формат: `INV-YYYYMMDD-NNN`

Приклад: `INV-20251218-001`

### 5.4 Коригування залишків

При завершенні інвентаризації:

```python
for item in inventory_items:
    if item.difference != 0:
        # Створити adjustment
        adjustment = {
            "nomenclature_id": item.nomenclature_id,
            "old_quantity": item.system_quantity,
            "new_quantity": item.actual_quantity,
            "adjustment_quantity": item.difference
        }

        # Створити stock_movement
        movement = {
            "nomenclature_id": item.nomenclature_id,
            "quantity": item.difference,  # + або -
            "operation_type": "inventory_adjustment",
            "source_operation_id": session_id,
            "notes": f"Інвентаризація {session_number}: {item.notes}"
        }

        # Оновити баланс
        UPDATE stock_balances
        SET quantity = item.actual_quantity
        WHERE nomenclature_id = item.nomenclature_id
```

---

## 6. Офлайн-режим

### 6.1 Особливості

**Складність:** Інвентаризація може тривати весь день

**Підхід:**
1. Зберігати всю сесію локально
2. Синхронізувати поетапно:
   - Створення сесії (одразу при онлайн)
   - Кожен підрахунок позиції (в черзі)
   - Завершення (тільки коли всі підрахунки синхронізовані)

### 6.2 Локальне зберігання

Ключі MMKV:
```
inventory_active_session    - поточна активна сесія
inventory_offline_counts    - черга підрахунків
inventory_cache             - кеш позицій для швидкого пошуку
```

---

## 7. Звітність

### 7.1 PDF звіт

**Генерація:**
- Server-side (Python + ReportLab або WeasyPrint)
- Шаблон з логотипом компанії
- Підписи відповідальних осіб

**Розділи:**
1. Шапка (номер, дата, відповідальні)
2. Підсумок (загальна статистика)
3. Детальний список відхилень
4. Позиції без відхилень (коротко)
5. Підписи

### 7.2 Excel звіт

**Структура:**

**Аркуш 1: "Підсумок"**
- Загальна інформація
- Підсумкові цифри
- Графіки (якщо є бібліотека)

**Аркуш 2: "Відхилення"**
- Таблиця всіх позицій з відхиленнями
- Колонки: Назва, Категорія, Система, Факт, Різниця, %, Причина

**Аркуш 3: "Всі позиції"**
- Повний список
- Колонки: Назва, Категорія, Одиниця, Система, Факт, Різниця, Статус

---

## 8. Тестування

### 8.1 Тест кейси

1. **Створення інвентаризації**
   - Перевірити створення знімку (snapshot)
   - Перевірити що всі позиції створені в inventory_items

2. **Підрахунок без відхилення**
   - actual = system → status = "counted", no verification needed

3. **Підрахунок з малим відхиленням (<10%)**
   - status = "counted", no verification needed

4. **Підрахунок з великим відхиленням (>10%)**
   - status = "discrepancy", requires_verification = true

5. **Підрахунок з дуже великим відхиленням (>20%)**
   - approval_required = true

6. **Завершення без затвердження (коли approval_required = true)**
   - Повинна бути помилка

7. **Завершення з оновленням залишків**
   - Перевірити створення stock_movements
   - Перевірити оновлення stock_balances

8. **Генерація звіту**
   - Перевірити PDF генерацію
   - Перевірити Excel генерацію

---

## 9. Приклади використання

### 9.1 Планова місячна інвентаризація

```
ДЕНЬ 1 (09:00): Початок
- Менеджер Петро починає повну інвентаризацію
- Система створює знімок 182 позицій
- Статус: in_progress

ДЕНЬ 1 (09:30 - 16:00): Підрахунок
- Олексій рахує сировину (13 позицій)
  * Яловичина вищого сорту: 125.5 кг (система) → 123.2 кг (факт)
  * Різниця: -2.3 кг (-1.83%) → статус: counted

- Марія рахує специї (29 позицій)
  * Пажитник: 10.0 кг (система) → 11.5 кг (факт)
  * Різниця: +1.5 кг (+15%) → статус: discrepancy ⚠️

- Іван рахує готову продукцію (10 позицій)
  * Бастурма вагова: 50.0 кг (система) → 48.5 кг (факт)
  * Різниця: -1.5 кг (-3%) → статус: counted

ДЕНЬ 1 (16:30): Перевірка відхилень
- Менеджер Іван перевіряє пажитник
  * Підтверджує 11.5 кг
  * Причина: "Знайдено додаткову упаковку на іншому стелажі"
  * Статус: verified ✓

ДЕНЬ 1 (17:00): Запит на затвердження
- Менеджер Петро запитує затвердження
- Надсилається на email директору
- Статус сесії: pending_approval

ДЕНЬ 1 (17:15): Затвердження
- Директор Василь переглядає звіт
- Бачить 8 відхилень, найбільше +15% (пажитник)
- Затверджує
- Статус затвердження: approved

ДЕНЬ 1 (17:30): Завершення
- Менеджер Петро завершує інвентаризацію
- Система:
  * Створює 12 коригувальних проводок
  * Оновлює stock_balances для 12 позицій
  * Генерує PDF звіт
  * Статус: completed

РЕЗУЛЬТАТ:
- Виявлено відхилення на -360.30 грн (нестача)
- Оновлено залишки по 12 позиціях
- Згенеровано звіт для бухгалтерії
```

---

## 10. Майбутні покращення

- [ ] Мобільний додаток зі сканером штрих-кодів
- [ ] Інтеграція з вагами (автоматичне зчитування)
- [ ] AI розпізнавання фото (підрахунок по фото)
- [ ] Планування інвентаризацій (розклад)
- [ ] ABC-аналіз (пріоритетність перевірки)
- [ ] Циклічна інвентаризація (різні категорії в різні дні)
- [ ] Push-нотифікації для керівництва
- [ ] Dashboard з аналітикою відхилень
- [ ] Порівняння з попередніми інвентаризаціями
- [ ] Експорт в 1С / SAP

---

## 11. Інтеграція з іншими модулями

### 11.1 Зв'язок з операціями

- Під час інвентаризації операції НЕ блокуються
- Але рекомендується проводити в неробочий час
- Після завершення - нові операції йдуть від оновлених залишків

### 11.2 Зв'язок з виробництвом

- Активні партії (in_progress) враховуються в знімку
- Матеріали в виробництві = списані зі складу
- Готова продукція = ще не оприходована

### 11.3 Зв'язок з фасуванням

- Активні сесії фасування враховуються
- Вагова продукція в сесії = списана
- SKU ще не оприходовані

---

## 12. Безпека та аудит

### 12.1 Права доступу

- Створити інвентаризацію: `ROLE_MANAGER`
- Підраховувати: `ROLE_WORKER`
- Затверджувати: `ROLE_DIRECTOR`
- Переглядати звіти: `ROLE_MANAGER`, `ROLE_DIRECTOR`, `ROLE_ACCOUNTANT`

### 12.2 Аудит змін

Всі дії логуються:
```json
{
  "action": "inventory_item_counted",
  "session_id": 42,
  "item_id": 1001,
  "nomenclature_id": 1,
  "user": "Олексій",
  "old_value": null,
  "new_value": 123.2,
  "timestamp": "2025-12-18T10:15:00"
}
```

### 12.3 Immutable snapshot

- Знімок (inventory_snapshot) НІКОЛИ не змінюється
- Використовується для розрахунку відхилень
- Навіть якщо під час інвентаризації відбулися операції

---

**Версія ТЗ:** 1.0
**Дата:** 18 грудня 2025
**Автор:** Claude Sonnet 4.5
**Статус:** Готово до розробки
