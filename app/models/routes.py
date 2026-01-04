"""Routing configuration models."""

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, field_validator


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


class FeishuChannelConfig(BaseModel):
    """Feishu webhook channel configuration."""

    type: Literal["feishu"]
    webhook_url: str
    secret: str = ""
    name: str = ""


class ResendEmailChannelConfig(BaseModel):
    """Resend email channel configuration.

    Notes:
    - Prefer passing the API key via environment variable `RESEND_API_KEY`.
    - `from` is supported as a YAML key (aliased to `from_email`).
    """

    type: Literal["resend_email"]
    to: list[str] = Field(default_factory=list, description="Recipient email(s)")
    from_email: str = Field(
        default="",
        validation_alias="from",
        serialization_alias="from",
        description="Sender email, e.g. 'Acme <onboarding@resend.dev>'",
    )
    subject_prefix: str = ""
    subject_template: str = Field(
        default="",
        description="Optional Jinja subject template, rendered with the same context as the HTML template",
    )
    template_path: str = Field(
        default="",
        description="Optional Jinja HTML template path (absolute or relative to working dir). Default uses built-in template.",
    )
    reply_to: str = ""
    api_key: str = Field(default="", description="Resend API key (optional, can use env RESEND_API_KEY)")
    name: str = ""

    @field_validator("to", mode="before")
    @classmethod
    def _coerce_to_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v]
        return v


ChannelConfig = Annotated[
    Union[FeishuChannelConfig, ResendEmailChannelConfig],
    Field(discriminator="type"),
]


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

