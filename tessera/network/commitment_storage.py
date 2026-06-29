"""
Storage abstraction for customer commitment registration.
Supports SQLite (default) with interface for other backends.
"""

import time
import json
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from pathlib import Path

import aiosqlite


class CommitmentStorage(ABC):
    """Abstract base class for commitment storage backends."""

    @abstractmethod
    async def initialize(self):
        """Initialize the storage backend."""
        pass

    @abstractmethod
    async def register_commitment(
        self,
        customer_id: str,
        commitment: str,
        device_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Register a customer's commitment."""
        pass

    @abstractmethod
    async def get_customer_commitments(self, customer_id: str) -> List[Dict]:
        """Get all commitments for a customer."""
        pass

    @abstractmethod
    async def get_commitment_customer(self, commitment: str) -> Optional[str]:
        """Get customer ID for a commitment."""
        pass

    @abstractmethod
    async def remove_commitment(self, customer_id: str, commitment: str) -> bool:
        """Remove a specific commitment."""
        pass

    @abstractmethod
    async def remove_customer(self, customer_id: str) -> int:
        """Remove all commitments for a customer. Returns count removed."""
        pass

    @abstractmethod
    async def list_customers(self, limit: int = 100, offset: int = 0) -> List[str]:
        """List customer IDs."""
        pass

    @abstractmethod
    async def get_stats(self) -> Dict:
        """Get storage statistics."""
        pass

    @abstractmethod
    async def close(self):
        """Close the storage backend."""
        pass


class SQLiteCommitmentStorage(CommitmentStorage):
    """SQLite-based commitment storage."""

    def __init__(self, db_path: str = "commitments.db"):
        self.db_path = db_path
        self._initialized = False

    async def initialize(self):
        """Initialize SQLite database."""
        if self._initialized:
            return

        # Ensure directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")

            # Customers table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS customers (
                    customer_id TEXT PRIMARY KEY,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    metadata TEXT
                )
            """)

            # Commitments table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS commitments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT NOT NULL,
                    commitment TEXT NOT NULL UNIQUE,
                    device_id TEXT,
                    registered_at INTEGER NOT NULL,
                    metadata TEXT,
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
                )
            """)

            # Indexes
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_commitments_customer
                ON commitments(customer_id)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_commitments_commitment
                ON commitments(commitment)
            """)

            await db.commit()

        self._initialized = True

    async def register_commitment(
        self,
        customer_id: str,
        commitment: str,
        device_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Register a customer's commitment."""
        now = int(time.time())

        async with aiosqlite.connect(self.db_path) as db:
            # Ensure customer exists
            await db.execute(
                """
                INSERT INTO customers (customer_id, created_at, updated_at, metadata)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(customer_id) DO UPDATE SET updated_at = ?
            """,
                (customer_id, now, now, json.dumps({}), now),
            )

            # Check if commitment already exists
            cursor = await db.execute(
                "SELECT customer_id FROM commitments WHERE commitment = ?",
                (commitment,),
            )
            existing = await cursor.fetchone()

            if existing:
                if existing[0] != customer_id:
                    raise ValueError(
                        f"Commitment already registered to different customer"
                    )
                # Update existing
                await db.execute(
                    """
                    UPDATE commitments
                    SET device_id = ?, metadata = ?, registered_at = ?
                    WHERE commitment = ?
                """,
                    (device_id, json.dumps(metadata or {}), now, commitment),
                )
            else:
                # Insert new
                await db.execute(
                    """
                    INSERT INTO commitments (customer_id, commitment, device_id, registered_at, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        customer_id,
                        commitment,
                        device_id,
                        now,
                        json.dumps(metadata or {}),
                    ),
                )

            await db.commit()

            # Get total devices for customer
            cursor = await db.execute(
                "SELECT COUNT(*) FROM commitments WHERE customer_id = ?", (customer_id,)
            )
            total = (await cursor.fetchone())[0]

        return {
            "customer_id": customer_id,
            "commitment": commitment,
            "device_id": device_id,
            "registered_at": now,
            "total_devices": total,
        }

    async def get_customer_commitments(self, customer_id: str) -> List[Dict]:
        """Get all commitments for a customer."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT commitment, device_id, registered_at, metadata
                FROM commitments
                WHERE customer_id = ?
                ORDER BY registered_at DESC
            """,
                (customer_id,),
            )

            rows = await cursor.fetchall()

        return [
            {
                "commitment": row["commitment"],
                "device_id": row["device_id"],
                "registered_at": row["registered_at"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
            }
            for row in rows
        ]

    async def get_commitment_customer(self, commitment: str) -> Optional[str]:
        """Get customer ID for a commitment."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT customer_id FROM commitments WHERE commitment = ?",
                (commitment,),
            )
            row = await cursor.fetchone()

        return row[0] if row else None

    async def remove_commitment(self, customer_id: str, commitment: str) -> bool:
        """Remove a specific commitment."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                DELETE FROM commitments
                WHERE customer_id = ? AND commitment = ?
            """,
                (customer_id, commitment),
            )
            await db.commit()

        return cursor.rowcount > 0

    async def remove_customer(self, customer_id: str) -> int:
        """Remove all commitments for a customer."""
        async with aiosqlite.connect(self.db_path) as db:
            # Remove commitments
            cursor = await db.execute(
                "DELETE FROM commitments WHERE customer_id = ?", (customer_id,)
            )
            count = cursor.rowcount

            # Remove customer
            await db.execute(
                "DELETE FROM customers WHERE customer_id = ?", (customer_id,)
            )

            await db.commit()

        return count

    async def list_customers(self, limit: int = 100, offset: int = 0) -> List[str]:
        """List customer IDs."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT customer_id FROM customers
                ORDER BY updated_at DESC
                LIMIT ? OFFSET ?
            """,
                (limit, offset),
            )

            rows = await cursor.fetchall()

        return [row[0] for row in rows]

    async def get_stats(self) -> Dict:
        """Get storage statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            # Total customers
            cursor = await db.execute("SELECT COUNT(*) FROM customers")
            total_customers = (await cursor.fetchone())[0]

            # Total commitments
            cursor = await db.execute("SELECT COUNT(*) FROM commitments")
            total_commitments = (await cursor.fetchone())[0]

            # Database size
            cursor = await db.execute(
                "SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size()"
            )
            db_size = (await cursor.fetchone())[0]

        return {
            "total_customers": total_customers,
            "total_commitments": total_commitments,
            "db_size_bytes": db_size,
        }

    async def vacuum(self):
        """Compact the database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("VACUUM")

    async def close(self):
        """Close storage (no-op for SQLite, connections are per-operation)."""
        pass


class MemoryCommitmentStorage(CommitmentStorage):
    """In-memory commitment storage for testing."""

    def __init__(self):
        self.customers: Dict[str, Dict] = {}
        self.commitments: Dict[str, Dict] = {}
        self.commitment_to_customer: Dict[str, str] = {}

    async def initialize(self):
        pass

    async def register_commitment(
        self,
        customer_id: str,
        commitment: str,
        device_id: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        now = int(time.time())

        # Check if commitment exists for different customer
        if commitment in self.commitment_to_customer:
            if self.commitment_to_customer[commitment] != customer_id:
                raise ValueError("Commitment already registered to different customer")

        # Ensure customer exists
        if customer_id not in self.customers:
            self.customers[customer_id] = {"created_at": now, "commitments": []}

        # Register commitment
        self.commitments[commitment] = {
            "customer_id": customer_id,
            "commitment": commitment,
            "device_id": device_id,
            "registered_at": now,
            "metadata": metadata or {},
        }
        self.commitment_to_customer[commitment] = customer_id

        if commitment not in self.customers[customer_id]["commitments"]:
            self.customers[customer_id]["commitments"].append(commitment)

        return {
            "customer_id": customer_id,
            "commitment": commitment,
            "device_id": device_id,
            "registered_at": now,
            "total_devices": len(self.customers[customer_id]["commitments"]),
        }

    async def get_customer_commitments(self, customer_id: str) -> List[Dict]:
        if customer_id not in self.customers:
            return []

        return [
            self.commitments[c]
            for c in self.customers[customer_id]["commitments"]
            if c in self.commitments
        ]

    async def get_commitment_customer(self, commitment: str) -> Optional[str]:
        return self.commitment_to_customer.get(commitment)

    async def remove_commitment(self, customer_id: str, commitment: str) -> bool:
        if commitment not in self.commitments:
            return False

        if self.commitments[commitment]["customer_id"] != customer_id:
            return False

        del self.commitments[commitment]
        del self.commitment_to_customer[commitment]

        if customer_id in self.customers:
            self.customers[customer_id]["commitments"].remove(commitment)

        return True

    async def remove_customer(self, customer_id: str) -> int:
        if customer_id not in self.customers:
            return 0

        count = 0
        for commitment in self.customers[customer_id]["commitments"]:
            if commitment in self.commitments:
                del self.commitments[commitment]
                del self.commitment_to_customer[commitment]
                count += 1

        del self.customers[customer_id]
        return count

    async def list_customers(self, limit: int = 100, offset: int = 0) -> List[str]:
        customers = list(self.customers.keys())
        return customers[offset : offset + limit]

    async def get_stats(self) -> Dict:
        return {
            "total_customers": len(self.customers),
            "total_commitments": len(self.commitments),
            "db_size_bytes": 0,
        }

    async def close(self):
        pass


def create_commitment_storage(backend: str = "sqlite", **kwargs) -> CommitmentStorage:
    """Factory function to create commitment storage."""
    if backend == "sqlite":
        return SQLiteCommitmentStorage(kwargs.get("db_path", "commitments.db"))
    elif backend == "memory":
        return MemoryCommitmentStorage()
    else:
        raise ValueError(f"Unknown storage backend: {backend}")
