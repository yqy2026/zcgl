#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Production Security Configuration Tool
Configures secure production settings including secret keys, CORS, and middleware
"""

import sys
import os
import secrets
import hashlib
from datetime import datetime

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def generate_secure_secret_key():
    """Generate a cryptographically secure secret key"""
    return secrets.token_urlsafe(32)

def create_production_env_file():
    """Create production environment configuration file"""
    print("Creating Production Environment Configuration")
    print("=" * 60)

    # Generate secure values
    secret_key = generate_secure_secret_key()
    database_secret = generate_secure_secret_key()
    redis_password = generate_secure_secret_key()[:16]  # Shorter for Redis

    env_content = f"""# Production Environment Configuration
# Generated on: {datetime.now().isoformat()}

# Environment
ENVIRONMENT=production

# Application Settings
DEBUG=false
LOG_LEVEL=INFO

# Security Settings
SECRET_KEY={secret_key}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Database Configuration
DATABASE_URL=sqlite:///./data/land_property.db
DATABASE_ECHO=false
DATABASE_SECRET={database_secret}

# Redis Configuration (Optional)
REDIS_ENABLED=false
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD={redis_password}

# CORS Settings - RESTRICTIVE FOR PRODUCTION
CORS_ORIGINS=https://your-production-domain.com

# Server Configuration
HOST=0.0.0.0
PORT=8002
RELOAD=false

# File Upload Security
MAX_FILE_SIZE=52428800
UPLOAD_DIR=./uploads

# Authentication Security
MIN_PASSWORD_LENGTH=12
SESSION_EXPIRE_DAYS=7
MAX_FAILED_ATTEMPTS=5
LOCKOUT_DURATION=900
MAX_CONCURRENT_SESSIONS=3

# Rate Limiting
ENABLE_RATE_LIMITING=true
GLOBAL_RATE_LIMIT=1000
AUTH_RATE_LIMIT=100
USER_RATE_LIMIT=500

# Security Headers
ENABLE_SECURITY_HEADERS=true
ENABLE_CSP=true
ENABLE_HSTS=true

# Audit and Monitoring
ENABLE_AUDIT_LOG=true
AUDIT_LOG_RETENTION_DAYS=90
ENABLE_METRICS=true
SLOW_QUERY_THRESHOLD=1.0

# Cache Security
CACHE_TTL=3600
CACHE_PREFIX=zcgl_prod
"""

    env_file = ".env.production"
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)

    print(f"OK:  Production environment file created: {env_file}")
    print(f"OK:  Secret key generated: {secret_key[:16]}...")
    print(f"OK:  Security settings configured for production")

    return env_file

def create_development_env_file():
    """Create development environment configuration file"""
    print("\nCreating Development Environment Configuration")
    print("=" * 60)

    # Generate development values
    secret_key = generate_secure_secret_key()

    env_content = f"""# Development Environment Configuration
# Generated on: {datetime.now().isoformat()}

# Environment
ENVIRONMENT=development

# Application Settings
DEBUG=true
LOG_LEVEL=DEBUG
DEV_MODE=true

# Security Settings (Development Only)
SECRET_KEY={secret_key}
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=30

# Database Configuration
DATABASE_URL=sqlite:///./data/land_property.db
DATABASE_ECHO=true

# Redis Configuration
REDIS_ENABLED=false

# CORS Settings - Permissive for Development
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5173

# Server Configuration
HOST=127.0.0.1
PORT=8002
RELOAD=true

# File Upload Security
MAX_FILE_SIZE=52428800
UPLOAD_DIR=./uploads

# Authentication Security (Relaxed for Development)
MIN_PASSWORD_LENGTH=8
SESSION_EXPIRE_DAYS=30
MAX_FAILED_ATTEMPTS=10
LOCKOUT_DURATION=300
MAX_CONCURRENT_SESSIONS=10

# Rate Limiting (Relaxed for Development)
ENABLE_RATE_LIMITING=false
GLOBAL_RATE_LIMIT=10000
AUTH_RATE_LIMIT=1000
USER_RATE_LIMIT=5000

# Security Headers (Disabled for Development)
ENABLE_SECURITY_HEADERS=false
ENABLE_CSP=false
ENABLE_HSTS=false

# Audit and Monitoring
ENABLE_AUDIT_LOG=true
AUDIT_LOG_RETENTION_DAYS=7
ENABLE_METRICS=true
SLOW_QUERY_THRESHOLD=5.0

# Cache Configuration
CACHE_TTL=300
CACHE_PREFIX=zcgl_dev
"""

    env_file = ".env.development"
    with open(env_file, 'w', encoding='utf-8') as f:
        f.write(env_content)

    print(f"OK:  Development environment file created: {env_file}")
    print(f"OK:  Secret key generated: {secret_key[:16]}...")
    print(f"OK:  Development settings configured")

    return env_file

def update_main_config_security():
    """Update main configuration with enhanced security settings"""
    print("\nUpdating Main Configuration Security")
    print("=" * 60)

    try:
        from src.core.config import settings

        # Current security analysis
        print("Current Security Configuration Analysis:")
        print(f"  SECRET_KEY: {'Secure' if settings.SECRET_KEY != 'your-secret-key-change-in-production' else 'DEFAULT - NEEDS CHANGE'}")
        print(f"  DEBUG: {'Enabled' if settings.DEBUG else 'Disabled'}")
        print(f"  CORS_ORIGINS: {len(settings.CORS_ORIGINS)} origins configured")
        print(f"  ACCESS_TOKEN_EXPIRE_MINUTES: {settings.ACCESS_TOKEN_EXPIRE_MINUTES}")
        print(f"  MIN_PASSWORD_LENGTH: {settings.MIN_PASSWORD_LENGTH}")
        print(f"  SESSION_EXPIRE_DAYS: {settings.SESSION_EXPIRE_DAYS}")

        # Security recommendations
        print("\nSecurity Recommendations:")

        if settings.SECRET_KEY == "your-secret-key-change-in-production":
            print("  FAIL:  CRITICAL: Default secret key in use - IMMEDIATE ACTION REQUIRED")
        else:
            print("  OK:  Secret key appears to be customized")

        if settings.DEBUG and os.getenv("ENVIRONMENT") == "production":
            print("  FAIL:  WARNING: DEBUG mode enabled in production")
        else:
            print("  OK:  DEBUG mode appropriately configured")

        if settings.ACCESS_TOKEN_EXPIRE_MINUTES > 1440:
            print("  WARN:   WARNING: Access token lifetime exceeds 24 hours")
        else:
            print("  OK:  Access token lifetime is reasonable")

        if settings.MIN_PASSWORD_LENGTH < 12:
            print("  WARN:   WARNING: Password minimum length less than 12 characters")
        else:
            print("  OK:  Password minimum length is secure")

        return True

    except Exception as e:
        print(f"FAIL:  Failed to analyze security configuration: {e}")
        return False

def create_security_middleware_enhancement():
    """Create enhanced security middleware configuration"""
    print("\nCreating Enhanced Security Middleware")
    print("=" * 60)

    security_config = """# Enhanced Security Middleware Configuration
# Add to src/middleware/enhanced_security.py

from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.base import BaseHTTPMiddleware
import time
import hashlib
import hmac
from ..core.config import settings

class EnhancedSecurityMiddleware(BaseHTTPMiddleware):
    \"\"\"Enhanced security middleware for production\"\"\"

    def __init__(self, app):
        super().__init__(app)
        self.rate_limiter = {}  # In production, use Redis

    async def dispatch(self, request: Request, call_next):
        # Security headers
        if settings.ENABLE_SECURITY_HEADERS:
            response = await self.add_security_headers(request, call_next)
        else:
            response = await call_next(request)

        return response

    async def add_security_headers(self, request: Request, call_next):
        \"\"\"Add security headers to response\"\"\"
        response = await call_next(request)

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # XSS Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Content Security Policy (if enabled)
        if settings.ENABLE_CSP:
            csp = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
            response.headers["Content-Security-Policy"] = csp

        # HSTS (if enabled and HTTPS)
        if settings.ENABLE_HSTS and request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response

# Rate limiting middleware
class RateLimitMiddleware(BaseHTTPMiddleware):
    \"\"\"Rate limiting middleware\"\"\"

    def __init__(self, app):
        super().__init__(app)
        self.requests = {}  # In production, use Redis

    async def dispatch(self, request: Request, call_next):
        if not settings.ENABLE_RATE_LIMITING:
            return await call_next(request)

        client_ip = self.get_client_ip(request)
        now = time.time()

        # Clean old requests
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if now - req_time < 3600  # 1 hour window
            ]
        else:
            self.requests[client_ip] = []

        # Check rate limit
        if len(self.requests[client_ip]) >= settings.GLOBAL_RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded"}
            )

        # Record request
        self.requests[client_ip].append(now)

        return await call_next(request)

    def get_client_ip(self, request: Request) -> str:
        \"\"\"Get client IP address\"\"\"
        # Check for forwarded headers
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        return request.client.host if request.client else "unknown"
"""

    config_file = "enhanced_security_config.py"
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(security_config)

    print(f"OK:  Enhanced security middleware configuration created: {config_file}")
    print(f"OK:  Security headers configuration included")
    print(f"OK:  Rate limiting middleware defined")
    print(f"OK:  CSP and HSTS support included")

    return config_file

def create_production_startup_script():
    """Create production startup script"""
    print("\nCreating Production Startup Script")
    print("=" * 60)

    if os.name == "nt":  # Windows
        script_content = """@echo off
title Production Server Startup

echo Starting Production Server...
cd /d %~dp0

REM Check for production environment file
if not exist ".env.production" (
    echo ERROR: .env.production file not found
    echo Please run: python configure_production_security.py
    pause
    exit /b 1
)

REM Set environment to production
set ENVIRONMENT=production

REM Check if SSL certificates exist (optional)
if exist "ssl\\cert.pem" (
    echo SSL certificates found, starting HTTPS server...
    uv run python -m uvicorn src.main:app --host 0.0.0.0 --port 8002 --ssl-keyfile=ssl\\key.pem --ssl-certfile=ssl\\cert.pem
) else (
    echo Starting HTTP server (SSL recommended for production)...
    uv run python -m uvicorn src.main:app --host 0.0.0.0 --port 8002 --workers 4
)

pause
"""

        script_path = "start_production.bat"
    else:  # Unix/Linux
        script_content = """#!/bin/bash

echo "Starting Production Server..."

# Check for production environment file
if [ ! -f ".env.production" ]; then
    echo "ERROR: .env.production file not found"
    echo "Please run: python configure_production_security.py"
    exit 1
fi

# Set environment to production
export ENVIRONMENT=production

# Check if SSL certificates exist (optional)
if [ -f "ssl/cert.pem" ]; then
    echo "SSL certificates found, starting HTTPS server..."
    uv run python -m uvicorn src.main:app --host 0.0.0.0 --port 8002 --ssl-keyfile=ssl/key.pem --ssl-certfile=ssl/cert.pem --workers 4
else
    echo "Starting HTTP server (SSL recommended for production)..."
    uv run python -m uvicorn src.main:app --host 0.0.0.0 --port 8002 --workers 4
fi
"""

        script_path = "start_production.sh"
        os.chmod(script_path, 0o755)

    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)

    print(f"OK:  Production startup script created: {script_path}")
    print(f"OK:  SSL certificate detection included")
    print(f"OK:  Multi-worker configuration ready")

    return script_path

def create_ssl_certificate_guide():
    """Create SSL certificate setup guide"""
    print("\nCreating SSL Certificate Setup Guide")
    print("=" * 60)

    ssl_guide = """# SSL Certificate Setup Guide

## For Development (Self-Signed Certificate)

### 1. Create SSL directory
mkdir ssl

### 2. Generate self-signed certificate (OpenSSL required)
openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes -subj "/C=CN/ST=State/L=City/O=Organization/CN=localhost"

### 3. Test HTTPS server
./start_production.sh  # or start_production.bat on Windows

## For Production

### Option 1: Let's Encrypt (Recommended)
1. Install certbot: `sudo apt-get install certbot` or `brew install certbot`
2. Obtain certificate: `sudo certbot certonly --standalone -d your-domain.com`
3. Copy certificates to ssl/ directory:
   - Certificate: `/etc/letsencrypt/live/your-domain.com/fullchain.pem` → `ssl/cert.pem`
   - Private key: `/etc/letsencrypt/live/your-domain.com/privkey.pem` → `ssl/key.pem`

### Option 2: Commercial SSL Certificate
1. Purchase SSL certificate from provider (DigiCert, Comodo, etc.)
2. Generate CSR: `openssl req -new -newkey rsa:4096 -nodes -keyout ssl/private.key -out ssl/certificate.csr`
3. Submit CSR to certificate provider
4. Download and install certificates in ssl/ directory

### Certificate Security Best Practices
- Use RSA 4096-bit or ECC certificates
- Set certificate expiration to maximum 1 year
- Use TLS 1.2 or higher only
- Implement certificate renewal automation
- Monitor certificate expiration alerts

## Testing SSL Configuration

### Test HTTPS endpoints
curl -k https://localhost:8002/health

### Check SSL certificate details
openssl s_client -connect localhost:8002 -servername localhost

### SSL Security Test
nmap --script ssl-enum-ciphers -p 8002 localhost
"""

    guide_file = "SSL_SETUP_GUIDE.md"
    with open(guide_file, 'w', encoding='utf-8') as f:
        f.write(ssl_guide)

    print(f"OK:  SSL setup guide created: {guide_file}")
    print(f"OK:  Development and production options included")
    print(f"OK:  Certificate management instructions provided")

    return guide_file

def run_security_audit():
    """Run comprehensive security audit"""
    print("\nRunning Security Audit")
    print("=" * 60)

    security_issues = []
    recommendations = []

    try:
        from src.core.config import settings

        # Check secret key
        if settings.SECRET_KEY == "your-secret-key-change-in-production":
            security_issues.append("CRITICAL: Default secret key in use")
            recommendations.append("Generate and set a secure SECRET_KEY immediately")

        # Check debug mode
        if settings.DEBUG:
            security_issues.append("HIGH: Debug mode enabled")
            recommendations.append("Disable DEBUG mode in production")

        # Check CORS configuration
        if "*" in settings.CORS_ORIGINS or "localhost" in str(settings.CORS_ORIGINS):
            security_issues.append("MEDIUM: Permissive CORS configuration")
            recommendations.append("Restrict CORS origins to specific domains")

        # Check token expiration
        if settings.ACCESS_TOKEN_EXPIRE_MINUTES > 1440:
            security_issues.append("MEDIUM: Long access token lifetime")
            recommendations.append("Reduce ACCESS_TOKEN_EXPIRE_MINUTES to 30-60 minutes")

        # Check password policy
        if settings.MIN_PASSWORD_LENGTH < 12:
            security_issues.append("MEDIUM: Weak password requirements")
            recommendations.append("Set MIN_PASSWORD_LENGTH to 12 or higher")

        # Check session duration
        if settings.SESSION_EXPIRE_DAYS > 7:
            security_issues.append("LOW: Long session duration")
            recommendations.append("Set SESSION_EXPIRE_DAYS to 7 or less")

        # Output results
        print(f"Security Audit Results:")
        print(f"  Issues found: {len(security_issues)}")
        print(f"  Recommendations: {len(recommendations)}")

        if security_issues:
            print("\nCRITICAL - Security Issues:")
            for issue in security_issues:
                print(f"  - {issue}")

        if recommendations:
            print("\nINFO - Recommendations:")
            for rec in recommendations:
                print(f"  - {rec}")

        if not security_issues:
            print("\nOK: No critical security issues detected")

        return len(security_issues) == 0

    except Exception as e:
        print(f"FAIL:  Security audit failed: {e}")
        return False

if __name__ == "__main__":
    print("Production Security Configuration Tool")
    print("=" * 70)
    print(f"Time: {datetime.now()}")
    print("=" * 70)

    # Run security audit first
    print("\n1. SECURITY AUDIT")
    security_ok = run_security_audit()

    # Create production environment file
    print("\n2. PRODUCTION CONFIGURATION")
    prod_env = create_production_env_file()

    # Create development environment file
    print("\n3. DEVELOPMENT CONFIGURATION")
    dev_env = create_development_env_file()

    # Update main configuration
    print("\n4. MAIN CONFIGURATION UPDATE")
    config_ok = update_main_config_security()

    # Create enhanced security middleware
    print("\n5. ENHANCED SECURITY MIDDLEWARE")
    security_config = create_security_middleware_enhancement()

    # Create production startup script
    print("\n6. PRODUCTION STARTUP")
    startup_script = create_production_startup_script()

    # Create SSL guide
    print("\n7. SSL CERTIFICATE SETUP")
    ssl_guide = create_ssl_certificate_guide()

    # Final summary
    print("\n" + "=" * 70)
    print("PRODUCTION SECURITY CONFIGURATION COMPLETE")
    print("=" * 70)

    print("\nFiles Created:")
    print(f"  - {prod_env} (Production environment)")
    print(f"  - {dev_env} (Development environment)")
    print(f"  - {security_config} (Enhanced security middleware)")
    print(f"  - {startup_script} (Production startup script)")
    print(f"  - {ssl_guide} (SSL certificate setup guide)")

    print("\nNext Steps:")
    print("  1. Copy .env.production to .env and customize values")
    print("  2. Generate SSL certificates using SSL_SETUP_GUIDE.md")
    print("  3. Test with: ./start_production.sh or start_production.bat")
    print("  4. Configure reverse proxy (nginx/Apache) for production")
    print("  5. Set up monitoring and backups")

    if security_issues:
        print("\nREMAINING ACTIONS:")
        for rec in recommendations:
            print(f"  - {rec}")

    print("\nProduction security configuration completed successfully!")