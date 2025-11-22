# 📱 Frontend - Meat Production Management App

**React Native мобільний додаток для управління м'ясним виробництвом**

[![Expo](https://img.shields.io/badge/Expo-SDK%2052-blue)]()
[![React Native](https://img.shields.io/badge/React%20Native-Latest-61DAFB)]()
[![TypeScript](https://img.shields.io/badge/TypeScript-5.x-3178C6)]()

---

## 🎯 Огляд

Кросплатформений мобільний додаток (iOS + Android) для управління повним циклом виробництва м'ясної продукції.

**Основні модулі:**
- 📦 **Операції** - Прихід/Розхід сировини та матеріалів
- 🔪 **Різання** - Розділка туш на напівфабрикати
- 🥓 **Виробництво** - Виробництво готової продукції за рецептами
- 📦 **Фасування** - Упаковка в SKU (вакуум, скін, вагова)
- 📊 **Склад** - Перегляд залишків
- 📜 **Історія** - Журнал всіх операцій
- 📈 **Аналітика** - Статистика виробництва

---

## 🛠 Технології

### Core
- **Expo SDK 52** - React Native framework
- **React Native** - Mobile UI framework
- **TypeScript** - Статична типізація
- **Expo Router v6** - File-based routing

### State Management
- **TanStack Query (React Query)** - Server state management
- **Zustand** - Client state management
- **React Native MMKV** - Швидке локальне сховище

### Networking
- **axios** - HTTP клієнт
- **NetInfo** - Моніторинг підключення до мережі

### UI/UX
- **React Native Toast Message** - Сповіщення
- **Expo Linear Gradient** - Градієнти
- **React Native Safe Area Context** - Safe areas

---

## 📁 Структура проекту

```
/app/frontend/
├── app/
│   ├── (tabs)/                    # Tab navigation screens
│   │   ├── _layout.tsx            # Tabs layout
│   │   ├── index.tsx              # Операції (Прихід/Розхід)
│   │   ├── operations.tsx         # Операції (deprecated, redirect)
│   │   ├── butchery.tsx           # Різання
│   │   ├── production.tsx         # Виробництво
│   │   ├── packaging.tsx          # Фасування
│   │   ├── inventory.tsx          # Склад (Залишки)
│   │   └── history.tsx            # Історія
│   │
│   ├── batches/                   # Production module
│   │   ├── [id].tsx               # Деталі партії виробництва
│   │   ├── salting-form.tsx       # Етап: Засолка
│   │   ├── mix-form.tsx           # Етап: Замішування
│   │   ├── stuffing-form.tsx      # Етап: Набивка
│   │   ├── sugar-form.tsx         # Етап: Цукор
│   │   ├── marinade-form.tsx      # Етап: Маринад
│   │   ├── massage-form.tsx       # Етап: Масаж
│   │   └── trim-form.tsx          # Етап: Обрізка
│   │
│   ├── butchery/                  # Butchery module
│   │   ├── select-meat-type.tsx   # Вибір типу м'яса
│   │   ├── select-grade.tsx       # Вибір ґатунку
│   │   ├── select-recipe.tsx      # Вибір рецепту розділки
│   │   ├── input-weight.tsx       # Введення ваги
│   │   ├── complete-form.tsx      # Завершення розділки
│   │   └── [id].tsx               # Деталі операції розділки
│   │
│   ├── packaging/                 # Packaging module
│   │   ├── new-session.tsx        # Створення нової сесії
│   │   └── [id].tsx               # Деталі сесії фасування
│   │
│   ├── recipes/                   # Recipes module
│   │   ├── index.tsx              # Список рецептів
│   │   └── [id].tsx               # Деталі рецепту
│   │
│   ├── stock/                     # Stock module
│   │   └── index.tsx              # Залишки на складі
│   │
│   ├── analytics/                 # Analytics module
│   │   └── index.tsx              # Аналітика (заглушка)
│   │
│   ├── _layout.tsx                # Root layout
│   └── index.tsx                  # Entry point
│
├── components/
│   └── HamburgerMenu.tsx          # Навігаційне меню
│
├── services/
│   └── api.ts                     # API клієнт (axios)
│
├── stores/
│   └── useStore.ts                # Zustand store
│
├── app.json                       # Expo конфігурація
├── package.json                   # Dependencies
├── tsconfig.json                  # TypeScript config
├── metro.config.js                # Metro bundler config
├── eslint.config.js               # ESLint config
├── .env                           # Environment variables
│
└── Utility scripts:
    ├── check_expo_url.js          # Перевірка Expo URL
    ├── generate_qr.js             # Генерація QR кода
    └── generate_correct_qr.js     # Генерація коректного QR
```

---

## 🚀 Запуск

### 1. Встановлення залежностей

```bash
cd /app/frontend
yarn install
```

### 2. Запуск Development Server

```bash
# Через Expo CLI
expo start --tunnel

# Або через yarn
yarn start
```

### 3. Запуск через Supervisor (Docker)

```bash
sudo supervisorctl restart expo
```

### 4. Відкриття в Expo Go

Скануйте QR код в терміналі через Expo Go app на вашому телефоні.

Або згенеруйте QR код:
```bash
node generate_correct_qr.js
```

---

## 📱 Навігація

### Tab Navigation

Додаток використовує **bottom tab navigation** з 6 основними екранами:

| Tab | Назва | Іконка | Функціонал |
|-----|-------|--------|-----------|
| 1 | Операції | 📦 | Прихід/Розхід матеріалів |
| 2 | Різання | 🔪 | Розділка туш |
| 3 | Виробництво | 🥓 | Створення партій |
| 4 | Фасування | 📦 | Упаковка в SKU |
| 5 | Склад | 📊 | Залишки |
| 6 | Історія | 📜 | Журнал операцій |

### Модульна навігація

Кожен модуль має власну навігацію з використанням **Stack Navigator** (через Expo Router):

**Приклад (Production):**
```
/production (tab) → /batches/new → /batches/[id] → /batches/[id]/salting-form
```

---

## 🔌 API Integration

### Конфігурація

API URL визначається через environment variables в `.env`:

```env
EXPO_PUBLIC_BACKEND_URL=https://your-backend-url.com
```

### API Client

Всі запити проходять через централізований API клієнт (`services/api.ts`):

```typescript
import api from '@/services/api';

// GET request
const { data } = await api.get('/nomenclature');

// POST request
await api.post('/operations', { type: 'receipt', ... });
```

### Endpoints

**Nomenclature:**
- `GET /api/nomenclature` - Список номенклатури
- `GET /api/nomenclature/categories` - Категорії

**Stock:**
- `GET /api/stock/balances` - Залишки
- `GET /api/stock/movements` - Рухи

**Production:**
- `GET /api/production/recipes` - Рецепти
- `POST /api/production/batches` - Створити партію
- `GET /api/production/batches/:id` - Деталі партії
- `POST /api/production/batches/:id/salt` - Засолка
- `POST /api/production/batches/:id/complete` - Завершити

**Packaging:**
- `POST /api/packaging/sessions` - Створити сесію
- `GET /api/packaging/sessions/:id` - Деталі сесії
- `POST /api/packaging/sessions/:id/outputs` - Додати вихід
- `POST /api/packaging/sessions/:id/complete` - Завершити

**Butchery:**
- `GET /api/butchery/recipes` - Рецепти розділки
- `POST /api/butchery/operations` - Створити операцію
- `POST /api/butchery/operations/:id/complete` - Завершити

---

## 💾 State Management

### Server State (TanStack Query)

Для роботи з серверними даними використовується **React Query**:

```typescript
const { data, isLoading } = useQuery({
  queryKey: ['nomenclature'],
  queryFn: () => api.get('/nomenclature')
});
```

**Переваги:**
- Автоматичне кешування
- Background refetch
- Optimistic updates
- Error handling

### Client State (Zustand)

Для локального стану використовується **Zustand** (`stores/useStore.ts`):

```typescript
const { selectedItems, addItem } = useStore();
```

---

## 🎨 UI Components

### Основні компоненти

**React Native Core:**
- `View`, `Text`, `ScrollView`, `FlatList`
- `TouchableOpacity`, `Pressable`
- `TextInput`
- `ActivityIndicator`

**Custom Components:**
- `HamburgerMenu` - Навігаційне меню

**Third-party:**
- `Toast` (react-native-toast-message) - Сповіщення
- `LinearGradient` (expo-linear-gradient) - Градієнти

### Styling

Стилізація виконується за допомогою **StyleSheet API**:

```typescript
const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
  }
});
```

**Design System:**
- Колірна схема: синьо-зелена палітра
- Відступи: 8pt grid (8, 16, 24, 32)
- Border radius: 8px, 12px
- Тіні: elevation / shadowOpacity

---

## 📝 TypeScript

Проект повністю типізований з TypeScript.

### Типи API

```typescript
interface NomenclatureItem {
  id: number;
  name: string;
  category: string;
  unit: string;
  precision_digits: number;
}

interface Batch {
  id: number;
  recipe_id: number;
  total_weight: number;
  status: 'created' | 'salt' | 'mix' | 'stuff' | 'dry' | 'completed';
  created_at: string;
}
```

---

## 🗑️ Видалені файлы

В процесі очистки видалено **3 backup файли**:

- `app/batches/stuffing-form.tsx.backup`
- `app/packaging/[id]-backup.tsx`
- `app/packaging/new-batch-old.tsx`

---

## 🧪 Тестування

### Manual Testing

Додаток тестується вручну через Expo Go на реальних пристроях:

1. iOS (iPhone 12/13/14)
2. Android (Samsung Galaxy S21)

### Debugging

```bash
# Перевірити Expo URL
node check_expo_url.js

# Згенерувати QR код для тестування
node generate_correct_qr.js
```

---

## 📦 Dependencies

### Main Dependencies

```json
{
  "expo": "~52.0.0",
  "expo-router": "^6.0.0",
  "react": "18.3.1",
  "react-native": "0.76.0",
  "axios": "^1.7.2",
  "@tanstack/react-query": "^5.51.11",
  "zustand": "^4.5.4",
  "react-native-mmkv": "^3.0.2",
  "react-native-toast-message": "^2.2.1"
}
```

### Dev Dependencies

```json
{
  "typescript": "~5.3.3",
  "@types/react": "~18.3.3",
  "eslint": "^9.6.0"
}
```

---

## 🔧 Configuration Files

### app.json
Expo configuration з routing, splash screen, navigation bar.

### tsconfig.json
TypeScript configuration з path aliases:
```json
{
  "paths": {
    "@/*": ["./*"]
  }
}
```

### metro.config.js
Metro bundler configuration для Expo Router.

### .env
Environment variables:
```env
EXPO_PUBLIC_BACKEND_URL=https://backend-url.com
EXPO_PACKAGER_HOSTNAME=hostname
EXPO_PACKAGER_PROXY_URL=proxy-url
```

---

## 📊 Статистика

| Категорія | Кількість |
|-----------|-----------|
| Екрани (tabs) | 7 |
| Production forms | 8 |
| Butchery screens | 6 |
| Packaging screens | 2 |
| Components | 1 |
| Services | 1 |
| Stores | 1 |
| **Всього актуальних** | **26** |
| Видалено backup | 3 |

---

## 🚨 Важливі примітки

### Expo Router

Проект використовує **file-based routing**. Кожен файл в папці `app/` автоматично стає route.

**Приклади:**
- `app/index.tsx` → `/`
- `app/(tabs)/production.tsx` → `/(tabs)/production`
- `app/batches/[id].tsx` → `/batches/123`

### Navigation

Навігація виконується через `useRouter()` hook:

```typescript
import { useRouter } from 'expo-router';

const router = useRouter();
router.push('/batches/123');
router.back();
```

### Environment Variables

Всі environment variables повинні мати префікс `EXPO_PUBLIC_` для доступу на клієнті:

```typescript
const backendUrl = process.env.EXPO_PUBLIC_BACKEND_URL;
```

---

## 🔗 Корисні посилання

- [Expo Documentation](https://docs.expo.dev/)
- [Expo Router](https://expo.github.io/router/)
- [React Native](https://reactnative.dev/)
- [TanStack Query](https://tanstack.com/query/latest)

---

**Версія:** 1.0.0  
**Дата оновлення:** 22 листопада 2025  
**Статус:** ✅ Production Ready
