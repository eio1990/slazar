# Клонування SLAZAR на віртуальну машину

## ✅ Готово на GitHub

Проект вже запушено на GitHub:
**https://github.com/eio1990/slazar**

---

## 📋 Інструкція для віртуальної машини

### Крок 1: Підключення до сервера

```bash
# Через RDP (Windows Server) або SSH (Linux)
ssh ваш_користувач@85.238.112.232
# або
mstsc /v:85.238.112.232
```

---

### Крок 2: Встановлення необхідних інструментів

#### Якщо Linux (Ubuntu/Debian):

```bash
# Оновити пакети
sudo apt update

# Встановити Git
sudo apt install git -y

# Встановити Python 3.11
sudo apt install python3.11 python3.11-venv python3-pip -y

# Встановити ODBC драйвер для MS SQL
curl https://packages.microsoft.com/keys/microsoft.asc | sudo apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | sudo tee /etc/apt/sources.list.d/mssql-release.list
sudo apt-get update
sudo ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev

# Перевірка
git --version
python3.11 --version
```

#### Якщо Windows Server:

```powershell
# Git вже має бути встановлено
git --version

# Python 3.11 вже має бути встановлено
python --version

# Якщо немає - завантажте з:
# Git: https://git-scm.com/download/win
# Python: https://www.python.org/downloads/
```

---

### Крок 3: Клонування проекту

```bash
# Створити директорію
sudo mkdir -p /opt/slazar
sudo chown ваш_користувач:ваш_користувач /opt/slazar

# Перейти в директорію
cd /opt

# Клонувати репозиторій
git clone https://github.com/eio1990/slazar.git

# Перейти в проект
cd slazar

# Перевірити що все на місці
ls -la
```

**Ви повинні побачити:**
```
backend/
frontend/
docs/
deploy.sh
deploy.bat
START_HERE.md
QUICK_START.md
DEPLOY_TO_SERVER.md
та інші файли...
```

---

### Крок 4: Налаштування Backend

```bash
cd /opt/slazar/backend

# Створити віртуальне середовище
python3.11 -m venv venv

# Активувати venv
source venv/bin/activate  # Linux
# або
venv\Scripts\activate  # Windows

# Оновити pip
pip install --upgrade pip

# Встановити залежності
pip install -r requirements.txt
```

---

### Крок 5: Створення .env файлу

```bash
cd /opt/slazar/backend

# Створити .env
nano .env
# або на Windows: notepad .env
```

**Вміст файлу:**
```env
# MS SQL Server Configuration
MSSQL_SERVER=localhost,14330
MSSQL_DATABASE=SLAZAR_DB
MSSQL_USER=llm_user
MSSQL_PASSWORD=EsmerA55%lda!
MSSQL_DRIVER=ODBC Driver 18 for SQL Server

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
```

**Зберегти:**
- Nano: `Ctrl+O`, `Enter`, `Ctrl+X`
- Notepad: `Ctrl+S`

---

### Крок 6: Перевірка підключення до БД

```bash
cd /opt/slazar/backend
source venv/bin/activate  # якщо ще не активовано

# Перевірити підключення
python -c "from database import get_db_connection; conn = get_db_connection().__enter__(); print('✅ DB connection successful')"
```

Якщо бачите `✅ DB connection successful` - все працює!

---

### Крок 7: Відкрити порт 8001 в Firewall

#### Linux (UFW):
```bash
sudo ufw allow 8001/tcp
sudo ufw status
```

#### Linux (firewalld):
```bash
sudo firewall-cmd --permanent --add-port=8001/tcp
sudo firewall-cmd --reload
sudo firewall-cmd --list-ports
```

#### Windows Server:
```powershell
New-NetFirewallRule -DisplayName "SLAZAR API" -Direction Inbound -Protocol TCP -LocalPort 8001 -Action Allow
```

---

### Крок 8: Налаштування автозапуску (systemd на Linux)

```bash
# Створити systemd service
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

**Активувати сервіс:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable slazar-backend
sudo systemctl start slazar-backend

# Перевірити статус
sudo systemctl status slazar-backend
```

---

### Крок 9: Перевірка доступності API

На вашому локальному ПК відкрийте браузер:
```
http://85.238.112.232:8001/docs
```

Має відкритися Swagger UI з документацією API ✅

---

## 🔄 Оновлення проекту в майбутньому

Коли я вношу зміни і ви пушите на GitHub, на сервері просто:

```bash
cd /opt/slazar
git pull origin main
sudo systemctl restart slazar-backend
```

---

## 📝 Корисні команди

### Переглянути логи:
```bash
sudo journalctl -u slazar-backend -f
```

### Перезапустити сервіс:
```bash
sudo systemctl restart slazar-backend
```

### Перевірити статус:
```bash
sudo systemctl status slazar-backend
```

### Зупинити сервіс:
```bash
sudo systemctl stop slazar-backend
```

---

## 🎉 Готово!

Тепер backend працює на сервері і доступний через:
- API: `http://85.238.112.232:8001`
- Swagger: `http://85.238.112.232:8001/docs`

**Наступні кроки:**
1. Зберіть APK на локальному ПК (QUICK_START.md)
2. Встановіть на планшет
3. Тестуйте!

**Робочий процес:**
```
Баг → Повідомлення → Виправлення локально → git push →
→ На сервері: git pull → restart → Тест ✅
```

---

## ❓ Якщо щось не працює

### Помилка: "Permission denied (publickey)"

**Рішення:** Налаштуйте SSH ключ для GitHub або використайте HTTPS:
```bash
git clone https://github.com/eio1990/slazar.git
```

### Помилка: "pyodbc can't open /SQL/bin/sqlservr"

**Рішення:** Перевірте, що MS SQL Server працює:
```bash
# Якщо SQL на тому ж сервері
sudo systemctl status mssql-server

# Або перевірте підключення
telnet 85.238.112.232 14330
```

### Помилка: "Port 8001 already in use"

**Рішення:** Зупиніть процес на порту 8001:
```bash
# Знайти процес
sudo netstat -tulpn | grep 8001
# або
sudo lsof -i :8001

# Вбити процес
sudo kill -9 PID
```

---

**Створено:** 15 грудня 2025
