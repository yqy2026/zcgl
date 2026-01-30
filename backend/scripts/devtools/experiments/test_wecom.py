#!/usr/bin/env python3
"""
WeCom Integration Test Script
Purpose: Verify Enterprise WeChat message delivery
"""

import asyncio
import logging
import sys
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.core.config import settings
from src.services.notification.wecom_service import wecom_service


async def test_wecom():
    logger.info("Starting WeCom Integration Test...")

    # 1. Check Configuration
    webhook_url = getattr(settings, "WECOM_WEBHOOK_URL", None)
    enabled = getattr(settings, "WECOM_ENABLED", False)

    logger.info(f"WeCom Enabled: {enabled}")
    logger.info(f"Webhook URL Configured: {'Yes' if webhook_url else 'No'}")

    if not webhook_url:
        logger.warning(
            "SKIPPING: WECOM_WEBHOOK_URL is not set in environment or config."
        )
        return

    # 2. Test Text Message
    logger.info("Sending Test Text Message...")
    success = await wecom_service.send_notification(
        message="[Test] This is a verification message from Land Property Management System V2."
    )
    if success:
        logger.info("✅ Text Message Sent Successfully")
    else:
        logger.error("❌ Text Message Failed")

    # 3. Test Markdown Message
    logger.info("Sending Test Markdown Message...")
    success = await wecom_service.send_markdown_notification(
        title="System Verification",
        content="**Test Notification**\n\n> This is a markdown test.\n\n- Item 1\n- Item 2",
    )
    if success:
        logger.info("✅ Markdown Message Sent Successfully")
    else:
        logger.error("❌ Markdown Message Failed")


if __name__ == "__main__":
    try:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(test_wecom())
    except Exception as e:
        logger.error(f"Test failed: {e}")
        sys.exit(1)
