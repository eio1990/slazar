# Розгортання SLAZAR Backend на віртуальній машині

## Огляд архітектури

```
┌─────────────────────┐         ┌──────────────────────────┐
│  Ваш локальний ПК   │         │  Віртуальна машина       │
│  (10.100.0.60)      │         │  (85.238.112.232)        │
│                     │         │                          │
│  - Розробка з       │         │  - Backend (port 8001)   │
│    Claude           │  SSH    │  - MS SQL Server         │
│  - Git push         ├────────►│    (port 14330)          │
│  - Команди деплою   │         │  - Python 3.11           │
│                     │         │  - FastAPI + uvicorn     │
└─────────────────────┘         └──────────────────────────┘
                                         │
                                         │ HTTP
                                         ▼
                                ┌──────────────────┐
                                │  Планшет Android │
                                │                  │
                                │  APK встановлено │
                                │  з будь-якої     │
                                │  мережі          │
                                └──────────────────┘
```

## Переваги цього підходу

✅ **Стабільність**: Backend завжди доступний на сервері
✅ **Продакшн дані**: Тестуєте на реальній БД
✅ **Незалежність**: Планшет працює з будь-якої мережі
✅ **Розробка локально**: Ви працюєте зі мною, я вношу зміни
✅ **Деплой за секунди**: Просто завантажуєте зміни на сервер

---

## Передумови

### На віртуальній машині (85.238.112.232):

- [ ] Встановлено Python 3.11+
- [ ] Встановлено Git
- [ ] Відкрито порт 8001 для HTTP
- [ ] MS SQL Server доступний на localhost:14330 або 85.238.112.232:14330
- [ ] SSH доступ (або RDP для Windows Server)

### На вашому локальному ПК:

- [ ] SSH клієнт (OpenSSH, PuTTY)
- [ ] Git встановлено
- [ ] Доступ до репозиторію проекту

---

## Крок 1: Підготовка віртуальної машини

### 1.1. Підключення до сервера

**Через SSH (якщо Linux):**
```bash
ssh ваш_користувач@85.238.112.232
```

**Через RDP (якщо Windows Server):**
```bash
mstsc /v:85.238.112.232
```

### 1.2. Перевірка Python

```bash
# Перевірте версію Python
python --version
# або
python3 --version

# Має бути 3.11 або вище
```

**Якщо Python не встановлено:**

**На Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip
```

**На CentOS/RHEL:**
```bash
sudo yum install python311 python311-pip
```

**На Windows Server:**
- Завантажте з https://www.python.org/downloads/
- Встановіть з опцією "Add to PATH"

### 1.3. Перевірка Git

```bash
git --version
```

**Якщо Git не встановлено:**

**На Linux:**
```bash
sudo apt install git  # Debian/Ubuntu
sudo yum install git  # CentOS/RHEL
```

**На Windows:**
- Завантажте з https://git-scm.com/download/win

---

## Крок 2: Клонування проекту на сервер

### 2.1. Створіть директорію для проекту

```bash
# Створіть директорію
mkdir -p /opt/slazar
cd /opt/slazar

# Або на Windows:
# mkdir C:\slazar
# cd C:\slazar
```

### 2.2. Клонуйте репозиторій

**Варіант А: Якщо проект в Git репозиторії (GitHub/GitLab):**
```bash
git clone https://github.com/ваш_користувач/slazar.git
cd slazar
```

**Варіант Б: Якщо проекту немає в Git (копіювання вручну):**

На вашому локальному ПК:
```bash
# Запакуйте проект (без node_modules, __pycache__ та ін.)
cd C:\slazar
tar -czf slazar-backend.tar.gz backend/ --exclude=backend/__pycache__ --exclude=backend/.env
```

Завантажте на сервер через SCP:
```bash
scp slazar-backend.tar.gz ваш_користувач@85.238.112.232:/opt/slazar/
```

На сервері розпакуйте:
```bash
cd /opt/slazar
tar -xzf slazar-backend.tar.gz
```

### 2.3. Альтернатива: Використання Git для синхронізації

**Рекомендую налаштувати Git репозиторій для зручності:**

На вашому локальному ПК:
```bash
cd C:\Users\Ihor\OneDrive\Appsss\bast\slazar

# Якщо ще не ініціалізовано Git репозиторій
git init
git add .
git commit -m "Initial commit"

# Додайте віддалений репозиторій (GitHub/GitLab)
# або використайте сервер як remote
```

---

## Крок 3: Налаштування Backend на сервері

### 3.1. Створіть віртуальне середовище Python

```bash
cd /opt/slazar/backend

# Створіть venv
python3 -m venv venv

# Активуйте
source venv/bin/activate  # Linux
# або
venv\Scripts\activate  # Windows
```

### 3.2. Встановіть залежності

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Можливі проблеми:**

**Якщо помилка з `pyodbc`:**
```bash
# На Ubuntu/Debian встановіть ODBC драйвер
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev

# Потім
pip install pyodbc
```

### 3.3. Створіть .env файл

```bash
cd /opt/slazar/backend
nano .env  # або vim .env, або notepad .env на Windows
```

**Вміст .env файлу:**
```env
# MS SQL Server Configuration
# Використовуйте localhost якщо SQL Server на тому ж сервері
MSSQL_SERVER=localhost,14330
# або якщо SQL на окремому сервері:
# MSSQL_SERVER=85.238.112.232,14330

MSSQL_DATABASE=SLAZAR_DB
MSSQL_USER=llm_user
MSSQL_PASSWORD=EsmerA55%lda!
MSSQL_DRIVER=ODBC Driver 18 for SQL Server

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
```

Збережіть файл:
- Nano: `Ctrl+O`, `Enter`, `Ctrl+X`
- Vim: `Esc`, `:wq`, `Enter`

### 3.4. Перевірте підключення до БД

```bash
cd /opt/slazar/backend
python -c "from database import get_db_connection; conn = get_db_connection(); print('✅ DB connection successful')"
```

Якщо успішно - побачите: `✅ DB connection successful`

---

## Крок 4: Запуск Backend на сервері

### 4.1. Тестовий запуск (вручну)

```bash
cd /opt/slazar/backend
source venv/bin/activate  # Активуйте venv якщо ще не активовано

# Запустіть uvicorn
python -m uvicorn main:app --host 0.0.0.0 --port 8001

# Ви повинні побачити:
# INFO:     Uvicorn running on http://0.0.0.0:8001
# INFO:     Application startup complete.
```

**Перевірка з локального ПК:**

На вашому комп'ютері відкрийте браузер:
```
http://85.238.112.232:8001/docs
```

Ви повинні побачити Swagger документацію API.

**Якщо не відкривається - перевірте firewall:**

**На Linux (UFW):**
```bash
sudo ufw allow 8001/tcp
sudo ufw status
```

**На Linux (firewalld):**
```bash
sudo firewall-cmd --permanent --add-port=8001/tcp
sudo firewall-cmd --reload
```

**На Windows Server:**
```powershell
New-NetFirewallRule -DisplayName "SLAZAR API" -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow
```

### 4.2. Налаштування автозапуску (systemd на Linux)

**Створіть systemd service:**

```bash
sudo nano /etc/systemd/system/slazar-backend.service
```

**Вміст файлу:**
```ini
[Unit]
Description=SLAZAR Backend API
After=network.target mssql-server.service

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

**Замініть `ваш_користувач`** на реального користувача (наприклад, `root`, `ubuntu`, `admin`).

**Активуйте сервіс:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable slazar-backend
sudo systemctl start slazar-backend

# Перевірте статус
sudo systemctl status slazar-backend
```

**Корисні команди:**
```bash
# Перезапустити
sudo systemctl restart slazar-backend

# Зупинити
sudo systemctl stop slazar-backend

# Логи
sudo journalctl -u slazar-backend -f
```

### 4.3. Налаштування автозапуску (Windows Service)

**Використайте NSSM (Non-Sucking Service Manager):**

1. Завантажте NSSM: https://nssm.cc/download
2. Розпакуйте в `C:\nssm`
3. Встановіть сервіс:

```cmd
cd C:\nssm\win64
nssm install SlazarBackend "C:\slazar\backend\venv\Scripts\python.exe" "-m uvicorn main:app --host 0.0.0.0 --port 8001"
nssm set SlazarBackend AppDirectory C:\slazar\backend
nssm start SlazarBackend
```

**Перевірити статус:**
```cmd
nssm status SlazarBackend
```

---

## Крок 5: Налаштування Frontend для роботи з сервером

### На вашому локальному ПК:

Оновіть `frontend/.env`:

```env
# Backend API URL - віртуальна машина
EXPO_PUBLIC_BACKEND_URL=http://85.238.112.232:8001
```

**Збережіть файл.**

---

## Крок 6: Процес розробки та деплою

### Робочий процес:

```
┌─────────────────────────────────────────────────────────┐
│  1. Ви працюєте зі мною (Claude) локально               │
│  2. Я вношу зміни в код                                 │
│  3. Ви тестуєте зміни локально (опціонально)            │
│  4. Ви завантажуєте зміни на сервер                     │
│  5. Перезапускаєте backend на сервері                   │
│  6. Тестуєте на планшеті                                │
└─────────────────────────────────────────────────────────┘
```

### 6.1. Після того, як я вніс зміни в код:

**Варіант А: Через Git (рекомендовано):**

На локальному ПК:
```bash
cd C:\Users\Ihor\OneDrive\Appsss\bast\slazar

# Закоммітьте зміни
git add backend/
git commit -m "Fix: виправлення помилки в модулі виробництва"
git push origin main
```

На сервері:
```bash
cd /opt/slazar
git pull origin main

# Перезапустіть backend
sudo systemctl restart slazar-backend

# Або якщо без systemd:
pkill -f uvicorn
cd backend
source venv/bin/activate
python -m uvicorn main:app --host 0.0.0.0 --port 8001 &
```

**Варіант Б: Через SCP (копіювання файлів):**

На локальному ПК:
```bash
# Скопіюйте конкретний файл
scp C:\slazar\backend\routes\production.py ваш_користувач@85.238.112.232:/opt/slazar/backend/routes/

# Або всю папку backend
scp -r C:\slazar\backend\ ваш_користувач@85.238.112.232:/opt/slazar/
```

На сервері:
```bash
sudo systemctl restart slazar-backend
```

**Варіант В: Синхронізація через rsync (найшвидший):**

На локальному ПК:
```bash
rsync -avz --exclude='__pycache__' --exclude='.env' \
  C:\slazar\backend/ \
  ваш_користувач@85.238.112.232:/opt/slazar/backend/
```

### 6.2. Швидкий деплой (створіть скрипт)

**На локальному ПК створіть файл `deploy.sh`:**

```bash
#!/bin/bash
echo "📦 Деплой SLAZAR backend на сервер..."

# Закомітьте зміни
git add backend/
git commit -m "Deploy: $(date '+%Y-%m-%d %H:%M:%S')"

# Завантажте на сервер
ssh ваш_користувач@85.238.112.232 << 'ENDSSH'
  cd /opt/slazar
  git pull origin main
  sudo systemctl restart slazar-backend
  echo "✅ Backend перезапущено"
ENDSSH

echo "✅ Деплой завершено!"
```

Зробіть виконуваним:
```bash
chmod +x deploy.sh
```

Використовуйте:
```bash
./deploy.sh
```

---

## Крок 7: Збірка та тестування APK

### 7.1. Збірка APK на локальному ПК:

```bash
cd C:\slazar\frontend

# Переконайтеся, що .env налаштовано на сервер
cat .env
# EXPO_PUBLIC_BACKEND_URL=http://85.238.112.232:8001

# Зберіть APK
npx expo run:android --variant release
```

APK буде в:
```
C:\slazar\frontend\android\app\build\outputs\apk\release\app-release.apk
```

### 7.2. Встановлення на планшет:

**Варіант 1: Через USB:**
```bash
adb install frontend\android\app\build\outputs\apk\release\app-release.apk
```

**Варіант 2: Скопіюйте APK файл:**
- Через Google Drive
- Через USB кабель
- Через Email

### 7.3. Тестування:

Відкрийте застосунок на планшеті - він автоматично під'єднається до `http://85.238.112.232:8001`.

---

## Крок 8: Моніторинг та відлагодження

### 8.1. Перегляд логів backend:

**На сервері:**
```bash
# Якщо використовується systemd
sudo journalctl -u slazar-backend -f

# Або якщо запущено вручну
tail -f /opt/slazar/backend/logs/app.log
```

### 8.2. Перевірка статусу:

```bash
# Перевірте, чи працює процес
ps aux | grep uvicorn

# Перевірте порт
netstat -tulpn | grep 8001
# або
ss -tulpn | grep 8001
```

### 8.3. Перезапуск при помилках:

```bash
sudo systemctl restart slazar-backend
sudo systemctl status slazar-backend
```

---

## Крок 9: Робочий цикл "Баг → Виправлення → Тест"

### Типовий сценарій:

1. **Ви тестуєте на планшеті** і знаходите баг
2. **Повідомляєте мені** про проблему
3. **Я аналізую** код і знаходжу помилку
4. **Я виправляю** код локально на вашому ПК
5. **Ви деплоїте** на сервер:
   ```bash
   ./deploy.sh
   ```
6. **Ви повторюєте тест** на планшеті
7. Повторюєте цикл до повного виправлення

---

## Чеклист готовності

### На сервері (85.238.112.232):
- [ ] Python 3.11+ встановлено
- [ ] Git встановлено (опціонально)
- [ ] Проект склоновано в `/opt/slazar`
- [ ] Створено venv і встановлено залежності
- [ ] Файл `.env` налаштовано
- [ ] Підключення до БД працює
- [ ] Порт 8001 відкрито в firewall
- [ ] Backend запущено і доступний
- [ ] Systemd service налаштовано (опціонально)

### На локальному ПК:
- [ ] Git налаштовано для синхронізації
- [ ] SSH доступ до сервера працює
- [ ] `frontend/.env` вказує на `http://85.238.112.232:8001`
- [ ] APK зібрано
- [ ] Скрипт деплою `deploy.sh` створено (опціонально)

### На планшеті:
- [ ] APK встановлено
- [ ] Застосунок під'єднується до backend
- [ ] Можна завантажити список номенклатури (тест з'єднання)

---

## Готово! 🚀

Тепер у вас повністю налаштоване середовище:

✅ **Backend працює на сервері** 24/7
✅ **Ви працюєте зі мною локально** - я вношу зміни
✅ **Деплой за 10 секунд** - `./deploy.sh`
✅ **Тестуєте на планшеті** з будь-якої мережі
✅ **Реальна БД** - всі операції записуються

**Цикл розробки:**
```
Баг → Повідомлення мені → Я виправляю → Деплой → Тест → ✅
```

Успішної роботи! 🎯
