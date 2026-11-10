"""MATRIX Event Monitoring Engine.
Provides a central asynchronous Pub/Sub event bus for system events,
alerts, integration health shifts, mobile notifications, and task triggers.
"""
from typing import Dict, Any, List, Callable, Awaitable, Optional
import time
import asyncio
from pydantic import BaseModel, Field
from config.logging_config import get_logger

logger = get_logger("core.autonomy.event_monitor")


class MatrixEvent(BaseModel):
    event_id: str
    event_type: str  # SYSTEM_ALERT, INTEGRATION_SYNC, TASK_COMPLETED, CALL_EVENT, DEVICE_SYNC, SECURITY_ALERT
    source: str
    title: str
    message: str
    severity: str = "INFO"  # INFO, WARNING, ERROR, CRITICAL
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)
    acknowledged: bool = False


class EventMonitorEngine:
    """Coordinates event publishing, listener dispatch, and alert filtering."""

    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[MatrixEvent], Awaitable[None]]]] = {
            "*": []
        }
        self._recent_events: List[MatrixEvent] = []
        self._max_history = 100

    def subscribe(self, event_type: str, handler: Callable[[MatrixEvent], Awaitable[None]]):
        """Subscribe a callable async handler to a specific event type or '*'."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        if handler not in self._subscribers[event_type]:
            self._subscribers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[MatrixEvent], Awaitable[None]]):
        if event_type in self._subscribers and handler in self._subscribers[event_type]:
            self._subscribers[event_type].remove(handler)

    async def publish(
        self,
        event_type: str,
        title: str,
        message: str,
        source: str = "system",
        severity: str = "INFO",
        data: Optional[Dict[str, Any]] = None
    ) -> MatrixEvent:
        """Publish an event across all subscribed listeners."""
        import uuid
        event = MatrixEvent(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            event_type=event_type,
            source=source,
            title=title,
            message=message,
            severity=severity,
            data=data or {}
        )

        self._recent_events.append(event)
        if len(self._recent_events) > self._max_history:
            self._recent_events.pop(0)

        # Notify specific listeners + wildcard listeners
        handlers = self._subscribers.get(event_type, []) + self._subscribers.get("*", [])
        for handler in handlers:
            try:
                res = handler(event)
                if asyncio.iscoroutine(res):
                    asyncio.create_task(res)
            except Exception as e:
                logger.debug(f"Event handler error for {event_type}: {e}")

        # Check if severity is CRITICAL and trigger proactive notification
        if severity == "CRITICAL":
            logger.warning(f"CRITICAL Event Published: [{title}] {message}")

        return event

    def get_recent_events(
        self,
        limit: int = 30,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return formatted list of recent events."""
        events = self._recent_events
        if severity:
            events = [e for e in events if e.severity == severity]
        return [e.model_dump() for e in reversed(events[-limit:])]

    def acknowledge_event(self, event_id: str) -> bool:
        for e in self._recent_events:
            if e.event_id == event_id:
                e.acknowledged = True
                return True
        return False


# Global singleton
event_monitor = EventMonitorEngine()
