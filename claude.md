# Система управління м'ясним виробництвом (SLAZAR)

## Краткое описание
Полнофункциональная мобильная и веб-система для управления полным циклом мясного производства: от приёма сырья через разделку и производство до фасовки в SKU с поддержкой офлайн-режима и автоматической синхронизацией.

## Технологический стек

### Backend
- Язык: Python 3.11
- Фреймворк: FastAPI 0.110.1
- База данных: MS SQL Server 2022
- ORM/Driver: pyodbc 5.3.0 (ODBC Driver 18)
- Валидация: Pydantic 2.12.4
- Сервер: uvicorn 0.25.0
- Подключение БД: 85.238.112.232:14330 → SLAZAR_DB

### Frontend
- Язык: TypeScript 5.9.2
- Фреймворк: React Native 0.81.5
- Платформа: Expo SDK 54.0.25
- Роутинг: Expo Router 6.0.14 (file-based routing)
- Состояние: Zustand 5.0.8 (client state) + TanStack Query 5.90.7 (server state)
- HTTP: Axios 1.13.2
- Хранилище: React Native MMKV 4.0.0
- Навигация: React Navigation 7.1.6
- Минимальная версия: iOS 13+, Android 5.0+

## Структура проекта

```
slazar/
├── backend/                          # FastAPI Python backend
│   ├── server.py                     # Главный FastAPI app (entry point)
│   ├── database.py                   # Подключение к MS SQL Server
│   ├── models.py                     # Pydantic модели
│   ├── production_api.py             # API производства (78 KB)
│   ├── packaging_api.py              # API фасовки (33 KB)
│   ├── butchery_api.py               # API разделки (23 KB)
│   ├── stock_api.py                  # API склада
│   ├── batch_operations.py           # Вспомогательные операции
│   ├── requirements.txt              # Зависимости Python
│   └── [utility scripts]             # show_full_chain.py, analyze_current_db.py
│
├── frontend/                         # React Native Expo app
│   ├── app/                          # Expo Router (file-based routing)
│   │   ├── _layout.tsx               # Root layout с providers
│   │   ├── (tabs)/                   # Главные экраны (Tab Navigation)
│   │   │   ├── index.tsx             # Операции (приход/расход)
│   │   │   ├── butchery.tsx          # Разделка
│   │   │   ├── production.tsx        # Производство
│   │   │   ├── packaging.tsx         # Фасовка
│   │   │   ├── inventory.tsx         # Склад/остатки
│   │   │   └── history.tsx           # История операций
│   │   ├── batches/                  # Экраны производственных партий
│   │   │   ├── [id].tsx              # Детали партии
│   │   │   ├── salting-form.tsx      # Этап засолки
│   │   │   ├── mix-form.tsx          # Этап замешивания специй
│   │   │   ├── stuffing-form.tsx     # Этап набивки в оболочку
│   │   │   └── [другие этапы]
│   │   ├── butchery/                 # Workflow разделки
│   │   │   ├── select-meat-type.tsx
│   │   │   ├── select-grade.tsx
│   │   │   ├── select-recipe.tsx
│   │   │   ├── input-weight.tsx
│   │   │   └── complete-form.tsx
│   │   ├── packaging/                # Сессии фасовки
│   │   │   ├── new-session.tsx
│   │   │   └── [id].tsx
│   │   └── recipes/                  # Справочник рецептов
│   │       ├── index.tsx
│   │       └── [id].tsx
│   ├── services/
│   │   └── api.ts                    # Axios client, offline queue, idempotency
│   ├── stores/
│   │   └── useStore.ts               # Zustand store (nomenclature, balances, connectivity)
│   ├── components/
│   │   └── HamburgerMenu.tsx         # Навигационное меню
│   ├── package.json                  # Зависимости
│   ├── tsconfig.json                 # TypeScript config
│   └── app.json                      # Expo конфигурация
│
├── Documentation/                    # Документация проекта
│   ├── README.md                     # Главная документация
│   ├── BACKEND_STRUCTURE.md          # Структура backend API
│   └── FRONTEND_STRUCTURE.md         # Структура frontend
│
└── tests/                            # Тестовый suite (pytest)
    └── [test files]
```

## Схема базы данных (MS SQL Server)

### Основные таблицы:

#### nomenclature (182 позиции)
- id (INT PRIMARY KEY)
- name (NVARCHAR) - название позиции
- category (NVARCHAR) - категория (сырьё, полуфабрикат, готовая продукция, специи, материалы, упаковка)
- unit (NVARCHAR) - единица измерения (кг, шт, л, м)
- meat_type (NVARCHAR NULL) - тип мяса (говядина, конина, курица, индейка, свинина)
- is_active (BIT) - активна ли позиция

#### stock_balances
- nomenclature_id (INT FK → nomenclature.id)
- quantity (DECIMAL(10,3)) - текущий остаток
- last_updated (DATETIME2)

#### stock_movements (аудит всех операций)
- id (INT PRIMARY KEY IDENTITY)
- nomenclature_id (INT FK)
- quantity (DECIMAL(10,3)) - количество (+ приход, - расход)
- movement_type (NVARCHAR) - тип операции
- reference_id (INT NULL) - ссылка на партию/сессию
- timestamp (DATETIME2)
- notes (NVARCHAR NULL)
- idempotency_key (NVARCHAR UNIQUE) - защита от дублей

#### recipes (8 основных рецептов)
- id (INT PRIMARY KEY)
- name (NVARCHAR) - название рецепта
- output_nomenclature_id (INT FK) - что производим
- meat_type (NVARCHAR)
- category (NVARCHAR) - production/packaging/butchery

#### recipe_ingredients
- recipe_id (INT FK)
- nomenclature_id (INT FK)
- quantity_per_kg (DECIMAL) - расход на 1 кг
- stage (NVARCHAR NULL) - на каком этапе используется

#### batches (производственные партии)
- id (INT PRIMARY KEY IDENTITY)
- recipe_id (INT FK)
- status (NVARCHAR) - created/salt/mix/stuff/dry/completed
- initial_weight (DECIMAL)
- current_weight (DECIMAL)
- created_at (DATETIME2)
- completed_at (DATETIME2 NULL)
- operator_notes (NVARCHAR NULL)

#### batch_stages (этапы партий)
- id (INT PRIMARY KEY IDENTITY)
- batch_id (INT FK)
- stage_name (NVARCHAR) - salt/mix/stuff/dry
- weight_before (DECIMAL)
- weight_after (DECIMAL)
- timestamp (DATETIME2)
- notes (NVARCHAR NULL)

#### packaging_sessions (сессии фасовки)
- id (INT PRIMARY KEY IDENTITY)
- source_nomenclature_id (INT FK) - весовая продукция
- initial_weight (DECIMAL)
- status (NVARCHAR) - active/completed
- created_at (DATETIME2)
- completed_at (DATETIME2 NULL)

#### packaging_outputs (результаты фасовки)
- id (INT PRIMARY KEY IDENTITY)
- session_id (INT FK)
- target_nomenclature_id (INT FK) - SKU
- quantity (INT) - количество упаковок
- weight_per_unit (DECIMAL) - вес одной упаковки
- packaging_type (NVARCHAR) - vacuum/skin
- timestamp (DATETIME2)

#### butchery_operations (операции разделки)
- id (INT PRIMARY KEY IDENTITY)
- recipe_id (INT FK → butchery_recipes)
- input_weight (DECIMAL) - вес туши
- waste_weight (DECIMAL) - вес отходов
- created_at (DATETIME2)
- operator_notes (NVARCHAR NULL)

#### butchery_recipes
- id (INT PRIMARY KEY)
- name (NVARCHAR)
- input_nomenclature_id (INT FK) - сырьё
- meat_type (NVARCHAR)

#### butchery_outputs (выход полуфабрикатов)
- recipe_id (INT FK)
- output_nomenclature_id (INT FK)
- percentage (DECIMAL) - процент выхода от веса туши

## Ключевые функции

### 1. Операции (Receipt/Withdrawal)
- Приход сырья и материалов на склад
- Расход/списание материалов
- Фильтрация по категориям и типам мяса
- Поиск по номенклатуре

### 2. Разделка (Butchery)
- Выбор рецепта разделки (говядина/конина)
- Ввод веса туши
- Расчёт ожидаемого выхода полуфабрикатов
- Фиксация фактических весов
- Учёт отходов (НЕ попадают на склад)
- Автоматическое списание сырья и оприходование полуфабрикатов

### 3. Производство (Production)
- Создание производственной партии по рецепту
- Многоэтапный процесс:
  - **Step 0 (created)**: Списание сырья с склада
  - **Step 1 (salt)**: Добавление соли и воды
  - **Step 2 (mix)**: Замешивание специй (с коэффициентом 1:4 для пажитника)
  - **Step 3 (stuff)**: Набивка в оболочку
  - **Step 4 (dry)**: Указание срока сушки
  - **Step 5 (completed)**: Взвешивание готового продукта, расчёт выхода
- Автоматическое списание ингредиентов на каждом этапе
- Учёт оболочек и материалов
- Оприходование готовой весовой продукции

### 4. Фасовка (Packaging)
- Создание сессии фасовки из весовой продукции
- Упаковка в различные SKU (вакуум/скин, разные веса)
- Автоматический расчёт материалов (пакеты, этикетки, лотки)
- Учёт брака и потерь
- Учёт остатков (осыпавшаяся специя и т.д.)
- Списание весовой продукции и оприходование SKU

### 5. Склад (Inventory)
- Просмотр текущих остатков по всей номенклатуре
- Фильтры по категориям и типам мяса
- Поиск по наименованию
- Обновление в реальном времени

### 6. История (History)
- Журнал всех операций (stock_movements)
- Фильтрация по типу операции
- Фильтрация по периоду (сегодня/неделя/месяц/всё)
- Детальная информация о каждой операции

## Архитектурные паттерны

### Offline-First Architecture
- **React Native MMKV**: персистентное локальное хранилище
- **Offline Queue**: операции ставятся в очередь при отсутствии сети
- **NetInfo Integration**: мониторинг состояния сети в реальном времени
- **Idempotency Keys**: защита от дублирования операций при повторе
- **Optimistic UI**: немедленный отклик интерфейса при синхронизации

### Модульная архитектура (Modular Monolith)
- Чёткое разделение по доменам (operations, butchery, production, packaging, stock)
- Каждый модуль имеет свой API-роутер в backend
- Frontend организован по модулям через file-based routing

### Domain-Driven Design
- 6 бизнес-доменов с явными API границами
- Pydantic модели для строгой валидации
- Row-level locking в SQL для предотвращения race conditions

### Session-Based Processing
- Производственные партии (batches) - многоэтапные сессии
- Фасовочные сессии (packaging_sessions) - одна весовая партия → много SKU
- Все сессии имеют статусы и временные метки

## Стиль кода

### Backend (Python)
- Используем async/await где возможно (FastAPI)
- Type hints обязательны для всех функций
- Pydantic модели для всех request/response
- Комментарии на русском языке для бизнес-логики
- Максимальная длина строки: 100 символов
- Black форматирование, Flake8 линтинг
- Обработка ошибок через HTTPException с понятными сообщениями

### Frontend (TypeScript)
- Strict TypeScript mode
- Functional components с hooks
- Именование: camelCase для переменных, PascalCase для компонентов
- Интерфейсы для всех API responses
- Комментарии на русском для сложной логики
- ESLint правила строго соблюдаются
- Expo Router conventions для навигации

### SQL
- Используем параметризованные запросы (защита от SQL injection)
- Row-level locking (WITH UPDLOCK, ROWLOCK) для критичных операций
- Timestamps в локальном времени (UTC+2 для Украины)
- NVARCHAR для всех текстовых полей (поддержка Unicode)

## Бизнес-правила

### Номенклатура (182 позиции)
- **Сырьё (13)**: говядина/конина по сортам, куриное/индюшачье филе/бедро, свиная вырезка, конский жир
- **Полуфабрикаты (14)**: заготовки для бастурмы, суджука, пластин, махана
- **Готовая весовая (10)**: бастурма, суджук, махан, пластина (говядина/конина), конина, индейка, курица, курхан, банкетная
- **SKU (~27)**: вакуум/скин упаковки разных весов (40/50/60/80/100г) + весовая упаковка
- **Специи (29)**: соль, чеснок, пажитник, перец и др.
- **Материалы (29)**: оболочки, нитки, крючки
- **Упаковка (17)**: пакеты, лотки, плёнка, этикетки

### Рецепты производства (8 основных)
1. Бастурма классическая (говядина)
2. Бастурма конская
3. Суджук (колбаса)
4. Махан
5. Курица копченая
6. Индейка
7. Пластина
8. Банкетная свинина

### Учёт отходов
- **Разделка**: отходы фиксируются, но НЕ попадают на склад
- **Производство**: естественная усушка учитывается через weight_before/weight_after
- **Фасовка**: брак и потери (осыпавшаяся специя) фиксируются отдельно

### Расчёт материалов в фасовке
- Пакеты/лотки: по количеству упаковок (1:1)
- Этикетки: по количеству упаковок (1:1)
- Плёнка (для скин): по весу продукта (коэффициент из рецепта)

## Тестирование

### Backend (pytest)
- ✅ 23/23 теста пройдены
- Покрытие:
  - Nomenclature API: 8 тестов
  - Production API: 4 теста
  - Packaging API: 3 теста
  - Butchery API: 3 теста
  - Stock API: 5 тестов

### Frontend
- Требуется ручное тестирование на реальных устройствах
- Тестирование через Expo Go на iOS/Android

## Известные особенности

### Дубликаты в номенклатуре
- Сохранены некоторые дубликаты "вагова/ваговий" для совместимости с рецептами
- Спецпозиции ID 101, 106 оставлены для исторических данных

### Временная зона
- Все timestamps в локальном времени Украины (UTC+2/UTC+3)
- Backend использует DATEADD(HOUR, 2, GETDATE())

### Коэффициенты
- Пажитник в рецептах: 1:4 (на 1 кг пажитника добавляется 4 кг воды)
- Выход полуфабрикатов в разделке: процентные соотношения из butchery_outputs

## Текущие задачи
- [x] Все 6 модулей реализованы и протестированы
- [x] Офлайн-режим работает
- [x] Финальная миграция БД выполнена (22.11.2025)
- [ ] Production deployment (ожидает)
- [ ] User acceptance testing на реальных устройствах

## Правила для Claude

### При работе с кодом:
1. **Всегда читай файл перед изменением** - используй Read tool
2. **Используй Edit для изменений** - никогда не переписывай файлы целиком
3. **Комментарии на русском** для бизнес-логики
4. **Type hints обязательны** в Python
5. **TypeScript strict mode** в frontend
6. **Спрашивай перед крупными рефакторингами**

### При работе с БД:
1. **ВСЕГДА используй параметризованные запросы** (защита от SQL injection)
2. **Используй WITH (UPDLOCK, ROWLOCK)** для операций изменения балансов
3. **Проверяй idempotency_key** перед созданием операций
4. **Обновляй stock_balances И stock_movements** в одной транзакции

### При добавлении функций:
1. **Добавляй Pydantic модели** для всех request/response
2. **Обновляй TypeScript интерфейсы** в frontend/services/api.ts
3. **Добавляй обработку ошибок** с понятными сообщениями
4. **Тестируй офлайн-режим** для всех новых операций
5. **Пиши тесты** для backend (pytest)

### Commit messages:
- На русском языке
- Формат: "Тип: краткое описание"
- Примеры:
  - "Добавлено: новый фильтр в истории операций"
  - "Исправлено: расчёт выхода в производстве"
  - "Оптимизировано: загрузка номенклатуры"

### Документация:
- Обновляй BACKEND_STRUCTURE.md при добавлении API endpoints
- Обновляй FRONTEND_STRUCTURE.md при добавлении экранов
- Документируй сложную бизнес-логику в комментариях

## Полезные команды

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
pytest  # запуск тестов
```

### Frontend
```bash
cd frontend
yarn install
expo start --tunnel  # для мобильного тестирования
expo start --web     # для веб-версии
```

### Supervisor (production)
```bash
sudo supervisorctl restart backend
sudo supervisorctl restart expo
sudo supervisorctl status
```

### Health check
```bash
curl http://localhost:8001/api/health
```

## Контакты и ссылки
- Git репозиторий: https://github.com/eio1990/slazar
- Версия: 1.0.0
- Статус: Production Ready
- Последнее обновление: 22.11.2025
