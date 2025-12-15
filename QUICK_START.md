# SLAZAR - Швидкий старт для тестування

## 🎯 Ціль

Ви працюєте зі мною (Claude) локально на вашому ПК, я вношу зміни в код.
Backend працює на віртуальній машині (85.238.112.232).
Ви тестуєте на планшеті з будь-якої мережі.

## 📋 Що потрібно зробити один раз

### 1. Налаштувати сервер (85.238.112.232)

**Див. детальну інструкцію:** [DEPLOY_TO_SERVER.md](DEPLOY_TO_SERVER.md)

**Коротко:**
```bash
# Підключитися до сервера
ssh ваш_користувач@85.238.112.232

# Створити директорію
sudo mkdir -p /opt/slazar
sudo chown ваш_користувач:ваш_користувач /opt/slazar

# Встановити Python 3.11+
python3 --version

# Відкрити порт 8001
sudo ufw allow 8001/tcp
# або
sudo firewall-cmd --permanent --add-port=8001/tcp && sudo firewall-cmd --reload
```

### 2. Завантажити проект на сервер

**Варіант А: Вручну (перший раз):**
```bash
# На локальному ПК
cd C:\slazar
tar -czf slazar-initial.tar.gz backend/ --exclude=backend/__pycache__ --exclude=backend/venv

# Завантажити
scp slazar-initial.tar.gz ваш_користувач@85.238.112.232:/opt/slazar/

# На сервері розпакувати
ssh ваш_користувач@85.238.112.232
cd /opt/slazar
tar -xzf slazar-initial.tar.gz
```

### 3. Налаштувати backend на сервері

```bash
# Підключитися до сервера
ssh ваш_користувач@85.238.112.232

cd /opt/slazar/backend

# Створити venv
python3 -m venv venv
source venv/bin/activate

# Встановити залежності
pip install -r requirements.txt

# Створити .env
nano .env
```

**Вміст .env:**
```env
MSSQL_SERVER=localhost,14330
MSSQL_DATABASE=SLAZAR_DB
MSSQL_USER=llm_user
MSSQL_PASSWORD=EsmerA55%lda!
MSSQL_DRIVER=ODBC Driver 18 for SQL Server
API_HOST=0.0.0.0
API_PORT=8001
```

### 4. Налаштувати автозапуск (systemd)

```bash
# Створити сервіс
sudo nano /etc/systemd/system/slazar-backend.service
```

**Вміст файлу** (замініть `ваш_користувач`):
```ini
[Unit]
Description=SLAZAR Backend API
After=network.target

[Service]
Type=simple
User=ваш_користувач
WorkingDirectory=/opt/slazar/backend
Environment="PATH=/opt/slazar/backend/venv/bin"
ExecStart=/opt/slazar/backend/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Запустити:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable slazar-backend
sudo systemctl start slazar-backend
sudo systemctl status slazar-backend
```

### 5. Перевірити доступність

На локальному ПК відкрийте в браузері:
```
http://85.238.112.232:8001/docs
```

Має відкритися Swagger UI з документацією API.

---

## 🚀 Щоденна робота

### Сценарій 1: Я (Claude) виправив баг

1. **Ви бачите зміни** які я вніс в код (локально на вашому ПК)
2. **Ви деплоїте на сервер:**

**Windows:**
```cmd
deploy.bat
```

**Linux/macOS/Git Bash:**
```bash
chmod +x deploy.sh
./deploy.sh
```

3. **Backend автоматично перезапускається** на сервері
4. **Ви тестуєте на планшеті**

### Сценарій 2: Ручний деплой (без скрипта)

```bash
# 1. Створіть архів
tar -czf backend.tar.gz backend/ --exclude=backend/__pycache__ --exclude=backend/venv

# 2. Завантажте
scp backend.tar.gz ваш_користувач@85.238.112.232:/opt/slazar/

# 3. Розгорніть і перезапустіть
ssh ваш_користувач@85.238.112.232 "cd /opt/slazar && tar -xzf backend.tar.gz && sudo systemctl restart slazar-backend"
```

### Сценарій 3: Тестування на планшеті

**Збірка APK (перший раз або після змін frontend):**
```bash
cd C:\slazar\frontend

# Переконайтеся, що .env вказує на сервер
# EXPO_PUBLIC_BACKEND_URL=http://85.238.112.232:8001

# Зберіть APK
npx expo run:android --variant release

# APK буде тут:
# C:\slazar\frontend\android\app\build\outputs\apk\release\app-release.apk
```

**Встановлення на планшет:**
- Скопіюйте APK на планшет (через USB, Google Drive, Email)
- Встановіть APK
- Запустіть застосунок

**Тестування:**
- Відкрийте застосунок
- Він автоматично під'єднається до `http://85.238.112.232:8001`
- Тестуйте функціонал
- Якщо знайшли баг - повідомте мені

---

## 🔍 Корисні команди

### Перевірка статусу backend на сервері

```bash
ssh ваш_користувач@85.238.112.232 "sudo systemctl status slazar-backend"
```

### Перегляд логів backend

```bash
ssh ваш_користувач@85.238.112.232 "sudo journalctl -u slazar-backend -f"
```

### Перезапуск backend

```bash
ssh ваш_користувач@85.238.112.232 "sudo systemctl restart slazar-backend"
```

### Зупинка backend

```bash
ssh ваш_користувач@85.238.112.232 "sudo systemctl stop slazar-backend"
```

### Перевірка підключення до БД

```bash
ssh ваш_користувач@85.238.112.232 "cd /opt/slazar/backend && source venv/bin/activate && python -c 'from database import get_db_connection; get_db_connection(); print(\"✅ OK\")'"
```

---

## 🐛 Типовий цикл виправлення багу

```
1. Ви тестуєте на планшеті
   └─> Знаходите баг

2. Повідомляєте мені про баг
   └─> "Модуль: Виробництво
       Екран: Створення партії
       Дія: Натиснув 'Створити'
       Помилка: 500 Internal Server Error"

3. Я аналізую код
   └─> Знаходжу проблему
   └─> Вношу виправлення локально

4. Ви деплоїте на сервер
   └─> deploy.bat (або deploy.sh)
   └─> Займає ~10 секунд

5. Ви повторюєте тест на планшеті
   └─> Баг виправлено ✅
   └─> або продовжуємо діагностику
```

---

## 📝 Чеклист перед початком тестування

**На сервері (85.238.112.232):**
- [ ] Python 3.11+ встановлено
- [ ] Проект в `/opt/slazar/backend`
- [ ] Venv створено, залежності встановлено
- [ ] Файл `.env` налаштовано
- [ ] Порт 8001 відкрито
- [ ] Systemd service налаштовано і запущено
- [ ] Backend доступний: `http://85.238.112.232:8001/docs`

**На локальному ПК:**
- [ ] SSH доступ до сервера працює
- [ ] Скрипт деплою налаштовано (`deploy.bat` або `deploy.sh`)
- [ ] `frontend/.env` вказує на `http://85.238.112.232:8001`

**На планшеті:**
- [ ] APK зібрано і встановлено
- [ ] Застосунок під'єднується до backend
- [ ] Можна завантажити дані (тест з'єднання)

---

## 🎯 Готово до роботи!

**Робочий процес:**
```
Тест → Баг → Повідомлення → Виправлення → Деплой (10 сек) → Тест → ✅
```

**Ви працюєте зі мною локально** - я швидко вношу зміни
**Backend на сервері** - завжди доступний
**Планшет тестує** - з будь-якої мережі

Успіхів! 🚀
