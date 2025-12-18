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

### Проблема: Працює локально і з локальної мережі, але НЕ працює з інших мереж

**Симптоми:**
- ✅ `curl http://localhost:8001/api/health` працює
- ✅ `curl http://10.100.0.60:8001/api/health` працює з локальної мережі
- ❌ З мобільного інтернету або іншого WiFi не працює

**Діагностика:**

#### 1. Перевірити чи SQL Server приймає віддалені підключення

Відкрити **SQL Server Configuration Manager**:

```
Start → SQL Server 2022 → SQL Server Configuration Manager
```

1. **SQL Server Network Configuration → Protocols for MSSQLSERVER**
   - Перевірити що **TCP/IP** = **Enabled**
   - Якщо Disabled - клікнути правою кнопкою → Enable → перезапустити SQL Server

2. **TCP/IP Properties → IP Addresses → IPAll**
   - TCP Dynamic Ports: **має бути ПУСТИМ**
   - TCP Port: **14330**

3. **SQL Server Services**
   - Перевірити що **SQL Server (MSSQLSERVER)** = **Running**
   - Перевірити що **SQL Server Browser** = **Running** (необов'язково для статичного порту)

#### 2. Перевірити SQL Server Authentication Mode

Відкрити **SQL Server Management Studio (SSMS)** та підключитися до сервера.

Виконати:
```sql
-- Перевірити режим аутентифікації
EXEC xp_instance_regread
    N'HKEY_LOCAL_MACHINE',
    N'Software\Microsoft\MSSQLServer\MSSQLServer',
    N'LoginMode'
```

Повинно повернути **2** (Mixed Mode - Windows + SQL Server Authentication).

Якщо повертає **1** - треба включити Mixed Mode:

1. SSMS → Правою кнопкою на сервер → Properties
2. Security → Server authentication → **SQL Server and Windows Authentication mode**
3. OK → перезапустити SQL Server

#### 3. Перевірити що llm_user має права для remote connections

```sql
-- Перевірити логін
SELECT name, type_desc, is_disabled
FROM sys.server_principals
WHERE name = 'llm_user';

-- Перевірити доступ до БД
SELECT
    dp.name as UserName,
    dp.type_desc,
    dp.default_schema_name
FROM SLAZAR_DB.sys.database_principals dp
WHERE dp.name = 'llm_user';

-- Надати права (якщо потрібно)
USE SLAZAR_DB;
GRANT CONNECT TO llm_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::dbo TO llm_user;
```

#### 4. Перевірити Port Forwarding на роутері

Проблема: **Firewall на Windows OK, але роутер блокує зовнішні підключення**

**Крок 1: Дізнатися Gateway (IP роутера)**
```bash
ipconfig | findstr "Default Gateway"
```

Звичайно це `192.168.0.1`, `192.168.1.1` або `10.100.0.1`

**Крок 2: Зайти в роутер**

Відкрити браузер та ввести IP роутера. Логін/пароль зазвичай:
- admin / admin
- admin / password
- admin / (пустий)

**Крок 3: Знайти Port Forwarding**

Різні роутери мають різні назви:
- Port Forwarding
- Virtual Server
- NAT
- Port Mapping
- Applications & Gaming

**Крок 4: Додати правила**

| Service Name | External Port | Internal IP | Internal Port | Protocol |
|--------------|---------------|-------------|---------------|----------|
| SLAZAR Backend | 8001 | 10.100.0.60 | 8001 | TCP |
| SQL Server | 14330 | 10.100.0.60 | 14330 | TCP |

**Крок 5: Зберегти та перезавантажити роутер**

#### 5. Перевірити публічний IP та провайдера

**Отримати публічний IP:**
```bash
curl https://api.ipify.org
```

Або відкрити в браузері: https://whatismyip.com

**⚠️ ВАЖЛИВО:**

Деякі провайдери використовують **CGNAT (Carrier-Grade NAT)**:
- Ваш "публічний" IP насправді спільний для багатьох користувачів
- Port forwarding НЕ ПРАЦЮВАТИМЕ
- Треба замовляти у провайдера **статичний публічний IP**

Перевірити чи CGNAT:
```bash
# На Windows запустити
ipconfig
```

Дивися на "Default Gateway". Якщо це починається з:
- `100.64.0.0` - `100.127.255.255` → **CGNAT** (не працюватиме)
- `10.0.0.0` - `10.255.255.255` → приватна мережа (нормально)
- `192.168.0.0` - `192.168.255.255` → приватна мережа (нормально)

#### 6. Тест підключення з зовнішньої мережі

**Спосіб 1: З телефону (вимкнути WiFi, використати мобільний інтернет)**
```
http://[публічний_IP]:8001/api/health
```

**Спосіб 2: Використати онлайн сервіс перевірки портів**
- https://www.yougetsignal.com/tools/open-ports/
- Ввести публічний IP
- Ввести порт 8001
- Check → повинно показати "Open"

**Спосіб 3: З іншого комп'ютера в іншій мережі**
```bash
telnet [публічний_IP] 8001
```

#### 7. Альтернативні рішення (якщо port forwarding не працює)

**Варіант 1: Ngrok (швидке рішення для тестування)**
```bash
# Встановити ngrok
choco install ngrok

# Запустити тунель
ngrok http 8001
```

Отримаєте публічний URL типу `https://abc123.ngrok.io` який можна використовувати замість IP.

**Варіант 2: CloudFlare Tunnel (безкоштовно, безпечніше)**
```bash
# Встановити cloudflared
choco install cloudflared

# Створити тунель
cloudflared tunnel --url http://localhost:8001
```

**Варіант 3: Tailscale VPN (найбезпечніше для production)**
- Створити безкоштовний акаунт на https://tailscale.com
- Встановити на сервер та на мобільний
- Підключатися через приватну VPN мережу

#### 8. Швидкий тест: Чи проблема в SQL Server чи в backend?

**Запустити простий Python HTTP сервер на порту 8001:**
```bash
cd /c/slazar
python -m http.server 8001
```

Спробувати підключитися з зовнішньої мережі до `http://[публічний_IP]:8001`

- Якщо працює → проблема в backend або SQL Server
- Якщо не працює → проблема в роутері або провайдері (port forwarding/CGNAT)

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
