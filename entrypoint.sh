#!/bin/sh
set -eu

if [ "${ALEMBIC_BASELINE_EXISTING_SCHEMA:-false}" = "true" ]; then
    alembic stamp head
else
    alembic upgrade head
fi

exec python src/main.py
