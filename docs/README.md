# Документація проекту SLAZAR

**Система управління м'ясним виробництвом**

---

## 📚 Загальна документація

### [database-schema.md](database-schema.md) (50 KB)
Повна схема бази даних MS SQL Server з описом всіх 27 таблиць, індексів, зв'язків та бізнес-правил.

**Що містить:**
- 7 модулів системи
- Детальний опис кожної таблиці
- Індекси та оптимізації
- Приклади даних
- Діаграми зв'язків

### [project-audit.md](project-audit.md) (45 KB)
Аудит проекту з аналізом архітектури, коду, бази даних та виявленими проблемами.

**Що містить:**
- Аналіз структури проекту
- Огляд бази даних
- Виявлені проблеми та рішення
- Рекомендації по покращенню

---

## 🎯 Технічні завдання модулів

### [BUTCHERY_SPECIFICATION.md](BUTCHERY_SPECIFICATION.md) (24 KB)

**Модуль розділки м'яса**

Повне технічне завдання для модуля розділки туш на полуфабрикати.

**Що містить:**
- **Бізнес-процес:** від вибору туші до оприходування полуфабрикатів
- **Структура даних:** 4 таблиці (recipes, outputs, operations, operation_outputs)
- **API:** 5 endpoints з детальними прикладами request/response
- **Frontend:** 6 екранів (select-meat-type, select-grade, select-recipe, input-weight, complete-form, [id])
- **Бізнес-правила:** розрахунок виходу, валідація, відходи
- **Приклади:** розділка яловичини 120 кг
- **Тестування:** unit та E2E тести

**Ключові особливості:**
- Відходи НЕ оприходуються на склад
- Автоматичний розрахунок виходу полуфабрикатів за відсотками
- Порівняння фактичного та очікуваного виходу

---

### [PRODUCTION_SPECIFICATION.md](PRODUCTION_SPECIFICATION.md) (31 KB)

**Модуль виробництва готової продукції**

Повне технічне завдання для багатоетапного виробництва (бастурма, суджук, махан та ін.).

**Що містить:**
- **Бізнес-процес:** 5 етапів (created → salt → mix → stuff → dry → completed)
- **Структура даних:** 8 таблиць (batches, operations, materials, mix_production...)
- **API:** 9 endpoints для кожного етапу
- **Frontend:** 8 екранів (new-batch, salt-form, mix-form, stuff-form, dry-form, complete-form...)
- **Бізнес-правила:** розрахунок матеріалів, коефіцієнт пажитнику 1:4, вихід продукції
- **Приклади:** повний цикл виробництва бастурми (21 день)
- **Тестування:** кейси для кожного етапу

**Ключові особливості:**
- **Пажитник:** на 1 кг пажитнику додається 4 л води
- **Суміш специй:** виробляється на етапі mix, залишок оприходується на склад
- **Обрізки:** можна повернути на склад або списати
- **Контроль виходу:** перевірка в межах очікуваного діапазону (65-75%)

---

### [PACKAGING_SPECIFICATION.md](PACKAGING_SPECIFICATION.md) (28 KB)

**Модуль фасування продукції**

Повне технічне завдання для фасування вагової продукції в SKU.

**Що містить:**
- **Бізнес-процес:** створення сесії → фасування в SKU → залишки → завершення
- **Структура даних:** 6 таблиць (sessions, outputs, remainders, waste, recipes...)
- **API:** 8 endpoints для роботи з сесіями
- **Frontend:** 6 екранів (new-session, [id], add-output-modal, add-remainder-modal...)
- **Бізнес-правила:** автоматичний розрахунок матеріалів, баланс сесії, облік браку
- **Приклади:** фасування 50 кг бастурми в різні SKU
- **Тестування:** тести балансу, браку, залишків

**Ключові особливості:**
- **Автоматичний розрахунок матеріалів:** пакети, етикетки, лотки, плівка
- **Облік браку:** окремо по кожному матеріалу (defect_quantity)
- **Баланс сесії:** взято = використано + залишки + брак (±0.1 кг допуск)
- **Залишки:** осипана специя, обрізки → повертаються на склад
- **Підтвердження матеріалів:** можливість коригувати автоматичний розрахунок

---

## 📖 Структура документації по папках

```
docs/
├── README.md                          # Цей файл (індекс документації)
├── database-schema.md                 # Схема БД (50 KB)
├── project-audit.md                   # Аудит проекту (45 KB)
├── BUTCHERY_SPECIFICATION.md          # ТЗ розділки (24 KB)
├── PRODUCTION_SPECIFICATION.md        # ТЗ виробництва (31 KB)
└── PACKAGING_SPECIFICATION.md         # ТЗ фасування (28 KB)
```

---

## 🔗 Додаткова документація

### Корінь проекту

- **[claude.md](../claude.md)** (23 KB) - Головна технічна специфікація, інструкції для Claude
- **[README.md](../README.md)** - Загальний опис проекту
- **[START_HERE.md](../START_HERE.md)** - Швидкий старт
- **[DOCS_INDEX.md](../DOCS_INDEX.md)** - Індекс всієї документації

### Backend

- **[backend/BACKEND_STRUCTURE.md](../backend/BACKEND_STRUCTURE.md)** - Структура backend API
  - Опис всіх API endpoints
  - Моделі Pydantic
  - Бізнес-логіка

### Frontend

- **[frontend/FRONTEND_STRUCTURE.md](../frontend/FRONTEND_STRUCTURE.md)** - Структура frontend
  - Структура app/ (Expo Router)
  - Компоненти
  - Services та stores
- **[frontend/README.md](../frontend/README.md)** - Інструкції по запуску

### Deployment

- **[DEPLOY_TO_SERVER.md](../DEPLOY_TO_SERVER.md)** - Деплой на сервер
- **[CLONE_ON_SERVER.md](../CLONE_ON_SERVER.md)** - Клонування на віртуальній машині
- **[TESTING_SETUP.md](../TESTING_SETUP.md)** - Налаштування тестів

---

## 📊 Статистика документації

| Документ | Розмір | Таблиць | Endpoints | Екранів | Опис |
|----------|--------|---------|-----------|---------|------|
| database-schema.md | 50 KB | 27 | - | - | Повна схема БД |
| project-audit.md | 45 KB | - | - | - | Аудит проекту |
| BUTCHERY_SPECIFICATION.md | 24 KB | 4 | 5 | 6 | ТЗ розділки |
| PRODUCTION_SPECIFICATION.md | 31 KB | 8 | 9 | 8 | ТЗ виробництва |
| PACKAGING_SPECIFICATION.md | 28 KB | 6 | 8 | 6 | ТЗ фасування |
| **Всього** | **178 KB** | **45** | **22** | **20** | |

---

## 🎓 Як користуватися документацією

### Для нових розробників

1. Почніть з [claude.md](../claude.md) - загальний огляд системи
2. Прочитайте [database-schema.md](database-schema.md) - зрозумійте структуру даних
3. Виберіть модуль який вас цікавить:
   - Розділка → [BUTCHERY_SPECIFICATION.md](BUTCHERY_SPECIFICATION.md)
   - Виробництво → [PRODUCTION_SPECIFICATION.md](PRODUCTION_SPECIFICATION.md)
   - Фасування → [PACKAGING_SPECIFICATION.md](PACKAGING_SPECIFICATION.md)
4. Дивіться детальну документацію:
   - Backend → [backend/BACKEND_STRUCTURE.md](../backend/BACKEND_STRUCTURE.md)
   - Frontend → [frontend/FRONTEND_STRUCTURE.md](../frontend/FRONTEND_STRUCTURE.md)

### Для тестувальників

1. [TESTING_SETUP.md](../TESTING_SETUP.md) - налаштування тестового середовища
2. Тестові сценарії в кожному ТЗ:
   - BUTCHERY_SPECIFICATION.md (розділ 8)
   - PRODUCTION_SPECIFICATION.md (розділ 7)
   - PACKAGING_SPECIFICATION.md (розділ 8)

### Для DevOps

1. [DEPLOY_TO_SERVER.md](../DEPLOY_TO_SERVER.md) - інструкції по деплою
2. [CLONE_ON_SERVER.md](../CLONE_ON_SERVER.md) - налаштування на сервері
3. [database-schema.md](database-schema.md) - для налаштування БД

### Для Product Owner / Бізнес-аналітиків

1. Бізнес-процеси в кожному ТЗ (розділ 1)
2. Приклади використання (розділ 8-9 в кожному ТЗ)
3. [project-audit.md](project-audit.md) - поточний стан проекту

---

## 🔄 Оновлення документації

**Остання версія:** 18 грудня 2025

**Changelog:**
- 18.12.2025 - Додано три детальних ТЗ (BUTCHERY, PRODUCTION, PACKAGING)
- 16.12.2025 - Створено database-schema.md та project-audit.md
- 15.12.2025 - Початкова документація

**Політика оновлення:**
- При додаванні нових API endpoints → оновити відповідне ТЗ
- При зміні структури БД → оновити database-schema.md
- При додаванні екранів → оновити відповідне ТЗ та FRONTEND_STRUCTURE.md
- Завжди вказувати дату оновлення

---

## 📞 Контакти

- **GitHub:** https://github.com/eio1990/slazar
- **Документація:** /docs/
- **Issues:** https://github.com/eio1990/slazar/issues

---

**Версія документації:** 1.0
**Дата:** 18 грудня 2025
**Статус проекту:** Production Ready
