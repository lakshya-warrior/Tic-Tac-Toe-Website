#!/bin/bash

# 1. Sync dependencies and create .env if not exists
uv sync

if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
fi

# 2. Determine Compose command
if command -v podman &> /dev/null; then
    COMPOSE="podman-compose"
    ENGINE="podman"
elif command -v docker &> /dev/null; then
    ENGINE="docker"
    if docker compose version &> /dev/null; then
        COMPOSE="docker compose"
    else
        COMPOSE="docker-compose"
    fi
else
    echo "Error: Neither Docker nor Podman found."
    exit 1
fi

$COMPOSE up -d

# 3. Wait for MySQL service inside to be ready
echo -n "Waiting for MySQL to initialize"
until $COMPOSE exec -T mysql-db mysqladmin ping -u root -parena_root --silent 2>/dev/null; do
    echo -n "."
    sleep 1
done

echo -e "\n✅ MySQL is ready!"

# 4. Inject Schema and Harvest (only if needed)
echo "Injecting SQL schema..."
cat init.sql | $COMPOSE exec -T mysql-db mysql -u root -parena_root arena_db

echo "Running data harvest..."
uv run harvest_data.py

# 5. Start FastAPI Server
echo "Starting App..."
uv run python -m app.main