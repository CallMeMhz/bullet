"""Routing configuration models."""

from typing import Literal

from pydantic import BaseModel, Field


class RouteMatcher(BaseModel):
    """Route matching configuration."""

    source: str = Field(default="", description="Alert source to match (empty matches all)")
    labels: dict[str, str] = Field(default_factory=dict, description="Labels to match")

    def matches(self, source: str, labels: dict[str, str]) -> bool:
        if self.source and self.source != source:
            return False
        for key, value in self.labels.items():
            if labels.get(key) != value:
                return False
        return True


class ChannelConfig(BaseModel):
    """Channel configuration in a route."""

    type: Literal["feishu"]
    webhook_url: str
    secret: str = ""
    name: str = ""


class Route(BaseModel):
    """Single routing rule."""

    name: str = ""
    match: RouteMatcher = Field(default_factory=RouteMatcher)
    channels: list[ChannelConfig] = Field(default_factory=list)

    def matches(self, source: str, labels: dict[str, str]) -> bool:
        return self.match.matches(source, labels)


class RoutesConfig(BaseModel):
    """Complete routing configuration."""

    routes: list[Route] = Field(default_factory=list)

    def find_matching_route(self, source: str, labels: dict[str, str]) -> Route | None:
        for route in self.routes:
            if route.matches(source, labels):
                return route
        return None

