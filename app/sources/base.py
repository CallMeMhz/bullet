"""Base class for alert source parsers."""

from abc import ABC, abstractmethod
from typing import Any

from app.models.alert import AlertGroup


class BaseSource(ABC):
    """Abstract base class for alert source parsers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Source name identifier."""
        ...

    @abstractmethod
    def parse(self, payload: dict[str, Any]) -> AlertGroup:
        """Parse webhook payload into unified AlertGroup."""
        ...

