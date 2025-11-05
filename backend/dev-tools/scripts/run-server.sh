#!/bin/bash
cd backend && uv run python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8002
