#!/bin/bash
set -e

echo "🔐 Generating strong secrets for production deployment..."
echo ""

SECRET_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")
DATA_ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_urlsafe(32))")

echo "Add these to your environment or secrets manager:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "SECRET_KEY=\"$SECRET_KEY\""
echo "DATA_ENCRYPTION_KEY=\"$DATA_ENCRYPTION_KEY\""
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  IMPORTANT:"
echo "  • Store these securely in your secrets manager"
echo "  • Do not commit to version control"
echo "  • Rotate keys every 90 days"
echo "  • Test key recovery procedures before production deployment"
