"""Base class for notification channels."""

import logging
from abc import ABC, abstractmethod

from app.models.event import Event

logger = logging.getLogger(__name__)


class BaseChannel(ABC):
    """Abstract base class for notification channels."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Channel name for logging."""
        ...

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether the channel is enabled."""
        ...

    @abstractmethod
    async def send(self, event: Event) -> bool:
        """Send an event to the channel."""
        ...

    async def send_safe(self, event: Event) -> bool:
        """Send event with error handling."""
        if not self.enabled:
            return False
        try:
            return await self.send(event)
        except Exception as e:
            logger.exception(f"Failed to send to channel {self.name}: {e}")
            return False

