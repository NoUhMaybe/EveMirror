"""Bounded, principal/device-bound context and per-session retry receipts, memory only."""

from __future__ import annotations

import asyncio
import time
from dataclasses import asdict, dataclass, field
from uuid import UUID, uuid4

from apps.config import AgentLimits
from apps.server.agent.messages import LLMMessage
from apps.server.providers.base import json_text
from apps.server.tools.base import Principal


class SessionError(Exception):
    def __init__(self, code: str, status: int):
        self.code, self.status = code, status
        super().__init__(code)


def context_size(messages: list[LLMMessage]) -> int:
    return len(json_text([asdict(message) for message in messages]).encode())


@dataclass
class Session:
    owner: str
    device_id: str | None
    touched: float
    id: UUID = field(default_factory=uuid4)
    history: list[list[LLMMessage]] = field(default_factory=list, repr=False)
    receipts: dict[UUID, tuple[str, dict | None]] = field(default_factory=dict, repr=False)
    task: asyncio.Task | None = field(default=None, repr=False)
    keep_until: float = 0

    def messages(self):
        return [message for turn in self.history for message in turn]


class SessionStore:
    def __init__(self, limits: AgentLimits, clock=time.monotonic):
        self.limits, self.clock = limits, clock
        self.sessions: dict[UUID, Session] = {}
        self.requests: dict[tuple[str, UUID], UUID] = {}

    def expire(self):
        expired = {
            sid
            for sid, session in self.sessions.items()
            if session.task is None
            and self.clock() >= session.keep_until
            and self.clock() - session.touched >= self.limits.session_idle_seconds
        }
        for sid in expired:
            del self.sessions[sid]
        if expired:
            self.requests = {key: sid for key, sid in self.requests.items() if sid not in expired}

    def create(self, principal: Principal, device_id: str | None = None) -> Session:
        self.expire()
        if device_id is not None and device_id not in principal.device_ids:
            raise SessionError("device_not_authorized", 403)
        if device_id is None and len(principal.device_ids) == 1:
            device_id = next(iter(principal.device_ids))
        if len(self.sessions) >= self.limits.max_sessions:
            raise SessionError("session_capacity", 503)
        session = Session(principal.id, device_id, self.clock())
        self.sessions[session.id] = session
        return session

    def get(self, sid: UUID, principal: Principal) -> Session:
        self.expire()
        session = self.sessions.get(sid)
        if session is None or session.owner != principal.id:
            raise SessionError("session_not_found", 404)
        return session

    def turn(self, principal, request_id, session_id, device_id, fingerprint):
        self.expire()
        previous_sid = self.requests.get((principal.id, request_id))
        if previous_sid is not None:
            if session_id is not None and previous_sid != session_id:
                raise SessionError("request_conflict", 409)
            session_id = previous_sid
        session = (
            self.get(session_id, principal) if session_id else self.create(principal, device_id)
        )
        if device_id is not None and device_id != session.device_id:
            raise SessionError("session_device_conflict", 409)
        old = session.receipts.get(request_id)
        if old:
            if old[0] != fingerprint:
                raise SessionError("request_conflict", 409)
            if old[1] is not None:
                session.touched = self.clock()
                return session, old[1]
            raise SessionError("session_busy" if session.task else "retry_result_expired", 409)
        if session.task is not None:
            raise SessionError("session_busy", 409)
        if len(session.receipts) >= self.limits.max_turns_per_session:
            raise SessionError("session_turn_limit", 409)
        session.receipts[request_id] = (fingerprint, None)
        self.requests[(principal.id, request_id)] = session.id
        session.touched = self.clock()
        return session, None

    def reset(self, sid, principal):
        session = self.get(sid, principal)
        if session.task is not None:
            raise SessionError("session_busy", 409)
        session.history.clear()
        # Retain retry receipts: reset must not make a previously executed action run again.
        session.touched = self.clock()

    def cancel(self, sid, principal) -> bool:
        session = self.get(sid, principal)
        if session.task is None:
            return False
        session.task.cancel()
        return True

    def remember(self, session: Session, messages: list[LLMMessage]):
        session.history.append(messages)
        while session.history and (
            context_size(session.messages()) > self.limits.max_context_bytes // 2
            or len(session.messages()) > self.limits.max_context_messages // 2
        ):
            # Whole turns preserve tool request/result ordering and private provider state.
            session.history.pop(0)
        session.touched = self.clock()

    def finish(self, session: Session, request_id: UUID, fingerprint: str, result: dict):
        session.receipts[request_id] = (fingerprint, result)
        # Keep ID/fingerprint tombstones while discarding older response text when over budget.
        retained_bytes = sum(
            len(json_text(entry[1]).encode())
            for entry in session.receipts.values()
            if entry[1] is not None
        )
        for old_id, (old_fingerprint, old_result) in session.receipts.items():
            if retained_bytes <= self.limits.max_context_bytes:
                break
            if old_result is None:
                continue
            retained_bytes -= len(json_text(old_result).encode())
            session.receipts[old_id] = (old_fingerprint, None)

    async def close(self):
        tasks = [session.task for session in self.sessions.values() if session.task]
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        self.sessions.clear()
        self.requests.clear()
