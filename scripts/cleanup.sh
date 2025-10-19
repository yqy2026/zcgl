#!/bin/bash

# Project Cleanup Script
# This script cleans up temporary files and maintains project structure

echo "Starting project cleanup..."

# Clean up Python cache files
echo "Cleaning Python cache files..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# Clean up SQLite temporary files
echo "Cleaning SQLite temporary files..."
find . -name "*.db-journal" -delete 2>/dev/null || true
find . -name "*.db-shm" -delete 2>/dev/null || true
find . -name "*.db-wal" -delete 2>/dev/null || true

# Clean up frontend build artifacts
echo "Cleaning frontend build artifacts..."
cd frontend 2>/dev/null || true
rm -rf dist/ build/ .vite/ node_modules/.cache 2>/dev/null || true
cd .. 2>/dev/null || true

# Clean up test files and temporary databases
echo "Cleaning test files..."
cd backend 2>/dev/null || true
rm -f test_*.py simple_rbac_test.py test_api.db test_api.db-journal 2>/dev/null || true
rm -rf .pytest_cache 2>/dev/null || true
rm -rf workspace/ 2>/dev/null || true
cd .. 2>/dev/null || true

# Clean up log files (only if not in use)
echo "Cleaning old log files..."
find . -name "*.log" -mtime +7 -delete 2>/dev/null || true

# Clean up temporary files
echo "Cleaning temporary files..."
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.temp" -delete 2>/dev/null || true
find . -name "*.bak" -delete 2>/dev/null || true
find . -name "*~" -delete 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "Thumbs.db" -delete 2>/dev/null || true

echo "Project cleanup completed!"