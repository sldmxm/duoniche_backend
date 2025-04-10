#!/bin/bash
set -e

echo "Applying Alembic migrations..."
alembic upgrade head

echo "Starting application..."
exec "$@"