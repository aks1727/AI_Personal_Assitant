#!/bin/bash

echo "=== Compile ==="
python -m compileall .

echo "=== Ruff Lint ==="
ruff check .

echo "=== Ruff Format ==="
ruff format --check .

echo "=== MyPy ==="
mypy .

echo "=== Bandit ==="
bandit -r .

echo "=== Dependency Audit ==="
pip-audit

echo "=== Tests ==="
pytest -v