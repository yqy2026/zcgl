"""
Main Application Entry Point - English Version (Temporary)
"""

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Database imports
from .database import create_tables, get_database_status, init_db
from .core.config import settings
from .core.config_manager import get_config, initialize_config
from .core.exception_handler import setup_exception_handlers
from .core.response_handler import success_response

# Set up logging
logger = logging.getLogger(__name__)

# ===== Application Lifecycle Management =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager"""
    logger.info("Starting application initialization...")

    # Initialize database
    init_db()
    create_tables()

    # Get database status
    db_status = get_database_status()
    logger.info(f"Database status: {db_status}")

    yield

    logger.info("Application shutdown complete")

# Create FastAPI application instance
app = FastAPI(
    title="Land Property Asset Management System",
    description="Intelligent work platform for asset managers",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Initialize configuration
initialize_config()

# Set up CORS middleware
cors_origins = get_config("cors_origins", ["http://localhost:5173", "http://localhost:5174"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Set up exception handlers
setup_exception_handlers(app)

# Health check endpoint (must be defined before route registration)
@app.get("/api/v1/health", tags=["Health Check"])
async def health_check():
    """Health check endpoint - includes database status"""
    try:
        # Get database status
        db_status = get_database_status()

        health_data = {
            "status": "healthy",
            "version": "2.0.0",
            "service": "Land Property Asset Management System",
            "database": {
                "enhanced_active": db_status.get("enhanced_active", False),
                "enhanced_available": db_status.get("enhanced_available", False),
                "engine_type": db_status.get("engine_type", "Unknown"),
            },
        }

        return success_response(data=health_data, message="System running normally")

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "success": False,
            "status": "unhealthy",
            "timestamp": datetime.now(UTC).isoformat(),
            "error": str(e),
            "database": {"status": "unknown"},
        }

# Root endpoint
@app.get("/", tags=["Root Route"])
async def root_endpoint():
    """Root route endpoint"""
    return success_response(
        data={
            "service": "Land Property Asset Management System API",
            "version": "2.0.0",
            "docs_url": "/docs",
            "health_check": "/api/v1/health",
        },
        message="Welcome to Land Property Asset Management System API",
    )

# API v1 root path
@app.get("/api/v1/", tags=["Root Path"])
async def api_v1_root():
    """API v1 root path"""
    return success_response(
        data={
            "version": "2.0.0",
            "endpoints": {
                "health": "/api/v1/health",
                "assets": "/api/v1/assets",
                "auth": "/api/v1/auth",
                "docs": "/docs",
            },
        },
        message="API v1 root path",
    )

# Application info endpoint
@app.get("/api/v1/info", tags=["App Info"])
async def app_info():
    """Application info endpoint"""
    return success_response(
        data={
            "name": "Land Property Asset Management System",
            "version": "2.0.0",
            "description": "Intelligent work platform for asset managers",
            "docs_url": "/docs",
            "features": [
                "PDF Smart Import",
                "58-Field Asset Management",
                "RBAC Permission Control",
                "Real-time Data Analysis",
                "Excel Import/Export",
            ],
        },
        message="Application info retrieved successfully",
    )

# ===== API ROUTE REGISTRATION =====
# Manual route registration to ensure all business APIs are available

routes_added = []

# 1. Auth routes
try:
    from .api.v1.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["Authentication"])
    routes_added.append("Authentication")
    logger.info("Added authentication routes")
except ImportError as e:
    logger.warning(f"Could not add authentication routes: {e}")
    # Add basic login endpoint
    @app.post("/api/v1/auth/login")
    async def login(credentials: dict):
        """Basic login endpoint"""
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        if username == "admin" and password == "admin123":
            return {
                "success": True,
                "message": "Login successful",
                "user": {"id": 1, "username": "admin", "full_name": "System Administrator", "roles": ["admin"]},
                "token": "mock_token_admin"
            }
        else:
            return {"success": False, "message": "Invalid username or password"}

# 2. Asset management routes
try:
    from .api.v1.assets import router as asset_router
    app.include_router(asset_router, prefix="/api/v1/assets", tags=["Asset Management"])
    routes_added.append("Asset Management")
    logger.info("Added asset management routes")
except ImportError as e:
    logger.warning(f"Could not add asset management routes: {e}")

# 3. Rent contract routes
try:
    from .api.v1.rent_contract import router as rent_contract_router
    app.include_router(rent_contract_router, prefix="/api/v1/rental-contracts", tags=["Rent Contracts"])
    routes_added.append("Rent Contracts")
    logger.info("Added rent contract routes")
except ImportError as e:
    logger.warning(f"Could not add rent contract routes: {e}")

# 4. Statistics routes
try:
    from .api.v1.statistics import statistics_router
    app.include_router(statistics_router, prefix="/api/v1/analytics", tags=["Data Analytics"])
    routes_added.append("Data Analytics")
    logger.info("Added statistics routes")
except ImportError as e:
    logger.warning(f"Could not add statistics routes: {e}")

# 5. System management routes
try:
    from .api.v1.system import system_router
    app.include_router(system_router, prefix="/api/v1/system", tags=["System Management"])
    routes_added.append("System Management")
    logger.info("Added system management routes")
except ImportError as e:
    logger.warning(f"Could not add system management routes: {e}")

# 6. Excel processing routes
try:
    from .api.v1.excel import excel_router
    app.include_router(excel_router, prefix="/api/v1/excel", tags=["Excel Processing"])
    routes_added.append("Excel Processing")
    logger.info("Added excel processing routes")
except ImportError as e:
    logger.warning(f"Could not add excel processing routes: {e}")

logger.info(f"Manual route registration completed. Added {len(routes_added)} modules: {', '.join(routes_added)}")

# Final application startup
logger.info("FastAPI application startup completed")