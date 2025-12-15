# 📚 Документація SLAZAR

Центральний індекс всієї документації проекту.

---

## 🚀 Початок роботи

### Для тестування на планшеті:

0. **[MOVE_TO_C_DRIVE.md](MOVE_TO_C_DRIVE.md)** ⚠️ **ПОЧНІТЬ ЗВІДСИ**
   - Переміщення проекту в C:\slazar
   - Займе 5 хвилин
   - Обов'язково перед початком роботи

1. **[START_HERE.md](START_HERE.md)** - Головна точка входу
   - Швидкий огляд що готово
   - Що потрібно зробити
   - Чеклисти

2. **[QUICK_START.md](QUICK_START.md)** - Швидкий старт за 5 хвилин
   - Що потрібно зробити один раз
   - Щоденна робота
   - Цикл виправлення багів

3. **[DEPLOY_TO_SERVER.md](DEPLOY_TO_SERVER.md)** - Детальна інструкція деплою
   - Повне налаштування віртуальної машини
   - Крок за кроком з поясненнями
   - Troubleshooting

4. **[TESTING_SETUP.md](TESTING_SETUP.md)** - Альтернативні варіанти тестування
   - Локальна мережа
   - Ngrok тунель
   - Збірка APK

---

## 📖 Проектна документація

### Загальний огляд:

5. **[claude.md](claude.md)** - Головна документація для Claude
   - Архітектура проекту
   - Технологічний стек
   - Бізнес-правила
   - Стандарти коду

6. **[README.md](README.md)** - Опис проекту
   - Що таке SLAZAR
   - Основні можливості
   - Структура проекту

### База даних:

7. **[docs/database-schema.md](docs/database-schema.md)** - Архітектура БД
   - 27 таблиць з описами
   - Діаграми зв'язків
   - Бізнес-правила
   - SQL приклади

### Аудит та якість:

8. **[docs/project-audit.md](docs/project-audit.md)** - Аналіз якості коду
   - Оцінка 6.8/10
   - Критичні проблеми
   - План виправлень (4 тижні)
   - Рекомендації

---

## 🔧 Допоміжні файли

### Скрипти деплою:

- **[deploy.sh](deploy.sh)** - Bash скрипт деплою (Linux/macOS/Git Bash)
- **[deploy.bat](deploy.bat)** - Batch скрипт деплою (Windows)

### Конфігурація:

- **[.claudeignore](.claudeignore)** - Файли для ігнорування Claude
- **[.gitignore](.gitignore)** - Файли для ігнорування Git

---

## 🎯 Швидка навігація

### Перший раз відкриваю проект:
→ **[MOVE_TO_C_DRIVE.md](MOVE_TO_C_DRIVE.md)** ⚠️ Перемістити в C:\slazar
→ **[START_HERE.md](START_HERE.md)** Почати звідси

### Хочу почати тестувати на планшеті:
→ [QUICK_START.md](QUICK_START.md)

### Хочу налаштувати сервер з нуля:
→ [DEPLOY_TO_SERVER.md](DEPLOY_TO_SERVER.md)

### Хочу зрозуміти структуру БД:
→ [docs/database-schema.md](docs/database-schema.md)

### Хочу побачити проблеми в коді:
→ [docs/project-audit.md](docs/project-audit.md)

### Хочу зрозуміти бізнес-логіку:
→ [claude.md](claude.md)

---

## 📊 Структура документації

```
C:\slazar\                  # ⚠️ Проект має бути тут!
├── MOVE_TO_C_DRIVE.md      # Інструкція переміщення
├── START_HERE.md           # ⭐ Почніть звідси!
├── QUICK_START.md          # Швидкий старт
├── DEPLOY_TO_SERVER.md     # Детальний деплой
├── TESTING_SETUP.md        # Альтернативи
├── DOCS_INDEX.md           # Цей файл
├── claude.md               # Для Claude
├── README.md               # Опис проекту
├── deploy.sh / deploy.bat  # Скрипти деплою
│
├── docs/
│   ├── database-schema.md  # 27 таблиць БД
│   └── project-audit.md    # Аналіз якості
│
├── backend/
│   ├── .env                # Конфігурація БД
│   ├── main.py             # FastAPI entry point
│   ├── database.py         # DB connection
│   ├── routes/             # API endpoints
│   └── requirements.txt    # Python dependencies
│
└── frontend/
    ├── .env                # Backend URL
    ├── app/                # React Native screens
    ├── components/         # UI компоненти
    ├── services/           # API клієнти
    └── package.json        # Node dependencies
```

---

## 🔗 Зовнішні ресурси

- **MS SQL Server:** 85.238.112.232:14330
- **Backend API:** http://85.238.112.232:8001
- **Swagger Docs:** http://85.238.112.232:8001/docs
- **База даних:** SLAZAR_DB

---

## ❓ Часті питання

### Як швидко задеплоїти зміни?
```bash
./deploy.sh  # або deploy.bat
```

### Як перевірити статус backend?
```bash
ssh user@85.238.112.232 "sudo systemctl status slazar-backend"
```

### Як переглянути логи?
```bash
ssh user@85.238.112.232 "sudo journalctl -u slazar-backend -f"
```

### Як зібрати новий APK?
```bash
cd frontend
npx expo run:android --variant release
```

### Де знаходиться APK після збірки?
```
frontend/android/app/build/outputs/apk/release/app-release.apk
```

---

## 🎓 Навчальні матеріали

### Модулі системи:

1. **Номенклатура та склад** (3 таблиці)
   - Довідник позицій
   - Облік залишків
   - Рухи по складу

2. **Рецепти** (4 таблиці)
   - Інгредієнти
   - Спеції
   - Технологічні етапи

3. **Виробництво** (4 таблиці)
   - Партії виробництва
   - Етапи обробки
   - Облік відходів

4. **Фасування** (9 таблиць: 5 актуальних + 4 legacy)
   - Сесії фасування
   - Облік матеріалів
   - Залишки та брак

5. **Розділка туш** (3 таблиці)
   - Рецепти розділки
   - Полуфабрикати
   - Облік відходів

6. **Інвентаризація** (2 таблиці)
   - Сесії інвентаризації
   - Коригування залишків

7. **Аудит** (1 таблиця)
   - Логування змін
   - Безпека

---

## 📞 Підтримка

**Працюєте зі мною (Claude):**
- Повідомляйте про баги
- Я аналізую код
- Вношу виправлення
- Ви деплоїте
- Тестуєте знову

**Цикл:**
```
Баг → Аналіз → Виправлення → Деплой → Тест → ✅
```

---

**Оновлено:** 15 грудня 2025
