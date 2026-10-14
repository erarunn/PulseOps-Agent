import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from app.db.database import get_connection
from app.db.models import (
    MessageModel,
    ToolTraceModel,
    TicketDraftModel,
    PRSummaryModel,
    ConversationDetail,
    DocChunkModel,
)

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class Repository:
    @staticmethod
    def get_or_create_conversation(conversation_id: Optional[str] = None, user_label: Optional[str] = None) -> str:
        conn = get_connection()
        cid = conversation_id or f"conv-{uuid.uuid4().hex[:8]}"
        with conn:
            cursor = conn.execute("SELECT id FROM conversations WHERE id = ?", (cid,))
            row = cursor.fetchone()
            if not row:
                conn.execute(
                    "INSERT INTO conversations (id, created_at, user_label) VALUES (?, ?, ?)",
                    (cid, utc_now(), user_label or "Default Session")
                )
        conn.close()
        return cid

    @staticmethod
    def add_message(conversation_id: str, role: str, content: str) -> MessageModel:
        conn = get_connection()
        msg_id = f"msg-{uuid.uuid4().hex[:8]}"
        created = utc_now()
        with conn:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, created_at) VALUES (?, ?, ?, ?, ?)",
                (msg_id, conversation_id, role, content, created)
            )
        conn.close()
        return MessageModel(
            id=msg_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            created_at=created
        )

    @staticmethod
    def get_messages(conversation_id: str) -> List[MessageModel]:
        conn = get_connection()
        cursor = conn.execute(
            "SELECT id, conversation_id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            MessageModel(
                id=r["id"],
                conversation_id=r["conversation_id"],
                role=r["role"],
                content=r["content"],
                created_at=r["created_at"]
            )
            for r in rows
        ]

    @staticmethod
    def record_tool_trace(
        conversation_id: str,
        step: int,
        tool_name: str,
        args: Dict[str, Any],
        result: Any,
        ok: bool
    ) -> ToolTraceModel:
        conn = get_connection()
        trace_id = f"trc-{uuid.uuid4().hex[:8]}"
        created = utc_now()
        args_json = json.dumps(args)
        result_json = json.dumps(result)
        with conn:
            conn.execute(
                """
                INSERT INTO tool_traces (id, conversation_id, step, tool_name, args_json, result_json, ok, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (trace_id, conversation_id, step, tool_name, args_json, result_json, 1 if ok else 0, created)
            )
        conn.close()
        return ToolTraceModel(
            id=trace_id,
            conversation_id=conversation_id,
            step=step,
            tool_name=tool_name,
            args=args,
            result=result,
            ok=ok,
            created_at=created
        )

    @staticmethod
    def get_traces(conversation_id: str) -> List[ToolTraceModel]:
        conn = get_connection()
        cursor = conn.execute(
            "SELECT id, conversation_id, step, tool_name, args_json, result_json, ok, created_at FROM tool_traces WHERE conversation_id = ? ORDER BY step ASC, created_at ASC",
            (conversation_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        results = []
        for r in rows:
            try:
                args = json.loads(r["args_json"])
            except Exception:
                args = {}
            try:
                result = json.loads(r["result_json"])
            except Exception:
                result = r["result_json"]
            results.append(
                ToolTraceModel(
                    id=r["id"],
                    conversation_id=r["conversation_id"],
                    step=r["step"],
                    tool_name=r["tool_name"],
                    args=args,
                    result=result,
                    ok=bool(r["ok"]),
                    created_at=r["created_at"]
                )
            )
        return results

    @staticmethod
    def save_ticket_draft(
        title: str,
        description: str,
        priority: str,
        labels: List[str],
        team: str,
        source_conversation_id: Optional[str] = None,
        ticket_id: Optional[str] = None
    ) -> TicketDraftModel:
        conn = get_connection()
        tid = ticket_id or f"DRAFT-{uuid.uuid4().hex[:6].upper()}"
        created = utc_now()
        with conn:
            conn.execute(
                """
                INSERT INTO ticket_drafts (id, title, description, priority, labels_json, team, source_conversation_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (tid, title, description, priority.upper(), json.dumps(labels), team, source_conversation_id, created)
            )
        conn.close()
        return TicketDraftModel(
            id=tid,
            title=title,
            description=description,
            priority=priority.upper(),
            labels=labels,
            team=team,
            source_conversation_id=source_conversation_id,
            created_at=created
        )

    @staticmethod
    def list_ticket_drafts() -> List[TicketDraftModel]:
        conn = get_connection()
        cursor = conn.execute("SELECT * FROM ticket_drafts ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        res = []
        for r in rows:
            try:
                labels = json.loads(r["labels_json"])
            except Exception:
                labels = []
            res.append(
                TicketDraftModel(
                    id=r["id"],
                    title=r["title"],
                    description=r["description"],
                    priority=r["priority"],
                    labels=labels,
                    team=r["team"],
                    source_conversation_id=r["source_conversation_id"],
                    created_at=r["created_at"]
                )
            )
        return res

    @staticmethod
    def save_pr_summary(
        pr_number: int,
        summary: Dict[str, Any],
        source_conversation_id: Optional[str] = None,
        summary_id: Optional[str] = None
    ) -> PRSummaryModel:
        conn = get_connection()
        sid = summary_id or f"PRS-{uuid.uuid4().hex[:6].upper()}"
        created = utc_now()
        with conn:
            conn.execute(
                """
                INSERT INTO pr_summaries (id, pr_number, summary_json, source_conversation_id, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (sid, pr_number, json.dumps(summary), source_conversation_id, created)
            )
        conn.close()
        return PRSummaryModel(
            id=sid,
            pr_number=pr_number,
            summary=summary,
            source_conversation_id=source_conversation_id,
            created_at=created
        )

    @staticmethod
    def list_pr_summaries() -> List[PRSummaryModel]:
        conn = get_connection()
        cursor = conn.execute("SELECT * FROM pr_summaries ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        res = []
        for r in rows:
            try:
                summary = json.loads(r["summary_json"])
            except Exception:
                summary = {"raw": r["summary_json"]}
            res.append(
                PRSummaryModel(
                    id=r["id"],
                    pr_number=r["pr_number"],
                    summary=summary,
                    source_conversation_id=r["source_conversation_id"],
                    created_at=r["created_at"]
                )
            )
        return res

    @staticmethod
    def get_conversation_detail(conversation_id: str) -> Optional[ConversationDetail]:
        conn = get_connection()
        cursor = conn.execute("SELECT id, created_at, user_label FROM conversations WHERE id = ?", (conversation_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        messages = Repository.get_messages(conversation_id)
        traces = Repository.get_traces(conversation_id)
        return ConversationDetail(
            id=row["id"],
            created_at=row["created_at"],
            user_label=row["user_label"],
            messages=messages,
            traces=traces
        )


class DocChunkRepository:
    """Persists and queries doc chunk metadata in SQLite (doc_chunks table).

    The actual dense vectors are stored in ChromaDB; this table acts as a
    lightweight audit log and fast metadata lookup store.
    """

    @staticmethod
    def upsert_chunks(
        chunks: List[Dict[str, Any]],
        file_fingerprints: Dict[str, str],
    ) -> List[DocChunkModel]:
        """Delete existing chunks for changed files and insert fresh ones.

        Args:
            chunks: List of chunk dicts with keys: id, filename, title,
                    chunk_index, text.
            file_fingerprints: Map of filename → SHA-256 so we can record
                               which file version each chunk came from.
        Returns:
            List of persisted DocChunkModel instances.
        """
        if not chunks:
            return []

        indexed_at = utc_now()
        conn = get_connection()
        filenames = list({c["filename"] for c in chunks})

        with conn:
            # Remove stale rows for the affected filenames
            placeholders = ",".join("?" for _ in filenames)
            conn.execute(
                f"DELETE FROM doc_chunks WHERE filename IN ({placeholders})",
                filenames,
            )
            # Bulk insert new chunks
            conn.executemany(
                """
                INSERT INTO doc_chunks
                    (id, filename, title, chunk_index, text, file_fingerprint, indexed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        c["id"],
                        c["filename"],
                        c["title"],
                        c["chunk_index"],
                        c["text"],
                        file_fingerprints.get(c["filename"], ""),
                        indexed_at,
                    )
                    for c in chunks
                ],
            )
        conn.close()

        return [
            DocChunkModel(
                id=c["id"],
                filename=c["filename"],
                title=c["title"],
                chunk_index=c["chunk_index"],
                text=c["text"],
                file_fingerprint=file_fingerprints.get(c["filename"], ""),
                indexed_at=indexed_at,
            )
            for c in chunks
        ]

    @staticmethod
    def get_chunks_by_filename(filename: str) -> List[DocChunkModel]:
        """Return all stored chunks for a given source file, ordered by index."""
        conn = get_connection()
        cursor = conn.execute(
            """
            SELECT id, filename, title, chunk_index, text, file_fingerprint, indexed_at
            FROM doc_chunks
            WHERE filename = ?
            ORDER BY chunk_index ASC
            """,
            (filename,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            DocChunkModel(
                id=r["id"],
                filename=r["filename"],
                title=r["title"],
                chunk_index=r["chunk_index"],
                text=r["text"],
                file_fingerprint=r["file_fingerprint"],
                indexed_at=r["indexed_at"],
            )
            for r in rows
        ]

    @staticmethod
    def list_indexed_files() -> List[Dict[str, Any]]:
        """Return a summary row per indexed file (filename, chunk_count, indexed_at)."""
        conn = get_connection()
        cursor = conn.execute(
            """
            SELECT filename, COUNT(*) AS chunk_count, MAX(indexed_at) AS indexed_at
            FROM doc_chunks
            GROUP BY filename
            ORDER BY filename ASC
            """
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "filename": r["filename"],
                "chunk_count": r["chunk_count"],
                "indexed_at": r["indexed_at"],
            }
            for r in rows
        ]
