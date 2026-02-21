from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.schemas.voice_loop import SessionRecord


def _utc_now() -> str:
    return datetime.now(tz=UTC).isoformat()


class SessionStore:
    def __init__(self, base_dir: str) -> None:
        self.base_path = Path(base_dir)
        self.sessions_path = self.base_path / "sessions"
        self.events_path = self.base_path / "events"
        self.sessions_path.mkdir(parents=True, exist_ok=True)
        self.events_path.mkdir(parents=True, exist_ok=True)

    def create_session(self, session_id: str) -> SessionRecord:
        now = _utc_now()
        record = SessionRecord(
            session_id=session_id,
            created_at=now,
            updated_at=now,
            turns=[],
        )
        self._write_session(record.model_dump())
        return record

    def get_session(self, session_id: str) -> SessionRecord:
        payload = self._read_session(session_id)
        return SessionRecord(**payload)

    def append_turn(self, session_id: str, turn: dict[str, Any]) -> SessionRecord:
        payload = self._read_session(session_id)
        payload.setdefault("turns", []).append(turn)
        payload["updated_at"] = _utc_now()
        self._write_session(payload)
        return SessionRecord(**payload)

    def append_event(self, session_id: str, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "timestamp": _utc_now(),
            "session_id": session_id,
            "event_type": event_type,
            "payload": payload,
        }
        with self._event_file(session_id).open("a", encoding="utf-8") as file:
            file.write(json.dumps(event, ensure_ascii=True) + os.linesep)

    def load_events(self, session_id: str) -> list[dict[str, Any]]:
        event_file = self._event_file(session_id)
        if not event_file.exists():
            return []
        lines = event_file.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(line) for line in lines if line]

    def _session_file(self, session_id: str) -> Path:
        return self.sessions_path / f"{session_id}.json"

    def _event_file(self, session_id: str) -> Path:
        return self.events_path / f"{session_id}.jsonl"

    def _read_session(self, session_id: str) -> dict[str, Any]:
        session_file = self._session_file(session_id)
        if not session_file.exists():
            raise FileNotFoundError(f"Session {session_id} not found")
        return json.loads(session_file.read_text(encoding="utf-8"))

    def _write_session(self, payload: dict[str, Any]) -> None:
        session_file = self._session_file(payload["session_id"])
        session_file.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")

