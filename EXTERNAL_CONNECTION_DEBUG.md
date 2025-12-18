# Діагностика підключення з зовнішніх мереж

**Дата:** 18 грудня 2025
**Проблема:** Локально працює, з локальної мережі працює, з інших мереж НЕ працює

---

## 🎯 Швидка діагностика

### Крок 1: Перевірити Gateway та можливість port forwarding

```bash
ipconfig | findstr "Default Gateway"
```

Записати IP роутера (наприклад: `10.100.0.1` або `192.168.1.1`)

### Крок 2: Перевірити чи є CGNAT

```bash
ipconfig
```

Дивися на IPv4 Address вашого комп'ютера:
- Якщо починається з `100.64.*.*` → **У вас CGNAT, port forwarding НЕ ПРАЦЮВАТИМЕ**
- Якщо `10.100.*.*` або `192.168.*.*` → все нормально, можна налаштувати port forwarding

### Крок 3: Отримати публічний IP

```bash
curl https://api.ipify.org
```

Або відкрити в браузері: https://whatismyip.com

Записати цей IP.

### Крок 4: Налаштувати Port Forwarding на роутері

1. Відкрити браузер
2. Ввести IP роутера (з Кроку 1)
3. Ввести логін/пароль (зазвичай `admin` / `admin`)
4. Знайти розділ **Port Forwarding** або **Virtual Server**
5. Додати **2 правила**:

**Правило 1: Backend**
- Service Name: `SLAZAR Backend`
- External Port: `8001`
- Internal IP: `10.100.0.60`
- Internal Port: `8001`
- Protocol: `TCP`

**Правило 2: SQL Server**
- Service Name: `SQL Server`
- External Port: `14330`
- Internal IP: `10.100.0.60`
- Internal Port: `14330`
- Protocol: `TCP`

6. **Зберегти** та **перезавантажити роутер**

### Крок 5: Перевірити чи порти відкриті

Відкрити в браузері: https://www.yougetsignal.com/tools/open-ports/

- Ввести **публічний IP** (з Кроку 3)
- Ввести порт **8001**
- Натиснути **Check**

Повинно показати: **"Port 8001 is open on [ваш IP]"**

Якщо показує **"Port 8001 is closed"** → port forwarding не працює або backend не запущений.

### Крок 6: Тест з мобільного

1. На телефоні вимкнути WiFi (використати мобільний інтернет)
2. Відкрити браузер
3. Ввести:
   ```
   http://[публічний_IP]:8001/api/health
   ```

Повинно показати JSON:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2025-12-18T..."
}
```

---

## 🐛 Що робити якщо не працює?

### Варіант 1: Використати Ngrok (найпростіше для тестування)

**Встановлення:**
```bash
# Якщо є chocolatey
choco install ngrok

# Або завантажити з https://ngrok.com/download
```

**Запуск:**
```bash
# Спочатку запустити backend
cd /c/slazar/backend
python main.py

# В іншому терміналі запустити ngrok
ngrok http 8001
```

Ngrok покаже публічний URL типу:
```
Forwarding   https://abc123.ngrok.io -> http://localhost:8001
```

Використати цей URL замість IP:
```
https://abc123.ngrok.io/api/health
```

**В frontend/services/api.ts змінити:**
```typescript
const BASE_URL = 'https://abc123.ngrok.io';
```

### Варіант 2: CloudFlare Tunnel (безкоштовно, безпечно)

**Встановлення:**
```bash
choco install cloudflared
```

**Запуск:**
```bash
cloudflared tunnel --url http://localhost:8001
```

Отримаєте URL типу `https://xyz.trycloudflare.com`

### Варіант 3: Замовити статичний IP у провайдера

Якщо у вас **CGNAT** (IP починається з `100.64.*.*`):
- Зателефонувати провайдеру
- Запитати **статичний публічний IP адресу**
- Зазвичай це коштує 50-100 грн/міс

Після отримання статичного IP - налаштувати port forwarding як в Кроці 4.

---

## ✅ Чеклист

Перед тестуванням з зовнішньої мережі:

- [ ] Backend запущений (`python main.py`)
- [ ] Локально працює (`curl http://localhost:8001/api/health`)
- [ ] З локальної мережі працює (`curl http://10.100.0.60:8001/api/health`)
- [ ] Windows Firewall правила додані для портів 8001 та 14330
- [ ] Port forwarding налаштований на роутері
- [ ] Роутер перезавантажений
- [ ] Публічний IP отриманий
- [ ] Порт 8001 відкритий (перевірено на yougetsignal.com)
- [ ] SQL Server налаштований для remote connections (якщо потрібно)

---

## 📊 Таблиця швидкої діагностики

| Що працює | Що НЕ працює | Проблема | Рішення |
|-----------|--------------|----------|---------|
| ✅ localhost | ❌ локальна мережа | Windows Firewall | Додати правила firewall |
| ✅ localhost<br>✅ локальна мережа | ❌ зовнішня мережа | Port forwarding | Налаштувати на роутері |
| ✅ все | ❌ БД з зовнішньої мережі | SQL Server remote | Увімкнути TCP/IP в SQL Server |
| ❌ все | - | Backend не запущений | `python main.py` |

---

## 🔍 SQL Server - Детальна конфігурація

### Якщо потрібен доступ до БД з інтернету

**⚠️ НЕБЕЗПЕЧНО для production! Тільки для тестування!**

#### 1. SQL Server Configuration Manager

```
Start → SQL Server 2022 → SQL Server Configuration Manager
```

1. **SQL Server Network Configuration → Protocols for MSSQLSERVER**
   - TCP/IP → Enabled
   - Правою кнопкою → Properties

2. **IP Addresses → IPAll**
   - TCP Dynamic Ports: **ПУСТО**
   - TCP Port: **14330**

3. **SQL Server Services**
   - SQL Server (MSSQLSERVER) → Restart

#### 2. Перевірити Authentication Mode (SSMS)

```sql
-- Перевірити режим
EXEC xp_instance_regread
    N'HKEY_LOCAL_MACHINE',
    N'Software\Microsoft\MSSQLServer\MSSQLServer',
    N'LoginMode'
```

Повинно бути **2** (Mixed Mode).

#### 3. Перевірити llm_user

```sql
-- Перевірити логін
SELECT name, type_desc, is_disabled
FROM sys.server_principals
WHERE name = 'llm_user';

-- Надати права
USE SLAZAR_DB;
GRANT CONNECT TO llm_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::dbo TO llm_user;
```

---

## 🎯 Рекомендації

### Для тестування (зараз)
✅ Використати **Ngrok** - найшвидше та найпростіше
✅ Або налаштувати port forwarding, якщо немає CGNAT

### Для production (потім)
❌ НЕ використовувати прямий port forwarding
✅ Використати **CloudFlare Tunnel** або **Tailscale VPN**
✅ Використати **HTTPS** з SSL сертифікатом
✅ НЕ відкривати SQL Server порт назовні (тільки backend)

---

**Підготував:** Claude Sonnet 4.5
**Дата:** 18 грудня 2025
