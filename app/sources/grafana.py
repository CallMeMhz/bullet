"""Grafana alerting webhook parser."""

from datetime import datetime
from typing import Any

from app.models.alert import Alert, AlertGroup
from app.sources.base import BaseSource


class GrafanaSource(BaseSource):
    """Parser for Grafana Unified Alerting webhooks."""

    @property
    def name(self) -> str:
        return "grafana"

    def parse(self, payload: dict[str, Any]) -> AlertGroup:
        alerts: list[Alert] = []

        for alert_data in payload.get("alerts", []):
            labels = alert_data.get("labels", {})
            annotations = alert_data.get("annotations", {})

            starts_at = self._parse_timestamp(alert_data.get("startsAt", ""))
            ends_at_str = alert_data.get("endsAt", "")
            ends_at = self._parse_timestamp(ends_at_str) if ends_at_str else None

            alert = Alert(
                source=self.name,
                status=alert_data.get("status", "firing"),
                name=labels.get("alertname", "Unknown"),
                severity=labels.get("severity", "warning"),
                summary=annotations.get("summary", ""),
                description=annotations.get("description", ""),
                labels=labels,
                annotations=annotations,
                starts_at=starts_at,
                ends_at=ends_at,
                generator_url=alert_data.get("generatorURL", ""),
                fingerprint=alert_data.get("fingerprint", ""),
                raw=alert_data,
            )
            alerts.append(alert)

        common_labels = payload.get("commonLabels", {})
        if not common_labels and alerts:
            common_labels = alerts[0].labels.copy()

        return AlertGroup(
            source=self.name,
            status=payload.get("status", "firing"),
            alerts=alerts,
            labels=common_labels,
            external_url=payload.get("externalURL", ""),
            receiver=payload.get("receiver", ""),
            raw=payload,
        )

    def _parse_timestamp(self, ts_str: str) -> datetime:
        if not ts_str:
            return datetime.now()
        ts_str = ts_str.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(ts_str)
        except ValueError:
            return datetime.now()

