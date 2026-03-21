"""In-process event bus for WebSocket broadcasting.

Provides sub-second latency for real-time UI updates (PixiJS character animations).
Prefect tasks emit events here, which are broadcast to all connected WebSocket clients.
"""

import asyncio
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine

import structlog

logger = structlog.get_logger()


class EventType(str, Enum):
    """Event types emitted by the pipeline."""

    # Collection events
    COLLECTION_STARTED = "collection.started"
    COLLECTION_PROGRESS = "collection.progress"
    COLLECTION_COMPLETED = "collection.completed"
    COLLECTION_FAILED = "collection.failed"

    # Analysis events
    ANALYSIS_STARTED = "analysis.started"
    ANALYSIS_PROGRESS = "analysis.progress"
    ANALYSIS_COMPLETED = "analysis.completed"

    # Forecast events
    FORECAST_STARTED = "forecast.started"
    FORECAST_PROGRESS = "forecast.progress"
    FORECAST_COMPLETED = "forecast.completed"

    # Report events
    REPORT_STARTED = "report.started"
    REPORT_PROGRESS = "report.progress"
    REPORT_COMPLETED = "report.completed"

    # Pipeline events
    PIPELINE_STARTED = "pipeline.started"
    PIPELINE_COMPLETED = "pipeline.completed"
    PIPELINE_FAILED = "pipeline.failed"

    # Agent events (for PixiJS character animation)
    AGENT_WORKING = "agent.working"
    AGENT_IDLE = "agent.idle"
    AGENT_THINKING = "agent.thinking"


@dataclass
class Event:
    """An event emitted by the pipeline."""

    type: EventType
    data: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
        }


# Async event handler type
EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """In-process async event bus.

    Supports:
    - Pub/sub with event type filtering
    - Broadcast to all subscribers
    - WebSocket integration via handlers
    """

    def __init__(self):
        self._handlers: dict[EventType, list[EventHandler]] = defaultdict(list)
        self._global_handlers: list[EventHandler] = []
        self._history: list[Event] = []
        self._max_history = 100
        self.log = logger.bind(component="event_bus")

    def subscribe(
        self,
        event_type: EventType,
        handler: EventHandler,
    ) -> None:
        """Subscribe to a specific event type."""
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to all events (used by WebSocket broadcaster)."""
        self._global_handlers.append(handler)

    def unsubscribe_all_handler(self, handler: EventHandler) -> None:
        """Remove a global handler."""
        self._global_handlers = [h for h in self._global_handlers if h is not handler]

    async def emit(
        self,
        event_type: EventType,
        data: dict[str, Any],
        source: str = "",
    ) -> None:
        """Emit an event to all matching subscribers."""
        event = Event(type=event_type, data=data, source=source)

        # Store in history
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        # Dispatch to type-specific handlers
        handlers = self._handlers.get(event_type, []) + self._global_handlers
        if handlers:
            await asyncio.gather(
                *(h(event) for h in handlers),
                return_exceptions=True,
            )

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent event history."""
        return [e.to_dict() for e in self._history[-limit:]]


# Global event bus instance
event_bus = EventBus()
