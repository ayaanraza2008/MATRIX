"""MATRIX Playback Coordinator & TTS Deduplication Manager.
Guarantees:
1. One response_id has exactly ONE TTS playback owner.
2. Generates unique playback_id per playback attempt.
3. Enforces 6 discrete playback states:
   QUEUED, GENERATING, PLAYING, COMPLETED, FAILED, CANCELLED.
4. Prevents duplicate audio playback for already completed or playing responses.
5. Deduplicates repeated playback events and WebSocket reconnections.
6. Ensures retries and duplicate requests cannot duplicate audible output.
7. Makes cancellation and interruption strictly idempotent.
8. Logs exact timestamps for TTS generation, playback start, and completion.
"""
from enum import Enum
from typing import Optional, Dict, Any, Tuple, List
import time
import uuid
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field
from config.logging_config import get_logger

logger = get_logger("voice.playback")


class PlaybackState(str, Enum):
    QUEUED = "QUEUED"
    GENERATING = "GENERATING"
    PLAYING = "PLAYING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PlaybackRecord(BaseModel):
    playback_id: str
    response_id: str
    request_id: Optional[str] = None
    owner: str = "direct"  # e.g., 'hands_free', 'frontend_ui', 'voice_agent', 'companion', 'direct'
    state: PlaybackState = PlaybackState.QUEUED
    text: str = ""
    audio_file: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    generating_started_at: Optional[float] = None
    playback_started_at: Optional[float] = None
    completed_at: Optional[float] = None
    duration_ms: float = 0.0
    error: Optional[str] = None


class PlaybackCoordinator:
    """Thread-safe coordinator managing TTS playback ownership and state lifecycle."""

    def __init__(self):
        self._records: Dict[str, PlaybackRecord] = {}           # playback_id -> record
        self._by_response_id: Dict[str, str] = {}              # response_id -> playback_id
        self._completed_response_ids: Dict[str, float] = {}     # response_id -> completed_at
        self._active_playing_id: Optional[str] = None
        self._lock = asyncio.Lock()

    async def acquire_playback(
        self,
        response_id: str,
        owner: str,
        text: str = "",
        request_id: Optional[str] = None,
        force_new: bool = False
    ) -> Tuple[bool, PlaybackRecord, Optional[str]]:
        """Acquire exclusive playback ownership for a response_id.
        
        Returns:
            (acquired, record, reason_if_rejected)
        """
        async with self._lock:
            # 1. Check if already completed
            if not force_new and response_id in self._completed_response_ids:
                existing_pid = self._by_response_id.get(response_id)
                rec = self._records.get(existing_pid) if existing_pid else None
                logger.info(
                    f"Playback REJECTED: response_id '{response_id}' was already COMPLETED at "
                    f"{self._completed_response_ids[response_id]:.3f}. Owner '{owner}' suppressed."
                )
                if rec is None:
                    rec = PlaybackRecord(
                        playback_id=f"pb_done_{uuid.uuid4().hex[:8]}",
                        response_id=response_id,
                        request_id=request_id,
                        owner=owner,
                        state=PlaybackState.COMPLETED,
                        text=text
                    )
                return False, rec, "ALREADY_COMPLETED"

            # 2. Check if already active/owned
            if not force_new:
                existing_pid = self._by_response_id.get(response_id)
                if existing_pid:
                    rec = self._records[existing_pid]
                    if rec.state in (PlaybackState.QUEUED, PlaybackState.PLAYING, PlaybackState.GENERATING):
                        if rec.owner == owner:
                            # Same owner re-entrant call
                            return True, rec, None
                        else:
                            # Another owner is already playing/generating
                            logger.warning(
                                f"Playback REJECTED: response_id '{response_id}' is currently {rec.state.value} "
                                f"by owner '{rec.owner}'. Competing owner '{owner}' suppressed."
                            )
                            return False, rec, f"ALREADY_OWNED_BY_{rec.owner.upper()}"
                    elif rec.state == PlaybackState.COMPLETED:
                        return False, rec, "ALREADY_COMPLETED"

            # 3. Create fresh playback record
            playback_id = f"pb_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}"
            rec = PlaybackRecord(
                playback_id=playback_id,
                response_id=response_id,
                request_id=request_id,
                owner=owner,
                state=PlaybackState.QUEUED,
                text=text,
                created_at=time.time()
            )
            self._records[playback_id] = rec
            self._by_response_id[response_id] = playback_id
            logger.info(
                f"Playback ACQUIRED: playback_id '{playback_id}' for response_id '{response_id}' "
                f"owned by '{owner}'. State: QUEUED."
            )
            return True, rec, None

    def mark_generating(self, playback_id: str):
        """Transition playback state to GENERATING."""
        rec = self._records.get(playback_id)
        if rec and rec.state != PlaybackState.CANCELLED:
            rec.state = PlaybackState.GENERATING
            rec.generating_started_at = time.time()
            logger.debug(f"Playback '{playback_id}' -> GENERATING at {rec.generating_started_at:.3f}")

    def mark_playing(self, playback_id: str):
        """Transition playback state to PLAYING."""
        rec = self._records.get(playback_id)
        if rec and rec.state != PlaybackState.CANCELLED:
            rec.state = PlaybackState.PLAYING
            rec.playback_started_at = time.time()
            self._active_playing_id = playback_id
            logger.info(f"Playback '{playback_id}' -> PLAYING (Owner: {rec.owner})")

    def mark_completed(self, playback_id: str, audio_file: Optional[Path] = None, duration_ms: float = 0.0):
        """Transition playback state to COMPLETED and seal response_id against replays."""
        rec = self._records.get(playback_id)
        if rec:
            rec.state = PlaybackState.COMPLETED
            rec.completed_at = time.time()
            if audio_file:
                rec.audio_file = str(audio_file)
            if duration_ms > 0:
                rec.duration_ms = duration_ms
            elif rec.playback_started_at:
                rec.duration_ms = round((rec.completed_at - rec.playback_started_at) * 1000, 2)
            self._completed_response_ids[rec.response_id] = rec.completed_at
            if self._active_playing_id == playback_id:
                self._active_playing_id = None
            logger.info(
                f"Playback '{playback_id}' -> COMPLETED ({rec.duration_ms}ms). "
                f"Response '{rec.response_id}' sealed against future duplicate playback."
            )

    def mark_failed(self, playback_id: str, error: str):
        """Transition playback state to FAILED."""
        rec = self._records.get(playback_id)
        if rec:
            rec.state = PlaybackState.FAILED
            rec.error = error
            if self._active_playing_id == playback_id:
                self._active_playing_id = None
            logger.warning(f"Playback '{playback_id}' -> FAILED: {error}")

    def cancel(self, playback_id: Optional[str] = None, response_id: Optional[str] = None):
        """Idempotently cancel ongoing or queued playback."""
        target_ids = []
        if playback_id and playback_id in self._records:
            target_ids.append(playback_id)
        elif response_id and response_id in self._by_response_id:
            pid = self._by_response_id[response_id]
            if pid in self._records:
                target_ids.append(pid)
        elif self._active_playing_id:
            target_ids.append(self._active_playing_id)

        for pid in target_ids:
            rec = self._records[pid]
            if rec.state not in (PlaybackState.COMPLETED, PlaybackState.CANCELLED):
                rec.state = PlaybackState.CANCELLED
                rec.error = "Cancelled by user interrupt"
                logger.info(f"Playback '{pid}' -> CANCELLED idempotently.")
        if self._active_playing_id in target_ids:
            self._active_playing_id = None

    def is_playable(self, response_id: str, owner: str) -> bool:
        """Check if response_id is eligible for audible playback by owner."""
        if response_id in self._completed_response_ids:
            return False
        existing_pid = self._by_response_id.get(response_id)
        if existing_pid:
            rec = self._records.get(existing_pid)
            if rec and rec.state in (PlaybackState.PLAYING, PlaybackState.GENERATING):
                return rec.owner == owner
        return True

    def get_playback_by_response(self, response_id: str) -> Optional[PlaybackRecord]:
        """Retrieve playback record for response_id if exists."""
        pid = self._by_response_id.get(response_id)
        return self._records.get(pid) if pid else None

    def get_playback(self, playback_id: str) -> Optional[PlaybackRecord]:
        """Retrieve playback record by playback_id."""
        return self._records.get(playback_id)

    def is_response_completed(self, response_id: str) -> bool:
        """Check if response has already been fully played."""
        return response_id in self._completed_response_ids


# Global Playback Coordinator singleton
playback_coordinator = PlaybackCoordinator()
