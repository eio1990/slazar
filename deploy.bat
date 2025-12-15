@echo off
REM ====================================================================
REM Скрипт швидкого деплою SLAZAR Backend на віртуальну машину
REM ====================================================================
REM
REM ВАЖЛИВО: Цей скрипт очікує, що проект знаходиться в C:\slazar
REM Якщо ваш проект в іншому місці, скопіюйте його туди або змініть шлях нижче
REM

echo.
echo ========================================
echo   SLAZAR Backend Deploy Script
echo ========================================
echo.

REM Перевірка, чи є зміни для комміту
git status --short
IF ERRORLEVEL 1 (
    echo [ERROR] Git не доступний або не ініціалізований
    pause
    exit /b 1
)

echo.
echo [1/4] Підготовка файлів...
echo.

REM Створюємо архів з backend (без __pycache__ та .env)
echo Архівування backend...
tar -czf backend-deploy.tar.gz ^
    --exclude=backend/__pycache__ ^
    --exclude=backend/.env ^
    --exclude=backend/venv ^
    backend/

IF ERRORLEVEL 1 (
    echo [ERROR] Помилка при створенні архіву
    pause
    exit /b 1
)

echo [OK] Архів створено: backend-deploy.tar.gz
echo.

echo [2/4] Завантаження на сервер...
echo.

REM Замініть SERVER_USER та SERVER_IP на ваші дані
REM Приклад: set SERVER=admin@85.238.112.232
set SERVER=YOUR_USER@85.238.112.232
set SERVER_PATH=/opt/slazar

echo Завантаження на %SERVER%:%SERVER_PATH%...
scp backend-deploy.tar.gz %SERVER%:%SERVER_PATH%/

IF ERRORLEVEL 1 (
    echo [ERROR] Помилка при завантаженні на сервер
    echo.
    echo Перевірте:
    echo - SSH доступ до сервера
    echo - Шлях на сервері існує
    echo - Змінна SERVER налаштована правильно
    pause
    exit /b 1
)

echo [OK] Файли завантажено
echo.

echo [3/4] Розгортання на сервері...
echo.

REM Підключаємось до сервера і розгортаємо
ssh %SERVER% "cd %SERVER_PATH% && tar -xzf backend-deploy.tar.gz && sudo systemctl restart slazar-backend"

IF ERRORLEVEL 1 (
    echo [WARNING] Можлива помилка при розгортанні
    echo Перевірте стан сервісу вручну: ssh %SERVER% 'sudo systemctl status slazar-backend'
)

echo [OK] Backend розгорнуто
echo.

echo [4/4] Очищення...
del backend-deploy.tar.gz
echo [OK] Тимчасові файли видалено
echo.

echo ========================================
echo   Деплой завершено успішно!
echo ========================================
echo.
echo Backend доступний на: http://85.238.112.232:8001
echo Swagger документація: http://85.238.112.232:8001/docs
echo.
echo Перевірте статус на сервері:
echo   ssh %SERVER% "sudo systemctl status slazar-backend"
echo.
echo Перегляд логів:
echo   ssh %SERVER% "sudo journalctl -u slazar-backend -f"
echo.

pause
