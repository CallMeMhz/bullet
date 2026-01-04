"""Generic event envelope for routing and delivery.

Signal Box (Bullet) is a relay station: alerts are only one scenario.
All channels should accept and send a generic Event.
"""

from typing import Any

from pydantic import BaseModel, Field


class Event(BaseModel):
    """A generic event that can be routed and delivered to channels."""

    source: str = Field(default="", description="Event source, e.g. grafana/kline/custom")
    type: str = Field(default="", description="Event type, e.g. alert/kline/custom")
    labels: dict[str, str] = Field(default_factory=dict, description="Routing labels")
    payload: dict[str, Any] = Field(default_factory=dict, description="Arbitrary event payload")
    meta: dict[str, Any] = Field(default_factory=dict, description="Optional metadata")


