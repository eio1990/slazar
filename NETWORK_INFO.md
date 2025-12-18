# Мережева конфігурація SLAZAR

**Дата:** 18 грудня 2025

---

## 📊 Поточні налаштування

### Мережа
- **Локальний IP сервера:** `10.100.0.60`
- **Gateway (роутер):** `10.100.0.1`
- **Публічний IP:** `195.138.67.124`
- **Backend порт:** `8001`
- **SQL Server порт:** `14330`

### Статус
- ✅ CGNAT: **НІ** (можна налаштувати port forwarding)
- ✅ Windows Firewall: правила створені для портів 8001 та 14330
- ✅ SQL Server: слухає на порті 14330
- ⏳ Port Forwarding на роутері: **потрібно налаштувати**

---

## 🎯 Наступні кроки для доступу з інтернету

### Опція 1: Port Forwarding (для постійного доступу)

#### 1. Зайти в роутер
Відкрити браузер та ввести:
```
http://10.100.0.1
```

Логін/пароль (спробувати в порядку):
- `admin` / `admin`
- `admin` / `password`
- `admin` / (пустий)
- Або подивитися на задній панелі роутера

#### 2. Знайти розділ Port Forwarding

Шукати в меню:
- **Port Forwarding**
- **Virtual Server**
- **NAT**
- **Port Mapping**
- **Applications & Gaming**

#### 3. Додати правила

**Правило 1: SLAZAR Backend**
```
Service Name: SLAZAR Backend
External Port: 8001
Internal IP: 10.100.0.60
Internal Port: 8001
Protocol: TCP
Enable: Yes
```

**Правило 2: SQL Server (опціонально, небезпечно!)**
```
Service Name: SQL Server
External Port: 14330
Internal IP: 10.100.0.60
Internal Port: 14330
Protocol: TCP
Enable: Yes
```

⚠️ **УВАГА:** Відкривати SQL Server порт в інтернет **НЕБЕЗПЕЧНО**!
Краще відкрити тільки Backend (8001), а SQL Server залишити доступним тільки локально.

#### 4. Зберегти та перезавантажити роутер

#### 5. Перевірити

**Онлайн перевірка портів:**
https://www.yougetsignal.com/tools/open-ports/

- IP: `195.138.67.124`
- Port: `8001`
- Check

Повинно показати: **"Port 8001 is open"**

**З мобільного телефону (вимкнути WiFi):**
```
http://195.138.67.124:8001/api/health
```

---

### Опція 2: Ngrok (швидке рішення для тестування)

Не потребує налаштування роутера!

#### 1. Встановити Ngrok

**Завантажити:**
https://ngrok.com/download

Або через Chocolatey:
```bash
choco install ngrok
```

#### 2. Запустити backend

```bash
cd /c/slazar/backend
python main.py
```

#### 3. У новому терміналі запустити Ngrok

```bash
ngrok http 8001
```

#### 4. Використати публічний URL

Ngrok покаже щось на кшталт:
```
Forwarding   https://abc123-xyz.ngrok-free.app -> http://localhost:8001
```

**Тестування:**
```
https://abc123-xyz.ngrok-free.app/api/health
```

**В frontend змінити базовий URL:**

Файл: `frontend/services/api.ts`
```typescript
const BASE_URL = 'https://abc123-xyz.ngrok-free.app';
```

---

### Опція 3: CloudFlare Tunnel (безкоштовно, безпечно)

#### 1. Встановити cloudflared

```bash
choco install cloudflared
```

#### 2. Запустити тунель

```bash
cloudflared tunnel --url http://localhost:8001
```

Отримаєте URL типу: `https://random-words-random.trycloudflare.com`

---

## 🧪 Тестування

### 1. Локальне тестування (працює ✅)
```bash
curl http://localhost:8001/api/health
```

### 2. Локальна мережа (працює ✅)
```bash
curl http://10.100.0.60:8001/api/health
```

### 3. З інтернету (потрібно налаштувати)

**Після налаштування port forwarding:**
```bash
curl http://195.138.67.124:8001/api/health
```

**Або з Ngrok:**
```bash
curl https://[ngrok-url]/api/health
```

---

## 📱 Налаштування мобільного додатку

### Для локальної мережі (працює зараз)

`frontend/services/api.ts`:
```typescript
const BASE_URL = 'http://10.100.0.60:8001';
```

Запустити:
```bash
cd /c/slazar/frontend
npx expo start --tunnel
```

### Для інтернету (після налаштування)

**З port forwarding:**
```typescript
const BASE_URL = 'http://195.138.67.124:8001';
```

**З Ngrok:**
```typescript
const BASE_URL = 'https://abc123-xyz.ngrok-free.app';
```

---

## 🔒 Безпека

### Для тестування (зараз)
- ✅ HTTP - OK
- ✅ Port forwarding - OK
- ⚠️ SQL Server порт НЕ відкривати в інтернет

### Для production (потім)
- ✅ HTTPS з SSL сертифікатом (Let's Encrypt)
- ✅ Reverse proxy (nginx або Caddy)
- ✅ Firewall на backend
- ✅ VPN або CloudFlare Tunnel
- ❌ НЕ відкривати SQL Server в інтернет
- ✅ Strong passwords
- ✅ Rate limiting
- ✅ IP whitelist (якщо можливо)

---

## 📋 Швидкий старт для тестування з інтернету

### Найпростіший спосіб (Ngrok)

```bash
# Термінал 1: Backend
cd /c/slazar/backend
python main.py

# Термінал 2: Ngrok
ngrok http 8001

# Скопіювати URL з ngrok (https://...)
# Відкрити frontend/services/api.ts
# Змінити BASE_URL на ngrok URL

# Термінал 3: Frontend
cd /c/slazar/frontend
npx expo start --tunnel
```

Готово! Тепер можна тестувати з будь-якої мережі.

---

**Підготував:** Claude Sonnet 4.5
**Дата:** 18 грудня 2025
