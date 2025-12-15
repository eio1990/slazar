#!/bin/bash
# ====================================================================
# Скрипт швидкого деплою SLAZAR Backend на віртуальну машину
# ====================================================================

set -e  # Зупинитися при помилці

# Кольори для виводу
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Налаштування сервера
# Замініть на ваші дані
SERVER_USER="YOUR_USER"
SERVER_IP="85.238.112.232"
SERVER_PATH="/opt/slazar"
SERVICE_NAME="slazar-backend"

echo ""
echo -e "${BLUE}========================================"
echo "  SLAZAR Backend Deploy Script"
echo -e "========================================${NC}"
echo ""

# Функція для виводу помилок
error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

# Функція для виводу успіху
success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

# Функція для виводу попереджень
warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Перевірка Git
if ! command -v git &> /dev/null; then
    error "Git не встановлено"
fi

# Перевірка SSH
if ! command -v ssh &> /dev/null; then
    error "SSH не встановлено"
fi

# Перевірка налаштувань
if [ "$SERVER_USER" = "YOUR_USER" ]; then
    error "Налаштуйте змінну SERVER_USER у скрипті (рядок 18)"
fi

# [1/5] Показати зміни
echo -e "${BLUE}[1/5]${NC} Перевірка змін..."
echo ""
git status --short || error "Git репозиторій не ініціалізований"
echo ""

# [2/5] Створити архів
echo -e "${BLUE}[2/5]${NC} Створення архіву backend..."
echo ""

tar -czf backend-deploy.tar.gz \
    --exclude='backend/__pycache__' \
    --exclude='backend/**/__pycache__' \
    --exclude='backend/.env' \
    --exclude='backend/venv' \
    --exclude='backend/.pytest_cache' \
    backend/ || error "Не вдалося створити архів"

success "Архів створено: backend-deploy.tar.gz ($(du -h backend-deploy.tar.gz | cut -f1))"
echo ""

# [3/5] Завантажити на сервер
echo -e "${BLUE}[3/5]${NC} Завантаження на сервер ${SERVER_USER}@${SERVER_IP}..."
echo ""

scp backend-deploy.tar.gz ${SERVER_USER}@${SERVER_IP}:${SERVER_PATH}/ || {
    error "Помилка завантаження. Перевірте SSH доступ: ssh ${SERVER_USER}@${SERVER_IP}"
}

success "Файли завантажено на сервер"
echo ""

# [4/5] Розгорнути на сервері
echo -e "${BLUE}[4/5]${NC} Розгортання на сервері..."
echo ""

ssh ${SERVER_USER}@${SERVER_IP} << EOF
    set -e
    cd ${SERVER_PATH}
    echo "Розпаковування архіву..."
    tar -xzf backend-deploy.tar.gz
    echo "Перезапуск сервісу..."
    sudo systemctl restart ${SERVICE_NAME}
    echo "Перевірка статусу..."
    sudo systemctl status ${SERVICE_NAME} --no-pager | head -n 10
    echo ""
    echo "Очищення..."
    rm -f backend-deploy.tar.gz
EOF

if [ $? -eq 0 ]; then
    success "Backend розгорнуто і перезапущено"
else
    warning "Можлива помилка при розгортанні. Перевірте логи вручну."
fi
echo ""

# [5/5] Очищення локальних файлів
echo -e "${BLUE}[5/5]${NC} Очищення тимчасових файлів..."
rm -f backend-deploy.tar.gz
success "Тимчасові файли видалено"
echo ""

# Підсумок
echo -e "${GREEN}========================================"
echo "  Деплой завершено успішно!"
echo -e "========================================${NC}"
echo ""
echo -e "Backend доступний на: ${BLUE}http://${SERVER_IP}:8001${NC}"
echo -e "Swagger документація: ${BLUE}http://${SERVER_IP}:8001/docs${NC}"
echo ""
echo "Корисні команди:"
echo ""
echo -e "${YELLOW}Перевірити статус:${NC}"
echo "  ssh ${SERVER_USER}@${SERVER_IP} 'sudo systemctl status ${SERVICE_NAME}'"
echo ""
echo -e "${YELLOW}Переглянути логи:${NC}"
echo "  ssh ${SERVER_USER}@${SERVER_IP} 'sudo journalctl -u ${SERVICE_NAME} -f'"
echo ""
echo -e "${YELLOW}Перезапустити вручну:${NC}"
echo "  ssh ${SERVER_USER}@${SERVER_IP} 'sudo systemctl restart ${SERVICE_NAME}'"
echo ""
