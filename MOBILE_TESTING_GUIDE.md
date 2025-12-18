# Керівництво по тестуванню з мобільного пристрою

**Дата:** 18 грудня 2025

---

## 📱 Мета

Протестувати додаток SLAZAR з реального мобільного пристрою через локальну мережу або інтернет.

---

## 🔧 Поточна конфігурація

### Сервер (Windows)
- **IP адреса:** 10.100.0.60 (локальна мережа)
- **Backend порт:** 8001
- **SQL Server порт:** 14330
- **Firewall:** Правила створені для обох портів

### Налаштування які вже зроблені ✅
- ✅ SQL Server слухає на порту 14330 (IPAll)
- ✅ Firewall правила додані
- ✅ SQL Login `llm_user` створений

---

## 🚀 Крок 1: Запустити backend сервер

### A. Перевірити налаштування підключення до БД

Створити файл `/c/slazar/backend/.env`:

```env
# Database Configuration
DB_SERVER=127.0.0.1,14330
DB_NAME=SLAZAR_DB
DB_USER=llm_user
DB_PASSWORD=твій_пароль_тут

# Charset for Ukrainian support
DB_CHARSET=UTF-8
```

⚠️ **ВАЖЛИВО:** Замінити `твій_пароль_тут` на реальний пароль для `llm_user`

### B. Запустити backend

**Опція 1: Через командний рядок (для тестування)**
```bash
cd /c/slazar/backend
python main.py
```

Повинно побачити:
```
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:8001
INFO:     Application startup complete.
```

**Опція 2: Через supervisor (production)**
```bash
sudo supervisorctl restart backend
sudo supervisorctl status backend
```

### C. Перевірити що порт слухається

Відкрити **PowerShell** та виконати:
```powershell
netstat -an | findstr ":8001"
```

Повинно побачити:
```
TCP    0.0.0.0:8001         0.0.0.0:0              LISTENING
```

---

## 🔥 Крок 2: Перевірити Firewall

### A. Перевірити існуючі правила

**PowerShell (від адміністратора):**
```powershell
Get-NetFirewallRule -DisplayName "*SLAZAR*" | Select-Object DisplayName, Enabled, Direction, Action
```

Повинно показати:
- ✅ SLAZAR Backend (port 8001) - Enabled, Inbound, Allow
- ✅ SQL Server Port 14330 - Enabled, Inbound, Allow

### B. Якщо правил немає - створити

```powershell
# Backend
netsh advfirewall firewall add rule name="SLAZAR Backend" dir=in action=allow protocol=TCP localport=8001

# SQL Server
netsh advfirewall firewall add rule name="SQL Server Port 14330" dir=in action=allow protocol=TCP localport=14330
```

---

## 🌐 Крок 3: Тестування з локальної мережі

### A. З комп'ютера в тій же мережі

**Перевірити підключення до backend:**
```bash
curl http://10.100.0.60:8001/api/health
```

Повинно повернути:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-12-18T10:00:00"
}
```

**Перевірити підключення до SQL Server:**
```bash
telnet 10.100.0.60 14330
```

Якщо підключилося - все OK.

### B. З мобільного телефону (Android/iOS)

#### 1. Переконатися що телефон в тій же WiFi мережі

Налаштування WiFi → інформація → IP адреса повинна починатися з `10.100.0.*`

#### 2. Відкрити браузер на телефоні

Перейти на:
```
http://10.100.0.60:8001/api/health
```

Якщо бачите JSON з "status": "healthy" - backend працює!

#### 3. Налаштувати frontend для тестування

Відредагувати файл `/c/slazar/frontend/services/api.ts`:

Змінити:
```typescript
const BASE_URL = 'http://localhost:8001';
```

На:
```typescript
const BASE_URL = 'http://10.100.0.60:8001';
```

#### 4. Запустити Expo додаток

```bash
cd /c/slazar/frontend
npx expo start --tunnel
```

Сканувати QR код з Expo Go на телефоні.

---

## 🌍 Крок 4: Тестування через інтернет (опціонально)

### A. Дізнатися публічний IP

Відкрити браузер та перейти на:
```
https://whatismyip.com
```

Записати IP (наприклад: `93.123.45.67`)

### B. Налаштувати Port Forwarding на роутері

**Увійти в роутер (зазвичай `192.168.0.1` або `192.168.1.1`):**

1. Знайти розділ "Port Forwarding" або "NAT"
2. Додати правило:
   - **External Port:** 8001
   - **Internal IP:** 10.100.0.60
   - **Internal Port:** 8001
   - **Protocol:** TCP
3. Додати ще одне правило для SQL:
   - **External Port:** 14330
   - **Internal IP:** 10.100.0.60
   - **Internal Port:** 14330
   - **Protocol:** TCP
4. Зберегти та перезавантажити роутер

### C. Перевірити з іншої мережі

З мобільного інтернету (вимкнути WiFi):
```
http://[твій_публічний_IP]:8001/api/health
```

⚠️ **БЕЗПЕКА:** Це небезпечно для production! Використовуйте тільки для тестування.

Для production треба:
- HTTPS (SSL сертифікат)
- Reverse proxy (nginx)
- Authentification
- VPN або CloudFlare Tunnel

---

## ✅ Чеклист перевірки

Перед тестуванням переконайтеся:

- [ ] SQL Server запущений і слухає на 14330
- [ ] Backend запущений і слухає на 8001
- [ ] Firewall правила додані
- [ ] .env файл створений з правильними даними
- [ ] З локального комп'ютера `curl http://10.100.0.60:8001/api/health` працює
- [ ] З мобільного телефону (в тій же WiFi) браузер відкриває `http://10.100.0.60:8001/api/health`

---

## 🐛 Troubleshooting

### Проблема: "Connection refused" або "Cannot connect"

**Рішення:**
1. Перевірити що backend запущений:
   ```powershell
   netstat -an | findstr ":8001"
   ```

2. Перевірити firewall:
   ```powershell
   Get-NetFirewallRule -DisplayName "SLAZAR*"
   ```

3. Перевірити що телефон в тій же мережі:
   - IP телефону повинен бути `10.100.0.*`

### Проблема: "Database connection failed"

**Рішення:**
1. Перевірити SQL Server:
   ```powershell
   Get-Service MSSQL*
   ```

2. Перевірити логін:
   ```sql
   SELECT * FROM sys.server_principals WHERE name = 'llm_user'
   ```

3. Перевірити порт:
   ```powershell
   netstat -an | findstr ":14330"
   ```

### Проблема: Працює локально, але не працює з телефону

**Рішення:**
1. Вимкнути Windows Firewall повністю (для тесту):
   ```powershell
   Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
   ```

2. Перевірити з телефону

3. Якщо запрацювало - проблема в Firewall, треба правильно налаштувати правила

4. Увімкнути Firewall назад:
   ```powershell
   Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled True
   ```

### Проблема: "Expo Go не може підключитися"

**Рішення:**
1. Використати `--tunnel`:
   ```bash
   npx expo start --tunnel
   ```

2. Або використати локальний IP в налаштуваннях Expo

---

## 📝 Приклад повного процесу

```bash
# 1. Створити .env
cd /c/slazar/backend
cat > .env << 'EOF'
DB_SERVER=127.0.0.1,14330
DB_NAME=SLAZAR_DB
DB_USER=llm_user
DB_PASSWORD=твій_пароль
DB_CHARSET=UTF-8
EOF

# 2. Запустити backend
python main.py

# У іншому терміналі:
# 3. Перевірити що працює
curl http://localhost:8001/api/health

# 4. Перевірити з локальної мережі
curl http://10.100.0.60:8001/api/health

# 5. Запустити frontend
cd /c/slazar/frontend
npx expo start --tunnel
```

---

## 🎯 Очікуваний результат

Після всіх кроків:
1. ✅ Backend доступний з будь-якого пристрою в локальній мережі
2. ✅ Мобільний додаток підключається до backend
3. ✅ Всі API запити працюють
4. ✅ Дані з БД відображаються в додатку

---

## 🔒 Безпека

**ДЛЯ ТЕСТУВАННЯ:**
- OK використовувати HTTP
- OK використовувати Port Forwarding

**ДЛЯ PRODUCTION:**
- ⚠️ ОБОВ'ЯЗКОВО HTTPS
- ⚠️ Authentification
- ⚠️ Rate limiting
- ⚠️ Reverse proxy (nginx)
- ⚠️ Не відкривати SQL Server порт назовні
- ⚠️ Використовувати CloudFlare або VPN

---

**Підготував:** Claude Sonnet 4.5
**Дата:** 18 грудня 2025
