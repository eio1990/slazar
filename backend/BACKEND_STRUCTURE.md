# Backend Structure Documentation

**Последнее обновление:** 22 ноября 2025

## 📁 Структура файлов

```
/app/backend/
├── server.py                          # FastAPI приложение (main)
├── database.py                        # Подключение к MS SQL Server
├── models.py                          # Pydantic модели (общие)
├── batch_operations.py                # Операции с партиями производства
│
├── API Modules:
│   ├── packaging_api.py               # API модуля фасования
│   ├── production_api.py              # API модуля производства
│   ├── butchery_api.py                # API модуля разделки
│   └── butchery_models.py             # Модели для butchery
│
├── Utilities:
│   ├── show_full_chain.py             # Показать цепочку производства
│   ├── analyze_current_db.py          # Анализ базы данных
│   └── final_nomenclature_migration.py # Финальная миграция (история)
│
└── Configuration:
    ├── .env                           # Environment variables
    └── requirements.txt               # Python dependencies
```

## 📄 Описание файлов

### Основные файлы

#### `server.py` (29 KB)
FastAPI приложение с роутами для всех модулей.

**Endpoints:**
- `/api/nomenclature` - Номенклатура
- `/api/stock` - Склад
- `/api/movements` - Движения
- `/api/operations` - Операции прихода/расхода
- `/api/production/*` - Производство (из production_api.py)
- `/api/packaging/*` - Фасование (из packaging_api.py)
- `/api/butchery/*` - Разделка (из butchery_api.py)

**Особенности:**
- CORS middleware
- Error handling
- Database initialization on startup
- Health check endpoint

#### `database.py` (18 KB)
Управление подключением к MS SQL Server.

**Функции:**
- `get_db_connection()` - Получить соединение с БД
- `init_database()` - Инициализация схемы БД
- Schema creation для всех таблиц

**Таблицы:**
- nomenclature
- stock_balances
- stock_movements
- recipes
- recipe_ingredients
- batches
- batch_stages
- packaging_sessions
- packaging_outputs
- packaging_recipes
- butchery_operations
- butchery_recipes
- butchery_recipe_outputs

#### `models.py` (7.6 KB)
Pydantic модели для валидации данных.

**Модели:**
- NomenclatureResponse
- StockBalance
- StockMovement
- Recipe, RecipeIngredient
- Batch, BatchStage
- PackagingSession, PackagingOutput
- ButcheryOperation

### API Модули

#### `packaging_api.py` (33 KB)
API для модуля фасования с концепцией сессий.

**Endpoints:**
- `GET /api/packaging/sessions` - Список сессий
- `POST /api/packaging/sessions` - Создать сессию
- `GET /api/packaging/sessions/{id}` - Детали сессии
- `POST /api/packaging/sessions/{id}/outputs` - Добавить вывод
- `POST /api/packaging/sessions/{id}/complete` - Завершить сессию
- `GET /api/packaging/recipes` - Packaging рецепты
- `GET /api/packaging/recipes/for-product/{id}` - Рецепты для продукта

**Особенности:**
- One-to-many: одна сессия → много SKU
- Автоматический расчет материалов
- Учет брака и остатков
- Опала специя (remnants)
- Waste tracking

#### `production_api.py` (74 KB)
API для модуля производства.

**Endpoints:**
- `GET /api/production/recipes` - Список рецептов
- `GET /api/production/recipes/{id}` - Детали рецепта
- `POST /api/production/batches` - Создать партию
- `GET /api/production/batches` - Список партий
- `GET /api/production/batches/{id}` - Детали партии
- `POST /api/production/batches/{id}/salt` - Засолка
- `POST /api/production/batches/{id}/mix` - Замешивание
- `POST /api/production/batches/{id}/stuff` - Набивка
- `POST /api/production/batches/{id}/dry` - Сушка
- `POST /api/production/batches/{id}/complete` - Завершение

**Стадии производства:**
1. **created** - Партия создана
2. **salt** - Засолка (добавление соли и воды)
3. **mix** - Замешивание (списание специй)
4. **stuff** - Набивка (учет оболонок)
5. **dry** - Сушка (установка даты готовности)
6. **completed** - Завершена (оприходование на склад)

**Особенности:**
- Строгий порядок стадий
- Автоматическое списание ингредиентов
- Расчет выхода продукции
- Tracking использования оболочек
- Расчет material_weight (для пластин)

#### `butchery_api.py` (22 KB)
API для модуля разделки туш.

**Endpoints:**
- `GET /api/butchery/recipes` - Список рецептов разделки
- `GET /api/butchery/recipes/{id}` - Детали рецепта
- `POST /api/butchery/operations` - Создать операцию
- `GET /api/butchery/operations` - Список операций
- `GET /api/butchery/operations/{id}` - Детали операции
- `POST /api/butchery/operations/{id}/complete` - Завершить операцию

**Рецепты разделки:**
- Яловичина туша (ID 27)
- Конина туша (ID 28)

**Особенности:**
- Расчет ожидаемого выхода
- Учет фактических весов
- Отходы (кости, стек) не идут в остатки
- Waste tracking

#### `butchery_models.py` (1.6 KB)
Pydantic модели для butchery.

**Модели:**
- ButcheryRecipeResponse
- ButcheryOperationCreate
- ButcheryOperationResponse

#### `batch_operations.py` (11 KB)
Вспомогательные функции для работы с партиями производства.

**Функции:**
- Валидация стадий
- Расчет выхода
- Обновление статусов
- Работа со специями и оболочками

### Утилиты

#### `show_full_chain.py` (3.3 KB)
Скрипт для отображения полной цепочки производства.

**Использование:**
```bash
python show_full_chain.py
```

**Вывод:**
- Сырое мясо → Полуфабрикаты (butchery recipes)
- Полуфабрикаты → Готовая продукция (production recipes)
- Готовая продукция → SKU (packaging recipes)

#### `analyze_current_db.py` (4.5 KB)
Скрипт для анализа текущего состояния базы данных.

**Использование:**
```bash
python analyze_current_db.py
```

**Анализ:**
- Подсчет номенклатуры по категориям
- Использование в рецептах
- Связи в таблицах
- Orphaned references

#### `final_nomenclature_migration.py` (25 KB)
Скрипт финальной миграции номенклатуры (выполнена 22.11.2025).

**Что было сделано:**
- Объединение дубликатов (ID 108 + 178)
- Переименование 5 продуктов
- Создание "Курка вагова" (ID 227)
- Удаление 23 устаревших позиций
- Обновление всех foreign keys

**Статус:** ✅ Выполнена, оставлена для истории

### Конфигурация

#### `.env`
Environment variables для подключения к БД.

**Переменные:**
- `MSSQL_SERVER` - Адрес сервера MS SQL
- `MSSQL_DATABASE` - Имя базы данных
- `MSSQL_USER` - Пользователь
- `MSSQL_PASSWORD` - Пароль
- `MSSQL_DRIVER` - ODBC Driver 18 for SQL Server
- `TZ` - Timezone (Europe/Kyiv)

#### `requirements.txt` (1.2 KB)
Python dependencies.

**Основные пакеты:**
- fastapi==0.110.1
- uvicorn==0.25.0
- pyodbc==5.3.0
- pydantic==2.12.4
- python-dotenv==1.2.1

## 🗑️ Удаленные файлы

В процессе очистки удалено **25 устаревших файлов**:

### Старые миграции (7):
- migrate_packaging_refactor.py
- migrate_add_butchery.py
- migrate_cleanup.py
- apply_nomenclature_cleanup.py
- cleanup_waste_nomenclature.py
- fix_duplicate_nomenclature.py
- fix_packaging_nomenclature.py

### Старые seed скрипты (11):
- seed_data.py
- seed_recipes.py
- seed_recipes_simple.py
- seed_recipe_ingredients.py
- seed_recipe_spices.py
- seed_finished_products.py
- seed_butchery_data.py
- seed_packaging_recipes.py
- add_indichka_packaging.py
- create_basturma_vagova_recipes.py
- create_universal_stek.py

### Старые проверки (2):
- check_missing_ingredients.py
- add_missing_spices_to_basturma.py

### Старые обновления (1):
- update_production_recipes.py

### Старые версии (2):
- server_v2.py
- packaging_api_old.py

### Устаревшая документация (2):
- cleanup_nomenclature_plan.md
- fix_recipes.txt

## 📊 Статистика

| Категория | Количество |
|-----------|-----------|
| Основные файлы | 5 |
| API модули | 4 |
| Утилиты | 3 |
| Конфигурация | 2 |
| **Всего актуальных** | **12** |
| Удалено устаревших | 25 |

## 🚀 Запуск

### Backend сервер
```bash
cd /app/backend
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```

### Через supervisor
```bash
sudo supervisorctl restart backend
```

### Проверка здоровья
```bash
curl http://localhost:8001/api/health
```

## 📝 Примечания

- Все файлы актуализированы 22.11.2025
- База данных в production состоянии
- Все API endpoints протестированы (23/23 ✅)
- ODBC Driver требует периодической переустановки в Docker

---

**Версия:** 1.0.0  
**Дата:** 22 ноября 2025  
**Статус:** ✅ Production Ready
