#!/bin/bash
set -e

echo "Waiting for database..."
while ! python -c "
import asyncio, asyncpg, os
async def check():
    url = os.environ['DATABASE_URL'].replace('+asyncpg', '')
    conn = await asyncpg.connect(url)
    await conn.close()
asyncio.run(check())
" 2>/dev/null; do
  sleep 1
done
echo "Database ready."

echo "Running migrations..."
alembic upgrade head

echo "Seeding data..."
python -m scripts.seed

echo "Starting API server..."
exec "$@"
