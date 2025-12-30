"""Feishu (Lark) webhook channel implementation."""

import hashlib
import hmac
import base64
import time
import logging
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo
import os

import httpx

from app.channels.base import BaseChannel
from app.models.alert import Alert, AlertGroup

logger = logging.getLogger(__name__)


class FeishuChannel(BaseChannel):
    """Feishu webhook bot channel."""

    def __init__(self, webhook_url: str, secret: str | None = None):
        self._webhook_url = webhook_url
        self._secret = secret or ""

    @property
    def name(self) -> str:
        return "feishu"

    @property
    def enabled(self) -> bool:
        return bool(self._webhook_url)

    def _generate_signature(self, timestamp: str) -> str:
        string_to_sign = f"{timestamp}\n{self._secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()
        return base64.b64encode(hmac_code).decode("utf-8")

    def _get_status_color(self, status: str) -> str:
        return "red" if status == "firing" else "green"

    def _format_alert_element(self, alert: Alert) -> list[dict[str, Any]]:
        elements: list[dict[str, Any]] = []

        status_emoji = "🔴" if alert.is_firing else "🟢"
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"{status_emoji} **{alert.name}**"},
        })

        if alert.summary:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**摘要:** {alert.summary}"},
            })

        if alert.description:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**详情:** {alert.description}"},
            })

        # Convert to local timezone
        local_tz = ZoneInfo(os.environ.get("TZ", "Asia/Shanghai"))
        starts_at = alert.starts_at
        if starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)
        local_time = starts_at.astimezone(local_tz)
        time_str = local_time.strftime("%Y-%m-%d %H:%M:%S")
        elements.append({
            "tag": "div",
            "text": {"tag": "lark_md", "content": f"**触发时间:** {time_str}"},
        })

        labels = {k: v for k, v in alert.labels.items() if k != "alertname"}
        if labels:
            label_str = " | ".join(f"`{k}={v}`" for k, v in labels.items())
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**标签:** {label_str}"},
            })

        if alert.generator_url:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"[查看详情]({alert.generator_url})"},
            })

        return elements

    def _build_card_message(self, alert_group: AlertGroup) -> dict[str, Any]:
        status = alert_group.status
        status_text = "告警触发" if status == "firing" else "告警恢复"
        status_emoji = "🚨" if status == "firing" else "✅"
        source_tag = f"[{alert_group.source.upper()}]"

        header = {
            "title": {"tag": "plain_text", "content": f"{status_emoji} {source_tag} {status_text}"},
            "template": self._get_status_color(status),
        }

        elements: list[dict[str, Any]] = []

        if alert_group.receiver:
            elements.append({
                "tag": "div",
                "text": {"tag": "lark_md", "content": f"**接收器:** {alert_group.receiver}"},
            })

        for i, alert in enumerate(alert_group.alerts):
            if i > 0:
                elements.append({"tag": "hr"})
            elements.extend(self._format_alert_element(alert))

        firing_count = len(alert_group.firing_alerts)
        resolved_count = len(alert_group.resolved_alerts)

        elements.append({"tag": "hr"})
        elements.append({
            "tag": "note",
            "elements": [{
                "tag": "plain_text",
                "content": f"来源: {alert_group.source} | 触发: {firing_count} | 恢复: {resolved_count}",
            }],
        })

        return {
            "msg_type": "interactive",
            "card": {"header": header, "elements": elements},
        }

    async def send(self, alert_group: AlertGroup) -> bool:
        message = self._build_card_message(alert_group)

        if self._secret:
            timestamp = str(int(time.time()))
            sign = self._generate_signature(timestamp)
            message["timestamp"] = timestamp
            message["sign"] = sign

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self._webhook_url, json=message)
            response.raise_for_status()

            result = response.json()
            if result.get("code") != 0:
                logger.error(f"Feishu API error: {result}")
                return False

            logger.info("Alert sent to Feishu successfully")
            return True

