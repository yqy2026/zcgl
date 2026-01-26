
import sys
import os
from fastapi import FastAPI

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.main import app
from src.core.router_registry import route_registry

print("Registered Routes:")
for route in app.routes:
    if hasattr(route, "path"):
        print(f"{route.methods} {route.path}")

print("\nRoute Registry Info:")
# Force include to check if it's missing
# setup_app_routing(app) is called in main.py, so app.routes should have them.
