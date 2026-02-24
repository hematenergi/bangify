"""Journal logging for all execution decisions and events.

D4 implementation: capture decisions, drafts, confirmations, and rejections
for later review and KPI evaluation.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class JournalEntry:
    id: str
    timestamp: str
    event_type: str
    data: dict[str, Any]
    metadata: dict[str, Any] | None = None


class Journal:
    """Simple append-only journal for execution decisions."""

    def __init__(self, log_dir: str = "journal_logs") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._buffer: list[JournalEntry] = []

    def _utcnow(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _new_id(self) -> str:
        return uuid4().hex

    def record(
        self,
        event_type: str,
        data: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> JournalEntry:
        entry = JournalEntry(
            id=self._new_id(),
            timestamp=self._utcnow(),
            event_type=event_type,
            data=data,
            metadata=metadata,
        )
        self._buffer.append(entry)
        return entry

    def record_decision(
        self,
        decision: Any,
        intent: Any | None = None,
        exposure: Any | None = None,
    ) -> JournalEntry:
        return self.record(
            event_type="decision",
            data={
                "allowed": getattr(decision, "allowed", None),
                "reason": getattr(decision, "reason", None),
                "suggested_size": getattr(decision, "suggested_size", None),
                "intent": asdict(intent) if intent else None,
                "exposure": asdict(exposure) if exposure else None,
            },
        )

    def record_draft(self, draft: Any, decision: Any) -> JournalEntry:
        return self.record(
            event_type="draft_order",
            data={
                "client_order_id": getattr(draft, "client_order_id", None),
                "size": getattr(draft, "size", None),
                "intent": asdict(getattr(draft, "intent", None)) if hasattr(draft, "intent") else None,
                "decision_reason": getattr(decision, "reason", None),
            },
        )

    def record_confirmation(self, confirmed: Any) -> JournalEntry:
        draft = getattr(confirmed, "draft", None)
        intent = getattr(draft, "intent", None) if draft else None
        return self.record(
            event_type="confirmation",
            data={
                "client_order_id": getattr(draft, "client_order_id", None) if draft else None,
                "size": getattr(draft, "size", None) if draft else None,
                "symbol": getattr(intent, "symbol", None) if intent else None,
                "side": getattr(intent, "side", None) if intent else None,
                "confirmation_token": getattr(getattr(confirmed, "confirmation", None), "value", None),
            },
        )

    def record_rejection(self, reason: str, details: dict[str, Any] | None = None) -> JournalEntry:
        return self.record(
            event_type="rejection",
            data={"reason": reason, "details": details or {}},
        )

    def flush_to_file(self, filename: str | None = None) -> Path:
        if not self._buffer:
            return Path(filename or "empty.json")

        fname = filename or f"journal_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.jsonl"
        fpath = self.log_dir / fname

        with fpath.open("a", encoding="utf-8") as f:
            for entry in self._buffer:
                f.write(json.dumps(asdict(entry)) + "\n")

        self._buffer.clear()
        return fpath

    def pending_count(self) -> int:
        return len(self._buffer)
