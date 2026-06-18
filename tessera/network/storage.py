"""
SQLite persistence layer for Tessera decentralized nodes.
Provides durable storage for proofs, subscriptions, and peer information.
"""

import sqlite3
import json
import time
import threading
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
from pathlib import Path


class NodeStorage:
    """
    SQLite-based storage for Tessera nodes.

    Handles persistence for:
    - Proof cache with TTL
    - Customer subscriptions
    - Peer connections
    - Pending proofs for pull model
    - Node statistics
    """

    def __init__(self, db_path: str = "tessera_node.db"):
        """
        Initialize node storage.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._local = threading.local()
        self._init_database()

    @contextmanager
    def _get_connection(self):
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self._local.connection.row_factory = sqlite3.Row

        try:
            yield self._local.connection
        except Exception:
            self._local.connection.rollback()
            raise

    def _init_database(self):
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Proofs table
            cursor.execute("""
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

            # Index for bucket-based routing
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_proofs_bucket
                ON proofs(bucket, timestamp)
            """)

            # Index for expiration cleanup
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_proofs_expires
                ON proofs(expires_at)
            """)

            # Subscriptions table
            cursor.execute("""
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

            # Index for bucket routing
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_subscriptions_bucket
                ON subscriptions(bucket)
            """)

            # Pending proofs table (for pull model)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_proofs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    subscriber_id TEXT NOT NULL,
                    proof_id TEXT NOT NULL,
                    queued_at INTEGER NOT NULL,
                    FOREIGN KEY (subscriber_id) REFERENCES subscriptions(subscriber_id),
                    FOREIGN KEY (proof_id) REFERENCES proofs(proof_id)
                )
            """)

            # Index for fetching pending proofs
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pending_subscriber
                ON pending_proofs(subscriber_id, queued_at)
            """)

            # Peers table
            cursor.execute("""
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    stat_key TEXT PRIMARY KEY,
                    stat_value INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                )
            """)

            # Node configuration table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)

            conn.commit()

    # ─────────────────────────────────────────────────────────────
    # Proof Storage
    # ─────────────────────────────────────────────────────────────

    def store_proof(self, proof_id: str, proof: dict, from_peer: str = None,
                   ttl: int = 3600) -> bool:
        """
        Store a proof in the database.

        Args:
            proof_id: Unique proof identifier
            proof: Proof data
            from_peer: Peer that sent this proof
            ttl: Time-to-live in seconds

        Returns:
            bool: True if stored (new), False if already exists
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            current_time = int(time.time())
            expires_at = current_time + ttl

            try:
                cursor.execute("""
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
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Already exists
                return False

    def get_proof(self, proof_id: str) -> Optional[dict]:
        """Get a proof by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT proof_data FROM proofs WHERE proof_id = ?",
                (proof_id,)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row["proof_data"])
            return None

    def proof_exists(self, proof_id: str) -> bool:
        """Check if proof already exists (for dedup)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM proofs WHERE proof_id = ?",
                (proof_id,)
            )
            return cursor.fetchone() is not None

    def get_proofs_by_bucket(self, bucket: int, since_timestamp: int = 0) -> List[dict]:
        """Get all proofs in a bucket since timestamp."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT proof_data FROM proofs
                WHERE bucket = ? AND timestamp >= ?
                ORDER BY timestamp DESC
            """, (bucket, since_timestamp))

            return [json.loads(row["proof_data"]) for row in cursor.fetchall()]

    def cleanup_expired_proofs(self) -> int:
        """Remove expired proofs. Returns count deleted."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            current_time = int(time.time())

            # First delete pending references
            cursor.execute("""
                DELETE FROM pending_proofs
                WHERE proof_id IN (
                    SELECT proof_id FROM proofs WHERE expires_at < ?
                )
            """, (current_time,))

            # Then delete proofs
            cursor.execute(
                "DELETE FROM proofs WHERE expires_at < ?",
                (current_time,)
            )
            deleted = cursor.rowcount
            conn.commit()
            return deleted

    # ─────────────────────────────────────────────────────────────
    # Subscription Storage
    # ─────────────────────────────────────────────────────────────

    def store_subscription(self, subscriber_id: str, subscription: dict):
        """
        Store or update a subscription.

        Args:
            subscriber_id: Unique subscriber identifier
            subscription: Subscription data
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            current_time = int(time.time())

            # Convert org_hints list to JSON
            org_hints = json.dumps(subscription.get("org_hints", []))

            # Get bloom filter as bytes
            bloom_filter = subscription.get("bloom_filter", b"")
            if isinstance(bloom_filter, str):
                import base64
                bloom_filter = base64.b64decode(bloom_filter)

            cursor.execute("""
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
            conn.commit()

    def get_subscription(self, subscriber_id: str) -> Optional[dict]:
        """Get a subscription by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM subscriptions WHERE subscriber_id = ?",
                (subscriber_id,)
            )
            row = cursor.fetchone()
            if row:
                import base64
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

    def get_subscribers_by_bucket(self, bucket: int) -> List[str]:
        """Get all subscriber IDs in a bucket."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT subscriber_id FROM subscriptions WHERE bucket = ?",
                (bucket,)
            )
            return [row["subscriber_id"] for row in cursor.fetchall()]

    def delete_subscription(self, subscriber_id: str) -> bool:
        """Delete a subscription."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Delete pending proofs first
            cursor.execute(
                "DELETE FROM pending_proofs WHERE subscriber_id = ?",
                (subscriber_id,)
            )

            # Delete subscription
            cursor.execute(
                "DELETE FROM subscriptions WHERE subscriber_id = ?",
                (subscriber_id,)
            )
            deleted = cursor.rowcount > 0
            conn.commit()
            return deleted

    def update_subscriber_last_seen(self, subscriber_id: str):
        """Update last seen timestamp for subscriber."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE subscriptions SET last_seen = ? WHERE subscriber_id = ?",
                (int(time.time()), subscriber_id)
            )
            conn.commit()

    def get_all_subscriptions(self) -> List[dict]:
        """Get all subscriptions."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM subscriptions")

            import base64
            subscriptions = []
            for row in cursor.fetchall():
                subscriptions.append({
                    "subscriber_id": row["subscriber_id"],
                    "bucket": row["bucket"],
                    "bloom_filter": base64.b64encode(row["bloom_filter"]).decode(),
                    "org_hints": json.loads(row["org_hints"]),
                    "time_window": row["time_window"],
                    "created_at": row["created_at"],
                    "last_seen": row["last_seen"]
                })
            return subscriptions

    # ─────────────────────────────────────────────────────────────
    # Pending Proofs (Pull Model)
    # ─────────────────────────────────────────────────────────────

    def queue_proof_for_subscriber(self, subscriber_id: str, proof_id: str):
        """Queue a proof for a subscriber to pull."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pending_proofs (subscriber_id, proof_id, queued_at)
                VALUES (?, ?, ?)
            """, (subscriber_id, proof_id, int(time.time())))
            conn.commit()

    def get_pending_proofs(self, subscriber_id: str,
                          delete_after: bool = True) -> List[dict]:
        """
        Get pending proofs for a subscriber.

        Args:
            subscriber_id: Subscriber to get proofs for
            delete_after: Remove from queue after retrieval

        Returns:
            list: List of proof data
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Get pending proof IDs
            cursor.execute("""
                SELECT pp.id, p.proof_data
                FROM pending_proofs pp
                JOIN proofs p ON pp.proof_id = p.proof_id
                WHERE pp.subscriber_id = ?
                ORDER BY pp.queued_at ASC
            """, (subscriber_id,))

            rows = cursor.fetchall()
            proofs = [json.loads(row["proof_data"]) for row in rows]

            if delete_after and rows:
                pending_ids = [row["id"] for row in rows]
                cursor.execute(
                    f"DELETE FROM pending_proofs WHERE id IN ({','.join('?' * len(pending_ids))})",
                    pending_ids
                )
                conn.commit()

            return proofs

    def get_pending_count(self, subscriber_id: str) -> int:
        """Get count of pending proofs for subscriber."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM pending_proofs WHERE subscriber_id = ?",
                (subscriber_id,)
            )
            return cursor.fetchone()[0]

    # ─────────────────────────────────────────────────────────────
    # Peer Storage
    # ─────────────────────────────────────────────────────────────

    def store_peer(self, peer_id: str, peer_info: dict):
        """Store or update a peer."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            current_time = int(time.time())

            cursor.execute("""
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
            conn.commit()

    def get_peer(self, peer_id: str) -> Optional[dict]:
        """Get a peer by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM peers WHERE peer_id = ?", (peer_id,))
            row = cursor.fetchone()
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

    def get_active_peers(self) -> List[dict]:
        """Get all active peers."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM peers WHERE is_active = 1")

            peers = []
            for row in cursor.fetchall():
                peers.append({
                    "peer_id": row["peer_id"],
                    "node_type": row["node_type"],
                    "address": row["address"],
                    "port": row["port"],
                    "connected_at": row["connected_at"],
                    "last_seen": row["last_seen"],
                    "is_active": bool(row["is_active"]),
                    "metadata": json.loads(row["metadata"])
                })
            return peers

    def update_peer_last_seen(self, peer_id: str):
        """Update last seen timestamp for peer."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE peers SET last_seen = ? WHERE peer_id = ?",
                (int(time.time()), peer_id)
            )
            conn.commit()

    def deactivate_peer(self, peer_id: str):
        """Mark a peer as inactive."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE peers SET is_active = 0 WHERE peer_id = ?",
                (peer_id,)
            )
            conn.commit()

    def delete_peer(self, peer_id: str):
        """Delete a peer."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM peers WHERE peer_id = ?", (peer_id,))
            conn.commit()

    # ─────────────────────────────────────────────────────────────
    # Statistics
    # ─────────────────────────────────────────────────────────────

    def increment_stat(self, stat_key: str, amount: int = 1):
        """Increment a statistic counter."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            current_time = int(time.time())

            cursor.execute("""
                INSERT INTO stats (stat_key, stat_value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(stat_key) DO UPDATE SET
                    stat_value = stat_value + ?,
                    updated_at = ?
            """, (stat_key, amount, current_time, amount, current_time))
            conn.commit()

    def get_stat(self, stat_key: str) -> int:
        """Get a statistic value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT stat_value FROM stats WHERE stat_key = ?",
                (stat_key,)
            )
            row = cursor.fetchone()
            return row["stat_value"] if row else 0

    def get_all_stats(self) -> Dict[str, int]:
        """Get all statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT stat_key, stat_value FROM stats")
            return {row["stat_key"]: row["stat_value"] for row in cursor.fetchall()}

    # ─────────────────────────────────────────────────────────────
    # Configuration
    # ─────────────────────────────────────────────────────────────

    def set_config(self, key: str, value: Any):
        """Set a configuration value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
                (key, json.dumps(value))
            )
            conn.commit()

    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM config WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row["value"])
            return default

    # ─────────────────────────────────────────────────────────────
    # Maintenance
    # ─────────────────────────────────────────────────────────────

    def get_database_stats(self) -> dict:
        """Get database statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            stats = {}

            cursor.execute("SELECT COUNT(*) FROM proofs")
            stats["total_proofs"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM subscriptions")
            stats["total_subscriptions"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM pending_proofs")
            stats["total_pending"] = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM peers WHERE is_active = 1")
            stats["active_peers"] = cursor.fetchone()[0]

            # Database file size
            stats["db_path"] = self.db_path
            try:
                stats["db_size_bytes"] = Path(self.db_path).stat().st_size
            except:
                stats["db_size_bytes"] = 0

            return stats

    def vacuum(self):
        """Compact the database."""
        with self._get_connection() as conn:
            conn.execute("VACUUM")

    def close(self):
        """Close database connections."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            delattr(self._local, 'connection')
