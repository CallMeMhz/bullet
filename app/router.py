"""Alert routing based on source and labels."""

import logging
from pathlib import Path

import yaml

from app.channels.base import BaseChannel
from app.channels.feishu import FeishuChannel
from app.models.alert import AlertGroup
from app.models.routes import ChannelConfig, Route, RoutesConfig

logger = logging.getLogger(__name__)


def load_routes_config(config_path: str | Path) -> RoutesConfig:
    """Load routing configuration from YAML file."""
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Routes config not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    return RoutesConfig.model_validate(data)


def create_channel_from_config(config: ChannelConfig) -> BaseChannel:
    """Create a channel instance from configuration."""
    if config.type == "feishu":
        return FeishuChannel(
            webhook_url=config.webhook_url,
            secret=config.secret or None,
        )
    else:
        raise ValueError(f"Unknown channel type: {config.type}")


class AlertRouter:
    """Routes alerts to appropriate channels based on source and labels."""

    def __init__(self, config: RoutesConfig):
        self._config = config
        self._route_channels: dict[str, list[BaseChannel]] = {}

        for i, route in enumerate(config.routes):
            route_key = route.name or f"route_{i}"
            self._route_channels[route_key] = [
                create_channel_from_config(ch_config)
                for ch_config in route.channels
            ]

        logger.info(f"Router initialized with {len(config.routes)} route(s)")

    @property
    def routes(self) -> list[Route]:
        return self._config.routes

    def find_route(self, alert_group: AlertGroup) -> tuple[Route | None, list[BaseChannel]]:
        """Find matching route and channels for alert group."""
        source = alert_group.source
        labels = alert_group.labels

        logger.debug(f"Matching source={source}, labels={labels}")

        for i, route in enumerate(self._config.routes):
            if route.matches(source, labels):
                route_key = route.name or f"route_{i}"
                channels = self._route_channels.get(route_key, [])
                logger.info(f"Matched route '{route_key}' with {len(channels)} channel(s)")
                return route, channels

        logger.info("No matching route found, alert will be discarded")
        return None, []

    async def route_alert(self, alert_group: AlertGroup) -> dict[str, bool]:
        """Route alert group to matching channels."""
        route, channels = self.find_route(alert_group)

        if not route or not channels:
            return {}

        results: dict[str, bool] = {}
        for channel in channels:
            success = await channel.send_safe(alert_group)
            results[channel.name] = success

            if success:
                logger.info(f"Alert sent to {channel.name}")
            else:
                logger.error(f"Failed to send alert to {channel.name}")

        return results

