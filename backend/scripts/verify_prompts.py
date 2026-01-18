#!/usr/bin/env python3
"""Verify prompts were created in database"""

import sys
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables before importing database
load_dotenv()

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import get_session_factory
from src.models.llm_prompt import PromptTemplate


def verify_prompts():
    """Verify property cert prompts exist"""
    session_local = get_session_factory()
    db = session_local()
    try:
        prompts = (
            db.query(PromptTemplate)
            .filter(PromptTemplate.doc_type == "PROPERTY_CERT")
            .all()
        )

        print(f"Found {len(prompts)} prompts")
        for p in prompts:
            print(f"  - {p.name} (version: {p.version}, status: {p.status})")

        return len(prompts)
    finally:
        db.close()


if __name__ == "__main__":
    count = verify_prompts()
    sys.exit(0 if count == 4 else 1)
