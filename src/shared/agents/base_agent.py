"""Base agent interface for all AI Data Science Team agents.

All agents inherit from BaseAgent and implement the execute() method.
Provides structured logging, event bus integration, and unified result format.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import structlog

from src.shared.utils.event_bus import EventType, event_bus


class AgentStatus(str, Enum):
    """Execution result status."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass
class AgentResult:
    """Standard result container returned by all agents."""

    status: str  # "success", "partial", "failed"
    data: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "data": self.data,
            "errors": self.errors,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


class BaseAgent(ABC):
    """Abstract base class for all pipeline agents.

    Subclasses must implement:
        - data_sources: list[str] property
        - execute(**kwargs) -> AgentResult
    """

    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.log = structlog.get_logger().bind(agent=name, role=role)

    @property
    @abstractmethod
    def data_sources(self) -> list[str]:
        """List of data source identifiers this agent handles."""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> AgentResult:
        """Run the agent's main workload.

        Returns:
            AgentResult with status, data, and any errors.
        """
        ...

    # ------------------------------------------------------------------
    # Helpers available to all agents
    # ------------------------------------------------------------------

    async def emit(
        self,
        event_type: EventType,
        data: dict[str, Any],
    ) -> None:
        """Emit an event through the global event bus."""
        await event_bus.emit(event_type, data, source=self.name)

    async def run_safe(
        self,
        coro: Any,
        label: str,
    ) -> tuple[Any, str | None]:
        """Execute a coroutine and capture exceptions instead of propagating.

        Returns:
            (result, None) on success or (None, error_message) on failure.
        """
        try:
            result = await coro
            return result, None
        except Exception as exc:
            error_msg = f"{label}: {exc}"
            self.log.error("task_failed", label=label, error=str(exc))
            return None, error_msg
