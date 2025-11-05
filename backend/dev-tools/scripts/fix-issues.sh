#!/bin/bash
cd backend && uv run ruff check src/ --fix
