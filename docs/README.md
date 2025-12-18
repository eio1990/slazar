# Документація проекту SLAZAR

**Система управління м'ясним виробництвом**

---

## 📚 Загальна документація

### [database-schema.md](database-schema.md) (50 KB)
Повна схема бази даних MS SQL Server з описом всіх 27 таблиць, індексів, зв'язків та бізнес-правил.

### [project-audit.md](project-audit.md) (45 KB)
Аудит проекту з аналізом архітектури, коду, бази даних та виявленими проблемами.

---

## 🎯 Технічні завдання модулів

### 1. [BUTCHERY_SPECIFICATION.md](BUTCHERY_SPECIFICATION.md) (20 KB) - **Розділка**
### 2. [PRODUCTION_SPECIFICATION.md](PRODUCTION_SPECIFICATION.md) (32 KB) - **Виробництво**
### 3. [PACKAGING_SPECIFICATION.md](PACKAGING_SPECIFICATION.md) (31 KB) - **Фасування**
### 4. [INVENTORY_SPECIFICATION.md](INVENTORY_SPECIFICATION.md) (40 KB) - **Інвентаризація** ⭐ NEW

---

## 📖 Структура документації

```
docs/
├── README.md                          # Індекс документації
├── database-schema.md                 # Схема БД (50 KB)
├── project-audit.md                   # Аудит (45 KB)
├── BUTCHERY_SPECIFICATION.md          # ТЗ розділки (20 KB)
├── PRODUCTION_SPECIFICATION.md        # ТЗ виробництва (32 KB)
├── PACKAGING_SPECIFICATION.md         # ТЗ фасування (31 KB)
└── INVENTORY_SPECIFICATION.md         # ТЗ інвентаризації (40 KB)
```

---

## 📊 Статистика

| Документ | Розмір | Таблиць | Endpoints | Екранів |
|----------|--------|---------|-----------|---------|
| BUTCHERY_SPECIFICATION | 20 KB | 4 | 5 | 6 |
| PRODUCTION_SPECIFICATION | 32 KB | 8 | 9 | 8 |
| PACKAGING_SPECIFICATION | 31 KB | 6 | 8 | 6 |
| INVENTORY_SPECIFICATION | 40 KB | 6 | 10 | 7 |
| **Всього** | **123 KB** | **24** | **32** | **27** |

Разом з database-schema.md і project-audit.md: **218 KB** документації

---

## 🔗 Інші документи

- [claude.md](../claude.md) - Головна технічна специфікація
- [backend/BACKEND_STRUCTURE.md](../backend/BACKEND_STRUCTURE.md) - Backend API
- [frontend/FRONTEND_STRUCTURE.md](../frontend/FRONTEND_STRUCTURE.md) - Frontend структура

---

**Оновлено:** 18 грудня 2025
