# Переміщення проекту SLAZAR в C:\slazar

## Чому переміщуємо?

Коротший шлях `C:\slazar` замість `C:\Users\Ihor\OneDrive\Appsss\bast\slazar`:
- ✅ Простіше вводити команди
- ✅ Менше проблем з пробілами в шляху
- ✅ Уникаємо синхронізації OneDrive (швидше збірка)
- ✅ Стандартизовано для всіх інструкцій

---

## Крок 1: Підготовка

### Закрийте всі програми:
- [ ] VSCode або інші редактори коду
- [ ] Термінали з відкритим проектом
- [ ] Metro Bundler (якщо запущено)
- [ ] Android Studio (якщо відкрито)

---

## Крок 2: Переміщення проекту

### Варіант А: Через Windows Explorer (рекомендовано)

1. **Відкрийте File Explorer**

2. **Перейдіть в:**
   ```
   C:\Users\Ihor\OneDrive\Appsss\bast\
   ```

3. **Знайдіть папку `slazar`**

4. **Скопіюйте папку** (Ctrl+C)

5. **Перейдіть в `C:\`**

6. **Вставте папку** (Ctrl+V)

7. **Перейменуйте якщо потрібно** щоб було `C:\slazar`

### Варіант Б: Через командний рядок

```cmd
# Відкрийте cmd як Administrator

# Перейдіть в папку з проектом
cd C:\Users\Ihor\OneDrive\Appsss\bast

# Скопіюйте всю папку в C:\
xcopy slazar C:\slazar /E /I /H /Y

# Або використайте robocopy (швидше для великих файлів)
robocopy slazar C:\slazar /E /COPYALL /R:0 /W:0
```

**Примітка:** `/E` - копіює всі підпапки, `/I` - створює директорію, `/H` - копіює приховані файли

---

## Крок 3: Перевірка

Переконайтеся, що всі файли скопійовані:

```cmd
cd C:\slazar
dir

# Ви повинні побачити:
# - backend/
# - frontend/
# - docs/
# - deploy.sh
# - deploy.bat
# - START_HERE.md
# та інші файли
```

Перевірте, що .env файли на місці:

```cmd
type backend\.env
type frontend\.env
```

---

## Крок 4: Налаштування Git (якщо використовується)

Якщо ви використовуєте Git, оновіть конфігурацію:

```cmd
cd C:\slazar

# Перевірте Git статус
git status

# Якщо є uncommitted changes, закомітьте їх
git add .
git commit -m "Move project to C:\slazar"

# Оновіть remote origin якщо потрібно
git remote -v
```

---

## Крок 5: Видалення старої копії (опціонально)

**⚠️ ВАЖЛИВО: Робіть це тільки після того, як переконалися що все працює!**

```cmd
# Видалити стару папку (БУДЬТЕ ОБЕРЕЖНІ!)
rmdir /S /Q "C:\Users\Ihor\OneDrive\Appsss\bast\slazar"
```

Або видаліть вручну через File Explorer.

---

## Крок 6: Оновлення середовища розробки

### VSCode

Якщо використовуєте VSCode:

1. Закрийте всі вікна VSCode
2. Відкрийте нову папку: `File → Open Folder → C:\slazar`
3. Налаштування середовища підхоплять автоматично

### Android Studio

Якщо працюєте з Android:

1. Закрийте Android Studio
2. Відкрийте проект: `File → Open → C:\slazar\frontend\android`

---

## Крок 7: Перевірка функціональності

### Backend:

```cmd
cd C:\slazar\backend

# Перевірте venv (якщо використовується)
# Якщо venv був в старій папці - створіть новий
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Перевірте підключення до БД
python -c "from database import get_db_connection; print('✅ OK')"
```

### Frontend:

```cmd
cd C:\slazar\frontend

# Встановіть залежності
npm install

# Перевірте .env
type .env

# Очистіть кеш Metro
npx expo start --clear
```

---

## Крок 8: Тестова збірка (опціонально)

```cmd
cd C:\slazar\frontend

# Зберіть APK для перевірки
npx expo run:android --variant debug
```

Якщо збірка пройшла успішно - все працює! ✅

---

## Можливі проблеми

### Проблема: "Access denied"

**Рішення:** Запустіть cmd як Administrator

### Проблема: "The system cannot find the path specified"

**Рішення:** Перевірте, що шляхи правильні і папки існують

### Проблема: node_modules занадто великий

**Рішення:** Не копіюйте node_modules, встановіть заново:

```cmd
# Видаліть node_modules перед копіюванням
rmdir /S /Q "C:\Users\Ihor\OneDrive\Appsss\bast\slazar\frontend\node_modules"

# Після копіювання встановіть заново
cd C:\slazar\frontend
npm install
```

### Проблема: OneDrive синхронізує нову папку

**Рішення:** Виключіть C:\slazar з синхронізації OneDrive:

1. Правий клік на іконці OneDrive в tray
2. Settings → Sync and backup → Manage backup
3. Переконайтеся що C:\slazar не в списку синхронізації

---

## Готово! 🎉

Тепер ваш проект в `C:\slazar` і всі інструкції працюють без змін!

**Наступні кроки:**
1. Відкрийте [START_HERE.md](START_HERE.md)
2. Продовжуйте налаштування сервера
3. Збірка APK

---

**Переваги нового розташування:**
- ✅ Короткий шлях: `C:\slazar`
- ✅ Немає синхронізації OneDrive
- ✅ Швидша збірка frontend
- ✅ Менше проблем з правами доступу
- ✅ Всі команди працюють без змін

**Структура:**
```
C:\slazar\
├── backend/          # Python FastAPI
├── frontend/         # React Native
├── docs/             # Документація
├── deploy.sh         # Скрипт деплою (bash)
├── deploy.bat        # Скрипт деплою (Windows)
└── START_HERE.md     # Почніть звідси
```
