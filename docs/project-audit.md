# ПОЛНЫЙ АУДИТ ПРОЕКТА SLAZAR
## Система управления мясным производством

**Дата аудита:** 15 декабря 2025
**Версия проекта:** 1.0.0
**Аудитор:** Claude (Sonnet 4.5)

---

## EXECUTIVE SUMMARY

**Общая оценка проекта: 6.8/10**

Проект SLAZAR - это комплексная система управления мясным производством с модулями разделки, производства и фасовки. Архитектура построена на FastAPI (backend) + React Native/Expo (frontend) с MS SQL Server базой данных.

### Сильные стороны:
- ✅ Хорошо структурированная модульная архитектура
- ✅ Отличная система идемпотентности для операций
- ✅ Продуманная бизнес-логика производственных процессов
- ✅ Качественная offline-first реализация

### Критические проблемы:
- ❌ SQL injection риски (f-string в SQL запросах)
- ❌ Отсутствие authentication/authorization
- ❌ Недостаточная обработка ошибок и логирования
- ❌ Практически полное отсутствие тестов
- ❌ Большое количество `any` типов в TypeScript (155 использований)

---

## 1. КАЧЕСТВО КОДА

### 1.1 BACKEND (Python/FastAPI)

#### FastAPI Best Practices: 7/10

**✅ Плюсы:**
- Правильное использование роутеров (`APIRouter`) для модульности
- Pydantic модели для валидации данных
- Асинхронные эндпоинты с `run_in_threadpool`
- CORS middleware настроен

**❌ Минусы:**
```python
# server.py - небезопасная CORS конфигурация
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ❌ Разрешает любые origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**📋 Рекомендации:**
- Ограничить `allow_origins` конкретными доменами
- Добавить rate limiting middleware
- Использовать dependency injection (Depends) для переиспользуемой логики

---

#### SQL Injection Защита: 3/10 🔥 КРИТИЧНО

**КРИТИЧЕСКАЯ ПРОБЛЕМА!** Найдено множество небезопасных SQL запросов:

```python
# butchery_api.py:267 - ОПАСНО!
if limit:
    query = f"SELECT TOP {limit} * FROM ({query}) AS subquery ORDER BY started_at DESC"
```

```python
# server.py:428
query = f"SELECT TOP {limit} * FROM ({query}) AS subquery"
```

**📋 Рекомендации:**
1. **НЕМЕДЛЕННО** заменить все f-string SQL на параметризованные запросы
2. Рассмотреть использование ORM (SQLAlchemy/SQLModel) вместо raw SQL
3. Добавить SQL injection тесты
4. Пример исправления:
```python
# ❌ Плохо
query = f"SELECT TOP {limit} * FROM batches"

# ✅ Хорошо
query = "SELECT TOP (?) * FROM batches"
cursor.execute(query, (limit,))
```

---

#### Обработка ошибок и исключений: 5/10

**✅ Плюсы:**
- HTTPException используется корректно
- Есть rollback при ошибках транзакций
- Идемпотентность через уникальные ключи

**❌ Минусы:**
```python
# server.py:44-45
except Exception as e:
    print(f"Error initializing database: {e}")  # ❌ Только print, нет логирования
```

**Проблемы:**
- Отсутствие structured logging (используется только `print()`)
- Общие `except Exception` блоки вместо конкретных исключений
- Нет централизованной обработки ошибок
- Отсутствие error tracking (Sentry, etc.)

**📋 Рекомендации:**
```python
import logging
from fastapi import Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error_code": "INTERNAL_ERROR"}
    )
```

---

#### Валидация данных (Pydantic): 8/10

**✅ Отлично:**
- Все модели хорошо типизированы
- Optional поля используются правильно
- Вложенные модели (List[ButcheryRecipeOutput])

**❌ Недостатки:**
```python
# butchery_models.py:40
idempotency_key: Optional[str] = None  # ❌ Должно быть обязательным!
```

**📋 Рекомендации:**
```python
from pydantic import BaseModel, Field, validator

class OperationCreate(BaseModel):
    weight: float = Field(gt=0, lt=10000, description="Вес в кг")
    idempotency_key: str  # Обязательное поле

    @validator('weight')
    def validate_weight(cls, v):
        if v <= 0:
            raise ValueError('Вес должен быть положительным')
        return v
```

---

#### Async/Await использование: 6/10

**⚠️ Проблема:** Блокирующий код обернут в `run_in_threadpool`:

```python
# server.py:133
return await run_in_threadpool(_get)  # ❌ Блокирующий DB код в thread pool
```

**📋 Рекомендации:**
- Использовать асинхронный драйвер БД (asyncpg для PostgreSQL, aioodbc для SQL Server)
- Избегать `run_in_threadpool` для I/O операций
- Пример:
```python
import aioodbc

async def get_nomenclature():
    async with aioodbc.connect(CONNECTION_STRING) as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM nomenclature")
            return await cursor.fetchall()
```

---

#### Дублирование кода: 6/10

**Найденные паттерны дублирования:**

```python
# Повторяется в server.py, production_api.py, packaging_api.py
cursor.execute(
    "UPDATE stock_balances SET quantity = ?, last_updated = DATEADD(HOUR, 2, GETDATE()) WHERE nomenclature_id = ?",
    (new_balance, nomenclature_id)
)
```

**📋 Рекомендации:**
```python
# utils/stock_manager.py
class StockManager:
    def __init__(self, conn):
        self.conn = conn

    def update_balance(self, nomenclature_id: int, quantity: float):
        """Обновляет остаток на складе"""
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE stock_balances SET quantity = ?, last_updated = DATEADD(HOUR, 2, GETDATE()) WHERE nomenclature_id = ?",
            (quantity, nomenclature_id)
        )

    def add_movement(self, nomenclature_id: int, quantity: float, movement_type: str, idempotency_key: str):
        """Добавляет движение на складе"""
        # ...
```

---

### 1.2 FRONTEND (React Native/TypeScript)

#### TypeScript строгость: 5/10 🔥 КРИТИЧНО

**КРИТИЧНО:** Найдено 155 использований `any`:

```typescript
// butchery.tsx:45
const operations = allOperations?.filter((op: any) => {  // ❌
```

```typescript
// production.tsx:127
onPress={() => router.push(`/batches/${item.id}` as any)}  // ❌
```

**📋 Рекомендации:**

1. Создать типы для всех API responses:
```typescript
// types/api.ts
export interface Operation {
  id: number;
  type: 'receipt' | 'withdrawal';
  nomenclature_id: number;
  quantity: number;
  timestamp: string;
}

export interface Batch {
  id: number;
  recipe_id: number;
  status: 'created' | 'salt' | 'mix' | 'stuff' | 'dry' | 'completed';
  initial_weight: number;
  current_weight: number;
}
```

2. Включить strict mode в `tsconfig.json`:
```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true
  }
}
```

3. Использовать type guards:
```typescript
function isOperation(obj: any): obj is Operation {
  return obj && typeof obj.id === 'number' && typeof obj.type === 'string';
}

const operations = allOperations?.filter(isOperation);
```

---

#### React Best Practices: 7/10

**✅ Плюсы:**
- Правильное использование hooks (useState, useQuery)
- Функциональные компоненты
- Key props в списках

**❌ Минусы:**
- Отсутствие useMemo/useCallback для оптимизации
- Inline функции в render методах

**📋 Рекомендации:**
```typescript
// ❌ Плохо - создается новый массив при каждом рендере
const filters = [
  { key: 'created', label: 'Нові' },
  { key: 'completed', label: 'Завершені' },
];

// ✅ Хорошо
const filters = useMemo(() => [
  { key: 'created', label: 'Нові' },
  { key: 'completed', label: 'Завершені' },
], []);

// ❌ Плохо - создается новая функция при каждом рендере
<TouchableOpacity onPress={() => handlePress(item.id)}>

// ✅ Хорошо
const handleItemPress = useCallback((id: number) => {
  handlePress(id);
}, [handlePress]);

<TouchableOpacity onPress={() => handleItemPress(item.id)}>
```

---

#### Обработка ошибок: 4/10

**⚠️ Проблемы:**
```typescript
// api.ts:82-86
} catch (error: any) {  // ❌ any
    console.log('[Network Check] Failed:', error.message || error);
    return false;  // ❌ Проглатывается ошибка
}
```

**30 console.log найдено** - норма для development, но нужен production guard:

**📋 Рекомендации:**
```typescript
// utils/logger.ts
export const logger = {
  log: (...args: any[]) => {
    if (__DEV__) {
      console.log(...args);
    }
  },
  error: (...args: any[]) => {
    if (__DEV__) {
      console.error(...args);
    }
    // В production отправлять в Sentry
    // Sentry.captureException(args[0]);
  }
};

// Использование
import { logger } from '@/utils/logger';
logger.log('[API Service] Using URL:', BASE_URL);
```

---

## 2. АРХИТЕКТУРА

### Модульность и Separation of Concerns: 8/10

**✅ Отлично:**
- Backend разделен на модули (butchery_api, production_api, packaging_api)
- Frontend использует expo-router для навигации
- Отдельный слой API сервиса

**Структура:**
```
backend/
  ├── butchery_api.py      # Модуль разделки
  ├── production_api.py     # Производство
  ├── packaging_api.py      # Фасовка
  ├── models.py            # Общие модели
  └── batch_operations.py  # Batch логика

frontend/
  ├── services/api.ts      # API слой
  ├── stores/useStore.ts   # State
  └── app/                 # Screens
```

**📋 Рекомендации:**
```python
# backend/repositories/stock_repository.py
class StockRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_balance(self, nomenclature_id: int) -> float:
        # ...

    def update_balance(self, nomenclature_id: int, quantity: float):
        # ...

# backend/services/stock_service.py
class StockService:
    def __init__(self, repo: StockRepository):
        self.repo = repo

    def process_receipt(self, operation: OperationCreate):
        # Business logic here
        self.repo.update_balance(...)
```

---

### API Design (REST): 7/10

**✅ Плюсы:**
- RESTful endpoints
- Правильные HTTP методы (GET, POST, PUT)
- Логичная вложенность ресурсов

**Примеры:**
```
POST /api/production/batches
GET  /api/production/batches/{id}
POST /api/production/batches/{id}/operations
PUT  /api/production/batches/{id}/complete
```

**❌ Недостатки:**
- Нет версионирования API (должно быть `/api/v1/...`)
- Нет pagination для списков
- Inconsistency в naming

**📋 Рекомендации:**
```python
# Версионирование
@router.get("/api/v1/production/batches")
async def get_batches(
    skip: int = 0,
    limit: int = 20,  # Pagination
    status: Optional[str] = None
):
    # ...
```

---

### База данных схема: 8/10

**✅ Отлично продумано:**
- Нормализация на хорошем уровне
- Foreign keys с CASCADE
- Unique constraints для бизнес-правил
- Идемпотентность через unique keys

**❌ Проблемы:**
- Нет индексов на frequently queried колонки
- Отсутствие soft deletes (is_deleted флаг)

**📋 Рекомендации:**
```sql
-- Добавить индексы
CREATE INDEX IX_batches_status ON batches(status);
CREATE INDEX IX_batches_created_at ON batches(created_at DESC);
CREATE INDEX IX_stock_movements_operation_type ON stock_movements(operation_type);
CREATE INDEX IX_nomenclature_category ON nomenclature(category);

-- Добавить soft deletes
ALTER TABLE nomenclature ADD is_deleted BIT DEFAULT 0;
ALTER TABLE batches ADD is_deleted BIT DEFAULT 0;
```

---

### Offline-first реализация: 6/10

**✅ Реализовано:**
```typescript
// api.ts
export interface QueuedOperation {
  id: string;
  type: 'receipt' | 'withdrawal' | 'inventory';
  data: any;
  timestamp: string;
}

export async function addToOfflineQueue(operation)
export async function syncOperations(operations)
```

**❌ Проблемы:**
- Queue не используется активно в компонентах
- Нет UI индикатора pending операций
- Sync стратегия не видна

**📋 Рекомендации:**
```typescript
// stores/offlineStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface OfflineStore {
  queue: QueuedOperation[];
  addToQueue: (operation: QueuedOperation) => void;
  removeFromQueue: (id: string) => void;
  getPendingCount: () => number;
}

export const useOfflineStore = create<OfflineStore>()(
  persist(
    (set, get) => ({
      queue: [],
      addToQueue: (operation) => set((state) => ({
        queue: [...state.queue, operation]
      })),
      removeFromQueue: (id) => set((state) => ({
        queue: state.queue.filter(op => op.id !== id)
      })),
      getPendingCount: () => get().queue.length,
    }),
    { name: 'offline-storage' }
  )
);

// components/OfflineIndicator.tsx
export function OfflineIndicator() {
  const pendingCount = useOfflineStore(state => state.getPendingCount());
  const isOnline = useStore(state => state.isOnline);

  if (isOnline && pendingCount === 0) return null;

  return (
    <View style={styles.indicator}>
      <Text>{isOnline ? `Синхронізація... ${pendingCount}` : 'Офлайн режим'}</Text>
    </View>
  );
}
```

---

### Масштабируемость: 6/10

**❌ Проблемы:**
- Нет connection pooling настроек
- Отсутствие кэширования (Redis)
- N+1 query проблемы

```python
# packaging_api.py:78-85 - N+1 query
for row in cursor.fetchall():
    # Для каждого рецепта делается отдельный запрос материалов
    cursor.execute("SELECT ... WHERE recipe_id = ?", recipe_id)
```

**📋 Рекомендации:**
```python
# ❌ N+1 query
for recipe in recipes:
    materials = get_materials(recipe.id)  # Отдельный запрос для каждого

# ✅ Batch loading
recipe_ids = [r.id for r in recipes]
materials = get_materials_batch(recipe_ids)  # Один запрос
materials_by_recipe = group_by(materials, 'recipe_id')

# Redis кэширование
import redis
cache = redis.Redis(host='localhost', port=6379)

def get_nomenclature():
    cached = cache.get('nomenclature')
    if cached:
        return json.loads(cached)

    data = fetch_from_db()
    cache.setex('nomenclature', 3600, json.dumps(data))  # TTL 1 час
    return data
```

---

### Security Patterns: 4/10 🔥 КРИТИЧНО

**❌ Критические проблемы:**

1. **SQL Injection риски** (см. раздел 1.1)

2. **CORS слишком открыт:**
```python
allow_origins=["*"]  # ❌ ОПАСНО
```

3. **Нет authentication/authorization:**
```python
@router.post("/operations")
async def create_butchery_operation(...)  # ❌ Любой может вызвать
```

**📋 Рекомендации:**

```python
# 1. JWT Authentication
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload["sub"]
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Использование
@router.post("/operations")
async def create_operation(
    operation: OperationCreate,
    current_user: str = Depends(get_current_user)
):
    # ...

# 2. RBAC
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"

def require_role(required_role: Role):
    async def role_checker(current_user = Depends(get_current_user)):
        if current_user.role != required_role:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

@router.delete("/batches/{batch_id}")
async def delete_batch(
    batch_id: int,
    current_user = Depends(require_role(Role.ADMIN))
):
    # Только админ может удалять

# 3. Rate Limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/operations")
@limiter.limit("10/minute")
async def create_operation(...):
    # Максимум 10 запросов в минуту
```

---

### Transaction Management: 7/10

**✅ Отлично:**
```python
# database.py
@contextmanager
def get_db_connection():
    conn = None
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        yield conn
        conn.commit()  # ✅
    except Exception as e:
        if conn:
            conn.rollback()  # ✅
        raise e
```

**❌ Недостатки:**
- Нет isolation level контроля
- Отсутствие distributed transactions

**📋 Рекомендации:**
```python
@contextmanager
def get_db_connection(isolation_level='READ COMMITTED'):
    conn = None
    try:
        conn = pyodbc.connect(CONNECTION_STRING)
        conn.execute(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()
```

---

## 3. ПОТЕНЦИАЛЬНЫЕ ПРОБЛЕМЫ

### Race Conditions: 6/10

**✅ Найдена защита:**
```python
# server.py:76-85
def get_current_balance_locked(conn, nomenclature_id: int) -> float:
    cursor = conn.cursor()
    # WITH (UPDLOCK, ROWLOCK) provides row-level exclusive lock
    cursor.execute(
        "SELECT quantity FROM stock_balances WITH (UPDLOCK, ROWLOCK) WHERE nomenclature_id = ?",
        (nomenclature_id,)
    )
```

**⚠️ Риски:**
- Не все операции используют locking
- Нет timeout для locks (может быть deadlock)

**📋 Рекомендации:**
```python
# Добавить lock timeout
cursor.execute("SET LOCK_TIMEOUT 5000")  # 5 секунд

# Check-then-insert должен использовать constraints, а не проверки
# ❌ Плохо - race condition
cursor.execute("SELECT id FROM batch_mix_production WHERE batch_id = ?", batch_id)
if cursor.fetchone():
    raise HTTPException(...)

# ✅ Хорошо - UNIQUE constraint на уровне БД
# CREATE UNIQUE INDEX IX_batch_mix_production_batch_id ON batch_mix_production(batch_id)
try:
    cursor.execute("INSERT INTO batch_mix_production ...")
except pyodbc.IntegrityError:
    raise HTTPException(status_code=409, detail="Mix production already exists")
```

---

### Performance Bottlenecks: 5/10

**❌ Найденные проблемы:**

1. **N+1 Queries:**
```python
# packaging_api.py:74-109
for row in cursor.fetchall():  # Для каждого рецепта
    cursor.execute("SELECT ... WHERE recipe_id = ?", recipe_id)  # Отдельный запрос
```

2. **Нет pagination:**
```python
# server.py:406
async def get_movements(..., limit: int = 100):  # ❌ Только limit, нет offset
```

3. **Hardcoded DATEADD в каждом запросе:**
```python
# Повторяется сотни раз
DATEADD(HOUR, 2, GETDATE())  # ❌ Вычисляется в каждом запросе
```

**📋 Рекомендации:**
```python
# 1. Исправить N+1
# ❌ Плохо
recipes = cursor.execute("SELECT * FROM recipes").fetchall()
for recipe in recipes:
    materials = cursor.execute("SELECT * FROM materials WHERE recipe_id = ?", recipe.id).fetchall()

# ✅ Хорошо - JOIN
cursor.execute("""
    SELECT r.*, m.*
    FROM recipes r
    LEFT JOIN materials m ON m.recipe_id = r.id
    WHERE r.category = ?
""", category)

# 2. Добавить pagination
@router.get("/movements")
async def get_movements(
    skip: int = 0,
    limit: int = 20,
    total: bool = False  # Опция получить total count
):
    if total:
        count = cursor.execute("SELECT COUNT(*) FROM stock_movements").fetchone()[0]

    cursor.execute(
        "SELECT * FROM stock_movements ORDER BY timestamp DESC OFFSET ? ROWS FETCH NEXT ? ROWS ONLY",
        (skip, limit)
    )
    return {"items": cursor.fetchall(), "total": count if total else None}

# 3. Timezone на уровне БД
# Установить default timezone для сессии
cursor.execute("SET TIME ZONE 'Europe/Kiev'")
# Или использовать UTC везде и конвертировать на клиенте
```

---

### Edge Cases не покрытые: 4/10

**❌ Найденные проблемы:**

1. **Деление на ноль:**
```python
# production_api.py:1613
yield_percent = (completion.final_weight / float(batch.initial_weight)) * 100
# ❌ Что если initial_weight = 0?
```

2. **Negative quantities:**
```python
# Валидация только quantity > 0, но нет проверки на максимум
```

3. **Timezone issues:**
```python
# Hardcoded +2 hours offset
DATEADD(HOUR, 2, GETDATE())  # ❌ Что при переходе на летнее время?
```

**📋 Рекомендации:**
```python
# 1. Защита от деления на ноль
if batch.initial_weight == 0:
    raise HTTPException(status_code=400, detail="Initial weight cannot be zero")
yield_percent = (completion.final_weight / float(batch.initial_weight)) * 100

# 2. Pydantic validators
class OperationCreate(BaseModel):
    quantity: float = Field(gt=0, le=10000)  # Между 0 и 10000

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('Quantity must be positive')
        if v > 10000:
            raise ValueError('Quantity too large (max 10000 kg)')
        return v

# 3. Использовать UTC везде
from datetime import datetime, timezone

now = datetime.now(timezone.utc)
# На клиенте конвертировать в локальное время
```

---

### Hardcoded Values: 4/10

**❌ Найдено много:**

```python
# production_api.py:19-22
FENUGREEK_ID = 19  # ❌ Hardcoded
WATER_ID = 136
SALT_ID = 28

# butchery_api.py:18-20
TIMEZONE_OFFSET_HOURS = 2  # ❌ Hardcoded timezone
```

```typescript
// api.ts:58
timeout: 30000,  // ❌ Magic number
```

**📋 Рекомендации:**
```python
# config.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Database
    mssql_server: str
    mssql_database: str
    mssql_user: str
    mssql_password: str

    # Business logic
    fenugreek_nomenclature_id: int = 19
    water_nomenclature_id: int = 136
    salt_nomenclature_id: int = 28

    # Timezone
    timezone_offset_hours: int = 2

    # API
    api_timeout_seconds: int = 30
    max_batch_size: int = 1000

    class Config:
        env_file = ".env"

settings = Settings()

# Использование
from config import settings
FENUGREEK_ID = settings.fenugreek_nomenclature_id
```

---

## 4. ТЕХНИЧЕСКИЙ ДОЛГ

### Отсутствующие тесты: 2/10 🔥 КРИТИЧНО

**КРИТИЧНО:** Найден только 1 тестовый файл:
```
tests/__init__.py  # Пустой!
mass_operations_test.py  # Один тест
```

**📋 Рекомендации:**
```python
# tests/test_stock_api.py
import pytest
from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)

def test_create_receipt_operation():
    response = client.post("/api/operations", json={
        "type": "receipt",
        "nomenclature_id": 1,
        "quantity": 100.0,
        "idempotency_key": "test-key-123"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_idempotency():
    # Создаем операцию дважды с одним ключом
    data = {
        "type": "receipt",
        "nomenclature_id": 1,
        "quantity": 100.0,
        "idempotency_key": "test-key-456"
    }

    response1 = client.post("/api/operations", json=data)
    response2 = client.post("/api/operations", json=data)

    assert response1.status_code == 200
    assert response2.json()["status"] == "already_processed"

def test_insufficient_stock():
    response = client.post("/api/operations", json={
        "type": "withdrawal",
        "nomenclature_id": 1,
        "quantity": 999999.0,  # Больше чем на складе
        "idempotency_key": "test-key-789"
    })
    assert response.status_code == 400
    assert "insufficient" in response.json()["detail"].lower()

# tests/test_production_api.py
def test_create_batch():
    # ...

def test_batch_salt_stage():
    # ...

# Запуск
# pytest tests/ --cov=backend --cov-report=html
```

**Цель:** Минимум 70% code coverage

---

### Отсутствующая документация: 3/10

**❌ Нет:**
- README.md с инструкциями по установке
- Database schema diagram
- Architecture decision records (ADR)
- Deployment guide

**📋 Рекомендации:**

```markdown
# README.md
# SLAZAR - Система управления мясным производством

## Требования
- Python 3.11+
- Node.js 18+
- MS SQL Server 2022
- ODBC Driver 18 for SQL Server

## Установка

### Backend
\`\`\`bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env  # Настроить переменные окружения
uvicorn server:app --reload
\`\`\`

### Frontend
\`\`\`bash
cd frontend
yarn install
cp .env.example .env
expo start
\`\`\`

## Тестирование
\`\`\`bash
cd backend
pytest tests/ --cov
\`\`\`

## Деплой
См. docs/deployment.md
```

---

### Logging и Monitoring: 2/10 🔥 КРИТИЧНО

**КРИТИЧНО:** Используется только `print()` и `console.log()`

```python
# server.py:45
print(f"Error initializing database: {e}")  # ❌
```

**📋 Рекомендации:**

```python
# backend/utils/logger.py
import logging
import sys
from pythonjsonlogger import jsonlogger

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    formatter = jsonlogger.JsonFormatter(
        '%(asctime)s %(name)s %(levelname)s %(message)s'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

# Использование
from utils.logger import setup_logger
logger = setup_logger(__name__)

@router.post("/operations")
async def create_operation(operation: OperationCreate):
    logger.info(
        "Creating operation",
        extra={
            "operation_type": operation.type,
            "nomenclature_id": operation.nomenclature_id,
            "quantity": operation.quantity
        }
    )
    try:
        # ...
        logger.info("Operation created successfully", extra={"operation_id": result.id})
        return result
    except Exception as e:
        logger.error(
            "Failed to create operation",
            exc_info=True,
            extra={"error": str(e)}
        )
        raise

# Sentry integration
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="YOUR_SENTRY_DSN",
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
)

# Health check endpoint с metrics
from prometheus_client import Counter, Histogram
import time

request_count = Counter('http_requests_total', 'Total HTTP requests')
request_duration = Histogram('http_request_duration_seconds', 'HTTP request duration')

@app.middleware("http")
async def add_metrics(request: Request, call_next):
    request_count.inc()
    start_time = time.time()
    response = await call_next(request)
    request_duration.observe(time.time() - start_time)
    return response
```

---

## 5. БЕЗОПАСНОСТЬ

### Итоговая оценка безопасности: 3.5/10 🔥 КРИТИЧНО

| Аспект | Оценка | Статус |
|--------|--------|--------|
| SQL Injection | 3/10 | 🔥 КРИТИЧНО |
| CORS | 3/10 | 🔥 КРИТИЧНО |
| Authentication | 0/10 | 🔥 КРИТИЧНО |
| Authorization | 0/10 | 🔥 КРИТИЧНО |
| Input Validation | 6/10 | ⚠️ Требует улучшения |
| Secrets Management | 7/10 | ✅ Приемлемо |
| Rate Limiting | 0/10 | 🔥 КРИТИЧНО |
| Error Disclosure | 5/10 | ⚠️ Требует улучшения |

**📋 Критические рекомендации:**

1. **Немедленно исправить SQL injection**
2. **Добавить JWT authentication**
3. **Настроить CORS для конкретных доменов**
4. **Добавить rate limiting**
5. **Не раскрывать внутренние детали в ошибках**

---

## 6. ПРОИЗВОДИТЕЛЬНОСТЬ

### Database Queries Оптимизация: 5/10

**❌ Проблемы:**
- SELECT * используется часто
- Нет prepared statements caching
- Отсутствие query планирования

**📋 Рекомендации:**
```python
# ❌ Плохо
cursor.execute("SELECT * FROM nomenclature")

# ✅ Хорошо - указываем нужные колонки
cursor.execute("""
    SELECT id, name, category, unit, precision_digits
    FROM nomenclature
    WHERE is_active = 1
""")

# Использовать EXPLAIN для анализа
cursor.execute("EXPLAIN SELECT ...")
```

---

### Индексы БД: 4/10

**❌ Найден только один индекс:**
```sql
CREATE INDEX IX_stock_movements_date ON stock_movements(operation_date DESC)
```

**📋 Рекомендации:**
```sql
-- Для частых фильтров
CREATE INDEX IX_batches_status ON batches(status);
CREATE INDEX IX_batches_recipe_id ON batches(recipe_id);
CREATE INDEX IX_nomenclature_category ON nomenclature(category);
CREATE INDEX IX_nomenclature_meat_type ON nomenclature(meat_type);

-- Для сортировки
CREATE INDEX IX_batches_created_at_desc ON batches(created_at DESC);
CREATE INDEX IX_stock_movements_timestamp_desc ON stock_movements(timestamp DESC);

-- Composite индексы для частых запросов
CREATE INDEX IX_batches_status_created ON batches(status, created_at DESC);
CREATE INDEX IX_nomenclature_category_active ON nomenclature(category, is_active);

-- Проверить использование индексов
SELECT * FROM sys.dm_db_index_usage_stats WHERE database_id = DB_ID('SLAZAR_DB');
```

---

### Caching Стратегии: 2/10

**❌ Проблемы:**
- Нет Redis/Memcached
- Нет HTTP caching headers
- React Query cache есть ✅ (но настройки по умолчанию)

**📋 Рекомендации:**
```python
# Backend - Redis caching
import redis
from functools import wraps
import json

redis_client = redis.Redis(host='localhost', port=6379, decode_responses=True)

def cache_result(key_prefix: str, ttl: int = 3600):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{':'.join(map(str, args))}"

            # Проверяем кэш
            cached = redis_client.get(cache_key)
            if cached:
                return json.loads(cached)

            # Вызываем функцию
            result = await func(*args, **kwargs)

            # Сохраняем в кэш
            redis_client.setex(cache_key, ttl, json.dumps(result))
            return result
        return wrapper
    return decorator

@app.get("/api/nomenclature")
@cache_result("nomenclature", ttl=3600)  # Кэш на 1 час
async def get_nomenclature():
    # ...

# HTTP caching headers
from fastapi import Response

@app.get("/api/nomenclature")
async def get_nomenclature(response: Response):
    response.headers["Cache-Control"] = "public, max-age=3600"
    response.headers["ETag"] = generate_etag(data)
    # ...
```

```typescript
// Frontend - React Query optimizations
import { QueryClient } from '@tanstack/react-query';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 минут
      cacheTime: 10 * 60 * 1000, // 10 минут
      refetchOnWindowFocus: false,
      retry: 3,
    },
  },
});

// Prefetching
queryClient.prefetchQuery({
  queryKey: ['nomenclature'],
  queryFn: fetchNomenclature,
});
```

---

## ИТОГОВЫЕ ОЦЕНКИ ПО КРИТЕРИЯМ

| Категория | Оценка | Приоритет |
|-----------|--------|-----------|
| **КАЧЕСТВО КОДА** | **6.2/10** | |
| ├─ Backend Best Practices | 7/10 | Средний |
| ├─ SQL Injection защита | 3/10 | 🔥 КРИТИЧНЫЙ |
| ├─ Обработка ошибок | 5/10 | Высокий |
| ├─ Валидация Pydantic | 8/10 | Низкий |
| ├─ TypeScript строгость | 5/10 | Высокий |
| └─ React Best Practices | 7/10 | Средний |
| **АРХИТЕКТУРА** | **6.8/10** | |
| ├─ Модульность | 8/10 | Низкий |
| ├─ API Design | 7/10 | Средний |
| ├─ БД схема | 8/10 | Низкий |
| ├─ Offline-first | 6/10 | Средний |
| ├─ Масштабируемость | 6/10 | Высокий |
| └─ Security Patterns | 4/10 | 🔥 КРИТИЧНЫЙ |
| **ПРОБЛЕМЫ** | **5.4/10** | |
| ├─ Race Conditions | 6/10 | Средний |
| ├─ Performance | 5/10 | Высокий |
| ├─ Data Consistency | 6/10 | Средний |
| └─ Edge Cases | 4/10 | Высокий |
| **ТЕХНИЧЕСКИЙ ДОЛГ** | **3.6/10** | |
| ├─ Тесты | 2/10 | 🔥 КРИТИЧНЫЙ |
| ├─ Документация | 3/10 | Высокий |
| ├─ Logging | 2/10 | 🔥 КРИТИЧНЫЙ |
| └─ Configuration | 5/10 | Средний |
| **БЕЗОПАСНОСТЬ** | **3.5/10** | 🔥 КРИТИЧНЫЙ |
| ├─ Authentication | 0/10 | 🔥 КРИТИЧНЫЙ |
| ├─ CORS | 3/10 | 🔥 КРИТИЧНЫЙ |
| └─ Input Validation | 6/10 | Высокий |
| **ПРОИЗВОДИТЕЛЬНОСТЬ** | **4.8/10** | |
| ├─ DB Optimization | 5/10 | Высокий |
| ├─ N+1 Queries | 4/10 | Высокий |
| └─ Caching | 2/10 | Средний |

---

## ПРИОРИТЕТНЫЕ РЕКОМЕНДАЦИИ

### 🔥 КРИТИЧЕСКИЕ (исправить немедленно):

#### 1. SQL Injection защита (Срок: 1-2 недели)
- [ ] Заменить все f-string SQL на параметризованные запросы
- [ ] Добавить SQL injection тесты
- [ ] Code review всех SQL запросов
- [ ] Рассмотреть переход на ORM (SQLModel/SQLAlchemy)

#### 2. Authentication & Authorization (Срок: 1 неделя)
- [ ] Добавить JWT authentication
- [ ] Implement RBAC для разных ролей (admin, operator, viewer)
- [ ] Защитить все sensitive endpoints
- [ ] Добавить refresh tokens

#### 3. CORS Configuration (Срок: 1 день)
- [ ] Ограничить `allow_origins` конкретными доменами
- [ ] Настроить для production и development отдельно
- [ ] Добавить в .env файл

#### 4. Тестирование (Срок: 2 недели)
- [ ] Unit тесты для всех API endpoints (цель: 70% coverage)
- [ ] Integration тесты для критических flows
- [ ] Frontend component tests
- [ ] End-to-end тесты

#### 5. Logging & Monitoring (Срок: 3 дня)
- [ ] Заменить print() на structured logging
- [ ] Добавить Sentry для error tracking
- [ ] Implement health checks и metrics (Prometheus)
- [ ] Настроить log aggregation

---

### ⚡ ВЫСОКИЙ ПРИОРИТЕТ (исправить в ближайшее время):

#### 6. TypeScript строгость (Срок: 1 неделя)
- [ ] Убрать все `any` типы (155 использований)
- [ ] Включить strict mode
- [ ] Создать типы для всех API responses
- [ ] Добавить type guards

#### 7. Error Handling (Срок: 3 дня)
- [ ] Централизованная обработка ошибок
- [ ] Custom exceptions с error codes
- [ ] Proper error messages для пользователя
- [ ] Не раскрывать внутренние детали в production

#### 8. Performance оптимизация (Срок: 1 неделя)
- [ ] Исправить все N+1 queries
- [ ] Добавить индексы БД
- [ ] Implement pagination везде
- [ ] Добавить Redis кэш для nomenclature

#### 9. Configuration Management (Срок: 2 дня)
- [ ] Создать centralized config
- [ ] Вынести все hardcoded значения
- [ ] Создать .env.example
- [ ] Использовать Pydantic Settings

#### 10. Документация (Срок: 3 дня)
- [ ] README с setup инструкциями
- [ ] Database schema diagram
- [ ] Architecture decision records
- [ ] Deployment guide

---

### 📋 СРЕДНИЙ ПРИОРИТЕТ:

11. Async DB driver вместо blocking pyodbc (1 неделя)
12. Connection pooling (2 дня)
13. Rate limiting (1 день)
14. Code splitting для frontend (2 дня)
15. Cleanup deprecated code (1 день)
16. Implement optimistic locking (3 дня)
17. Better offline sync strategy (3 дня)

---

## ПЛАН ДЕЙСТВИЙ НА БЛИЖАЙШИЕ 4 НЕДЕЛИ

### Неделя 1: Критические проблемы безопасности
- День 1-2: SQL Injection - исправление всех f-string запросов
- День 3-4: JWT Authentication базовая реализация
- День 5: CORS configuration, Rate limiting
- День 6-7: Structured logging setup, Sentry integration

### Неделя 2: Тестирование
- День 1-3: Backend unit тесты (API endpoints)
- День 4-5: Integration тесты
- День 6-7: Frontend component тесты

### Неделя 3: Качество кода
- День 1-3: TypeScript строгость - убрать any
- День 4-5: Error handling improvement
- День 6-7: Configuration management

### Неделя 4: Производительность и документация
- День 1-2: Performance оптимизация (N+1, индексы)
- День 3-4: Redis caching
- День 5-7: Документация (README, ADR, deployment guide)

---

## МЕТРИКИ УСПЕХА

После выполнения всех критических и высокоприоритетных задач:

| Метрика | Текущее | Цель |
|---------|---------|------|
| Test Coverage | 0% | 70%+ |
| TypeScript any | 155 | 0 |
| SQL Injection риски | Высокий | Нет |
| Authentication | Нет | JWT + RBAC |
| Logging | print() | Structured |
| Performance Score | 5/10 | 8/10 |
| Security Score | 3.5/10 | 8/10 |
| **Общая оценка** | **6.8/10** | **8.5/10** |

---

## ЗАКЛЮЧЕНИЕ

**Проект SLAZAR** демонстрирует **отличную бизнес-логику и архитектурный дизайн**, но имеет **критические проблемы безопасности и качества кода**, которые **НЕОБХОДИМО** исправить перед production deployment.

### Главные сильные стороны:
- ✅ Отлично продуманная бизнес-логика производственных процессов
- ✅ Система идемпотентности для предотвращения дублирования операций
- ✅ Хорошая БД схема с proper constraints
- ✅ Модульная архитектура с чистым разделением ответственности
- ✅ Offline-first подход для мобильного приложения

### Критические слабости:
- ❌ **SQL injection риски** - требуют немедленного исправления
- ❌ **Отсутствие authentication/authorization** - система открыта для всех
- ❌ **Нет тестов** - высокий риск регрессий
- ❌ **Плохой logging** - сложно диагностировать проблемы в production
- ❌ **TypeScript any everywhere** - теряются преимущества типизации

### Рекомендация по deployment:

**⚠️ НЕ ДЕПЛОИТЬ В PRODUCTION ДО ИСПРАВЛЕНИЯ КРИТИЧЕСКИХ ПРОБЛЕМ**

**Готовность к production:** 4/10

После выполнения плана на 4 недели: **8.5/10** ✅

---

**Следующий шаг:** Создать GitHub Issues для всех критических задач и начать с SQL Injection защиты.
