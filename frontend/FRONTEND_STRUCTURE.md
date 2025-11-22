# Frontend Structure Documentation

**Останнє оновлення:** 22 листопада 2025

## 📁 Структура файлів

```
/app/frontend/
├── app/
│   ├── (tabs)/                    # Tab navigation (Bottom tabs)
│   │   ├── _layout.tsx            # Tab bar layout з навігацією
│   │   ├── index.tsx              # Tab 1: Операції (Прихід/Розхід)
│   │   ├── operations.tsx         # Redirect на index
│   │   ├── butchery.tsx           # Tab 2: Різання (Розділка)
│   │   ├── production.tsx         # Tab 3: Виробництво
│   │   ├── packaging.tsx          # Tab 4: Фасування
│   │   ├── inventory.tsx          # Tab 5: Склад (Залишки)
│   │   └── history.tsx            # Tab 6: Історія
│   │
│   ├── batches/                   # Production module screens
│   │   ├── [id].tsx               # Деталі партії (стан, історія, дії)
│   │   ├── salting-form.tsx       # Етап: Засолка
│   │   ├── mix-form.tsx           # Етап: Замішування
│   │   ├── stuffing-form.tsx      # Етап: Набивка
│   │   ├── sugar-form.tsx         # Етап: Цукор (для бастурми)
│   │   ├── marinade-form.tsx      # Етап: Маринад
│   │   ├── massage-form.tsx       # Етап: Масаж
│   │   └── trim-form.tsx          # Етап: Обрізка
│   │
│   ├── butchery/                  # Butchery module screens
│   │   ├── select-meat-type.tsx   # Крок 1: Вибір типу м'яса
│   │   ├── select-grade.tsx       # Крок 2: Вибір ґатунку
│   │   ├── select-recipe.tsx      # Крок 3: Вибір рецепту
│   │   ├── input-weight.tsx       # Крок 4: Введення ваги
│   │   ├── complete-form.tsx      # Крок 5: Завершення з вводом результатів
│   │   └── [id].tsx               # Деталі завершеної операції
│   │
│   ├── packaging/                 # Packaging module screens
│   │   ├── new-session.tsx        # Створення нової сесії фасування
│   │   └── [id].tsx               # Деталі сесії (додавання виходів)
│   │
│   ├── recipes/                   # Recipes module
│   │   ├── index.tsx              # Список всіх рецептів виробництва
│   │   └── [id].tsx               # Деталі рецепту (інгредієнти, вихід)
│   │
│   ├── stock/                     # Stock module
│   │   └── index.tsx              # Залишки на складі (фільтри, пошук)
│   │
│   ├── analytics/                 # Analytics module
│   │   └── index.tsx              # Аналітика (заглушка)
│   │
│   ├── _layout.tsx                # Root layout (providers, toast)
│   └── index.tsx                  # Entry point (redirect на operations)
│
├── components/
│   └── HamburgerMenu.tsx          # Навігаційне меню (burger icon)
│
├── services/
│   └── api.ts                     # API client (axios + interceptors)
│
├── stores/
│   └── useStore.ts                # Zustand store (client state)
│
├── Configuration:
│   ├── app.json                   # Expo конфігурація
│   ├── package.json               # Dependencies
│   ├── tsconfig.json              # TypeScript config
│   ├── metro.config.js            # Metro bundler config
│   ├── eslint.config.js           # ESLint config
│   └── .env                       # Environment variables
│
└── Utilities:
    ├── check_expo_url.js          # Перевірка Expo URL
    ├── generate_qr.js             # Генерація QR кода
    └── generate_correct_qr.js     # Генерація коректного QR
```

---

## 📱 Модулі додатку

### 1. Операції (Operations)

**Файл:** `app/(tabs)/index.tsx`

**Функціонал:**
- Вибір типу операції: Прихід або Розхід
- Вибір номенклатури з фільтрами за категоріями
- Введення кількості та ціни (для приходу)
- Перевірка залишків перед розходом
- Додавання приміток

**API Endpoints:**
- `GET /api/nomenclature` - Список номенклатури
- `GET /api/stock/balances` - Залишки
- `POST /api/operations` - Створити операцію

---

### 2. Різання (Butchery)

**Головний файл:** `app/(tabs)/butchery.tsx`

**Процес (5 кроків):**

1. **select-meat-type.tsx** - Вибір типу м'яса (Яловичина/Конина)
2. **select-grade.tsx** - Вибір ґатунку (Туша/Вищий/Перший/Другий)
3. **select-recipe.tsx** - Вибір рецепту розділки
4. **input-weight.tsx** - Введення ваги сировини + розрахунок очікуваного виходу
5. **complete-form.tsx** - Введення фактичних ваг виходів + завершення

**Деталі операції:**
- **[id].tsx** - Перегляд завершеної операції

**API Endpoints:**
- `GET /api/butchery/recipes` - Список рецептів
- `GET /api/butchery/recipes/:id` - Деталі рецепту
- `POST /api/butchery/operations` - Створити операцію
- `POST /api/butchery/operations/:id/complete` - Завершити

**Особливості:**
- Автоматичний розрахунок виходу за рецептом
- Облік відходів (кістки, стек)
- Валідація ваг

---

### 3. Виробництво (Production)

**Головний файл:** `app/(tabs)/production.tsx`

**Lifecycle партії:**

```
created → salt → mix → stuff → dry → completed
```

**Екрани форм:**

1. **salting-form.tsx** - Засолка
   - Введення кількості солі
   - Введення кількості води
   - Автоматичне списання зі складу

2. **mix-form.tsx** - Замішування
   - Відображення специй з рецепту
   - Автоматичне списання специй
   - Перехід до набивки

3. **stuffing-form.tsx** - Набивка
   - Зважування оболонок до набивки
   - Зважування після набивки
   - Розрахунок використаних оболонок

4. **sugar-form.tsx** - Додавання цукру (для бастурми)
5. **marinade-form.tsx** - Маринування
6. **massage-form.tsx** - Масаж
7. **trim-form.tsx** - Обрізка

**Деталі партії:**
- **batches/[id].tsx** - Статус партії, історія етапів, доступні дії

**API Endpoints:**
- `GET /api/production/recipes` - Список рецептів
- `POST /api/production/batches` - Створити партію
- `GET /api/production/batches/:id` - Деталі партії
- `POST /api/production/batches/:id/salt` - Засолка
- `POST /api/production/batches/:id/mix` - Замішування
- `POST /api/production/batches/:id/stuff` - Набивка
- `POST /api/production/batches/:id/dry` - Сушіння
- `POST /api/production/batches/:id/complete` - Завершення

**Особливості:**
- Строга послідовність етапів
- Автоматичне списання матеріалів
- Tracking оболонок
- Розрахунок виходу продукції

---

### 4. Фасування (Packaging)

**Головний файл:** `app/(tabs)/packaging.tsx`

**Концепція сесій:**

Одна сесія фасування = один джерельний продукт (вагова продукція).  
В рамках однієї сесії можна упакувати в різні SKU.

**Екрани:**

1. **new-session.tsx** - Створення нової сесії
   - Вибір джерельного продукту
   - Перевірка залишків
   - Введення кількості для фасування

2. **[id].tsx** - Деталі сесії
   - Horizontal ScrollView з кнопками SKU
   - Форми для кожного SKU (quantity, waste, remnants)
   - Облік браку матеріалів
   - Завершення сесії

**API Endpoints:**
- `GET /api/packaging/sessions` - Список сесій
- `POST /api/packaging/sessions` - Створити сесію
- `GET /api/packaging/sessions/:id` - Деталі сесії
- `POST /api/packaging/sessions/:id/outputs` - Додати вихід
- `POST /api/packaging/sessions/:id/complete` - Завершити сесію
- `GET /api/packaging/recipes` - Packaging рецепти
- `GET /api/packaging/recipes/for-product/:id` - Рецепти для продукту

**Особливості:**
- One-to-many: 1 сесія → N SKU
- Автоматичний розрахунок матеріалів (пакети, етикетки)
- Облік браку
- Облік залишків (опала спеція)
- Waste tracking

---

### 5. Склад (Stock)

**Файл:** `app/stock/index.tsx`

**Функціонал:**
- Перегляд залишків всієї номенклатури
- Фільтри за категоріями
- Фільтри за типами м'яса
- Швидкий пошук
- Pull-to-refresh

**API Endpoints:**
- `GET /api/stock/balances` - Всі залишки
- `GET /api/nomenclature/usage-stats` - Статистика використання

**Категорії:**
- Сировина - М'ясо
- Напівфабрикати
- Готова продукція
- Спеції
- Матеріали
- Упаковка

---

### 6. Історія (History)

**Файл:** `app/(tabs)/history.tsx`

**Функціонал:**
- Журнал всіх операцій
- Фільтри за типом (Прихід/Розхід/Виробництво)
- Фільтри за періодом
- Перегляд деталей операції

**API Endpoints:**
- `GET /api/stock/movements` - Рухи з фільтрами

---

### 7. Рецепти (Recipes)

**Файли:**
- `app/recipes/index.tsx` - Список рецептів
- `app/recipes/[id].tsx` - Деталі рецепту

**Функціонал:**
- Перегляд всіх рецептів виробництва
- Деталі: інгредієнти, специї, вихід
- Використання в production модулі

**API Endpoints:**
- `GET /api/production/recipes` - Список рецептів
- `GET /api/production/recipes/:id` - Деталі рецепту

---

## 🧩 Components

### HamburgerMenu.tsx

**Призначення:** Навігаційне меню (burger icon)

**Функціонал:**
- Відображення меню з основними розділами
- Швидкий доступ до аналітики, налаштувань
- Інформація про користувача

**Використання:**
```tsx
import HamburgerMenu from '@/components/HamburgerMenu';

<HamburgerMenu />
```

---

## 🔌 Services

### api.ts

**Призначення:** Централізований API client на базі axios

**Конфігурація:**
```typescript
const api = axios.create({
  baseURL: process.env.EXPO_PUBLIC_BACKEND_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
});
```

**Interceptors:**
- Request interceptor: додавання токенів авторизації
- Response interceptor: обробка помилок

**Використання:**
```typescript
import api from '@/services/api';

const response = await api.get('/nomenclature');
const data = await api.post('/operations', payload);
```

---

## 💾 Stores

### useStore.ts (Zustand)

**Призначення:** Client-side state management

**State:**
- `selectedItems` - Вибрані елементи
- `filters` - Фільтри
- `user` - Інформація про користувача

**Actions:**
- `addItem` - Додати елемент
- `removeItem` - Видалити елемент
- `setFilters` - Встановити фільтри

**Використання:**
```typescript
import { useStore } from '@/stores/useStore';

const { selectedItems, addItem } = useStore();
```

---

## ⚙️ Configuration

### app.json

Expo конфігурація з:
- `expo.name` - Назва додатку
- `expo.slug` - URL slug
- `expo.scheme` - Deep linking scheme
- `expo.splash` - Splash screen
- `expo.ios` / `expo.android` - Platform configs
- `expo.extra` - Environment variables

### package.json

Dependencies і scripts:
```json
{
  "scripts": {
    "start": "expo start --tunnel",
    "android": "expo start --android",
    "ios": "expo start --ios"
  }
}
```

### tsconfig.json

TypeScript конфігурація з path aliases:
```json
{
  "compilerOptions": {
    "paths": {
      "@/*": ["./*"]
    }
  }
}
```

### .env

Environment variables:
```env
EXPO_PUBLIC_BACKEND_URL=https://backend-url.com
EXPO_PACKAGER_HOSTNAME=hostname
EXPO_PACKAGER_PROXY_URL=proxy-url
```

---

## 🗑️ Видалені файли

В процесі очистки видалено **3 backup файли**:

1. `app/batches/stuffing-form.tsx.backup`
2. `app/packaging/[id]-backup.tsx`
3. `app/packaging/new-batch-old.tsx`

---

## 📊 Статистика

### За модулями:

| Модуль | Екрани | Форми | Статус |
|--------|--------|-------|--------|
| Operations | 1 | 1 | ✅ |
| Butchery | 6 | 5 | ✅ |
| Production | 8 | 7 | ✅ |
| Packaging | 2 | 2 | ✅ |
| Stock | 1 | 0 | ✅ |
| History | 1 | 0 | ✅ |
| Recipes | 2 | 0 | ✅ |
| Analytics | 1 | 0 | 🚧 |

### Загальна статистика:

| Категорія | Кількість |
|-----------|-----------|
| Екрани (tabs) | 7 |
| Production forms | 7 |
| Butchery screens | 6 |
| Packaging screens | 2 |
| Recipes screens | 2 |
| Stock screens | 1 |
| Analytics screens | 1 |
| Components | 1 |
| Services | 1 |
| Stores | 1 |
| Config files | 5 |
| Utility scripts | 3 |
| **Всього** | **37** |

---

## 🎨 Design System

### Колірна палітра

**Primary:**
- Blue: `#2196F3`
- Green: `#4CAF50`
- Teal: `#009688`

**Semantic:**
- Success: `#4CAF50`
- Warning: `#FFC107`
- Error: `#F44336`
- Info: `#2196F3`

**Neutral:**
- Background: `#F5F5F5`
- Surface: `#FFFFFF`
- Text Primary: `#212121`
- Text Secondary: `#757575`

### Spacing (8pt grid)

- XS: 4px
- S: 8px
- M: 16px
- L: 24px
- XL: 32px

### Typography

**Font Sizes:**
- H1: 24px
- H2: 20px
- H3: 18px
- Body: 16px
- Caption: 14px
- Small: 12px

**Font Weights:**
- Regular: 400
- Medium: 500
- Bold: 700

### Border Radius

- Small: 4px
- Medium: 8px
- Large: 12px
- XLarge: 16px

---

## 🚀 Навігація

### File-based Routing (Expo Router)

**Приклади:**
```
app/index.tsx              → /
app/(tabs)/production.tsx  → /(tabs)/production
app/batches/[id].tsx       → /batches/123
app/batches/mix-form.tsx   → /batches/mix-form?id=123
```

### Navigation API

```typescript
import { useRouter } from 'expo-router';

const router = useRouter();

// Push
router.push('/batches/123');

// Replace
router.replace('/(tabs)/production');

// Back
router.back();

// With params
router.push({
  pathname: '/batches/[id]',
  params: { id: '123' }
});
```

---

## 🧪 Debugging

### Console Logs

Всі важливі операції логуються в консоль:
```typescript
console.log('[Production Screen] Loading recipes...');
console.log('[API Service] Using backend URL:', backendUrl);
```

### Toast Messages

Для користувацьких сповіщень:
```typescript
import Toast from 'react-native-toast-message';

Toast.show({
  type: 'success',
  text1: 'Успіх',
  text2: 'Операція виконана'
});
```

### Error Handling

Всі помилки API обробляються централізовано в `api.ts` interceptor.

---

## 📝 Best Practices

### 1. TypeScript

✅ Використовуйте типи для всіх API responses  
✅ Використовуйте interfaces для props  
✅ Уникайте `any`

### 2. State Management

✅ Server state → React Query  
✅ Client state → Zustand  
✅ Local state → useState

### 3. Navigation

✅ Використовуйте `useRouter()` hook  
✅ Не використовуйте `router.back()` без fallback  
✅ Використовуйте typed routes

### 4. API Calls

✅ Завжди обробляйте помилки  
✅ Показуйте loading states  
✅ Використовуйте React Query для кешування

### 5. Styling

✅ Використовуйте StyleSheet.create()  
✅ Використовуйте 8pt grid  
✅ Використовуйте design tokens

---

**Версія:** 1.0.0  
**Дата:** 22 листопада 2025  
**Статус:** ✅ Production Ready
