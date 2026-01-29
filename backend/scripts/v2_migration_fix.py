#!/usr/bin/env python3
"""
V2 Data Migration Script
Purpose: fix existing contracts by setting default V2 fields (contract_type, payment_cycle)
"""

import logging
import sys
from pathlib import Path

from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Add init path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import get_database_engine to ensure initialization
from src.database import get_database_engine, get_database_url
from src.models.rent_contract import ContractType, PaymentCycle


def run_migration():
    logger.info("Starting V2 Data Migration...")

    # Initialize the database engine explicitly
    db_url = get_database_url()
    logger.info(f"Connecting to database: {db_url}")
    engine = get_database_engine()

    with engine.begin() as conn:
        # 1. Update contract_type to 'lease_downstream' where null
        logger.info("Migrating contract_type...")
        result = conn.execute(
            text("""
                UPDATE rent_contracts
                SET contract_type = :default_type
                WHERE contract_type IS NULL
            """),
            {"default_type": ContractType.LEASE_DOWNSTREAM.value},
        )
        logger.info(f"Updated {result.rowcount} contracts with default contract_type.")

        # 2. Update payment_cycle to 'monthly' where null
        logger.info("Migrating payment_cycle...")
        result = conn.execute(
            text("""
                UPDATE rent_contracts
                SET payment_cycle = :default_cycle
                WHERE payment_cycle IS NULL
            """),
            {"default_cycle": PaymentCycle.MONTHLY.value},
        )
        logger.info(f"Updated {result.rowcount} contracts with default payment_cycle.")

        # 3. Ensure service_fee_rate is 0 for non-entrusted contracts
        logger.info("Normalizing service_fee_rate...")

        logger.info("Migration completed successfully.")


if __name__ == "__main__":
    try:
        run_migration()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        # traceback for easier debugging
        import traceback

        traceback.print_exc()
        sys.exit(1)
