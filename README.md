# Signal Box

多来源 Webhook 转发服务，接收各种监控系统的报警并根据来源和标签路由到不同的通知渠道。

## 架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Grafana   │     │ Alertmanager│     │   Custom    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────┐
│                    Signal Box                        │
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
uv run signal-box
```

## 配置示例

```yaml
# routes.yaml
routes:
  # 只接收 Grafana 的后端项目报警
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
```

## API

| 端点 | 说明 |
|------|------|
| `GET /health` | 健康检查 |
| `GET /sources` | 已注册来源 |
| `GET /routes` | 路由配置 |
| `POST /webhook/grafana` | Grafana webhook |
| `POST /webhook/{source}` | 通用 webhook |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HOST` | `0.0.0.0` | 监听地址 |
| `PORT` | `5032` | 端口 |
| `LOG_LEVEL` | `INFO` | 日志级别 |
| `ROUTES_CONFIG` | `routes.yaml` | 配置文件路径 |

## 项目结构

```
signal_box/
├── app/
│   ├── main.py           # FastAPI 应用
│   ├── config.py         # 配置
│   ├── router.py         # 路由匹配
│   ├── models/
│   │   ├── alert.py      # 统一报警模型
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
