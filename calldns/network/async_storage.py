"""
Async SQLite persistence layer for CallDNS decentralized nodes.
Uses aiosqlite for non-blocking database operations.
"""

import aiosqlite
import json
import time
import base64
from typing import Dict, List, Optional, Any
from pathlib import Path


class AsyncNodeStorage:
    """
    Async SQLite-based storage for CallDNS nodes.

    Handles persistence for:
    - Proof cache with TTL
    - Customer subscriptions
    - Peer connections
    - Pending proofs for pull model
    - Node statistics
    """

    def __init__(self, db_path: str = "calldns_node.db"):
        """
        Initialize node storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._initialized = False

    async def initialize(self):
        """Initialize database schema."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            # Enable WAL mode for better concurrent performance
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA synchronous=NORMAL")

            # Proofs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS proofs (
                    proof_id TEXT PRIMARY KEY,
                    bucket INTEGER NOT NULL,
                    bloom_fingerprint TEXT NOT NULL,
                    proof_data TEXT NOT NULL,
                    org_hint TEXT,
                    timestamp INTEGER NOT NULL,
                    received_at INTEGER NOT NULL,
                    from_peer TEXT,
                    expires_at INTEGER NOT NULL
                )
            """)

            # Indexes
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_proofs_bucket
                ON proofs(bucket, timestamp)
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_proofs_expires
                ON proofs(expires_at)
            """)

            # Subscriptions table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS subscriptions (
                    subscriber_id TEXT PRIMARY KEY,
                    bucket INTEGER NOT NULL,
                    bloom_filter BLOB NOT NULL,
                    org_hints TEXT,
                    time_window INTEGER NOT NULL,
                    created_at INTEGER NOT NULL,
                    last_seen INTEGER NOT NULL
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_subscriptions_bucket
                ON subscriptions(bucket)
            """)

            # Pending proofs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pending_proofs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscriber_id TEXT NOT NULL,
                    proof_id TEXT NOT NULL,
                    queued_at INTEGER NOT NULL
                )
            """)

            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_pending_subscriber
                ON pending_proofs(subscriber_id, queued_at)
            """)

            # Peers table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS peers (
                    peer_id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    address TEXT NOT NULL,
                    port INTEGER NOT NULL,
                    connected_at INTEGER NOT NULL,
                    last_seen INTEGER NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    metadata TEXT
                )
            """)

            # Statistics table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    stat_key TEXT PRIMARY KEY,
                    stat_value INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)

            # Configuration table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            await db.commit()
            self._initialized = True

    # ─────────────────────────────────────────────────────────────
    # Proof Storage
    # ─────────────────────────────────────────────────────────────

    async def store_proof(self, proof_id: str, proof: dict, from_peer: str = None,
                         ttl: int = 3600) -> bool:
        """Store a proof in the database."""
        async with aiosqlite.connect(self.db_path) as db:
            current_time = int(time.time())
            expires_at = current_time + ttl

            try:
                await db.execute("""
                    INSERT INTO proofs
                    (proof_id, bucket, bloom_fingerprint, proof_data, org_hint,
                     timestamp, received_at, from_peer, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    proof_id,
                    proof.get("bucket"),
                    proof.get("bloom_fingerprint", ""),
                    json.dumps(proof),
                    proof.get("org_hint"),
                    proof.get("timestamp", current_time),
                    current_time,
                    from_peer,
                    expires_at
                ))
                await db.commit()
                return True
            except aiosqlite.IntegrityError:
                return False

    async def get_proof(self, proof_id: str) -> Optional[dict]:
        """Get a proof by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT proof_data FROM proofs WHERE proof_id = ?",
                (proof_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row["proof_data"])
                return None

    async def proof_exists(self, proof_id: str) -> bool:
        """Check if proof already exists."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT 1 FROM proofs WHERE proof_id = ?",
                (proof_id,)
            ) as cursor:
                return await cursor.fetchone() is not None

    async def get_proofs_by_bucket(self, bucket: int, since_timestamp: int = 0) -> List[dict]:
        """Get all proofs in a bucket since timestamp."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("""
                SELECT proof_data FROM proofs
                WHERE bucket = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (bucket, since_timestamp)) as cursor:
                rows = await cursor.fetchall()
                return [json.loads(row["proof_data"]) for row in rows]

    async def cleanup_expired_proofs(self) -> int:
        """Remove expired proofs."""
        async with aiosqlite.connect(self.db_path) as db:
            current_time = int(time.time())

            # Delete pending references first
            await db.execute("""
                DELETE FROM pending_proofs
                WHERE proof_id IN (
                    SELECT proof_id FROM proofs WHERE expires_at < ?
                )
            """, (current_time,))

            # Delete proofs
            cursor = await db.execute(
                "DELETE FROM proofs WHERE expires_at < ?",
                (current_time,)
            )
            deleted = cursor.rowcount
            await db.commit()
            return deleted

    # ─────────────────────────────────────────────────────────────
    # Subscription Storage
    # ─────────────────────────────────────────────────────────────

    async def store_subscription(self, subscriber_id: str, subscription: dict):
        """Store or update a subscription."""
        async with aiosqlite.connect(self.db_path) as db:
            current_time = int(time.time())
            org_hints = json.dumps(subscription.get("org_hints", []))

            bloom_filter = subscription.get("bloom_filter", b"")
            if isinstance(bloom_filter, str):
                bloom_filter = base64.b64decode(bloom_filter)

            await db.execute("""
                INSERT OR REPLACE INTO subscriptions
                (subscriber_id, bucket, bloom_filter, org_hints, time_window,
                 created_at, last_seen)
                VALUES (?, ?, ?, ?, ?,
                        COALESCE((SELECT created_at FROM subscriptions WHERE subscriber_id = ?), ?),
                        ?)
            """, (
                subscriber_id,
                subscription.get("bucket"),
                bloom_filter,
                org_hints,
                subscription.get("time_window", 600),
                subscriber_id,
                current_time,
                current_time
            ))
            await db.commit()

    async def get_subscription(self, subscriber_id: str) -> Optional[dict]:
        """Get a subscription by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM subscriptions WHERE subscriber_id = ?",
                (subscriber_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "subscriber_id": row["subscriber_id"],
                        "bucket": row["bucket"],
                        "bloom_filter": base64.b64encode(row["bloom_filter"]).decode(),
                        "org_hints": json.loads(row["org_hints"]),
                        "time_window": row["time_window"],
                        "created_at": row["created_at"],
                        "last_seen": row["last_seen"]
                    }
                return None

    async def get_subscribers_by_bucket(self, bucket: int) -> List[str]:
        """Get all subscriber IDs in a bucket."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT subscriber_id FROM subscriptions WHERE bucket = ?",
                (bucket,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [row[0] for row in rows]

    async def delete_subscription(self, subscriber_id: str) -> bool:
        """Delete a subscription."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM pending_proofs WHERE subscriber_id = ?",
                (subscriber_id,)
            )
            cursor = await db.execute(
                "DELETE FROM subscriptions WHERE subscriber_id = ?",
                (subscriber_id,)
            )
            deleted = cursor.rowcount > 0
            await db.commit()
            return deleted

    async def update_subscriber_last_seen(self, subscriber_id: str):
        """Update last seen timestamp."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE subscriptions SET last_seen = ? WHERE subscriber_id = ?",
                (int(time.time()), subscriber_id)
            )
            await db.commit()

    async def get_all_subscriptions(self) -> List[dict]:
        """Get all subscriptions."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM subscriptions") as cursor:
                rows = await cursor.fetchall()
                return [{
                    "subscriber_id": row["subscriber_id"],
                    "bucket": row["bucket"],
                    "bloom_filter": base64.b64encode(row["bloom_filter"]).decode(),
                    "org_hints": json.loads(row["org_hints"]),
                    "time_window": row["time_window"],
                    "created_at": row["created_at"],
                    "last_seen": row["last_seen"]
                } for row in rows]

    # ─────────────────────────────────────────────────────────────
    # Pending Proofs
    # ─────────────────────────────────────────────────────────────

    async def queue_proof_for_subscriber(self, subscriber_id: str, proof_id: str):
        """Queue a proof for a subscriber."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO pending_proofs (subscriber_id, proof_id, queued_at)
                VALUES (?, ?, ?)
            """, (subscriber_id, proof_id, int(time.time())))
            await db.commit()

    async def get_pending_proofs(self, subscriber_id: str,
                                 delete_after: bool = True) -> List[dict]:
        """Get pending proofs for a subscriber."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            async with db.execute("""
                SELECT pp.id, p.proof_data
                FROM pending_proofs pp
                JOIN proofs p ON pp.proof_id = p.proof_id
                WHERE pp.subscriber_id = ?
                ORDER BY pp.queued_at ASC
            """, (subscriber_id,)) as cursor:
                rows = await cursor.fetchall()

            proofs = [json.loads(row["proof_data"]) for row in rows]

            if delete_after and rows:
                pending_ids = [row["id"] for row in rows]
                placeholders = ','.join('?' * len(pending_ids))
                await db.execute(
                    f"DELETE FROM pending_proofs WHERE id IN ({placeholders})",
                    pending_ids
                )
                await db.commit()

            return proofs

    async def get_pending_count(self, subscriber_id: str) -> int:
        """Get count of pending proofs."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT COUNT(*) FROM pending_proofs WHERE subscriber_id = ?",
                (subscriber_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0]

    # ─────────────────────────────────────────────────────────────
    # Peer Storage
    # ─────────────────────────────────────────────────────────────

    async def store_peer(self, peer_id: str, peer_info: dict):
        """Store or update a peer."""
        async with aiosqlite.connect(self.db_path) as db:
            current_time = int(time.time())

            await db.execute("""
                INSERT OR REPLACE INTO peers
                (peer_id, node_type, address, port, connected_at, last_seen,
                 is_active, metadata)
                VALUES (?, ?, ?, ?,
                        COALESCE((SELECT connected_at FROM peers WHERE peer_id = ?), ?),
                        ?, ?, ?)
            """, (
                peer_id,
                peer_info.get("node_type", "unknown"),
                peer_info.get("address", ""),
                peer_info.get("port", 0),
                peer_id,
                current_time,
                current_time,
                1,
                json.dumps(peer_info.get("metadata", {}))
            ))
            await db.commit()

    async def get_peer(self, peer_id: str) -> Optional[dict]:
        """Get a peer by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM peers WHERE peer_id = ?",
                (peer_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "peer_id": row["peer_id"],
                        "node_type": row["node_type"],
                        "address": row["address"],
                        "port": row["port"],
                        "connected_at": row["connected_at"],
                        "last_seen": row["last_seen"],
                        "is_active": bool(row["is_active"]),
                        "metadata": json.loads(row["metadata"])
                    }
                return None

    async def get_active_peers(self) -> List[dict]:
        """Get all active peers."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM peers WHERE is_active = 1"
            ) as cursor:
                rows = await cursor.fetchall()
                return [{
                    "peer_id": row["peer_id"],
                    "node_type": row["node_type"],
                    "address": row["address"],
                    "port": row["port"],
                    "connected_at": row["connected_at"],
                    "last_seen": row["last_seen"],
                    "is_active": bool(row["is_active"]),
                    "metadata": json.loads(row["metadata"])
                } for row in rows]

    async def deactivate_peer(self, peer_id: str):
        """Mark a peer as inactive."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE peers SET is_active = 0 WHERE peer_id = ?",
                (peer_id,)
            )
            await db.commit()

    # ─────────────────────────────────────────────────────────────
    # Statistics
    # ─────────────────────────────────────────────────────────────

    async def increment_stat(self, stat_key: str, amount: int = 1):
        """Increment a statistic counter."""
        async with aiosqlite.connect(self.db_path) as db:
            current_time = int(time.time())
            await db.execute("""
                INSERT INTO stats (stat_key, stat_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(stat_key) DO UPDATE SET
                    stat_value = stat_value + ?,
                    updated_at = ?
            """, (stat_key, amount, current_time, amount, current_time))
            await db.commit()

    async def get_stat(self, stat_key: str) -> int:
        """Get a statistic value."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT stat_value FROM stats WHERE stat_key = ?",
                (stat_key,)
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_all_stats(self) -> Dict[str, int]:
        """Get all statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT stat_key, stat_value FROM stats"
            ) as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}

    # ─────────────────────────────────────────────────────────────
    # Configuration
    # ─────────────────────────────────────────────────────────────

    async def set_config(self, key: str, value: Any):
        """Set a configuration value."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                (key, json.dumps(value))
            )
            await db.commit()

    async def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT value FROM config WHERE key = ?",
                (key,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0])
                return default

    # ─────────────────────────────────────────────────────────────
    # Maintenance
    # ─────────────────────────────────────────────────────────────

    async def get_database_stats(self) -> dict:
        """Get database statistics."""
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}

            async with db.execute("SELECT COUNT(*) FROM proofs") as cursor:
                stats["total_proofs"] = (await cursor.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM subscriptions") as cursor:
                stats["total_subscriptions"] = (await cursor.fetchone())[0]

            async with db.execute("SELECT COUNT(*) FROM pending_proofs") as cursor:
                stats["total_pending"] = (await cursor.fetchone())[0]

            async with db.execute(
                "SELECT COUNT(*) FROM peers WHERE is_active = 1"
            ) as cursor:
                stats["active_peers"] = (await cursor.fetchone())[0]

            stats["db_path"] = self.db_path
            try:
                stats["db_size_bytes"] = Path(self.db_path).stat().st_size
            except:
                stats["db_size_bytes"] = 0

            return stats

    async def vacuum(self):
        """Compact the database."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("VACUUM")
