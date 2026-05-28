#!/usr/bin/env python3
"""
Seeds the RadSight database with initial users and sample data.
Usage: python scripts/seed_data.py
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import bcrypt

load_dotenv()

SEED_USERS = [
    {
        "email": "admin@radsight.health",
        "full_name": "System Administrator",
        "role": "admin",
        "password": "RadSight@Admin2024",
        "department": "Administration",
    },
    {
        "email": "radiologist@radsight.health",
        "full_name": "Dr. Sarah Mitchell",
        "role": "radiologist",
        "password": "RadSight@Rad2024",
        "department": "Radiology",
    },
    {
        "email": "clinician@radsight.health",
        "full_name": "Dr. James Okafor",
        "role": "clinician",
        "password": "RadSight@Clin2024",
        "department": "Internal Medicine",
    },
]


async def seed_users(db) -> None:
    collection = db["users"]
    from datetime import datetime, timezone

    for user_data in SEED_USERS:
        existing = await collection.find_one({"email": user_data["email"]})
        if existing:
            print(f"  Skipping {user_data['email']} (already exists)")
            continue

        hashed = bcrypt.hashpw(user_data["password"].encode(), bcrypt.gensalt(12)).decode()
        now = datetime.now(timezone.utc)

        await collection.insert_one({
            "email": user_data["email"],
            "full_name": user_data["full_name"],
            "role": user_data["role"],
            "status": "active",
            "hashed_password": hashed,
            "department": user_data["department"],
            "last_login": None,
            "reports_processed": 0,
            "created_at": now,
            "updated_at": now,
        })
        print(f"  Created {user_data['role']}: {user_data['email']}")


async def main():
    mongodb_uri = os.getenv("MONGODB_URI")
    if not mongodb_uri:
        print("Error: MONGODB_URI not set in .env")
        sys.exit(1)

    client = AsyncIOMotorClient(mongodb_uri, serverSelectionTimeoutMS=5000)
    db = client[os.getenv("MONGODB_DB_NAME", "radsight")]

    print("Seeding RadSight database...\n")

    print("Users:")
    await seed_users(db)

    client.close()
    print("\nSeed complete.")
    print("\nDefault credentials:")
    for u in SEED_USERS:
        print(f"  {u['role']:15} {u['email']:35} {u['password']}")


if __name__ == "__main__":
    asyncio.run(main())
