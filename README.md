# Bullet

多来源 Webhook 转发服务（中转站），接收各种来源的事件并根据来源和标签路由到不同的通知渠道。**报警只是其中一种应用场景**。

## 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Grafana   │     │ Alertmanager│     │   Custom    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────┐
│                      Bullet                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐              │
│  │ Grafana │  │Alertmgr │  │ Generic │  Sources     │
│  │ Parser  │  │ Parser  │  │ Parser  │              │
│  └────┬────┘  └────┬────┘  └────┬────┘              │
│       └────────────┼───────────┘                    │
│                    ▼                                 │
│              ┌──────────┐                           │
│              │  Router  │  Match: source + labels   │
│              └────┬─────┘                           │
│                   │                                  │
│       ┌───────────┼───────────┐                     │
│       ▼           ▼           ▼                     │
│  ┌────────┐  ┌────────┐  ┌────────┐                │
│  │ Feishu │  │DingTalk│  │ Slack  │  Channels      │
│  └────────┘  └────────┘  └────────┘                │
└──────────────────────────────────────────────────────┘
```

## 快速开始

```bash
# 安装
uv sync

# 配置路由
cp routes.yaml.example routes.yaml
vim routes.yaml

# 启动
uv run bullet
```

## 配置示例

```yaml
# routes.yaml
routes:
  # 只接收 Grafana 的后端项目事件（其中 alert 是一种 event）
  - name: "grafana-backend"
    match:
      source: grafana
      labels:
        project: "backend"
    channels:
      - type: feishu
        webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"

  # 兜底
  - name: "default"
    match: {}
    channels:
      - type: feishu
        webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/yyy"

  # 严重告警同时发邮件（Resend）
  - name: "critical-email"
    match:
      labels:
        severity: "critical"
    channels:
      - type: resend_email
        from: "Bullet <noreply@your-domain.com>"
        to:
          - "oncall@your-domain.com"
        subject_prefix: "[SRE] "
        # 可选：自定义邮件模板（Jinja2），不填则使用内置默认模板
        # template_path: "/abs/path/to/resend_email.html.j2"
        # 可选：自定义 subject 模板（Jinja2 from_string）
        # subject_template: "[{{ event.source|upper }}] {{ event.type }}"
```

## API

| 端点 | 说明 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /sources` | 已注册来源 |
| `GET /routes` | 路由配置 |
| `POST /webhook/grafana` | Grafana webhook |
| `POST /webhook/{source}` | 通用 webhook |

说明：目前对外仍以 webhook 形式接入；内部会把解析后的数据封装成 `Event` 再投递给各个 channel。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `5032` | 端口 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `ROUTES_CONFIG` | `routes.yaml` | 配置文件路径 |
| `RESEND_API_KEY` | `""` | Resend API Key（用于 `resend_email` 渠道） |
| `RESEND_FROM_EMAIL` | `""` | Resend 发件人（用于 `resend_email` 渠道，可被 routes.yaml 的 `from` 覆盖） |
| `RESEND_API_URL` | `https://api.resend.com/emails` | Resend 发送接口地址（一般不需要改） |

## 项目结构

```
bullet/
├── app/
│   ├── main.py           # FastAPI 应用
│   ├── config.py         # 配置
│   ├── router.py         # 路由匹配
│   ├── models/
│   │   ├── alert.py      # 统一报警模型
│   │   ├── event.py      # 统一事件模型（报警只是其中一种）
│   │   └── routes.py     # 路由配置模型
│   ├── sources/
│   │   ├── base.py       # 来源解析器基类
│   │   └── grafana.py    # Grafana 解析器
│   └── channels/
│       ├── base.py       # 渠道基类
│       └── feishu.py     # 飞书渠道
├── routes.yaml
└── pyproject.toml
```

## License

MIT
